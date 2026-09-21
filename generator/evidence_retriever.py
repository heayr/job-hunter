import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS


# ── DYNAMIC ACHIEVEMENT MATCHING ENGINE ───────────────────────────────────────

def _score_achievement(achievement: Dict, job_text: str, lang: str = "ru") -> int:
    """Score an achievement against job requirements based on tag overlap and keyword density."""
    score = 0
    tags = achievement.get("tags", [])
    techs = [t.lower() for t in achievement.get("technologies", [])]
    job_lower = job_text.lower()

    # Tag matching — core signal
    tag_keywords = {
        "performance": ["performance", "pagespeed", "core web vitals", "lcp", "cls", "speed", "скорост", "оптимиз", "быстр", "производительн"],
        "fullstack": ["fullstack", "full-stack", "backend", "бэкенд", "api", "fastapi", "node", "postgres", "sql", "фуллстек"],
        "delivery": ["hackathon", "хакатон", "deadline", "дедлайн", "velocity", "скорость", "mvp", "стартап", "быстр", "sprint", "спринт"],
        "infrastructure": ["docker", "infrastructure", "инфраструктур", "devops", "deploy", "деплой", "traefik", "ci/cd", "kubernetes"],
        "design_system": ["component", "компонент", "design system", "дизайн-систем", "figma", "ui kit", "ui-kit", "animation", "анимац", "gsap", "motion"],
        "security": ["auth", "авториз", "rbac", "security", "безопасн", "session", "cookie", "cms", "админ"],
        "automation": ["automation", "автоматиз", "bot", "бот", "telegram", "integration", "интеграц"],
    }

    for tag in tags:
        if tag in tag_keywords:
            for kw in tag_keywords[tag]:
                if kw in job_lower:
                    score += 15
                    break

    # Technology matching — secondary signal
    for tech in techs:
        if tech in job_lower:
            score += 10

    # Defensibility bonus — HIGH defensibility = stronger claim
    if achievement.get("defensibility") == "HIGH":
        score += 5

    # Metric specificity bonus — concrete numbers > vague claims
    metric = achievement.get("metric", "")
    if re.search(r'\d+', metric):
        score += 8

    return score


def _reframe_achievement(achievement: Dict, job_text: str, lang: str = "ru") -> str:
    """Reframe an achievement into a high-impact bullet point tailored to the job."""
    problem = achievement.get("problem", "")
    action = achievement.get("action", "")
    result = achievement.get("result", "")
    metric = achievement.get("metric", "")
    metric_unit = achievement.get("metric_unit", "")
    techs = achievement.get("technologies", [])

    tech_str = ", ".join(techs[:3]) if techs else ""

    if lang == "ru":
        # Pick the strongest framing based on what the job needs
        if metric and metric_unit:
            return f"{metric} {metric_unit}: {action.lower().rstrip('.')}. Технологии: {tech_str}." if tech_str else f"{metric} {metric_unit}: {action.lower().rstrip('.')}."
        elif result:
            return f"{result}. Технологии: {tech_str}." if tech_str else f"{result}."
        else:
            return f"{action}. Технологии: {tech_str}." if tech_str else f"{action}."
    else:
        if metric and metric_unit:
            return f"{metric} {metric_unit}: {action.lower().rstrip('.')}. Stack: {tech_str}." if tech_str else f"{metric} {metric_unit}: {action.lower().rstrip('.')}."
        elif result:
            return f"{result}. Stack: {tech_str}." if tech_str else f"{result}."
        else:
            return f"{action}. Stack: {tech_str}." if tech_str else f"{action}."


