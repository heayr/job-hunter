import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from generator.llm_generator import get_api_key, GEMINI_MODELS

# ── STRATEGIC FRAMING PRESETS ────────────────────────────────────────────────

STRATEGIC_PRESETS_RU = {
    "performance": {
        "pattern": r'(?:performance|скорост|pagespeed|оптимиз|core web vitals|lcp|cls|бандл)',
        "pain": "Падение Core Web Vitals, тяжелый JS-бандл или долгий LCP, ухудшающий конверсию",
        "claim": "Оптимизация производительности и Core Web Vitals до 100/100",
        "framing": "Архитектурная оптимизация клиентской части: достижение 100/100 в Google PageSpeed на Next.js 16 (App Router) за счет изоляции серверных компонентов (RSC), SSR-стриминга и устранения раздувания клиентского бандла.",
        "seniority": "Lead / Senior Architect",
        "defensibility": "HIGH (аргументация на базе RSC, App Router, bundle analyzer и code splitting)"
    },
    "design_system": {
        "pattern": r'(?:компонент|дизайн-систем|ui kit|ui-kit|figma|анимац|gsap|motion|верстк|интерфейс)',
        "pain": "Фрагментация UI, отсутствие консистентной дизайн-системы и медленная разработка новых экранов",
        "claim": "Разработка модульных дизайн-систем и сложного интерактивного UI",
        "framing": "Сквозное проектирование дизайн-систем и UI-библиотек из Figma: опыт построения компонентных библиотек (Cloveri для Минцифры) и кастомных интерактивных сценариев на GSAP (@gsap/react), Lottie и Tailwind CSS v4 без сторонних перегруженных зависимостей.",
        "seniority": "Senior / Lead UI Engineer",
        "defensibility": "HIGH (опыт создания библиотек компонентов и работы с токенами)"
    },
    "admin_rbac": {
        "pattern": r'(?:auth|авториз|rbac|cms|админ|панел|безопасн|session|cookie)',
        "pain": "Сложности с разграничением прав доступа (RBAC), безопасностью сессий и рассинхроном SSR-гидратации",
        "claim": "Разработка защищенных CMS и аналитических платформ с RBAC",
        "framing": "Разработка enterprise админ-панелей и CMS (Radiotochka): проектирование гранулярного ролевого доступа (RBAC), безопасных session-cookies (httpOnly, SameSite) и полное устранение проблем гидратации с NextAuth.",
        "seniority": "Senior Fullstack / Product Engineer",
        "defensibility": "HIGH (демонстрация реальной архитектуры сессий и прав доступа)"
    },
    "fullstack_ownership": {
        "pattern": r'(?:fullstack|бэкенд|backend|fastapi|python|node|postgres|sql|docker|api|инфраструктур)',
        "pain": "Блокировки фронтенда из-за медленной поставки серверных API, нехватка рук на бэкенде",
        "claim": "Сквозная разработка под ключ: от интерфейса до API и Docker",
        "framing": "Полное владение фичами (End-to-End Ownership): автономное проектирование REST API на FastAPI и Node.js, модели данных PostgreSQL, упаковка в multi-stage Docker контейнеры с Traefik v3 и авто-TLS без ожидания выделенного бэкенда.",
        "seniority": "Lead Product Engineer / Autonomous Senior",
        "defensibility": "HIGH (знание FastAPI, Docker, SQL, API contracts)"
    },
    "velocity_startups": {
        "pattern": r'(?:скорость|дедлайн|стартап|mvp|хакатон|сжатые сроки|гибкост)',
        "pain": "Потребность в сверхбыстром выводе фич на рынок и тестировании продуктовых гипотез без бюрократии",
        "claim": "Экстремальная скорость поставки и победы на хакатонах",
        "framing": "1 место на хакатоне Droog: с нуля спроектировал и запустил 3 ролевых интерфейса за 48 часов в условиях жесткого дедлайна. Прагматичный фокус на business-impact без оверинжиниринга.",
        "seniority": "Fast-Paced Senior / Founding Engineer",
        "defensibility": "HIGH (подтвержденный диплом и работающий проект)"
    }
}

