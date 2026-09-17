import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS
from filter.profile_filter import detect_vacancy_grade

def validate_job_understanding(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that a job understanding result strictly adheres to the schema
    and maintains the Fact vs Hypothesis separation.
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Job understanding must be a dict"]

    # 1. Check role overview
    overview = data.get("role_overview")
    if not isinstance(overview, dict):
        errors.append("Missing or invalid 'role_overview' object")
    else:
        if not overview.get("title"):
            errors.append("Role overview missing 'title'")

    # 2. Check facts (Verifiable facts from job text)
    facts = data.get("facts")
    if not isinstance(facts, dict):
        errors.append("Missing or invalid 'facts' object")
    else:
        for f_key in ["explicit_requirements", "responsibilities"]:
            if not isinstance(facts.get(f_key), list):
                errors.append(f"Facts missing list for '{f_key}'")

    # 3. Check reasoning (Inferred hypotheses & signals)
    reasoning = data.get("reasoning")
    if not isinstance(reasoning, dict):
        errors.append("Missing or invalid 'reasoning' object")
    else:
        for r_key in ["implicit_requirements", "likely_team_problems", "hiring_priorities", "risks", "unknowns"]:
            if not isinstance(reasoning.get(r_key), list):
                errors.append(f"Reasoning missing list for '{r_key}'")

    # 4. Check boilerplate separation
    bp = data.get("boilerplate_vs_signal")
    if not isinstance(bp, dict):
        errors.append("Missing or invalid 'boilerplate_vs_signal' object")

    return len(errors) == 0, errors


def heuristic_job_understanding(title: str, description: str, company: str = "Company") -> Dict[str, Any]:
    """
    Offline heuristic analyzer providing structured job understanding
    when LLM inference is disabled or offline.
    """
    desc_lower = description.lower()
    seniority = detect_vacancy_grade(title, description)

    # Extract explicit requirements
    explicit_reqs = []
    known_tech = [
        "React", "Next.js", "TypeScript", "JavaScript", "HTML5", "CSS3", "Tailwind CSS",
        "Redux", "Zustand", "FastAPI", "Node.js", "Python", "PostgreSQL", "Docker",
        "Git", "CI/CD", "REST API", "GraphQL", "Vitest", "Jest", "Playwright"
    ]
    for tech in known_tech:
        if re.search(r'\b' + re.escape(tech.lower()) + r'\b', desc_lower):
            explicit_reqs.append(tech)

    # Extract stated constraints
    constraints = []
    if any(k in desc_lower for k in ["только ип", "самозанятость", "b2b"]):
        constraints.append("B2B / Самозанятость контракт")
    if any(k in desc_lower for k in ["english", "английск", "c1", "c2", "fluent", "b2"]):
        constraints.append("Требование к уровню английского языка")
    if any(k in desc_lower for k in ["удален", "remote", "дистанцион"]):
        constraints.append("Удаленный формат работы")

    # Infer team problems & hypotheses from signals
    problems = []
    signals = []
    if any(k in desc_lower for k in ["legacy", "легаси", "рефакторинг", "переезд", "миграция", "migration"]):
        signals.append("Упоминание миграции / рефакторинга устаревшего стека")
        problems.append("Необходимость модернизировать legacy-код без остановки продуктовой разработки")

    if any(k in desc_lower for k in ["performance", "скорост", "оптимиз", "быстродейств", "pagespeed"]):
        signals.append("Акцент на скорости работы приложения и метриках")
        problems.append("Проблемы с производительностью, долгим LCP или тяжелым JS-бандлом")

    if any(k in desc_lower for k in ["design system", "дизайн-систем", "ui kit", "ui-kit", "компонент"]):
        signals.append("Фокус на переиспользуемых интерфейсных компонентах")
        problems.append("Фрагментация UI, отсутствие единой дизайн-системы между командами")

    if not problems:
        problems.append("Потребность в автономном инженере, способном доводить фичи от постановки до продакшна")

    # Implicit requirements
    implicit_reqs = [
        "Умение работать без микроменеджмента и принимать обоснованные архитектурные решения",
        "Инженерная прагматичность: баланс между скоростью поставки и качеством кода"
    ]

    hiring_priorities = [
        "Практический опыт решения аналогичных задач в продакшне",
        "Предсказуемость сроков и самостоятельность"
    ]

    risks = []
    if "тестовое задание" in desc_lower:
        risks.append("Наличие объемного тестового задания на раннем этапе воронки")
    if any(k in desc_lower for k in ["ненормированный", "овертайм", "аврал", "crunch"]):
        risks.append("Риск переработок и размытых зон ответственности")

    unknowns = [
        "Точный размер и распределение ролей в текущей инженерной команде",
        "Степень зрелости backend API контрактов и документации"
    ]

    return {
        "role_overview": {
            "title": title or "Software Engineer",
            "company": company or "Direct Employer",
            "seniority": seniority,
            "domain": "Web / SaaS",
            "work_format": "Remote" if "remote" in desc_lower or "удален" in desc_lower else "Flexible"
        },
        "facts": {
            "explicit_requirements": explicit_reqs if explicit_reqs else ["Web Development", "Frontend"],
            "responsibilities": [
                line.strip().lstrip('•-–* ')
                for line in description.split('\n')
                if any(w in line.lower() for w in ["разработ", "участ", "создан", "develop", "build", "lead"])
            ][:4] or ["Разработка и поддержка ключевых фич приложения"],
            "stated_constraints": constraints
        },
        "reasoning": {
            "implicit_requirements": implicit_reqs,
            "engineering_signals": signals if signals else ["Стандартный продуктовый цикл разработки"],
            "likely_team_problems": problems,
            "hiring_priorities": hiring_priorities,
            "risks": risks if risks else ["Требуется уточнение процессов тестирования на интервью"],
            "unknowns": unknowns
        },
        "boilerplate_vs_signal": {
            "boilerplate": ["Дружный коллектив", "Динамичная атмосфера", "Конкурентная зарплата"],
            "high_signal": explicit_reqs[:5]
        }
    }


def understand_job_posting(
    title: str,
    description: str,
    company: str = "Company",
    source_url: str = ""
) -> Dict[str, Any]:
    """
    Uses Gemini LLM to deeply reason about the job posting, separating
    verifiable facts from analytical hypotheses and team problems.
    Falls back gracefully to heuristic_job_understanding on failure.
    """
    api_key = get_api_key()
    if not api_key:
        return heuristic_job_understanding(title, description, company)

    prompt = f"""You are a Principal Software Architect and Strategic Technical Recruiter.
Analyze this job posting deeply. DO NOT simply summarize keywords or repeat boilerplate.
You must REASON about what this engineering team is actually dealing with and strictly separate VERIFIED FACTS from REASONING HYPOTHESES.

Job Title: {title}
Company: {company}
Posting Text:
\"\"\"{description[:5500]}\"\"\"

Output STRICT JSON matching this schema:
{{
  "role_overview": {{
    "title": "Normalized job title",
    "company": "{company}",
    "seniority": "Junior | Middle | Senior | Lead | Principal",
    "domain": "e.g. Fintech, B2B SaaS, E-Commerce, DevTools, etc.",
    "work_format": "Remote | Hybrid | Onsite"
  }},
  "facts": {{
    "explicit_requirements": ["Verifiable hard requirements directly stated in text (technologies, years, degrees)"],
    "responsibilities": ["Explicit engineering duties directly stated in text"],
    "stated_constraints": ["Explicit contractual or legal constraints stated, e.g. B2B only, timezone, citizenship"]
  }},
  "reasoning": {{
    "implicit_requirements": ["Unspoken capabilities required by the nature of the role (e.g. autonomy, migration endurance)"],
    "engineering_signals": ["Clues in wording indicating codebase maturity, technical debt, or team culture"],
    "likely_team_problems": ["What bottlenecks or pain points is this team actually trying to solve by hiring this person?"],
    "hiring_priorities": ["What will the hiring manager value most when evaluating applicants?"],
    "risks": ["Potential red flags, scope creep, or engineering risks for a candidate"],
    "unknowns": ["What critical details are left unstated in the description?"]
  }},
  "boilerplate_vs_signal": {{
    "boilerplate": ["Generic HR buzzwords present in text (e.g. 'fast-paced environment', 'friendly team')"],
    "high_signal": ["High-value specific technical requirements or domain specifics"]
  }}
}}

Rules:
1. NEVER confuse a Fact with a Hypothesis. (Fact = directly written in text. Hypothesis = your engineering deduction).
2. If text mentions legacy migration, infer the team likely suffers from slowdowns or regression fears.
3. If text is in Russian, formulate reasoning in Russian. If English, in English.
4. Output ONLY valid JSON, without any markdown formatting or commentary.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    models_to_try = GEMINI_MODELS[:]
    for model in models_to_try:
        model_path = model if model.startswith("models/") else f"models/{model}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key
                }
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                resp_text = response.read().decode('utf-8')
                resp_data = json.loads(resp_text)
                text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text).strip()
                parsed = json.loads(text)
                valid, errors = validate_job_understanding(parsed)
                if valid:
                    return parsed
                else:
                    print(f"  [job_understanding] Validation warning for model {model}: {errors}")
        except Exception as e:
            print(f"  [job_understanding] Model {model} failed: {e}")

    # Fallback to heuristic
    return heuristic_job_understanding(title, description, company)
