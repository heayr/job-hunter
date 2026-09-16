import re
import os
import json
from typing import Dict, Any, List

from generator.llm_generator import generate_ai_pitch
from anti_bs_filter import analyze_vacancy_traps


KNOWN_TECH_KEYWORDS = [
    "React", "Next.js", "TypeScript", "JavaScript", "HTML5", "CSS3", "SCSS", "Tailwind CSS",
    "Redux", "Redux Toolkit", "RTK Query", "Zustand", "MobX", "TanStack Query", "React Query",
    "Webpack", "Vite", "Babel", "Microfrontends", "Module Federation", "FSD", "Feature-Sliced Design",
    "SSR", "SSG", "ISR", "React Server Components", "REST API", "GraphQL", "WebSocket",
    "Jest", "Vitest", "React Testing Library", "Playwright", "Cypress", "Storybook",
    "Node.js", "NestJS", "Express", "FastAPI", "Python", "PostgreSQL", "Prisma", "Docker", "CI/CD", "Git"
]


# ─────────────────────────────────────────────
#  Profile loading from the UI-editable file
# ─────────────────────────────────────────────

def load_profiles() -> List[Dict]:
    path = os.path.join(os.path.dirname(__file__), 'profiles.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def select_profile(lang: str = "ru", profile_id: Optional[str] = None) -> Dict:
    """Pick the active profile by ID or by matching language from profiles.json."""
    profiles = load_profiles()
    if not profiles:
        return {
            "name": "Candidate Name",
            "lang": "en",
            "role": "Frontend / Fullstack Engineer",
            "contacts": "Telegram: @username | Email: candidate@example.com | GitHub: https://github.com/username | LinkedIn: https://linkedin.com/in/username",
            "keywords": "React, Next.js, TypeScript, JavaScript, Redux Toolkit, Tailwind CSS, Node.js, FastAPI, Docker",
            "summary": "Fullstack Engineer with experience building production web applications with React, Next.js and TypeScript.",
            "experience": "• Engineered high-performance web applications\n• Delivered production-ready microservices and REST APIs\n• Integrated modern auth, state management, and containerized deployments",
        }
    # 1. If explicit profile_id provided, find it
    if profile_id:
        for p in profiles:
            if p.get('id') == profile_id:
                return p
    # 2. Prefer exact language match
    for p in profiles:
        if p.get('lang', 'ru') == lang:
            return p
    # Fallback to first profile
    return profiles[0]


# ─────────────────────────────────────────────
#  Keyword extraction
# ─────────────────────────────────────────────

def extract_target_keywords(title: str, skills: str, desc: str) -> List[str]:
    full_text = f"{title} {skills} {desc}".lower()
    matched = []
    for kw in KNOWN_TECH_KEYWORDS:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, full_text):
            matched.append(kw)
    for base in ["React", "TypeScript", "JavaScript"]:
        if base not in matched:
            matched.insert(0, base)
    return matched


# ─────────────────────────────────────────────
#  Language detection
# ─────────────────────────────────────────────

def determine_language(vacancy: Dict[str, Any]) -> str:
    lang = vacancy.get("language")
    if lang in ("ru", "en"):
        return lang
    source = vacancy.get("source", "").lower()
    combined = f"{vacancy.get('company', '')} {vacancy.get('title', '')} {vacancy.get('description', '')} {vacancy.get('location', '')}"

    if any(s in source for s in ["wwr", "remoteok", "weworkremotely", "relocateme", "crypto", "remotive"]):
        return "en"
    if any(s in source for s in ["habr", "superjob", "rabota", "talanto", "geekjob"]):
        return "ru"
    if bool(re.search(r"[а-яёА-ЯЁ]", combined)):
        return "ru"
    return "en"


# ─────────────────────────────────────────────
#  CV builder — uses real profile data
# ─────────────────────────────────────────────

