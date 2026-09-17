import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS

def validate_application_strategy(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that an Application Strategy strictly adheres to the required schema:
    - positioning_archetype
    - narrative_tone
    - highlight_priorities (list)
    - deliberate_omissions (list of filtered-out distractions)
    - tailored_artifacts_required (dict with tailored_cv, custom_cover_letter, short_dm)
    - screening_questions_guidance (list)
    - strategic_thesis_refinement
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Strategy data must be a dictionary"]

    for str_key in ["positioning_archetype", "narrative_tone", "strategic_thesis_refinement"]:
        val = data.get(str_key)
        if not val or not isinstance(val, str) or len(val.strip()) < 5:
            errors.append(f"Missing or invalid string for '{str_key}'")

    for list_key in ["highlight_priorities", "deliberate_omissions", "screening_questions_guidance"]:
        val = data.get(list_key)
        if not isinstance(val, list) or len(val) == 0:
            errors.append(f"Missing or empty list for '{list_key}'")

    artifacts = data.get("tailored_artifacts_required")
    if not isinstance(artifacts, dict):
        errors.append("Missing or invalid 'tailored_artifacts_required' dict")
    else:
        for k in ["tailored_cv", "custom_cover_letter", "short_dm"]:
            if k not in artifacts:
                errors.append(f"'tailored_artifacts_required' missing '{k}' boolean")

    return len(errors) == 0, errors


def heuristic_application_strategy(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    company_dossier: Dict[str, Any],
    thesis_data: Dict[str, Any],
    lang: str = "ru",
    seniority_alignment: bool = True,
    highload_guardrail: bool = True
) -> Dict[str, Any]:
    """
    Deterministic offline strategy planner synthesizing job pains, company context,
    and the approved thesis into an executable application strategy plan.

    Features:
    - seniority_alignment (toggleable): Calibrates archetype to match vacancy seniority (e.g. Middle vs Senior/Lead),
      preventing 'overqualified' rejections.
    - highload_guardrail (toggleable): Keeps focus strictly on verifiable Client-Side Performance & Clean Architecture,
      preventing hallucinated distributed backend highload promises that fail at interviews.
    """
    overview = job_understanding.get("role_overview", {})
    job_title = overview.get("title", "Frontend Engineer")
    target_seniority = overview.get("seniority", "Senior")
    company = overview.get("company", "Company")

    # Determine calibrated seniority
    if seniority_alignment:
        # If target vacancy is explicitly Middle or Junior, do NOT scream "Lead"
        if target_seniority.lower() in ("middle", "мидл", "junior", "младший", "intern", "стажер"):
            seniority = target_seniority.capitalize()
            role_label = "Frontend / Fullstack Developer"
        else:
            seniority = "Senior"
            role_label = "Senior Product Engineer"
    else:
        seniority = target_seniority or "Lead"
        role_label = "Lead / Senior Product Engineer"

    thesis = thesis_data.get("thesis", "")

    # Base omissions (Strict rule: eliminate founder/pet-project traps and distracting tech)
    if lang == "ru":
        omissions = [
            "Категорически исключить упоминания 'фаундер', 'основатель', 'мой стартап' или 'владелец' (позиционировать проекты NoLogs и Radiotochka исключительно как роли Lead Frontend / Product Engineer).",
            "Исключить упоминания непрофильного бэкенда или дата-сайнс библиотек, чтобы не выглядеть расфокусированным универсалом.",
            "Не упоминать устаревшие технологии (jQuery, Bitrix, WordPress)."
        ]
        if highload_guardrail:
            omissions.append("Не обещать опыт распределенного бэкенд-хайлоада (шардирование, кафка-кластеры); фокусироваться на клиентской производительности и надежном API.")

        if seniority.lower() in ("middle", "junior"):
            archetype = f"Самостоятельный {seniority} {role_label} с фокусом на надёжную реализацию задач"
            tone = "Исполнительный, технически грамотный, вовлечённый (без лишнего пафоса и споров о процессах)"
            guidance = [
                "При вопросе о роли: подчеркивать самостоятельность в закрытии задач по ТЗ и качественное покрытие тестами.",
                "При вопросе о дате выхода: готовность оперативно включиться в спринт.",
                "При вопросе о стеке: подтверждать уверенное владение React 19 / TypeScript и быстрое погружение в кодовую базу."
            ]
        else:
            archetype = f"Автономный {seniority} {role_label} со сквозным владением (End-to-End Ownership)"
            tone = "Партнерский, уверенный, инженерно-прагматичный (без заискиваний и водянистых формулировок)"
            guidance = [
                "При вопросе о зарплате: указывать рыночную планку с учетом сеньорного скоупа ответственности и автономности.",
                "При вопросе о дате выхода: готовность начать через 1-2 недели или сразу после согласования оффера.",
                "При вопросе о стеке: подтверждать глубокую экспертизу в React 19 / TypeScript и способность быстро адаптировать смежные инструменты."
            ]

        highlights = [
            "Next.js 16 (App Router), React 19 и оптимизация Core Web Vitals до 100/100",
            "Дизайн-системы и модульные компоненты из Figma (Cloveri для Минцифры)",
            "Сквозная поставка фич: от архитектуры UI до FastAPI API контрактов и Docker"
        ]
    else:
        omissions = [
            "Strictly avoid terms like 'founder', 'creator', 'owner', or 'my startup' (frame SaaS platforms purely as Lead Frontend / Product Engineer roles).",
            "Omit irrelevant backend or data science references to maintain a laser-sharp engineering focus.",
            "Omit legacy CMS technologies (WordPress, Bitrix, jQuery)."
        ]
        if highload_guardrail:
            omissions.append("Avoid claiming unverified distributed backend highload (sharded Cassandra, multi-cluster Kafka); anchor firmly to Client Performance & Clean Architecture.")

        if seniority.lower() in ("middle", "junior"):
            archetype = f"Autonomous {seniority} {role_label} focused on delivery and clean execution"
            tone = "Pragmatic, cooperative, engineering-focused (high accountability, zero friction)"
            guidance = [
                "Scope questions: emphasize independent task completion from specs and thorough test coverage.",
                "Availability: ready to onboard smoothly and contribute to upcoming sprints immediately.",
                "Stack questions: demonstrate strong fundamentals in React 19, TypeScript, and modern state management."
            ]
        else:
            archetype = f"Autonomous {seniority} {role_label} with End-to-End Technical Ownership"
            tone = "Peer-to-peer, crisp, pragmatic, high-ownership engineering voice (zero junior fluff)"
            guidance = [
                "Salary expectations: state top-of-market tier based on full-cycle ownership and zero onboarding drag.",
                "Availability: standard 2-week transition window or immediate remote engagement.",
                "Stack questions: anchor strongly to React 19 / TypeScript 5 architecture fundamentals."
            ]

        highlights = [
            "Next.js 16 (App Router), React 19, and Core Web Vitals 100/100 optimization",
            "Modular design system engineering from Figma (Cloveri project)",
            "End-to-End delivery: UI architecture, FastAPI backend contracts, and Docker"
        ]

    return {
        "positioning_archetype": archetype,
        "narrative_tone": tone,
        "highlight_priorities": highlights,
        "deliberate_omissions": omissions,
        "tailored_artifacts_required": {
            "tailored_cv": True,
            "custom_cover_letter": True,
            "short_dm": True
        },
        "screening_questions_guidance": guidance,
        "strategic_thesis_refinement": thesis[:250] if thesis else f"Targeted application for {company} — {job_title}",
        "seniority_alignment_active": seniority_alignment,
        "highload_guardrail_active": highload_guardrail
    }


def plan_application_strategy(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    company_dossier: Dict[str, Any],
    thesis_data: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Dedicated AI Strategic Layer: synthesizes Job Understanding + Company Dossier +
    Candidate Profile + Approved Thesis to formulate the tactical application plan.
    Falls back gracefully to heuristic strategy planner on API failure.
    """
    api_key = get_api_key()
    if not api_key:
        return heuristic_application_strategy(profile, job_understanding, company_dossier, thesis_data, lang)

    candidate_name = profile.get("name") or profile.get("identity", {}).get("name", "Candidate")
    overview = job_understanding.get("role_overview", {})
    title = overview.get("title", "Engineer")
    company = overview.get("company", "Company")

    thesis = thesis_data.get("thesis", "")
    supporting = thesis_data.get("supporting_evidence", [])
    problems = job_understanding.get("reasoning", {}).get("likely_team_problems", [])
    company_facts = company_dossier.get("public_facts", {})
    eng_signals = company_dossier.get("engineering_signals", {})

    language_name = "Russian" if lang == "ru" else "English"

    prompt = f"""You are an Elite Executive Career Strategist and Principal Engineering Partner representing {candidate_name}.
Formulate the comprehensive APPLICATION STRATEGY PLAN for {company} ({title}).

DO NOT WRITE COVER LETTER TEXT OR RESUME TEXT HERE.
Your job is to decide the STRATEGIC RULES that will govern all subsequent artifact generation.

INPUT INTELLIGENCE:
1. Job Understanding: {json.dumps(overview, ensure_ascii=False)}
2. Team Bottlenecks & Pain Points: {json.dumps(problems, ensure_ascii=False)}
3. Company Dossier: {json.dumps(company_facts, ensure_ascii=False)} | {json.dumps(eng_signals, ensure_ascii=False)}
4. Approved Application Thesis:
\"\"\"{thesis}\"\"\"
5. Supporting Evidence: {json.dumps(supporting, ensure_ascii=False)}

MANDATORY RULES:
1. DELIBERATE OMISSIONS: You must list specific facts that should be DELIBERATELY HIDDEN or omitted (e.g. founder/owner references, distracting secondary skills, irrelevant legacy tools).
2. HIGHLIGHT PRIORITIES: The 3 exact engineering outcomes from candidate experience that best dismantle this company's bottlenecks.
3. NARRATIVE TONE: Peer-to-peer, confident, technical director level.
4. SCREENING QUESTIONS GUIDANCE: Strategic tactics for common application form questions.

LANGUAGE: {language_name}

OUTPUT STRICT JSON matching this schema:
{{
  "positioning_archetype": "Autonomous Lead / Senior Product Engineer",
  "narrative_tone": "Crisp, peer-to-peer, pragmatic, high-ownership",
  "highlight_priorities": ["Priority 1", "Priority 2", "Priority 3"],
  "deliberate_omissions": [
    "Never mention being a founder/owner (frame as Lead Engineer)",
    "Omit irrelevant non-target skills"
  ],
  "tailored_artifacts_required": {{
    "tailored_cv": true,
    "custom_cover_letter": true,
    "short_dm": true
  }},
  "screening_questions_guidance": [
    "Tactic 1 for forms",
    "Tactic 2 for salary expectations"
  ],
  "strategic_thesis_refinement": "Refined core strategic takeaway"
}}
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
                headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key}
            )
            with urllib.request.urlopen(req, timeout=18) as response:
                resp_text = response.read().decode('utf-8')
                resp_data = json.loads(resp_text)
                text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text).strip()
                parsed = json.loads(text)
                valid, errors = validate_application_strategy(parsed)
                if valid:
                    return parsed
        except Exception as e:
            print(f"  [application_strategy] Model {model} strategy failed: {e}")

    return heuristic_application_strategy(profile, job_understanding, company_dossier, thesis_data, lang)