def heuristic_evidence_retrieval(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Dynamic achievement matcher: pulls from profile's key_achievements,
    scores them against job requirements, returns top 3 reframed bullets.
    """
    # Build job context text
    facts = job_understanding.get("facts", {})
    reasoning = job_understanding.get("reasoning", {})
    overview = job_understanding.get("role_overview", {})

    job_text = " ".join([
        overview.get("title", ""),
        " ".join(facts.get("explicit_requirements", [])),
        " ".join(facts.get("responsibilities", [])),
        " ".join(reasoning.get("likely_team_problems", [])),
        " ".join(reasoning.get("engineering_signals", []))
    ])

    # Get achievements from profile
    achievements = profile.get("key_achievements", [])

    if achievements:
        # Score and sort achievements by relevance to this specific job
        scored = []
        for ach in achievements:
            s = _score_achievement(ach, job_text, lang=lang)
            scored.append((s, ach))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Take top 3 and reframe them
        matched_evidence = []
        for _, ach in scored[:3]:
            reframed = _reframe_achievement(ach, job_text, lang=lang)
            matched_evidence.append({
                "job_pain_point": ach.get("problem", ""),
                "candidate_claim": ach.get("result", ""),
                "aggressive_framing": reframed,
                "seniority_signal": "Senior / Lead Engineer",
                "interview_defensibility": ach.get("defensibility", "HIGH"),
                "source_achievement_id": ach.get("id", "")
            })
    else:
        # Fallback to legacy presets if no key_achievements defined
        matched_evidence = _fallback_preset_matching(job_text, lang=lang)

    # Strategic narrative
    if lang == "ru":
        positioning = "Senior / Lead Product Engineer со сквозным владением (End-to-End Ownership): от архитектуры интерфейса и дизайн-системы до серверных API и деплоя в Docker"
        leverage_points = [
            "Автономность: способность в одиночку закрывать модули и фичи под ключ",
            "Реальный опыт оптимизации производительности до 100/100 PageSpeed",
            "Высокая скорость поставки, доказанная на хакатонах и в коммерческих проектах"
        ]
    else:
        positioning = "Senior / Lead Product Engineer with End-to-End Ownership: from UI architecture to backend APIs and Docker deployments"
        leverage_points = [
            "Complete autonomy: takes features from Figma to production without micro-management",
            "Proven performance benchmark: achieved 100/100 Core Web Vitals on Next.js 16",
            "High shipping velocity: proven hackathon winner and commercial SaaS delivery"
        ]

    return {
        "matched_evidence": matched_evidence,
        "strategic_narrative": {
            "positioning_angle": positioning,
            "leverage_points": leverage_points,
            "defensive_pivots": [
                "Focus on deep React/TypeScript fundamentals that transfer to any stack"
            ]
        }
    }


def _fallback_preset_matching(job_text: str, lang: str = "ru") -> List[Dict]:
    """Legacy fallback when no key_achievements are defined."""
    # Minimal hardcoded presets as safety net
    presets = {
        "performance": {
            "pattern": r'(?:performance|pagespeed|core web vitals|lcp|cls|speed|скорост|оптимиз)',
            "framing_ru": "Оптимизация Core Web Vitals до 100/100 на Next.js 16 (App Router) за счет RSC, SSR-стриминга и code splitting.",
            "framing_en": "Achieved 100/100 PageSpeed on Next.js 16 via RSC streaming, bundle splitting, and zero-bloat state architecture."
        },
        "fullstack": {
            "pattern": r'(?:fullstack|backend|fastapi|python|node|postgres|sql|docker|api)',
            "framing_ru": "Сквозная разработка: REST API на FastAPI/Node.js, PostgreSQL, multi-stage Docker с Traefik v3 и авто-TLS.",
            "framing_en": "End-to-End ownership: REST APIs with FastAPI/Node.js, PostgreSQL, multi-stage Docker with Traefik v3 auto-TLS."
        },
        "delivery": {
            "pattern": r'(?:hackathon|velocity|deadline|мvp|стартап|хакатон|дедлайн)',
            "framing_ru": "1 место на хакатоне Droog: 3 ролевых интерфейса за 48 часов в условиях жесткого дедлайна.",
            "framing_en": "1st place at Droog Hackathon: shipped 3 role-based interfaces in 48 hours under strict deadline."
        },
    }

    matched = []
    for key, preset in presets.items():
        if re.search(preset["pattern"], job_text, re.I):
            framing = preset[f"framing_{lang}"]
            matched.append({
                "job_pain_point": f"Requires {key} expertise",
                "candidate_claim": framing,
                "aggressive_framing": framing,
                "seniority_signal": "Senior Engineer",
                "interview_defensibility": "HIGH"
            })

    return matched[:3]


def retrieve_and_reframe_evidence(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Synthesizes candidate profile evidence and job understanding into an
    aggressive, highly defensible engineering positioning package.
    Uses Gemini if available; falls back smoothly to heuristic reframing.
    """
    api_key = get_api_key()
    if not api_key:
        return heuristic_evidence_retrieval(profile, job_understanding, lang)

    # Extract core facts
    candidate_name = profile.get("name") or profile.get("identity", {}).get("name", "Candidate")
    target_role = profile.get("role") or profile.get("identity", {}).get("target_role", "Senior Engineer")
    raw_exp = profile.get("experience", "")[:2000]
    key_achievements = profile.get("key_achievements", [])

    job_title = job_understanding.get("role_overview", {}).get("title", "Engineer")
    company = job_understanding.get("role_overview", {}).get("company", "Company")
    problems = job_understanding.get("reasoning", {}).get("likely_team_problems", [])
    signals = job_understanding.get("reasoning", {}).get("engineering_signals", [])
    explicit_reqs = job_understanding.get("facts", {}).get("explicit_requirements", [])

    language_name = "Russian" if lang == "ru" else "English"

    achievements_text = ""
    if key_achievements:
        achievements_list = []
        for ach in key_achievements:
            achievements_list.append(
                f"- [{ach.get('category', 'general')}] {ach.get('metric', '')} {ach.get('metric_unit', '')}: "
                f"{ach.get('action', '')} | Result: {ach.get('result', '')} | "
                f"Tech: {', '.join(ach.get('technologies', []))} | "
                f"Tags: {', '.join(ach.get('tags', []))}"
            )
        achievements_text = "\n".join(achievements_list)

    prompt = f"""You are a Strategic Career Agent representing {candidate_name} ({target_role}).
Your job is to build an AGGRESSIVE, HIGH-STATUS engineering positioning package connecting this company's hidden pain points to the candidate's real capabilities.

CRITICAL INSTRUCTIONS:
1. NO ACADEMIC TIMIDITY: Frame the candidate as a decisive Senior / Lead Product Engineer who owns features end-to-end (Figma -> Client Architecture -> API Contracts -> Docker/Production).
2. REAL CAPABILITY ANCHORING: Every claim must be defensible in an interview.
3. STRICT NO FOUNDER / NO PET-PROJECT MARKERS: Never mention being a 'founder', 'owner', or 'pet project'. Frame all SaaS work as Lead Engineer roles.
4. DYNAMIC ACHIEVEMENT MATCHING: Select the 2-3 most relevant achievements from the candidate's key_achievements below that directly address this specific job's requirements. Do NOT use achievements that are irrelevant to the role.
5. ATS KEYWORD OPTIMIZATION: Ensure the reframed bullets contain the exact technologies and keywords mentioned in the job requirements.

CANDIDATE KEY ACHIEVEMENTS (select the most relevant 2-3 for this specific job):
{achievements_text}

CANDIDATE EXPERIENCE:
{raw_exp}

JOB CONTEXT ({company} — {job_title}):
- Team Pains: {json.dumps(problems, ensure_ascii=False)}
- Engineering Signals: {json.dumps(signals, ensure_ascii=False)}
- Hard Requirements: {json.dumps(explicit_reqs, ensure_ascii=False)}

LANGUAGE: {language_name}

Respond ONLY with valid JSON in this exact structure:
{{
  "matched_evidence": [
    {{
      "job_pain_point": "The specific bottleneck this company has",
      "candidate_claim": "The specific achievement addressing it",
      "aggressive_framing": "High-impact bullet point with concrete metrics, tailored to this job's keywords",
      "seniority_signal": "Lead / Senior Architect",
      "interview_defensibility": "HIGH (can discuss X, Y, Z in depth)"
    }}
  ],
  "strategic_narrative": {{
    "positioning_angle": "Core positioning angle for THIS specific role",
    "leverage_points": ["Point 1 matching job requirements", "Point 2", "Point 3"],
    "defensive_pivots": ["Pivot for interview"]
  }}
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
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
                if "matched_evidence" in parsed and "strategic_narrative" in parsed:
                    return parsed
        except Exception as e:
            print(f"  [evidence_retriever] Model {model} attempt failed: {e}")

    # Fallback if Gemini fails
    return heuristic_evidence_retrieval(profile, job_understanding, lang)