def build_tailored_cv(vacancy: Dict[str, Any], target_keywords: List[str], lang: str = "ru", profile: Optional[Dict] = None) -> str:
    if profile is None:
        profile = select_profile(lang)
    kw_str = ", ".join(target_keywords)
    title = vacancy.get("title", profile.get("role", "Frontend Engineer"))
    name = profile.get("name", "Имя Фамилия" if lang == "ru" else "Candidate Name")
    contacts = profile.get("contacts", "")
    summary = profile.get("summary", "")
    experience = profile.get("experience", "")

    if lang == "en":
        cv = f"""{name.upper()}
{contacts}

TARGET POSITION: {title}

PROFESSIONAL SUMMARY:
{summary}
Key Technologies: {kw_str}.

CORE TECHNICAL SKILLS:
• Frontend: React 18/19, Next.js 15 (App Router), TypeScript, JavaScript (ES6+), Redux Toolkit, Tailwind CSS
• Rendering & Web: SSR, SSG, NextAuth, JWT, REST API, RBAC
• Backend & AI: FastAPI, Node.js, PostgreSQL, OpenAI API, LLM Integrations
• Infrastructure: Git, GitHub Actions, Docker, Vite, Webpack, Figma

PROFESSIONAL EXPERIENCE:
{experience}

EDUCATION & LANGUAGES:
• Master's Degree (2015–2017)
• Professional Retraining — Frontend Development (2022–2023)
• Languages: English (B2), Russian (Native)"""
    else:
        cv = f"""{name.upper()}
{contacts}

ЦЕЛЕВАЯ ПОЗИЦИЯ: {title}

ПРОФЕССИОНАЛЬНОЕ САММАРИ:
{summary}
Используемые технологии: {kw_str}.

КЛЮЧЕВЫЕ КОМПЕТЕНЦИИ:
• Фронтенд: React 18/19, Next.js 15 (App Router), TypeScript, JavaScript (ES6+), Redux Toolkit, Tailwind CSS
• Бэкенд и БД: FastAPI, Node.js, PostgreSQL, REST API
• Инфраструктура: Git, Docker, CI/CD, Webpack, Vite

ОПЫТ РАБОТЫ:
{experience}

ОБРАЗОВАНИЕ И ЯЗЫКИ:
• Магистратура (2015–2017)
• Проф. переподготовка — Frontend-разработчик (2022–2023)
• Языки: Английский (B2), Русский (Родной)"""
    return cv.strip()


# ─────────────────────────────────────────────
#  Main pitch generator
# ─────────────────────────────────────────────

