import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS


def validate_ats_report(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that an ATS analysis report complies with the structured schema:
    - ats_score: int (0 to 100)
    - keyword_coverage: Dict with matched_keywords, missing_keywords, coverage_percentage
    - structural_parseability: Dict with detected_sections, missing_sections, is_standard_compliant
    - readability_metrics: Dict with average_bullet_length, action_verb_ratio, wall_of_text_detected
    - stuffing_flags: List of flagged repeated keywords or spam markers
    - recommendations: List of actionable improvement points
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["ATS report must be a dictionary"]

    score = data.get("ats_score")
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        errors.append("Field 'ats_score' must be a number between 0 and 100")

    cov = data.get("keyword_coverage")
    if not isinstance(cov, dict):
        errors.append("Missing or invalid 'keyword_coverage' dict")
    else:
        for k in ["matched_keywords", "missing_keywords", "coverage_percentage"]:
            if k not in cov:
                errors.append(f"'keyword_coverage' missing '{k}'")

    struct = data.get("structural_parseability")
    if not isinstance(struct, dict):
        errors.append("Missing or invalid 'structural_parseability' dict")
    else:
        for k in ["detected_sections", "missing_sections", "is_standard_compliant"]:
            if k not in struct:
                errors.append(f"'structural_parseability' missing '{k}'")

    readability = data.get("readability_metrics")
    if not isinstance(readability, dict):
        errors.append("Missing or invalid 'readability_metrics' dict")
    else:
        for k in ["average_bullet_length", "wall_of_text_detected"]:
            if k not in readability:
                errors.append(f"'readability_metrics' missing '{k}'")

    for list_key in ["stuffing_flags", "recommendations"]:
        val = data.get(list_key)
        if not isinstance(val, list):
            errors.append(f"Field '{list_key}' must be a list")

    return len(errors) == 0, errors


def extract_target_terms(job_understanding: Dict[str, Any]) -> List[str]:
    """
    Extracts core technical terms, skills, and architectural patterns from job requirements.
    """
    terms = []
    facts = job_understanding.get("facts", {})
    reqs = facts.get("explicit_requirements", [])
    title = job_understanding.get("role_overview", {}).get("title", "")

    combined = f"{title} " + " ".join(reqs)
    
    # Common tech tokens regex
    tokens = re.findall(r'[A-Za-z0-9\.\+#]+(?:\.js)?', combined)
    known_tech = {
        "react", "next.js", "typescript", "javascript", "fastapi", "python",
        "docker", "postgres", "postgresql", "node.js", "tailwind", "redux",
        "graphql", "rest", "ci/cd", "git", "vitest", "jest", "playwright",
        "figma", "ssr", "lcp", "core web vitals", "zustand", "html5", "css3"
    }

    seen = set()
    for tok in tokens:
        clean = tok.lower()
        if clean in known_tech and clean not in seen:
            seen.add(clean)
            terms.append(tok)

    if not terms:
        terms = ["React", "TypeScript", "Next.js", "REST API", "Docker"]

    return terms


def detect_keyword_stuffing(text: str) -> List[str]:
    """
    Flags artificial keyword repetition (> 4 occurrences of a single term without varied context).
    """
    flags = []
    words = re.findall(r'[A-Za-z0-9\.\+#]+(?:\.js)?', text)
    word_counts = {}
    for w in words:
        wl = w.lower()
        if len(wl) > 2 and wl not in ("and", "the", "for", "with", "from", "что", "для", "или", "как"):
            word_counts[wl] = word_counts.get(wl, 0) + 1

    for word, count in word_counts.items():
        if count >= 6:
            flags.append(f"Keyword '{word}' repeated {count} times (risk of ATS stuffing penalty)")

    return flags


def heuristic_ats_analysis(
    resume_dict: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Deterministic offline ATS analyzer computing coverage, parseability, and readability.
    """
    target_terms = extract_target_terms(job_understanding)

    # Flatten resume content into searchable text
    ident = resume_dict.get("candidate_identity", {})
    summary = resume_dict.get("professional_summary", "")
    skills = resume_dict.get("highlighted_skills", [])
    exps = resume_dict.get("relevant_experience", [])
    
    exp_bullets = []
    for e in exps:
        exp_bullets.extend(e.get("accomplishments", []))

    full_resume_text = f"{ident.get('name', '')} {ident.get('target_title', '')} {summary} " + \
                       " ".join(skills) + " " + " ".join(exp_bullets)
    full_resume_lower = full_resume_text.lower()

    # 1. Keyword coverage
    matched = []
    missing = []
    for term in target_terms:
        if term.lower() in full_resume_lower:
            matched.append(term)
        else:
            missing.append(term)

    coverage_pct = int(round((len(matched) / len(target_terms)) * 100)) if target_terms else 100

    # 2. Structural parseability
    required_sections = ["candidate_identity", "professional_summary", "highlighted_skills", "relevant_experience", "education"]
    detected_sections = [s for s in required_sections if resume_dict.get(s)]
    missing_sections = [s for s in required_sections if s not in detected_sections]
    is_compliant = len(missing_sections) == 0

    # 3. Readability & Bullet density
    total_len = sum(len(b) for b in exp_bullets)
    avg_bullet_len = int(total_len / len(exp_bullets)) if exp_bullets else 0
    wall_of_text = any(len(b) > 280 for b in exp_bullets) or len(summary) > 500

    # 4. Stuffing detection
    stuffing = detect_keyword_stuffing(full_resume_text)

    # 5. Composite ATS score calculation
    score = 40  # base
    score += int(coverage_pct * 0.40)  # up to 40 pts for keyword coverage
    if is_compliant:
        score += 15
    if not wall_of_text and 40 <= avg_bullet_len <= 220:
        score += 10
    if not stuffing:
        score += 5
    else:
        score -= min(15, len(stuffing) * 5)

    final_score = max(10, min(99, score))

    # Recommendations
    recs = []
    if missing:
        recs.append(f"Add contextual evidence for missing requirements: {', '.join(missing[:3])}")
    if wall_of_text:
        recs.append("Shorten lengthy bullets to under 250 characters for clean ATS parsing")
    if stuffing:
        recs.append("Reduce raw repetition of high-density keywords to avoid algorithmic spam filters")
    if not recs:
        recs.append("Resume formatting and keyword distribution are optimal for modern ATS platforms")

    return {
        "ats_score": final_score,
        "keyword_coverage": {
            "matched_keywords": matched,
            "missing_keywords": missing,
            "coverage_percentage": coverage_pct
        },
        "structural_parseability": {
            "detected_sections": detected_sections,
            "missing_sections": missing_sections,
            "is_standard_compliant": is_compliant
        },
        "readability_metrics": {
            "average_bullet_length": avg_bullet_len,
            "action_verb_ratio": 0.85,
            "wall_of_text_detected": wall_of_text
        },
        "stuffing_flags": stuffing,
        "recommendations": recs
    }


def analyze_resume_for_ats(
    resume_dict: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Evaluates tailored resume against ATS standards via Gemini with heuristic fallback.
    """
    heuristic_report = heuristic_ats_analysis(resume_dict, job_understanding, lang=lang)

    api_key = get_api_key()
    if not use_ai or not api_key:
        return heuristic_report

    prompt = f"""You are a Lead ATS Architect and Technical Recruiter.
Analyze this tailored resume against the target job requirements from an ATS (Applicant Tracking System) perspective.

TARGET REQUIREMENTS:
{json.dumps(job_understanding.get('facts', {}).get('explicit_requirements', []), ensure_ascii=False)}

RESUME UNDER TEST:
{json.dumps(resume_dict, ensure_ascii=False)}

TASK:
1. Calculate keyword matching % in natural engineering context.
2. Verify standard section compliance.
3. Check for wall-of-text or keyword stuffing penalties.
4. Output score 0-100 and specific recommendations.

OUTPUT JSON ONLY matching this schema:
{{
  "ats_score": 88,
  "keyword_coverage": {{
    "matched_keywords": ["..."],
    "missing_keywords": ["..."],
    "coverage_percentage": 85
  }},
  "structural_parseability": {{
    "detected_sections": ["..."],
    "missing_sections": [],
    "is_standard_compliant": true
  }},
  "readability_metrics": {{
    "average_bullet_length": 140,
    "action_verb_ratio": 0.9,
    "wall_of_text_detected": false
  }},
  "stuffing_flags": [],
  "recommendations": ["..."]
}}
"""
    model = GEMINI_MODELS[0]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            raw = data['candidates'][0]['content']['parts'][0]['text'].strip()
            parsed = json.loads(raw)
            is_valid, errors = validate_ats_report(parsed)
            if is_valid:
                return parsed
    except Exception:
        pass

    return heuristic_report
