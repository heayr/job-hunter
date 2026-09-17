import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import urllib.error
import json
import re
import html
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from generator.llm_generator import get_api_key, GEMINI_MODELS
from generator.pitch_builder import generate_pitch
from filter.profile_filter import detect_vacancy_grade
from tracker.db import get_db_connection, save_vacancy
from enricher.lead_finder import extract_contacts


def fetch_clean_text_from_url(url: str) -> str:
    """Fetches HTML from a URL and strips away markup, scripts, and styles."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        raw_html = response.read().decode('utf-8', errors='ignore')

    # Remove non-content elements
    cleaned = re.sub(r'<(script|style|svg|noscript|header|footer|nav)[\s\S]*?</\1>', ' ', raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!--[\s\S]*?-->', ' ', cleaned)
    
    # Replace block level elements with newlines
    cleaned = re.sub(r'<(?:p|div|br|hr|li|h[1-6]|tr)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    
    # Compress repetitive whitespaces and excessive newlines
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.split('\n')]
    non_empty = [line for line in lines if line]
    
    # Join text, keeping up to 7000 chars for LLM context
    full_text = '\n'.join(non_empty)
    return full_text[:7000]


def heuristic_fallback_parse(raw_text: str, source_url: str = "") -> Dict[str, Any]:
    """Fallback extraction when AI is unavailable or offline."""
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    first_few = " ".join(lines[:5])
    
    # Detect Title
    title = "Software Engineer"
    title_match = re.search(r'(?:vacancy|вакансия|position|должность|роль)[\s:]*([^\n,.]+)', first_few, re.I)
    if title_match:
        title = title_match.group(1).strip()
    elif lines:
        title = lines[0][:80]

    # Detect Company
    company = "Direct Employer"
    comp_match = re.search(r'(?:компания|company|команда)[\s:]*([A-Za-zА-Яа-я0-9\s_-]+)', first_few, re.I)
    if comp_match:
        company = comp_match.group(1).strip()

    # Detect Remote
    is_remote = 1 if re.search(r'\b(remote|удаленк|дистанцион|удаленно|anywhere)\b', raw_text, re.I) else 0

    # Detect Contacts
    contacts = extract_contacts(raw_text)
    contact_handle = contacts.get("primary_handle") or source_url or ""
    contact_type = contacts.get("primary_type") or ("email" if "@" in contact_handle else "portal")

    grade = detect_vacancy_grade(title, raw_text[:1000])

    return {
        "title": title,
        "company": company,
        "location": "Remote" if is_remote else "По договоренности",
        "is_remote": is_remote,
        "salary": "По договоренности",
        "grade": grade,
        "language": "ru" if re.search(r'[а-яА-Я]', raw_text[:500]) else "en",
        "skills": "React, TypeScript, Frontend, Web",
        "description": raw_text[:2500],
        "contact_name": contacts.get("contact_name") or "",
        "contact_handle": contact_handle,
        "contact_type": contact_type
    }


def parse_with_gemini(raw_text: str, source_url: str = "") -> Dict[str, Any]:
    """Uses Gemini to parse unstructured job text into strict CRM schema."""
    api_key = get_api_key()
    if not api_key:
        return heuristic_fallback_parse(raw_text, source_url)

    prompt = f"""You are an expert Technical Recruiter and Headhunter.
Analyze the following unstructured job posting text (which could be from a website, Telegram message, email, or LinkedIn).
Extract key job information and output STRICT JSON matching this schema:

{{
  "title": "Clean, precise job title (e.g. Senior Frontend Engineer, Fullstack React/Node Developer)",
  "company": "Company or startup name",
  "location": "Location (e.g. Remote (Worldwide), Moscow, London, Remote (RU))",
  "is_remote": true or false,
  "salary": "Salary with currency if mentioned (e.g. 'от 300 000 ₽', '$5,000 - $7,000') or 'По договоренности'",
  "grade": "Junior" or "Middle" or "Senior" or "Lead",
  "language": "ru" or "en",
  "skills": "Comma-separated key technologies (e.g. React, TypeScript, Next.js, Redux, PostgreSQL)",
  "description": "Clean, structured summary of responsibilities, requirements, and benefits (up to 2000 characters)",
  "contact_name": "Contact person or HR name if found, else empty string",
  "contact_handle": "Direct Telegram handle (@...), email, or application URL if found",
  "contact_type": "telegram" or "email" or "portal" or "ats"
}}