def calculate_match_score(vacancy: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> int:
    """
    Calculates deterministic match percentage (0-100%) based on tech stack overlap,
    role seniority, and keywords between vacancy and candidate profile.
    """
    if profile is None:
        profile = select_profile("ru")
    title = (vacancy.get("title") or "").lower()
    desc = (vacancy.get("description") or "").lower()
    skills = (vacancy.get("skills") or "").lower()
    full_text = f"{title} {skills} {desc}"

    # 1. Base score for qualified frontend/fullstack role
    score = 35

    # 2. Positive target role boost
    if any(k in title for k in ["frontend", "фронтенд", "react", "next.js", "nextjs", "web developer", "разработчик интерфейс"]):
        score += 10

    # 3. Core stack points (up to +30)
    matched_core = 0
    for tech, pts in [("react", 10), ("typescript", 10), ("next.js", 10), ("nextjs", 10), ("javascript", 5)]:
        if tech in full_text:
            matched_core = min(30, matched_core + pts)
    score += matched_core

    # 4. Secondary stack / tools (up to +25)
    secondary_tech = [
        "tailwind", "fastapi", "docker", "redux", "node.js", "nodejs",
        "graphql", "rest", "postgresql", "ci/cd", "git", "vite",
        "webpack", "vitest", "jest", "zustand", "tanstack", "react query"
    ]
    matched_sec = sum(3 for tech in secondary_tech if tech in full_text)
    score += min(25, matched_sec)

    # 5. Seniority / leadership bonus (up to +10)
    if any(k in title for k in ["lead", "senior", "лид", "ведущий", "architect", "founding"]):
        score += 10
    elif any(k in title for k in ["middle", "мидл", "fullstack", "фуллстек"]):
        score += 5

    # 6. Role mismatch penalty (QA, SDET, DevOps, Data, PM, Design, HR) - drops non-target roles to bottom!
    non_target_roles = [
        r'\bqa\b', r'\bqa\s*(?:automation|engineer|lead|manual)?\b',
        r'\bsdet\b', r'\bengineer\s+in\s+test\b', r'\bтестировщик\b', r'\bтестировани[еяю]\b',
        r'\btest(?:ing)?\s+engineer\b', r'\bautomation\s+test\b',
        r'\bdevops\b', r'\bsre\b', r'\bsysadmin\b', r'\bсистемн\w+\s+администратор\b',
        r'\bdata\s*(?:scientist|engineer|analyst)\b', r'\bаналитик\b', r'\bml\s*engineer\b',
        r'\bproduct\s*manager\b', r'\bproject\s*manager\b', r'\bscrum\s*master\b',
        r'\bдизайнер\b', r'\bdesigner\b', r'\bui/ux\s*designer\b',
        r'\brecruiter\b', r'\bрекрутер\b', r'\bhr\b', r'\bкопирайтер\b'
    ]
    for ntr in non_target_roles:
        if re.search(ntr, title):
            score -= 55
            break

    # 7. Mixed / foreign stack penalty (-15 to -20 points)
    # If the vacancy requires tech outside the candidate's core stack (e.g. PHP, C#, .NET, Java, 1C, Bitrix)
    foreign_tech = [
        r'\bphp\b', r'\blaravel\b', r'\bc#\b', r'\.net\b', r'\bjava(?!script)\b',
        r'\bruby\b', r'\bror\b', r'\b1с\b', r'\b1c\b', r'\bbitrix\b', r'\bбитрикс\b',
        r'\bwordpress\b', r'\bangular\b'
    ]
    for ft in foreign_tech:
        if re.search(ft, full_text):
            score -= 15
            break

    return max(5, min(98, score))


# ─────────────────────────────────────────────
#  Main pitch generator
# ─────────────────────────────────────────────

def select_dynamic_achievements(full_text: str, lang: str = "ru") -> List[str]:
    """Select the 2-3 most relevant real achievements from candidate's profile matching the job requirements."""
    bullets = []
    text_lower = full_text.lower()

    if lang == "en":
        if any(w in text_lower for w in ["performance", "pagespeed", "core web vitals", "speed", "оптимиз"]):
            bullets.append("Core Web Vitals & performance optimization: achieved 100/100 PageSpeed on Next.js 16 (App Router) via bundle optimization and SSR streaming.")
        if any(w in text_lower for w in ["component", "design system", "ui kit", "ui-kit", "figma", "animat", "gsap", "motion"]):
            bullets.append("Design systems & interactive UI: built modular component libraries (Cloveri for Mintsifry) and rich interactive animations via GSAP (@gsap/react), Lottie, and Embla Carousel.")
        if any(w in text_lower for w in ["auth", "security", "rbac", "cms", "dashboard", "admin"]):
            bullets.append("Shipped end-to-end admin dashboards & CMS platforms (Radiotochka), implementing RBAC, secure session cookies (httpOnly/SameSite), and robust SSR hydration.")
        if any(w in text_lower for w in ["fullstack", "backend", "fastapi", "python", "node", "postgres", "sql", "docker", "api"]):
            bullets.append("Fullstack architecture & ownership: built REST APIs with FastAPI & Node.js, PostgreSQL, multi-stage Docker builds, Traefik v3 reverse proxy with TLS, automated billing & webhooks.")
        if any(w in text_lower for w in ["hackathon", "speed", "startup", "scale", "mvp", "lead", "senior"]):
            bullets.append("1st place at Droog hackathon: architected and shipped 3 role-based interfaces with React/Redux in 48 hours under tight deadline.")

        if not bullets:
            bullets.append("Lead Frontend Engineer at NoLogs SaaS: client architecture on Next.js 16 (App Router), React 19, and TypeScript 5.")
            bullets.append("Full-cycle production delivery: from Figma design systems to Docker containerization and live deployment.")
    else:
        if any(w in text_lower for w in ["performance", "pagespeed", "скорость", "оптимиз"]):
            bullets.append("Оптимизация производительности и Core Web Vitals: результат 100/100 в PageSpeed на Next.js 16 (App Router) за счет оптимизации бандла и SSR-стриминга.")
        if any(w in text_lower for w in ["компонент", "дизайн-систем", "ui-kit", "ui kit", "figma", "анимац", "animat", "gsap", "motion", "дизайн"]):
            bullets.append("Дизайн-системы и сложный UI: опыт создания компонентных библиотек (Cloveri для Минцифры) и интерактивных сценариев на GSAP (@gsap/react), Lottie и Embla Carousel.")
        if any(w in text_lower for w in ["auth", "авториз", "rbac", "cms", "админ", "панел"]):
            bullets.append("Разработка админ-панелей и CMS (Radiotochka): реализация RBAC, безопасных session-cookies и устранение рассинхронизации SSR-гидратации с NextAuth.")
        if any(w in text_lower for w in ["fullstack", "backend", "бэкенд", "фуллстек", "fastapi", "python", "node", "postgres", "sql", "docker", "api"]):
            bullets.append("Полный стек и инфраструктура: разработка REST API на FastAPI и Node.js, PostgreSQL, multi-stage сборки в Docker, Traefik v3 c авто-TLS, интеграция эквайринга и вебхуков.")
        if any(w in text_lower for w in ["стартап", "хакатон", "mvp", "лид", "senior", "сеньор"]):
            bullets.append("1 место на хакатоне Droog: с нуля разработал 3 ролевых интерфейса за 48 часов в условиях жестких дедлайнов.")

        if not bullets:
            bullets.append("Lead Frontend-разработчик NoLogs SaaS: архитектура клиентской части на Next.js 16 (App Router), React 19, TypeScript 5.")
            bullets.append("Сквозная разработка фич от архитектуры и дизайн-системы до деплоя в Docker и поддержки пользователей.")

    return bullets[:3]


def generate_pitch(vacancy: Dict[str, Any], use_ai: bool = False, profile_id: Optional[str] = None) -> Dict[str, Any]:
    title = vacancy.get("title", "Frontend Developer")
    company = vacancy.get("company", "вашей компании")
    recipient = vacancy.get("contact_name", "")
    skills = vacancy.get("skills", "")
    desc = vacancy.get("description", "")
    lang = determine_language(vacancy)

    if profile_id is None:
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    profile_id = cfg.get("active_profile_id")
        except Exception:
            pass

    profile = select_profile(lang, profile_id=profile_id)
    name = profile.get("name", "Имя Фамилия" if lang == "ru" else "Candidate Name")

    # Clean structured contact formatting
    c_struct = profile.get("contacts_structured") or {}
    tg_val = c_struct.get("telegram") or "@username"
    email_val = c_struct.get("email") or "candidate@example.com"
    github_val = c_struct.get("github") or "https://github.com/username"
    linkedin_val = c_struct.get("linkedin") or "https://linkedin.com/in/username"

    tg = f"Telegram: {tg_val}" if not tg_val.lower().startswith("telegram:") else tg_val
    email = f"Email: {email_val}" if not email_val.lower().startswith("email:") else email_val
    github = f"GitHub: {github_val}" if not github_val.lower().startswith("github:") else github_val
    linkedin = f"LinkedIn: {linkedin_val}" if not linkedin_val.lower().startswith("linkedin:") else linkedin_val

    target_kws = extract_target_keywords(title, skills, desc)
    highlight_kw = ", ".join(target_kws[:4])

    tailored_cv = build_tailored_cv(vacancy, target_kws, lang=lang, profile=profile)

    # Anti-BS trap analysis
    warnings = analyze_vacancy_traps(desc)
    warn_text = "\n".join(warnings) if warnings else ""
    warning_header = f"[{warn_text}]\n\n" if warnings else ""

    # Select real matching achievements
    achievements = select_dynamic_achievements(f"{title} {skills} {desc}", lang=lang)
    bullet_text = "\n".join(f"• {b}" for b in achievements)

    if lang == "en":
        greeting_dm = f"Hi {recipient}!" if recipient else "Hi!"
        greeting_cl = f"Dear {company} Team," if company else "Hello Hiring Team,"

        top_fact = achievements[0] if achievements else f"I build production web apps with {highlight_kw}."

        short_dm = (
            warning_header +
            f"{greeting_dm} Saw your {title} opening at {company}.\n\n"
            f"My focus aligns directly with your stack ({highlight_kw}). {top_fact}\n\n"
            f"{github} | {linkedin}\n\n"
            f"Still interviewing for this role? Would love to connect!"
        )
        cover_letter = (
            warning_header +
            f"{greeting_cl}\n\n"
            f"I'm applying for the {title} role at {company}.\n\n"
            f"I build high-performance, maintainable web applications with React, Next.js, and TypeScript, with full technical ownership across the stack ({highlight_kw}).\n\n"
            f"Relevant experience & outcomes:\n"
            f"{bullet_text}\n\n"
            f"Would be glad to discuss how my background can help your team ship fast and scale.\n\n"
            f"Best regards,\n{name}\n{tg} | {email}\n{github} | {linkedin}"
        )
    else:
        greeting_dm = f"Привет, {recipient}!" if recipient else "Привет!"

        top_fact = achievements[0] if achievements else f"Специализируюсь на продуктовой веб-разработке с фокусом на {highlight_kw}."

        short_dm = (
            warning_header +
            f"{greeting_dm} Увидел вакансию «{title}» в {company}.\n\n"
            f"Мой стек и опыт напрямую пересекаются с вашими задачами ({highlight_kw}). {top_fact}\n\n"
            f"{github} | {linkedin}\n\n"
            f"Если позиция актуальна — буду рад пообщаться!"
        )
        cover_letter = (
            warning_header +
            f"Здравствуйте!\n\n"
            f"Меня зовут {name}, откликаюсь на вакансию «{title}» в {company}.\n\n"
            f"Специализируюсь на фронтенде и фуллстек-разработке (React, Next.js, TypeScript). Фокусируюсь на чистой архитектуре, высокой производительности и надежности в production ({highlight_kw}).\n\n"
            f"Ключевой опыт под задачи позиции:\n"
            f"{bullet_text}\n\n"
            f"Буду рад обсудить задачи с командой!\n\n"
            f"Контакты:\n{tg} | {email}\n{github} | {linkedin}"
        )

    # Calculate baseline heuristic score
    score = calculate_match_score(vacancy, profile)
    ai_generated = False
    ai_error = None

    # ONLY call AI when explicitly requested (saves tokens and prevents unexpected API costs)
    if use_ai:
        ai_res = generate_ai_pitch(vacancy, profile, warn_text, lang=lang)
        if ai_res.get("success"):
            ai_dm = ai_res.get("short_dm", "")
            ai_cl = ai_res.get("cover_letter", "")
            if ai_dm:
                short_dm = warning_header + ai_dm
            if ai_cl:
                cover_letter = warning_header + ai_cl
            ai_score = ai_res.get("score")
            if isinstance(ai_score, (int, float)) and ai_score > 0:
                score = int(ai_score)
            ai_generated = True
        else:
            ai_error = ai_res.get("error", "Не удалось сгенерировать ответ через ИИ")

    return {
        "short_dm": short_dm.strip(),
        "cover_letter": cover_letter.strip(),
        "tailored_cv": tailored_cv.strip(),
        "target_keywords": target_kws,
        "language": lang,
        "score": score,
        "ai_generated": ai_generated,
        "ai_error": ai_error
    }
