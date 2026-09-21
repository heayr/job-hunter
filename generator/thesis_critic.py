import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS
from generator.thesis_generator import generate_application_thesis

# ── FORBIDDEN GENERIC CLICHES / FLUFF PATTERNS ───────────────────────────────

BANNED_FLUFF_PATTERNS = [
    r'(?:опытный специалист|быстро обучаем|стрессоустойчив|коммуникабелен)',
    r'(?:идеально подхожу|рад предложить свои услуги|с удовольствием поучаствую)',
    r'(?:в сегодняшнем быстро меняющемся мире|настоящий энтузиаст)',
    r'(?:experienced professional|fast learner|hard worker|motivated team player)',
    r'(?:thrilled to apply|passionate about coding|excited for this opportunity)',
    r'(?:in today\'s fast-paced world|perfect fit for this role)',
    r'(?:меня зовут \w+,\s*(?:и\s+)?(?:хочу|желаю|готов|хотел))',
    r'(?:увидел(?:а)? вашу вакансию|видел(?:а)? вашу вакансию|наткнулся на вашу)',
    r'(?:ваша компания ищет|вы ищете|your company is looking|you are looking for|you\'re looking for)',
    r'(?:рассматриваю вашу вакансию|considering your (?:opening|position|vacancy))',
]

def detect_generic_fluff(text: str) -> List[str]:
    """Detects presence of forbidden generic AI clichés or lazy buzzwords."""
    matched = []
    text_lower = text.lower()
    for pattern in BANNED_FLUFF_PATTERNS:
        if re.search(pattern, text_lower):
            matched.append(pattern)
    return matched


