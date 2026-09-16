import urllib.request
import urllib.error
import json
import os
import re
from typing import Dict, Any, Optional

def get_api_key() -> str:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                key = json.load(f).get('gemini_api_key', '')
                if key and key.strip():
                    return key.strip()
        except Exception:
            pass
    return os.environ.get("GEMINI_API_KEY", "").strip()


def generate_ai_pitch(
    vacancy: Dict[str, Any],
    profile: Any,
    warnings: str = "",
    lang: str = "ru"
) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        return {"success": False, "error": "Gemini API ключ не указан в Настройках ИИ"}

    title = vacancy.get("title", "Frontend Engineer")
    company = vacancy.get("company", "Company")
    desc = (vacancy.get("description") or "")[:2500]

    # Format profile data cleanly
    if isinstance(profile, dict):
        name = profile.get("name", "Имя Фамилия" if lang == "ru" else "Candidate Name")
        role = profile.get("role", "Lead Frontend / Fullstack Engineer")
        summary = profile.get("summary", "")
        exp = profile.get("experience", "")[:2000]
        keywords = profile.get("keywords", "")
        contacts_struct = profile.get("contacts_structured", {})
        tg = contacts_struct.get("telegram", "@username")
        email = contacts_struct.get("email", "candidate@example.com")
        github = contacts_struct.get("github", "https://github.com/username")
        linkedin = contacts_struct.get("linkedin", "https://linkedin.com/in/username")
    else:
        name = "Имя Фамилия" if lang == "ru" else "Candidate Name"
        role = "Frontend / Fullstack Engineer"
        summary = str(profile)
        exp = ""
        keywords = "React, Next.js, TypeScript, Tailwind CSS, FastAPI, Docker, Node.js"
        tg = "@username"
        email = "candidate@example.com"
        github = "https://github.com/username"
        linkedin = "https://linkedin.com/in/username"

    language_name = "Russian" if lang == "ru" else "English"

    prompt = f"""
You are {name}, an experienced engineer writing directly to an engineering lead, tech founder, or hiring manager.
Write in the first person ("I" / "я").

JOB DETAILS:
- Role: {title}
- Company: {company}
- Requirements & Description:
{desc}

MY REAL PROFILE & BACKGROUND:
- Name: {name}
- Role: {role}
- Core Summary: {summary}
- Real Projects & Track Record:
{exp}
- Tech Stack: {keywords}
- Contacts: Telegram: {tg} | Email: {email} | GitHub: {github} | LinkedIn: {linkedin}

LANGUAGE: {language_name}

POSITIONING STRATEGY (FRONTEND / PRODUCT ENGINEER WITH END-TO-END OWNERSHIP):
1. T-SHAPED CORE:
   - Deep expertise: React 19, TypeScript, Next.js 15/16 (App Router, Server/Client components, SSR/SSG, caching, bundle optimization, 100/100 PageSpeed, clean component architecture & state).
   - Solid engineering breadth: API contracts, HTTP/status codes, auth/session cookies (httpOnly, SameSite), optimistic updates, robust error handling, Git, GitHub Actions CI/CD, multi-stage Docker builds, Traefik/Nginx, and root-cause debugging across the entire web stack.
   - DO NOT sound like an unfocused "knows 25 random backends" junior. Sound like an autonomous engineer who takes a feature or product from Figma/requirements to live production.
2. DYNAMICALLY MATCH THE CANDIDATE'S STRONGEST PROOF TO THE JOB'S PRIMARY NEED:
   Do NOT mindlessly repeat the same metric for every vacancy. Look at what THIS company values most and pick the matching proof:
   - UI/UX, Design Systems, Animations, Component Kits:
     Highlight: Experience building reusable component libraries from Figma (Cloveri project for Mintsifry) and custom interactive animations (GSAP, Lottie, Embla Carousel, Tailwind CSS v4) without bloated third-party libraries.
   - Dashboards, CMS, Role-Based Access, Web Apps:
     Highlight: Developed end-to-end CMS platforms and admin dashboards (Radiotochka), implementing RBAC, secure session-cookies (httpOnly/SameSite), and eliminating SSR hydration mismatches.
   - Execution Speed, Hackathons, Startups, MVPs:
     Highlight: 1st place at Droog hackathon (shipped 3 role-based interfaces in 48 hours under strict deadline) and fast autonomous delivery without waiting for micromanagement.
   - Fullstack Ownership, API Contracts, Integrations:
     Highlight: End-to-end feature delivery: FastAPI/Node.js REST APIs, payment webhooks (ЮKassa/HMAC), background bots, multi-stage Docker builds with Traefik/Nginx, and Vitest unit testing.
   - Core Performance (ONLY when the job specifically asks for speed/optimization):
     Highlight: Bundle optimization, SSR/RSC rendering strategies, and zero-bloat delivery.

3. STRICT NO FOUNDER / NO PET-PROJECT MARKERS:
   - NEVER say or imply that you are the "founder", "creator", "owner", or running your "own startup" ("создатель", "владелец", "фаундер", "мой стартап", "мое детище", "свой проект").
   - Employers see this as a red flag (risk of distraction or moonlighting).
   - Frame your experience purely as a Senior Engineering role: "Lead Frontend / Product Engineer в продуктовом SaaS NoLogs", highlighting client-side architecture, React 19, TypeScript, and shipping production features.

4. NO AI CLICHES: Never use generic buzzwords ("thrilled to apply", "in today's fast-paced world", "I hope this finds you well", "as an enthusiast", "идеально подхожу").

5. SHORT DM (for Telegram/LinkedIn outreach):
   - 2 to 3 sentences maximum.
   - Sentence 1: Direct mention of their opening + your relevant technical focus.
   - Sentence 2: 1 specific proof point tailored to THEIR specific requirement (from the proof points above).
   - Sentence 3: Crisp, peer-to-peer call to action.

6. COVER LETTER (for portal/email):
   - Paragraph 1: Direct application for {title} at {company}. State core expertise addressing their exact technical need.
   - Paragraph 2: 2-3 specific bullet points connecting your real engineering outcomes to their required tech stack and problems (vary the bullets: 1 UI/Frontend, 1 Architecture/Integration, 1 Product/Delivery).
   - Paragraph 3: Wrap-up + clean contact signature.
6. WARNINGS TO ACCOUNT FOR: {warnings if warnings else "None"} (If a specific code word or trap was flagged, address it naturally).
7. MATCH SCORE (0 to 100):
   - Evaluate real career fit for the candidate's TARGET role (Frontend / Fullstack / Product Web Engineer).
   - PENALTY FOR NON-TARGET PROFESSIONS: If this vacancy is for QA / SDET / Тестировщик, DevOps / SRE / Sysadmin, Data Science / ML, Product / Project Manager, Designer, or HR — give it a LOW score (10 to 30) because the core profession does NOT match, even if common tools (Git, Docker, JS) are mentioned!
   - High scores (75 to 98) are strictly for Frontend / Fullstack / Product Web Developer roles matching React, Next.js, and TypeScript.

Respond ONLY with valid JSON in this exact structure:
{{
  "short_dm": "...",
  "cover_letter": "...",
  "score": 75
}}
"""

    models_to_try = [
        "models/gemini-flash-lite-latest",
        "models/gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-flash-latest"
    ]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "responseMimeType": "application/json"
        }
    }

    last_error = ""

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                resp_text = response.read().decode('utf-8')
                resp_data = json.loads(resp_text)
                text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Clean possible markdown wrapping if any
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text).strip()
                parsed = json.loads(text)
                return {
                    "success": True,
                    "short_dm": parsed.get("short_dm", "").strip(),
                    "cover_letter": parsed.get("cover_letter", "").strip(),
                    "score": int(parsed.get("score", 75))
                }
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='ignore')
            last_error = f"HTTP {he.code}: {he.reason}"
            if he.code in (404, 429, 500, 502, 503, 504):
                # Temporary Google capacity spike (503), rate limit (429) or missing model -> try next model
                continue
            if he.code == 403:
                return {
                    "success": False,
                    "error": "Gemini API 403 Forbidden (Требуется активный VPN для доступа к Google AI из РФ)"
                }
            if he.code == 400:
                return {
                    "success": False,
                    "error": "Неверный Gemini API ключ или невалидный запрос (400)"
                }
        except (TimeoutError, urllib.error.URLError) as ue:
            reason_str = str(getattr(ue, 'reason', ue))
            if "timed out" in reason_str.lower() or isinstance(ue, TimeoutError):
                last_error = "Таймаут соединения с Gemini API (проверьте стабильность VPN или повторите попытку)"
            else:
                last_error = f"Сетевая ошибка: {reason_str} (Проверьте подключение к интернету / VPN)"
            continue
        except Exception as e:
            if "timed out" in str(e).lower():
                last_error = "Таймаут соединения с Gemini API (проверьте стабильность VPN или повторите попытку)"
            else:
                last_error = f"Ошибка генерации: {str(e)}"
            continue

    return {
        "success": False,
        "error": last_error or "Не удалось получить ответ от Gemini API (проверьте VPN)"
    }
