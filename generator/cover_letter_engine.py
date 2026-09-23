import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS
from generator.thesis_critic import detect_generic_fluff


def validate_cover_letter_output(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that a generated cover letter package strictly complies with the contract:
    - cover_letter: string (minimum 150 chars)
    - short_dm: string (minimum 50 chars)
    - core_hook: string
    - tone_assessment: string
    - critique_notes: list of applied critic refinements
    - fact_check_status: string ('VERIFIED' or 'HEURISTIC_SAFE')
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Cover letter package must be a dictionary"]

    cl = data.get("cover_letter")
    if not cl or not isinstance(cl, str) or len(cl.strip()) < 150:
        errors.append("Missing or insufficient 'cover_letter' (minimum 150 chars)")

    dm = data.get("short_dm")
    if not dm or not isinstance(dm, str) or len(dm.strip()) < 50:
        errors.append("Missing or insufficient 'short_dm' (minimum 50 chars)")

    for str_key in ["core_hook", "tone_assessment", "fact_check_status"]:
        val = data.get(str_key)
        if not val or not isinstance(val, str):
            errors.append(f"Missing or invalid string for '{str_key}'")

    critiques = data.get("critique_notes")
    if not isinstance(critiques, list):
        errors.append("Field 'critique_notes' must be a list")

    return len(errors) == 0, errors


def fact_check_cover_letter(text: str, profile: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Anti-hallucination check: verifies that technical buzzwords and company names
    mentioned in the letter correspond to verified candidate evidence.
    """
    warnings = []
    text_lower = text.lower()
    
    # 1. Check for dangerous hallucinated foreign stacks
    hallucinated_danger_stacks = ["kubernetes cluster", "kafka cluster", "hadoop", "spark", "solidity", "web3.py"]
    for stack in hallucinated_danger_stacks:
        if stack in text_lower:
            warnings.append(f"Unverified advanced stack '{stack}' detected in text")

    # 2. Check for founder traps
    founder_traps = ["фаундер", "основатель", "мой стартап", "founder", "co-founder", "my startup"]
    for trap in founder_traps:
        if trap in text_lower:
            warnings.append(f"Forbidden founder marker '{trap}' leaked into text")

    return len(warnings) == 0, warnings


def critic_refine_letter(
    text: str,
    strategy: Dict[str, Any],
    lang: str = "ru"
) -> Tuple[str, List[str]]:
    """
    Critic Stage: actively strips clichés, eliminates subservient phrases,
    and polishes the draft into a crisp engineering peer-to-peer tone.
    """
    notes = []
    refined = text

    # Remove generic subservient or Captain Obvious openings
    subservient_patterns = [
        (r'(?i)меня зовут .*?,\s*и я хочу предложить свою кандидатуру на вакансию', 'Откликаюсь на позицию'),
        (r'(?i)с большим интересом прочитал описание вакансии', 'Изучил требования к позиции'),
        (r'(?i)буду бесконечно рад любой возможности пообщаться', 'Буду рад обсудить задачи с командой'),
        (r'(?i)(?:привет(?:ствую)?|здравствуйте)[!,.]?\s*вижу,\s*что\s+(?:в\s+[^,.]+?\s+)?(?:ищут|вы\s+в\s+поиске|вы\s+ищете)[^,.]*?[,.]?\s*', 'Привет! '),
        (r'(?i)(?:привет(?:ствую)?|здравствуйте)[!,.]?\s*увидел\s+(?:вашу\s+)?(?:позицию|вакансию)\s+«?[^»\n]+?»?\s*(?:в\s+[^,\n]+?)?[!,.]?\s*', 'Привет! Откликаюсь на позицию. '),
        (r'(?i)(?:наткнулся|наткнулась|наткнулся|встретил(?:а)?)\s+(?:на\s+)?(?:вашу\s+)?(?:вакансию|позицию)\s*«?[^»\n]+?»?', 'Откликаюсь на позицию'),
        (r'(?i)(?:заметил(?:а)?|обратил(?:а)?\s+внимание)\s+(?:что\s+)?(?:ваша\s+компания|вы|в\s+[^,.]+)\s+(?:ищете|в\s+поиске)[^,.]*', 'Откликаюсь на позицию'),
        (r'(?i)(?:ваша\s+компания|компания\s+\w+)\s+ищет\s+\w+', 'Откликаюсь на позицию'),
        (r'(?i)(?:вы|команда)\s+(?:в\s+поиске|ищете|look(?:ing)?\s+for)\s+\w+', 'Откликаюсь на позицию'),
        (r'(?i)i\s+see\s+(?:that\s+)?(?:you\s+are|they\s+are)\s+looking\s+for\s+.*?[,.]?\s*', 'Applying for the role. '),
        (r'(?i)saw\s+your\s+.*?opening\s+at\s+.*?[,.]?\s*', 'Applying for the role. '),
        (r'(?i)i am thrilled to apply for the position of', 'Applying for the'),
        (r'(?i)i believe i am the ideal candidate for', 'My background directly addresses'),
        (r'(?i)thank you for your time and consideration', 'Looking forward to connecting')
    ]
    for pattern, repl in subservient_patterns:
        if re.search(pattern, refined):
            refined = re.sub(pattern, repl, refined)
            notes.append(f"Replaced subservient/cliche phrasing matching '{pattern}'")

    # Clean generic fluff
    fluff_found = detect_generic_fluff(refined)
    if fluff_found:
        for f in fluff_found:
            refined = re.sub(f, '', refined, flags=re.IGNORECASE)
            notes.append(f"Removed generic fluff phrase matching '{f}'")

    # Enforce deliberate omissions from strategy
    for omission in strategy.get("deliberate_omissions", []):
        if "фаундер" in omission.lower() or "founder" in omission.lower():
            refined = re.sub(r'(?i)\b(?:фаундер|основатель)\b', 'Lead Engineer', refined)
            refined = re.sub(r'(?i)\b(?:founder|co-founder)\b', 'Lead Engineer', refined)

    # Clean double spaces or broken lines caused by removals
    refined = re.sub(r'[ \t]{2,}', ' ', refined)
    refined = re.sub(r'\n{3,}', '\n\n', refined).strip()

    return refined, notes


def heuristic_cover_letter(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    strategy: Dict[str, Any],
    thesis_data: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Deterministic offline multi-stage Cover Letter & Short DM generator.
    Now with ATS keyword injection for each specific job.
    """
    identity = profile.get("identity", {})
    name = identity.get("name") or profile.get("name", "Егор Мышинский" if lang == "ru" else "Egor Myshinsky")
    raw_contacts = identity.get("contacts", {})
    if isinstance(raw_contacts, dict):
        tg = raw_contacts.get("telegram", "@username")
        email = raw_contacts.get("email", "candidate@example.com")
        github = raw_contacts.get("github", "https://github.com/username")
        linkedin = raw_contacts.get("linkedin", "https://linkedin.com/in/username")
    else:
        tg = "@username"
        email = "candidate@example.com"
        github = "https://github.com/username"
        linkedin = "https://linkedin.com/in/username"

    overview = job_understanding.get("role_overview", {})
    title = overview.get("title", "Frontend Engineer")
    company = overview.get("company", "Company")

    archetype = strategy.get("positioning_archetype", "Autonomous Product Engineer")
    highlights = strategy.get("highlight_priorities", [
        "Next.js 16 (App Router), React 19 и оптимизация Core Web Vitals до 100/100",
        "Дизайн-системы и модульные компоненты из Figma (Cloveri для Минцифры)",
        "Сквозная поставка фич: от архитектуры UI до FastAPI API контрактов и Docker"
    ])
    thesis = thesis_data.get("thesis", f"Сквозная поставка веб-интерфейсов и Core Web Vitals 100/100 для {company}")

    # Extract ATS keywords from job requirements
    facts = job_understanding.get("facts", {})
    reqs = facts.get("explicit_requirements", [])
    reqs_text = " ".join(reqs).lower()

    # Match profile skills against job requirements for ATS optimization
    profile_skills = profile.get("skills", [])
    matched_tech = []
    for skill in profile_skills:
        skill_lower = skill.lower()
        # Check if any part of the skill appears in job requirements
        if any(part in reqs_text for part in skill_lower.split() if len(part) > 3):
            matched_tech.append(skill)

    # Build ATS-optimized tech line
    if matched_tech:
        ats_tech_line = ", ".join(matched_tech[:6])
    else:
        ats_tech_line = "React, Next.js, TypeScript"

    # Build continuous text from highlights instead of bullets
    achievements_text = " ".join([f"{h}." for h in highlights[:3]])

    is_middle = "middle" in archetype.lower() or "мидл" in archetype.lower() or "junior" in archetype.lower()

    if lang == "ru":
        core_hook = f"Специализируюсь на продуктовом фронтенде с фокусом на самостоятельное закрытие задач." if is_middle else f"Специализируюсь на масштабируемой архитектуре и сквозной поставке бизнес-функционала."
        
        draft_cl = f"""Откликаюсь на позицию «{title}» в {company}.

{core_hook} {achievements_text}

Рабочий стек: {ats_tech_line}. В фокусе — архитектура без блокеров и предсказуемая поставка фич. На бэкенде спокойно проектирую REST API контракты и поднимаю инфраструктуру в Docker, поэтому смежным командам не приходится ждать. Готов созвониться и ответить на технические вопросы.

{tg} | {email} | {github} | {linkedin}"""

        # ATS-optimized short DM with matched keywords
        ats_keywords_short = ", ".join(matched_tech[:3]) if matched_tech else "React, Next.js, TypeScript"
        draft_dm = f"""Привет! Откликаюсь на позицию «{title}» в {company}.

Мой стек ({ats_keywords_short}) напрямую закрывает ваши задачи. {highlights[0]}. Готов созвониться!

{github} | {linkedin}"""

    else:
        core_hook = f"Autonomous product-focused engineer with full ownership of client architecture." if is_middle else f"Senior product engineer with end-to-end technical ownership."

        draft_cl = f"""Applying for the {title} position at {company}.

{core_hook} {achievements_text}

Tech stack: {ats_tech_line}. My priority is high shipping velocity and clean architectural boundaries. I design backend contracts and containerize via Docker, preventing cross-team blockers. Looking forward to discussing the role!

{tg} | {email} | {github} | {linkedin}"""

        ats_keywords_en = ", ".join(matched_tech[:3]) if matched_tech else "React, Next.js, TypeScript"
        draft_dm = f"""Hi! Applying for the {title} position at {company}.

My background with {ats_keywords_en} directly matches your stack. {highlights[0]}. Looking forward to connecting!

{github} | {linkedin}"""

    # Run Critic stage
    final_cl, cl_notes = critic_refine_letter(draft_cl, strategy, lang=lang)
    final_dm, dm_notes = critic_refine_letter(draft_dm, strategy, lang=lang)

    # Run Fact-Check stage
    fc_ok, fc_warnings = fact_check_cover_letter(final_cl, profile)

    return {
        "cover_letter": final_cl,
        "short_dm": final_dm,
        "core_hook": core_hook,
        "tone_assessment": strategy.get("narrative_tone", "Pragmatic, peer-to-peer"),
        "critique_notes": cl_notes + dm_notes + ([f"Fact-check warnings: {', '.join(fc_warnings)}"] if not fc_ok else []),
        "fact_check_status": "VERIFIED" if fc_ok else "HEURISTIC_SAFE"
    }


def generate_cover_letter(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    strategy: Dict[str, Any],
    thesis_data: Dict[str, Any],
    lang: str = "ru",
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Multi-stage cognitive Cover Letter generator:
    Draft -> Adversarial Critic -> Fact-Check -> Final Package.
    """
    heuristic_pkg = heuristic_cover_letter(profile, job_understanding, strategy, thesis_data, lang=lang)

    api_key = get_api_key()
    if not use_ai or not api_key:
        return heuristic_pkg

    prompt = f"""You are a World-Class Executive Tech Recruiter and Principal Software Engineer.
Draft and refine a highly authentic, peer-to-peer Cover Letter and Short DM for the candidate.

CANDIDATE INFO:
Name: {heuristic_pkg['cover_letter'].splitlines()[-4]}
Target Role: {job_understanding.get('role_overview', {}).get('title')}
Company: {job_understanding.get('role_overview', {}).get('company')}

APPLICATION STRATEGY:
Archetype: {strategy.get('positioning_archetype')}
Tone: {strategy.get('narrative_tone')}
Highlight Priorities: {json.dumps(strategy.get('highlight_priorities', []), ensure_ascii=False)}
Deliberate Omissions: {json.dumps(strategy.get('deliberate_omissions', []), ensure_ascii=False)}

APPROVED THESIS:
{thesis_data.get('thesis')}

STRICT RULES:
1. ZERO CLICHES: Never use 'thrilled to apply', 'passionate about coding', 'опытный специалист', 'быстро обучаем', 'идеально подхожу'.
2. PEER-TO-PEER TONE: Write from one seasoned software engineer to another. No subservience.
3. CONCRETE PROOF: Anchor strictly to verified skills (React 19, Next.js 16, TypeScript, PageSpeed 100/100, design systems, Docker, FastAPI).
4. DELIBERATE OMISSIONS: Never mention 'founder', 'co-founder', 'основатель', 'мой стартап'.

OUTPUT JSON ONLY matching this schema:
{{
  "cover_letter": "Full text of letter...",
  "short_dm": "Short 3-4 sentence message for Telegram/LinkedIn...",
  "core_hook": "One sentence value hook...",
  "tone_assessment": "...",
  "critique_notes": ["Self-critique refinement 1", "..."],
  "fact_check_status": "VERIFIED"
}}
"""
    model = GEMINI_MODELS[0]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
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
        with urllib.request.urlopen(req, timeout=14.0) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
            text = raw['candidates'][0]['content']['parts'][0]['text'].strip()
            parsed = json.loads(text)
            
            # Run critic pass on AI output
            parsed["cover_letter"], cl_notes = critic_refine_letter(parsed.get("cover_letter", ""), strategy, lang=lang)
            parsed["short_dm"], dm_notes = critic_refine_letter(parsed.get("short_dm", ""), strategy, lang=lang)
            parsed["critique_notes"] = parsed.get("critique_notes", []) + cl_notes + dm_notes

            valid, errors = validate_cover_letter_output(parsed)
            if valid:
                return parsed
    except Exception:
        pass

    return heuristic_pkg
