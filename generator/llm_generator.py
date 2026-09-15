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
You are {name}, writing directly to an engineering team or tech recruiter.
Write in the first person ("I" / "я").

JOB DETAILS:
- Role: {title}
- Company: {company}
- Requirements & Description:
{desc}

MY PROFILE & BACKGROUND:
- Name: {name}
- Role: {role}
- Core Summary: {summary}
- Projects & Track Record:
{exp}
- Tech Stack: {keywords}
- Contacts: Telegram: {tg} | Email: {email} | GitHub: {github} | LinkedIn: {linkedin}

LANGUAGE: {language_name}

CRITICAL RULES (SENIOR ENGINEER TONE):
1. NO AI CLICHES: Never say "I hope this email finds you well", "I was thrilled to see", "As an AI", "In today's fast-paced digital world", "I am writing to express my enthusiasm", or similar generic boilerplate.
2. SHORT DM (for Telegram/LinkedIn outreach):
   - 2 to 3 sentences maximum.
   - Natural, direct, professional developer tone.
   - Directly state your core stack fit and reference 1 specific matching metric/project from your real background (e.g. NoLogs SaaS ownership, 100/100 PageSpeed, complex animations, FastAPI/Docker).
   - Crisp call to action (e.g. asking if they are currently interviewing).
3. COVER LETTER (for job portals/email):
   - 2 to 3 concise, punchy paragraphs.
   - Paragraph 1: Direct application for {title} at {company}. State core expertise that matches their specific pain points.
   - Paragraph 2: 2-3 specific bullet points highlighting real engineering outcomes and technologies matching THIS job description.
   - Paragraph 3: Brief wrap-up and clean contact signature.
4. WARNINGS TO ACCOUNT FOR: {warnings if warnings else "None"} (If a specific code word or trap was flagged, handle it naturally).
5. MATCH SCORE: Integer from 0 to 100 assessing real tech stack fit.

Respond ONLY with valid JSON in this exact structure:
{{
  "short_dm": "...",
  "cover_letter": "...",
  "score": 85
}}
"""

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.5-flash-lite"
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
            with urllib.request.urlopen(req, timeout=9) as response:
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
            if he.code == 404:
                # Model not found on this endpoint, try next model
                continue
            if he.code == 403:
                return {
                    "success": False,
                    "error": "Gemini API 403 Forbidden (Требуется VPN для доступа из РФ или проверьте права ключа)"
                }
            if he.code == 400:
                return {
                    "success": False,
                    "error": "Неверный Gemini API ключ или запрос (400)"
                }
        except urllib.error.URLError as ue:
            last_error = f"Сетевая ошибка: {ue.reason} (Проверьте подключение к интернету / VPN)"
            break
        except Exception as e:
            last_error = f"Ошибка генерации: {str(e)}"
            break

    return {
        "success": False,
        "error": last_error or "Не удалось получить ответ от Gemini API (проверьте VPN)"
    }