Rules:
1. Do not invent facts not present in the text.
2. If language of text is Russian, set "language": "ru". If English, set "language": "en".
3. Return ONLY valid JSON, without any markdown wrappers or commentary.

Job Posting Text:
\"\"\"{raw_text[:6500]}\"\"\"
"""

    models_to_try = GEMINI_MODELS[:]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

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
                
                # Validation & sensible defaults
                return {
                    "title": str(parsed.get("title") or "Software Engineer").strip(),
                    "company": str(parsed.get("company") or "Direct Employer").strip(),
                    "location": str(parsed.get("location") or "Remote").strip(),
                    "is_remote": 1 if parsed.get("is_remote") else 0,
                    "salary": str(parsed.get("salary") or "По договоренности").strip(),
                    "grade": str(parsed.get("grade") or "Middle").strip(),
                    "language": "ru" if parsed.get("language", "").lower() == "ru" else "en",
                    "skills": str(parsed.get("skills") or "React, TypeScript, Frontend").strip(),
                    "description": str(parsed.get("description") or raw_text[:2000]).strip(),
                    "contact_name": str(parsed.get("contact_name") or "").strip(),
                    "contact_handle": str(parsed.get("contact_handle") or source_url or "").strip(),
                    "contact_type": str(parsed.get("contact_type") or "portal").strip()
                }
        except Exception as e:
            print(f"  [ai_parser] Model {model} attempt failed: {e}")

    # Fallback if all Gemini models fail or network fails
    return heuristic_fallback_parse(raw_text, source_url)


def ingest_vacancy_with_ai(
    raw_input: str,
    is_url: bool = False,
    profile_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entrypoint: parses URL or raw text, extracts vacancy schema,
    generates tailored pitches and match score, and persists directly into jobs.db.
    """
    raw_input = raw_input.strip()
    if not raw_input:
        return {"success": False, "error": "Пустой ввод"}

    source_url = ""
    clean_text = raw_input

    # Determine if input is a URL
    if is_url or raw_input.startswith("http://") or raw_input.startswith("https://"):
        source_url = raw_input.split()[0]
        try:
            clean_text = fetch_clean_text_from_url(source_url)
        except Exception as e:
            return {"success": False, "error": f"Ошибка загрузки страницы: {str(e)}"}

    if len(clean_text) < 30:
        return {"success": False, "error": "Текст вакансии слишком короткий или не содержит полезной информации"}

    # Parse with AI
    parsed = parse_with_gemini(clean_text, source_url)

    # Perform Deep Job Understanding (Phase 2)
    from generator.job_understanding import understand_job_posting
    understanding = understand_job_posting(parsed["title"], clean_text, parsed["company"], source_url)

    # Generate unique ID
    key = source_url or f"{parsed['title']}:{parsed['company']}:{clean_text[:100]}"
    vac_hash = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
    vac_id = f"ai:{vac_hash}"

    vacancy = {
        "id": vac_id,
        "source": "ai_import",
        "title": parsed["title"],
        "company": parsed["company"],
        "url": source_url or parsed.get("contact_handle") or "",
        "salary": parsed["salary"],
        "location": parsed["location"],
        "is_remote": parsed["is_remote"],
        "description": parsed["description"],
        "skills": parsed["skills"],
        "language": parsed["language"],
        "grade": parsed["grade"],
        "contact_name": parsed["contact_name"],
        "contact_handle": parsed["contact_handle"],
        "contact_type": parsed["contact_type"],
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "new"
    }

    # Generate personalized pitch & match score
    pitch_data = generate_pitch(vacancy, use_ai=True, profile_id=profile_id)
    score = pitch_data.get("score", 70)
    lang = pitch_data.get("language", vacancy["language"])

    # Persist in Database
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check if already exists
        cur.execute("SELECT id FROM vacancies WHERE id = ? OR (url = ? AND url != '')", (vac_id, vacancy["url"]))
        existing = cur.fetchone()
        if existing:
            vac_id = existing["id"]
        else:
            save_vacancy(vacancy)

        # Multi-Agent Specialized Cognitive Cycle (Phase 11)
        from agents.multi_agent_roles import CareerOrchestrator
        orchestrator = CareerOrchestrator()

        agent_context = orchestrator.process_application({
            "title": parsed["title"],
            "description": clean_text,
            "company": parsed["company"],
            "url": source_url,
            "profile_id": profile_id,
            "lang": lang,
            "use_ai": True
        })

        understanding = agent_context.get("job_understanding", understanding)
        app_thesis = agent_context.get("application_thesis", {})
        app_strategy = agent_context.get("application_strategy", {})
        tailored_cv_text = agent_context.get("resume_markdown", pitch_data.get("tailored_cv", ""))
        critic_cl = agent_context.get("critic_refined_cover_letter") or pitch_data.get("cover_letter", "")
        short_dm_text = agent_context.get("short_dm") or pitch_data.get("short_dm", "")
        ats_report = agent_context.get("ats_report", {})

        # Save Deep Job Understanding (Phase 2), Application Thesis (Phase 4), Strategy (Phase 7), and ATS (Phase 9)
        cur.execute("""
        UPDATE vacancies 
        SET understanding_json = ?, application_thesis_json = ?, application_strategy_json = ?, ats_report_json = ?
        WHERE id = ?
        """, (
            json.dumps(understanding, ensure_ascii=False),
            json.dumps(app_thesis, ensure_ascii=False),
            json.dumps(app_strategy, ensure_ascii=False),
            json.dumps(ats_report, ensure_ascii=False),
            vac_id
        ))

        # Clear old drafts and insert new pitches
        cur.execute("DELETE FROM pitches WHERE vacancy_id = ?", (vac_id,))
        pitch_map = {
            "short_dm": short_dm_text,
            "cover_letter": critic_cl,
            "tailored_cv": tailored_cv_text
        }
        for p_type, content in pitch_map.items():
            cur.execute(
                "INSERT INTO pitches (vacancy_id, pitch_type, language, content, status) VALUES (?, ?, ?, ?, 'DRAFT')",
                (vac_id, p_type, lang, content)
            )

        cur.execute(
            "UPDATE vacancies SET score = ?, status = 'new', language = ?, grade = ? WHERE id = ?",
            (score, lang, parsed["grade"], vac_id)
        )
        conn.commit()

        # Persist Observability Execution Trace (Phase 18)
        trace = agent_context.get("execution_trace", [])
        from tracker.db import log_agent_run_step
        for step in trace:
            log_agent_run_step(
                vacancy_id=vac_id,
                step_name=step.get("agent", "Agent"),
                status="SUCCESS" if not step.get("error") else "FAILED",
                duration_ms=int(step.get("duration_ms", 0)),
                details=step
            )

        return {
            "success": True,
            "vacancy_id": vac_id,
            "score": score,
            "vacancy": vacancy,
            "execution_trace": agent_context.get("execution_trace", []),
            "ai_generated": pitch_data.get("ai_generated", False)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Ошибка сохранения в базу: {str(e)}"}
    finally:
        conn.close()


if __name__ == "__main__":
    sample_text = """
    Компания FinTech Global ищет Senior Frontend Developer (React / Next.js).
    Удаленная работа (РФ или за рубежом).
    Зарплата: 350 000 - 450 000 руб на руки.
    Стек: React, TypeScript, Next.js 14, Zustand, Tailwind CSS, Jest.
    Обязанности: проектирование архитектуры клиентских приложений, работа в Agile команде.
    Контакты для связи: @fintech_hr_anna или hr@fintechglobal.io
    """
    res = ingest_vacancy_with_ai(sample_text)
    print("AI Import Result:", json.dumps(res, indent=2, ensure_ascii=False))