def heuristic_critique(
    thesis_data: Dict[str, Any],
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Offline deterministic critic assessing thesis strength, evidence backing,
    and absence of generic fluff.
    """
    thesis_text = thesis_data.get("thesis", "")
    fluff = detect_generic_fluff(thesis_text)
    
    score = 1.0
    reasons = []
    unsubstantiated = []

    # 1. Penalize fluff
    if fluff:
        score -= 0.35
        reasons.append("Обнаружены шаблонные фразы / вода")

    # 2. Check thesis length and depth
    if len(thesis_text) < 45:
        score -= 0.30
        reasons.append("Тезис слишком короткий или не раскрывает техническую суть")

    # 3. Check evidence backing
    supp_ev = thesis_data.get("supporting_evidence", [])
    if not supp_ev or len(supp_ev) == 0:
        score -= 0.40
        reasons.append("Отсутствуют прямые ссылки на подтвержденный опыт кандидата")

    # 4. Check whether thesis addresses job specifics or remains generic
    overview = job_understanding.get("role_overview", {})
    company = overview.get("company", "").lower()
    title = overview.get("title", "").lower()

    has_context_link = False
    if company and company in thesis_text.lower():
        has_context_link = True
    if any(term in thesis_text.lower() for term in ["next.js", "react", "fastapi", "docker", "pagespeed", "100/100", "typescript", "архитектур", "architecture"]):
        has_context_link = True

    if not has_context_link:
        score -= 0.25
        reasons.append("Тезис недостаточно привязан к конкретному техническому стеку или компании")

    score = max(0.1, min(1.0, round(score, 2)))

    if score >= 0.75:
        verdict = "APPROVED"
        summary = "Тезис конкретен, опирается на подтвержденный опыт и решает проблему работодателя."
    elif score >= 0.55:
        verdict = "NEEDS_REVISION"
        summary = "Тезис приемлем, но требует усиления технической конкретики или устранения клише."
    else:
        verdict = "REJECTED"
        summary = "Тезис слабый, слишком абстрактный или содержит шаблоны. Рекомендуется переключение на альтернативу."

    return {
        "verdict": verdict,
        "score": score,
        "fluff_detected": len(fluff) > 0,
        "fluff_reasons": fluff,
        "evidence_grounding_score": 0.9 if supp_ev else 0.3,
        "logical_leaps": reasons,
        "unsubstantiated_claims": unsubstantiated,
        "critique_summary": summary
    }


def critique_application_thesis(
    thesis_data: Dict[str, Any],
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Adversarial AI Critic: evaluates thesis strength, detects generic AI fluff,
    checks evidence sufficiency, and flags logical leaps.
    """
    if not use_ai:
        return heuristic_critique(thesis_data, profile, job_understanding, lang)

    api_key = get_api_key()
    if not api_key:
        return heuristic_critique(thesis_data, profile, job_understanding, lang)

    thesis_text = thesis_data.get("thesis", "")
    supporting = thesis_data.get("supporting_evidence", [])
    rationale = thesis_data.get("strategic_rationale", "")

    raw_exp = profile.get("experience", "")[:2000]
    overview = job_understanding.get("role_overview", {})
    problems = job_understanding.get("reasoning", {}).get("likely_team_problems", [])

    language_name = "Russian" if lang == "ru" else "English"

    prompt = f"""You are a Skeptical Technical Director, Hiring Manager, and Thesis Critic.
Your goal is to ADVERSARIALLY ATTACK and rigorously evaluate this proposed Application Thesis.

PROPOSED THESIS:
\"\"\"{thesis_text}\"\"\"

STRATEGIC RATIONALE:
\"\"\"{rationale}\"\"\"

SUPPORTING EVIDENCE ANCHORS:
{json.dumps(supporting, ensure_ascii=False)}

JOB CONTEXT:
- Company & Role: {overview.get('company')} — {overview.get('title')}
- Team Pain Points: {json.dumps(problems, ensure_ascii=False)}

CANDIDATE'S ACTUAL EXPERIENCE:
{raw_exp}

CRITICAL RULES:
1. REJECT GENERIC FLUFF: If the thesis contains empty praise ('experienced professional', 'motivated', 'enthusiastic'), mark verdict as REJECTED or NEEDS_REVISION.
2. CHECK EVIDENCE GROUNDING: Does the candidate's actual experience genuinely support the claim, or is it a wild leap?
3. VERDICT must be one of: "APPROVED", "NEEDS_REVISION", "REJECTED".
4. Score between 0.0 and 1.0. (Only give >= 0.75 if the thesis is truly punchy, concrete, and evidence-grounded).

LANGUAGE: {language_name}

Respond ONLY with valid JSON in this exact structure:
{{
  "verdict": "APPROVED" | "NEEDS_REVISION" | "REJECTED",
  "score": 0.85,
  "fluff_detected": false,
  "fluff_reasons": [],
  "evidence_grounding_score": 0.9,
  "logical_leaps": [],
  "unsubstantiated_claims": [],
  "critique_summary": "Detailed technical critique of why the thesis succeeded or failed"
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
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
            with urllib.request.urlopen(req, timeout=18) as response:
                resp_text = response.read().decode('utf-8')
                resp_data = json.loads(resp_text)
                text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text).strip()
                parsed = json.loads(text)
                if "verdict" in parsed and "score" in parsed:
                    return parsed
        except Exception as e:
            print(f"  [thesis_critic] Model {model} critique failed: {e}")

    return heuristic_critique(thesis_data, profile, job_understanding, lang)


def evaluate_and_refine_thesis(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    reframed_evidence: Dict[str, Any],
    lang: str = "ru",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Main closed-loop strategy runner:
    1. Generates primary thesis (Phase 4).
    2. Executes adversarial critique (Phase 5).
    3. If rejected or score < 0.70, pivots to top alternative thesis and critiques again.
    4. Attaches critique audit trail to the final thesis.
    """
    # Generate initial thesis
    thesis_result = generate_application_thesis(profile, job_understanding, reframed_evidence, lang=lang, use_ai=use_ai)
    critique = critique_application_thesis(thesis_result, profile, job_understanding, lang=lang, use_ai=use_ai)

    best_thesis = thesis_result
    best_thesis["critique"] = critique
    best_thesis["strategy_status"] = "APPROVED_PRIMARY" if critique.get("verdict") == "APPROVED" else "NEEDS_REVISION"
    best_score = critique.get("score", 0.0)

    # If primary is already strong, return immediately
    if critique.get("verdict") == "APPROVED" and best_score >= 0.70:
        return best_thesis

    # Iterate through Alternative Theses to find a higher scoring defensible angle
    alt_theses = thesis_result.get("alternative_theses", [])
    primary_critique_log = critique

    for idx, alt_text in enumerate(alt_theses):
        candidate_thesis = {
            "thesis": alt_text,
            "strategic_rationale": f"Alternative Strategy #{idx+1} selected to address critique: {critique.get('critique_summary', '')}",
            "supporting_evidence": thesis_result.get("supporting_evidence", []),
            "alternative_theses": [t for i, t in enumerate(alt_theses) if i != idx],
            "potential_risks": thesis_result.get("potential_risks", []),
            "confidence": round(thesis_result.get("confidence", 0.8) * 0.95, 2)
        }
        cand_critique = critique_application_thesis(candidate_thesis, profile, job_understanding, lang=lang)
        candidate_thesis["critique"] = cand_critique
        candidate_thesis["primary_critique_log"] = primary_critique_log
        cand_score = cand_critique.get("score", 0.0)

        if cand_critique.get("verdict") == "APPROVED" and cand_score >= 0.70:
            candidate_thesis["strategy_status"] = "PIVOTED_APPROVED_ALTERNATIVE"
            return candidate_thesis

        if cand_score > best_score:
            best_score = cand_score
            best_thesis = candidate_thesis
            best_thesis["strategy_status"] = "PIVOTED_BEST_ALTERNATIVE"

    return best_thesis
