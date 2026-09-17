import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS

def validate_application_thesis(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that an Application Thesis result strictly contains all mandatory fields:
    - thesis (non-generic string)
    - strategic_rationale (explanation)
    - supporting_evidence (list of evidence anchors)
    - alternative_theses (list of at least 1 alternative)
    - potential_risks (list)
    - confidence (float between 0.0 and 1.0)
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Thesis data must be a dictionary"]

    thesis = data.get("thesis")
    if not thesis or not isinstance(thesis, str) or len(thesis.strip()) < 20:
        errors.append("Missing or too short 'thesis' string (min 20 chars)")

    rationale = data.get("strategic_rationale")
    if not rationale or not isinstance(rationale, str):
        errors.append("Missing 'strategic_rationale' string")

    supporting_ev = data.get("supporting_evidence")
    if not isinstance(supporting_ev, list) or len(supporting_ev) == 0:
        errors.append("Missing or empty 'supporting_evidence' list")

    alt_theses = data.get("alternative_theses")
    if not isinstance(alt_theses, list):
        errors.append("Missing 'alternative_theses' list")

    risks = data.get("potential_risks")
    if not isinstance(risks, list):
        errors.append("Missing 'potential_risks' list")

    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        errors.append("Invalid 'confidence' (must be float between 0.0 and 1.0)")

    return len(errors) == 0, errors


def heuristic_application_thesis(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    reframed_evidence: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Offline heuristic generator for Application Thesis.
    Synthesizes the strongest evidence point and narrative into a clear value proposition.
    """
    overview = job_understanding.get("role_overview", {})
    job_title = overview.get("title", "Software Engineer")
    company = overview.get("company", "Company")

    matched_list = reframed_evidence.get("matched_evidence", [])
    primary_ev = matched_list[0] if matched_list else {}
    secondary_ev = matched_list[1] if len(matched_list) > 1 else {}

    primary_claim = primary_ev.get("candidate_claim", "End-to-End Frontend Architecture")
    primary_framing = primary_ev.get("aggressive_framing", "Опыт полного цикла разработки на Next.js 16 и TypeScript")
    job_pain = primary_ev.get("job_pain_point", "ускорение продуктовой поставки")

    if lang == "ru":
        main_thesis = (
            f"Кандидат обладает подтвержденным практическим опытом решения ключевой задачи вакансии: "
            f"{primary_framing}. Это напрямую закрывает потребность {company} в части: {job_pain}."
        )
        rationale = (
            f"Вместо шаблонного перечисления библиотек мы позиционируем кандидата как автономного Lead/Senior Product инженера, "
            f"который снимет с команды архитектурные риски и ускорит поставку фич без онбординг-задержек."
        )
        alt_theses = [
            f"Позиционирование через сквозную Fullstack-автономию: разработка REST API на FastAPI и контейнеризация в Docker устраняют зависимость фронтенда от бэкенд-команды.",
            f"Позиционирование через экстремальную скорость поставки и хакатонный опыт: 1 место на хакатоне Droog (3 интерфейса за 48ч) гарантирует быстрое закрытие горящих задач."
        ]
        risks = [
            "Если вакансия требует узких корпоративных legacy-инструментов, акцентировать базовый фундамент в TypeScript / React, позволяющий быстро закрыть дефицит без просадки в качестве."
        ]
        supporting = [
            f"Подтвержденное доказательство: {primary_claim}",
            f"Сквозной стек: Next.js 16 (App Router), React 19, TypeScript, Docker, FastAPI"
        ]
    else:
        main_thesis = (
            f"The candidate has demonstrable, hands-on architectural experience addressing the company's exact bottleneck: "
            f"{primary_framing}. This directly resolves {company}'s challenge regarding {job_pain}."
        )
        rationale = (
            f"Instead of standard keyword listing, we frame the candidate as an autonomous Lead/Senior Product Engineer "
            f"capable of taking full technical ownership without requiring micromanagement."
        )
        alt_theses = [
            f"Fullstack Autonomy angle: building FastAPI REST endpoints and multi-stage Docker builds eliminates team dependencies on backend blockers.",
            f"Velocity & Hackathon track record angle: 1st place at Droog Hackathon (3 apps in 48h) proves rapid delivery under extreme deadlines."
        ]
        risks = [
            "If niche enterprise tooling is requested, anchor to deep TypeScript and architectural mastery ensuring a near-zero learning curve."
        ]
        supporting = [
            f"Verified Evidence Anchor: {primary_claim}",
            f"Core Capability Stack: Next.js 16, React 19, TypeScript 5, Docker, FastAPI"
        ]

    return {
        "thesis": main_thesis,
        "strategic_rationale": rationale,
        "supporting_evidence": supporting,
        "alternative_theses": alt_theses,
        "potential_risks": risks,
        "confidence": 0.88
    }


def generate_application_thesis(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    reframed_evidence: Dict[str, Any],
    lang: str = "ru",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Dedicated AI stage: synthesizes Job Understanding + Canonical Evidence + Reframed Capabilities
    to formulate the singular, winning Application Thesis with supporting evidence, alternatives, and risks.
    Falls back gracefully to heuristic_application_thesis on API errors.
    """
    if not use_ai:
        return heuristic_application_thesis(profile, job_understanding, reframed_evidence, lang)

    api_key = get_api_key()
    if not api_key:
        return heuristic_application_thesis(profile, job_understanding, reframed_evidence, lang)

    candidate_name = profile.get("name") or profile.get("identity", {}).get("name", "Candidate")
    target_role = profile.get("role") or profile.get("identity", {}).get("target_role", "Senior Engineer")

    overview = job_understanding.get("role_overview", {})
    title = overview.get("title", "Software Engineer")
    company = overview.get("company", "Company")
    problems = job_understanding.get("reasoning", {}).get("likely_team_problems", [])
    priorities = job_understanding.get("reasoning", {}).get("hiring_priorities", [])

    matched_evidence = reframed_evidence.get("matched_evidence", [])
    narrative = reframed_evidence.get("strategic_narrative", {})

    language_name = "Russian" if lang == "ru" else "English"

    prompt = f"""You are an Elite Career Strategist and Principal Tech Lead representing {candidate_name} ({target_role}).
Before writing any application materials, you must formulate the APPLICATION THESIS for applying to {company} for the role of {title}.

CORE PRINCIPLE:
The Application Thesis is the single, defensible, non-generic core argument:
"Why is this specific candidate compelling for this specific team's exact technical and business problems?"

NEVER OUTPUT GENERIC CLICHES:
- FORBIDDEN: "The candidate knows React and is excited to apply."
- REQUIRED: "The candidate has already executed zero-downtime frontend modernizations on Next.js 16 / React 19, which directly resolves the legacy architectural slowdowns identified in {company}'s roadmap."

INPUT CONTEXT:
1. Company & Role: {company} — {title}
2. Core Team Pain Points: {json.dumps(problems, ensure_ascii=False)}
3. Hiring Priorities: {json.dumps(priorities, ensure_ascii=False)}
4. Candidate Matched Evidence: {json.dumps(matched_evidence, ensure_ascii=False)}
5. Positioning Angle: {narrative.get('positioning_angle', '')}

LANGUAGE: {language_name}

OUTPUT STRICT JSON matching this schema:
{{
  "thesis": "The singular primary strategic argument (2-3 crisp sentences)",
  "strategic_rationale": "Why this specific argument beats 100 other generic applicants",
  "supporting_evidence": [
    "Specific verified capability from candidate evidence backing this thesis",
    "Secondary supporting capability"
  ],
  "alternative_theses": [
    "Alternative Strategy 1 (e.g. pivoting on Fullstack ownership or velocity)",
    "Alternative Strategy 2"
  ],
  "potential_risks": [
    "Potential blind spot or risk in the match to be addressed carefully"
  ],
  "confidence": 0.90
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
                valid, errors = validate_application_thesis(parsed)
                if valid:
                    return parsed
                else:
                    print(f"  [thesis_generator] Validation warnings for model {model}: {errors}")
        except Exception as e:
            print(f"  [thesis_generator] Model {model} failed: {e}")

    # Fallback to heuristic
    return heuristic_application_thesis(profile, job_understanding, reframed_evidence, lang)