STRATEGIC_PRESETS_EN = {
    "performance": {
        "pattern": r'(?:performance|speed|pagespeed|optimiz|core web vitals|lcp|cls|bundle)',
        "pain": "Core Web Vitals degradation, bloated JavaScript payloads, and slow LCP harming conversion",
        "claim": "Core Web Vitals & performance optimization to 100/100 PageSpeed",
        "framing": "Client-side architectural modernization: achieved 100/100 in Google PageSpeed on Next.js 16 (App Router) via React Server Components streaming, aggressive bundle splitting, and zero-bloat state architectures.",
        "seniority": "Lead / Senior Architect",
        "defensibility": "HIGH (proven Next.js App Router & streaming benchmarks)"
    },
    "design_system": {
        "pattern": r'(?:component|design system|ui kit|ui-kit|figma|animat|gsap|motion|frontend|ui)',
        "pain": "UI fragmentation, inconsistent components across teams, and slow front-end delivery",
        "claim": "Modular design system engineering & rich interactive UI",
        "framing": "Design system & component library engineering: built reusable UI kits directly from Figma (Cloveri project) and high-performance interactive interfaces using GSAP (@gsap/react), Lottie, and modern Tailwind CSS without bloated dependencies.",
        "seniority": "Senior UI / Product Engineer",
        "defensibility": "HIGH (hands-on experience with modular UI libraries & tokens)"
    },
    "admin_rbac": {
        "pattern": r'(?:auth|rbac|cms|dashboard|admin|security|session|cookie)',
        "pain": "Complex role-based access control (RBAC), session vulnerabilities, and SSR hydration mismatches",
        "claim": "Enterprise dashboard & CMS platform engineering with RBAC",
        "framing": "Shipped end-to-end admin dashboards & CMS platforms (Radiotochka): implemented granular RBAC, secure session-cookies (httpOnly, SameSite), and eliminated SSR hydration errors with NextAuth.",
        "seniority": "Senior Fullstack / Product Engineer",
        "defensibility": "HIGH (concrete session management and authorization architecture)"
    },
    "fullstack_ownership": {
        "pattern": r'(?:fullstack|full-stack|backend|fastapi|python|node|postgres|sql|docker|api|infra)',
        "pain": "Frontend blockers caused by slow backend API cycles and lack of full-cycle ownership",
        "claim": "End-to-End Ownership: from UI architecture to backend APIs & Docker",
        "framing": "End-to-End Feature Ownership: autonomous delivery from Figma to production. Designed REST APIs with FastAPI & Node.js, PostgreSQL relational models, multi-stage Docker builds, and Traefik v3 TLS routing without waiting for dedicated backend teams.",
        "seniority": "Lead Product Engineer / Autonomous Senior",
        "defensibility": "HIGH (solid API contracts, SQL models, and containerization)"
    },
    "velocity_startups": {
        "pattern": r'(?:velocity|speed|deadline|startup|mvp|hackathon|fast-paced|early stage)',
        "pain": "Urgent requirement for rapid time-to-market and autonomous shipping under tight deadlines",
        "claim": "Extreme shipping velocity & proven hackathon victory",
        "framing": "1st place at Droog Hackathon: architected and shipped 3 role-based interfaces in 48 hours under strict deadline. Relentless focus on delivery velocity and business value without over-engineering.",
        "seniority": "Founding / Fast-Paced Senior Engineer",
        "defensibility": "HIGH (verifiable 1st place track record and live deliverables)"
    }
}


