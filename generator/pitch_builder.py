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


def select_profile(lang: str) -> Dict:
    """Pick the best profile for the given language from profiles.json."""
    profiles = load_profiles()
    # Prefer exact language match
    for p in profiles:
        if p.get('lang', 'ru') == lang:
            return p
    # Fallback: first profile regardless of language
    if profiles:
        return profiles[0]
    # Hard fallback if profiles.json is empty
    return {
        "name": "Candidate Name",
        "lang": "en",
        "role": "Frontend / Fullstack Engineer",
        "contacts": "Telegram: @username | Email: candidate@example.com | GitHub: https://github.com/username | LinkedIn: https://linkedin.com/in/username",
        "keywords": "React, Next.js, TypeScript, JavaScript, Redux Toolkit, Tailwind CSS, Node.js, FastAPI, Docker",
        "summary": "Fullstack Engineer with experience building production web applications with React, Next.js and TypeScript.",
        "experience": "• Engineered high-performance web applications\n• Delivered production-ready microservices and REST APIs\n• Integrated modern auth, state management, and containerized deployments",
    }


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

def build_tailored_cv(vacancy: Dict[str, Any], target_keywords: List[str], lang: str = "ru") -> str:
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

def calculate_match_score(vacancy: Dict[str, Any], profile: Dict[str, Any]) -> int:
    """
    Calculates deterministic match percentage (0-100%) based on tech stack overlap,
    role seniority, and keywords between vacancy and candidate profile.
    """
    title = (vacancy.get("title") or "").lower()
    desc = (vacancy.get("description") or "").lower()
    skills = (vacancy.get("skills") or "").lower()
    full_text = f"{title} {skills} {desc}"

    # 1. Base score for qualified frontend/fullstack role
    score = 35

    # 2. Core stack points (up to +30)
    matched_core = 0
    for tech, pts in [("react", 10), ("typescript", 10), ("next.js", 10), ("nextjs", 10), ("javascript", 5)]:
        if tech in full_text:
            matched_core = min(30, matched_core + pts)
    score += matched_core

    # 3. Secondary stack / tools (up to +25)
    secondary_tech = [
        "tailwind", "fastapi", "docker", "redux", "node.js", "nodejs",
        "graphql", "rest", "postgresql", "ci/cd", "git", "vite",
        "webpack", "vitest", "jest", "zustand", "tanstack", "react query"
    ]
    matched_sec = sum(3 for tech in secondary_tech if tech in full_text)
    score += min(25, matched_sec)

    # 4. Seniority / leadership bonus (up to +10)
    if any(k in title for k in ["lead", "senior", "лид", "ведущий", "architect", "founding"]):
        score += 10
    elif any(k in title for k in ["middle", "мидл", "fullstack", "фуллстек"]):
        score += 5

    return max(30, min(98, score))


# ─────────────────────────────────────────────
#  Main pitch generator
# ─────────────────────────────────────────────

def select_dynamic_achievements(full_text: str, lang: str = "ru") -> List[str]:
    """Select the 2-3 most relevant real achievements from candidate's profile matching the job requirements."""
    bullets = []
    text_lower = full_text.lower()

    if lang == "en":
        if any(w in text_lower for w in ["next", "react", "frontend", "ui", "performance", "speed", "tailwind", "css"]):
            bullets.append("Lead Engineer at NoLogs SaaS: production web app on Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS v4, achieving 100/100 Google PageSpeed Insights.")
        if any(w in text_lower for w in ["fullstack", "backend", "fastapi", "python", "node", "postgres", "sql", "docker", "api"]):
            bullets.append("Fullstack architecture & ownership: built REST APIs with FastAPI & Node.js, PostgreSQL, multi-stage Docker builds, Traefik v3 reverse proxy with TLS, automated billing & webhooks.")
        if any(w in text_lower for w in ["animat", "gsap", "motion", "creative", "design", "figma"]):
            bullets.append("Rich interactive UI engineering: custom animation sequences via GSAP (@gsap/react), Lottie, and Embla Carousel with zero heavy external motion bloat.")
        if any(w in text_lower for w in ["auth", "security", "rbac", "cms", "dashboard", "admin"]):
            bullets.append("Shipped end-to-end admin dashboards & CMS platforms (Radiotochka), implementing RBAC, secure session cookies (httpOnly/SameSite), and robust SSR hydration.")
        if any(w in text_lower for w in ["speed", "startup", "scale", "hackathon", "mvp", "lead", "senior"]):
            bullets.append("1st place at Droog hackathon (delivered 3 role-based interfaces in 48h) and contributed to public component libraries with clean design systems.")

        if not bullets:
            bullets.append("Lead Engineer at NoLogs SaaS (Next.js 16, React 19, TypeScript, FastAPI, 100/100 PageSpeed).")
            bullets.append("Full-cycle production delivery: from Figma design systems to Docker containerization and live deployment.")
    else:
        if any(w in text_lower for w in ["next", "react", "frontend", "ui", "performance", "speed", "tailwind", "верстк", "интерфейс"]):
            bullets.append("Lead-разработчик NoLogs SaaS: продакшен-сервис на Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS v4, результат 100/100 в Google PageSpeed Insights.")
        if any(w in text_lower for w in ["fullstack", "backend", "бэкенд", "фуллстек", "fastapi", "python", "node", "postgres", "sql", "docker", "api"]):
            bullets.append("Полный стек и инфраструктура: разработка REST API на FastAPI и Node.js, PostgreSQL, multi-stage сборки в Docker, Traefik v3 c авто-TLS, интеграция эквайринга и вебхуков.")
        if any(w in text_lower for w in ["анимац", "animat", "gsap", "motion", "дизайн", "figma"]):
            bullets.append("Сложный анимированный UI: интерактивные сценарии на GSAP (@gsap/react), Lottie и Embla Carousel без лишних тяжелых библиотек.")
        if any(w in text_lower for w in ["auth", "авториз", "rbac", "cms", "админ", "панел"]):
            bullets.append("Разработка админ-панелей и CMS (Radiotochka): реализация RBAC, безопасных session-cookies и стабильной SSR-гидратации.")
        if any(w in text_lower for w in ["скорость", "стартап", "хакатон", "mvp", "лид", "senior", "сеньор"]):
            bullets.append("1 место на хакатоне Droog (с нуля разработал 3 ролевых интерфейса за 48 часов) и опыт создания компонентных библиотек (Cloveri для Минцифры).")

        if not bullets:
            bullets.append("Lead-разработчик NoLogs SaaS (Next.js 16, React 19, TypeScript, FastAPI, 100/100 PageSpeed).")
            bullets.append("Полный цикл владения продуктом: от архитектуры и дизайн-системы до деплоя в Docker и поддержки реальных пользователей.")

    return bullets[:3]


def generate_pitch(vacancy: Dict[str, Any], use_ai: bool = False) -> Dict[str, Any]:
    title = vacancy.get("title", "Frontend Developer")
    company = vacancy.get("company", "вашей компании")
    recipient = vacancy.get("contact_name", "")
    skills = vacancy.get("skills", "")
    desc = vacancy.get("description", "")
    lang = determine_language(vacancy)

    profile = select_profile(lang)
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

    tailored_cv = build_tailored_cv(vacancy, target_kws, lang=lang)

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