def heuristic_evidence_retrieval(
    profile: Dict[str, Any],
    job_understanding: Dict[str, Any],
    lang: str = "ru"
) -> Dict[str, Any]:
    """
    Offline heuristic reframing engine that maps company pain points to
    high-impact candidate evidence statements.
    """
    presets = STRATEGIC_PRESETS_RU if lang == "ru" else STRATEGIC_PRESETS_EN

    # Collect job context signals
    facts = job_understanding.get("facts", {})
    reasoning = job_understanding.get("reasoning", {})
    overview = job_understanding.get("role_overview", {})

    combined_text = " ".join([
        overview.get("title", ""),
        " ".join(facts.get("explicit_requirements", [])),
        " ".join(facts.get("responsibilities", [])),
        " ".join(reasoning.get("likely_team_problems", [])),
        " ".join(reasoning.get("engineering_signals", []))
    ]).lower()

    matched_evidence = []
    selected_keys = []

    # Match in priority order
    for key, preset in presets.items():
        if re.search(preset["pattern"], combined_text, re.I):
            selected_keys.append(key)
            matched_evidence.append({
                "job_pain_point": preset["pain"],
                "candidate_claim": preset["claim"],
                "aggressive_framing": preset["framing"],
                "seniority_signal": preset["seniority"],
                "interview_defensibility": preset["defensibility"]
            })

    # Ensure at least 2 strong strategic anchors are always present
    fallback_order = ["fullstack_ownership", "design_system", "performance"]
    for fb_key in fallback_order:
        if len(matched_evidence) >= 3:
            break
        if fb_key not in selected_keys:
            preset = presets[fb_key]
            selected_keys.append(fb_key)
            matched_evidence.append({
                "job_pain_point": preset["pain"],
                "candidate_claim": preset["claim"],
                "aggressive_framing": preset["framing"],
                "seniority_signal": preset["seniority"],
                "interview_defensibility": preset["defensibility"]
            })

    # Strategic narrative & positioning
    if lang == "ru":
        positioning = "Senior / Lead Product Engineer со сквозным владением (End-to-End Ownership): от архитектуры интерфейса и дизайн-системы до серверных API и деплоя в Docker"
        leverage_points = [
            "Автономность: способность в одиночку закрывать модули и фичи под ключ без нянченья со стороны тимлида",
            "Реальный опыт оптимизации Core Web Vitals до 100/100 на Next.js 16 App Router",
            "Высокая скорость поставки, доказанная 1-м местом на хакатоне (3 интерфейса за 48 часов)"
        ]
        defensive_pivots = [
            "Если в вакансии упоминаются редкие или легаси библиотеки: делать упор на глубокий фундамент в React 19 / TypeScript, позволяющий освоить смежный инструмент за пару дней без рисков для продакшна."
        ]
    else:
        positioning = "Senior / Lead Product Engineer with End-to-End Ownership: from UI architecture and design systems to backend APIs and Docker deployments"
        leverage_points = [
            "Complete autonomy: takes features from Figma to production without requiring micro-management",
            "Proven performance benchmark: achieved 100/100 Core Web Vitals on Next.js 16 App Router",
            "Exceptional delivery velocity: 1st place in Droog hackathon (shipped 3 role-based apps in 48 hours)"
        ]
        defensive_pivots = [
            "If asked about obscure or unmentioned niche libraries: pivot to deep TypeScript/React architecture fundamentals ensuring zero onboarding drag."
        ]

    return {
        "matched_evidence": matched_evidence[:3],
        "strategic_narrative": {
            "positioning_angle": positioning,
            "leverage_points": leverage_points,
            "defensive_pivots": defensive_pivots
        }
    }


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
    candidate_evidence = profile.get("evidence", [])
    raw_exp = profile.get("experience", "")[:2000]

    job_title = job_understanding.get("role_overview", {}).get("title", "Engineer")
    company = job_understanding.get("role_overview", {}).get("company", "Company")
    problems = job_understanding.get("reasoning", {}).get("likely_team_problems", [])
    signals = job_understanding.get("reasoning", {}).get("engineering_signals", [])
    explicit_reqs = job_understanding.get("facts", {}).get("explicit_requirements", [])

    language_name = "Russian" if lang == "ru" else "English"

    prompt = f"""You are a Strategic Career Agent representing {candidate_name} ({target_role}).
Your job is to build an AGGRESSIVE, HIGH-STATUS engineering positioning package connecting this company's hidden pain points to the candidate's real capabilities.

CRITICAL INSTRUCTIONS:
1. NO ACADEMIC TIMIDITY: Frame the candidate as a decisive Senior / Lead Product Engineer who owns features end-to-end (Figma -> Client Architecture -> API Contracts -> Docker/Production).
2. REAL CAPABILITY ANCHORING: Every claim must be defensible in an interview. Anchor all claims in the candidate's verified stack:
   - React 19, TypeScript 5, Next.js 16 (App Router, RSC, Streaming, PageSpeed 100/100).
   - Fast delivery (1st place at Droog Hackathon: 3 role-based interfaces in 48h).
   - Design systems & modular UI (Cloveri for Mintsifry, GSAP, Tailwind CSS v4).
   - Fullstack versatility (FastAPI, Node.js, PostgreSQL, Docker, Traefik, session cookies).
   - Admin platforms & RBAC (Radiotochka CMS).
3. STRICT NO FOUNDER / NO PET-PROJECT MARKERS: Never mention being a 'founder', 'owner', or 'pet project'. Frame all SaaS work as Lead Engineer roles.

JOB CONTEXT ({company} — {job_title}):
- Team Pains: {json.dumps(problems, ensure_ascii=False)}
- Engineering Signals: {json.dumps(signals, ensure_ascii=False)}
- Hard Requirements: {json.dumps(explicit_reqs, ensure_ascii=False)}

CANDIDATE EVIDENCE & EXPERIENCE:
{raw_exp}

LANGUAGE: {language_name}

Respond ONLY with valid JSON in this exact structure:
{{
  "matched_evidence": [
    {{
      "job_pain_point": "The specific bottleneck or need this company has",
      "candidate_claim": "The capability from candidate profile addressing it",
      "aggressive_framing": "High-impact, senior-level bullet point showing business & technical value",
      "seniority_signal": "Lead / Senior Architect",
      "interview_defensibility": "HIGH (can discuss X, Y, Z in depth)"
    }}
  ],
  "strategic_narrative": {{
    "positioning_angle": "Core positioning angle",
    "leverage_points": ["Point 1", "Point 2", "Point 3"],
    "defensive_pivots": ["Pivot statement for interview"]
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
