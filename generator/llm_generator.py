import urllib.request
import urllib.error
import json
import os
import re
from typing import Dict, Any, Optional

GEMINI_MODELS = ["gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-flash-latest"]

def _sanitize_text(text: str, custom_stop_phrases: list = None) -> str:
    """Anti-BS & Anti-Bullet sanitizer."""
    # Remove bullets
    text = re.sub(r'(?m)^[\s]*[-*•]\s*', '', text)
    text = re.sub(r'(?m)^[\s]*\d+\.\s*', '', text)
    # Remove cliches
    cliches = [
        r"(?i)буду рад(а)? внести (свой )?вклад",
        r"(?i)динамично развивающ\w+ компани",
        r"(?i)ознакомился с (вашей )?вакансией",
        r"(?i)с большим интересом прочитал",
        r"(?i)могу принести пользу",
        r"(?i)нацелен(а)? на результат"
    ]
    if custom_stop_phrases:
        for p in custom_stop_phrases:
            if len(p) > 2:
                cliches.append(r"(?i)" + re.escape(p))
                
    for c in cliches:
        text = re.sub(c, "", text)
    # Clean double spaces or broken lines caused by removals
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def _sanitize_short_dm(dm: str, custom_stop_phrases: list = None) -> str:
    return _sanitize_text(dm, custom_stop_phrases)

def get_llm_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    cfg = {
        "provider": "gemini", # "gemini" | "lm_studio"
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
        "lm_studio_url": "http://127.0.0.1:1234/v1"
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Apply all loaded keys to cfg
                for k, v in data.items():
                    if k == "gemini_api_key" and v:
                        cfg[k] = v.strip()
                    elif k == "lm_studio_url" and v:
                        cfg[k] = v.strip()
                    elif k == "llm_provider" and v:
                        cfg["provider"] = v
                    else:
                        cfg[k] = v
        except Exception:
            pass
    return cfg

def get_api_key() -> str:
    return get_llm_config().get("gemini_api_key", "")

def get_lm_studio_active_model(base_url: str) -> str:
    try:
        req = urllib.request.Request(f"{base_url}/models")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            chat_models = [m["id"] for m in models if "embed" not in m.get("id", "").lower()]
            if chat_models:
                return chat_models[0]
            if models:
                return models[0].get("id", "")
    except Exception:
        pass
    return "zai-org/glm-4.6v-flash"

def extract_json_payload(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    first = text.find('{')
    last = text.rfind('}')
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(text[first:last+1])
        except Exception:
            pass
    return None

def call_lm_studio(prompt: str, system_prompt: str = "", json_mode: bool = True, timeout: float = 300.0) -> Optional[str]:
    """Calls local LM Studio instance via OpenAI-compatible endpoint with ample token headroom."""
    cfg = get_llm_config()
    base_url = cfg.get("lm_studio_url", "http://127.0.0.1:1234/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    model = cfg.get("lm_studio_model") or get_lm_studio_active_model(base_url)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.2)),
        "max_tokens": 3500
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = (msg.get("content") or "").strip()
                if not content and msg.get("reasoning_content"):
                    content = msg.get("reasoning_content", "").strip()
                return content
    except Exception as e:
        print(f"DEBUG: LM Studio request failed: {type(e).__name__}: {e}")
        return None
    return None


def get_gold_standard_examples(lang: str = "ru", limit: int = 2) -> list:
    """Retrieve user-approved gold standard pitches to serve as few-shot exemplars."""
    try:
        from tracker.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT p.pitch_type, p.content, v.title, v.company
            FROM pitches p
            JOIN vacancies v ON v.id = p.vacancy_id
            WHERE (p.rating = 1 OR v.pitch_rating = 1)
              AND p.pitch_type IN ('cover_letter', 'short_dm')
              AND p.language = ?
              AND length(p.content) > 50
            ORDER BY p.id DESC
            LIMIT ?
        ''', (lang, limit * 2))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[FEW_SHOT] Could not load gold standard examples: {e}")
        return []


def get_rejected_examples(lang: str = "ru", limit: int = 3) -> list:
    """Retrieve user-rejected pitches to serve as anti-patterns (what NOT to do)."""
    try:
        from tracker.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT p.pitch_type, p.content, v.title, v.company
            FROM pitches p
            JOIN vacancies v ON v.id = p.vacancy_id
            WHERE p.rating = -1
              AND p.pitch_type IN ('cover_letter', 'short_dm')
              AND p.language = ?
              AND length(p.content) > 50
            ORDER BY p.id DESC
            LIMIT ?
        ''', (lang, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[ANTI_PATTERN] Could not load rejected examples: {e}")
        return []


def generate_ai_pitch(
    vacancy: Dict[str, Any],
    profile: Any,
    warnings: str = "",
    lang: str = "ru"
) -> Dict[str, Any]:
    cfg = get_llm_config()
    stop_phrases = cfg.get("stop_phrases", [])
    stop_phrases_text = ", ".join(stop_phrases) if stop_phrases else ""
    
    provider = cfg.get("provider", "gemini")
    api_key = cfg.get("gemini_api_key", "")
    if provider == "gemini" and not api_key:
        # Check if LM Studio is reachable as alternative
        pass

    title = vacancy.get("title", "Frontend Engineer")
    company = vacancy.get("company", "Company")
    desc = (vacancy.get("description") or "")[:2500]

    # Enrich description with AI understanding if available
    understanding = vacancy.get("understanding_json") or ""
    if understanding:
        try:
            u = json.loads(understanding) if isinstance(understanding, str) else understanding
            u_parts = []
            facts = u.get("facts", {})
            if facts.get("explicit_requirements"):
                u_parts.append(f"Requirements: {', '.join(facts['explicit_requirements'])}")
            if facts.get("responsibilities"):
                u_parts.append(f"Responsibilities: {'; '.join(facts['responsibilities'])}")
            reasoning = u.get("reasoning", {})
            if reasoning.get("engineering_signals"):
                u_parts.append(f"Engineering context: {'; '.join(reasoning['engineering_signals'][:3])}")
            if reasoning.get("likely_team_problems"):
                u_parts.append(f"Team challenges: {'; '.join(reasoning['likely_team_problems'][:3])}")
            if reasoning.get("hiring_priorities"):
                u_parts.append(f"Hiring priorities: {'; '.join(reasoning['hiring_priorities'][:3])}")
            if u_parts:
                desc += "\n\nCOMPANY ANALYSIS (from AI understanding):\n" + "\n".join(u_parts)
        except Exception:
            pass

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

    gold_examples_text = ""
    gold_list = get_gold_standard_examples(lang=lang, limit=2)
    if gold_list:
        gold_examples_text = "\nUSER-APPROVED GOLD STANDARD EXAMPLES (The candidate personally approved these generations — adopt this exact tone, cadence, formatting, and high-impact style):\n"
        for ex in gold_list:
            gold_examples_text += f"\n--- GOLD EXAMPLE FOR {ex.get('title')} AT {ex.get('company')} ({ex.get('pitch_type', '').upper()}):\n{ex.get('content')}\n"

    rejected_text = ""
    rejected_list = get_rejected_examples(lang=lang, limit=3)
    if rejected_list:
        rejected_text = "\nUSER-REJECTED ANTI-PATTERNS (The candidate explicitly disliked these — DO NOT repeat these styles, structures, or phrases):\n"
        for ex in rejected_list:
            rejected_text += f"\n--- REJECTED EXAMPLE ({ex.get('pitch_type', '').upper()}) — DO NOT MIMIC:\n{ex.get('content')}\n"

    stop_phrases_block = f'''
CRITICAL RULE - BLACKLIST (АБСОЛЮТНЫЙ ЗАПРЕТ):
Ты ни при каких обстоятельствах не должен использовать следующие слова и фразы (даже синонимы или в измененном виде). Представь, что их не существует в языке:
[{stop_phrases_text}]
''' if stop_phrases_text else ""

    default_template = """ТЫ — опытный IT-специалист и карьерный стратег. Твоя задача — писать короткие, пробивные и 100% конвертящие сопроводительные письма под конкретную вакансию.

КОНТЕКСТ РЫНКА (ПРАВИЛА ИГРЫ):
1. Все приукрашивают. Кандидат должен выглядеть максимально уверенным практиком с твердым релевантным бэкграундом (минимум 2+ года, уверенно адаптируй опыт под требования).
2. Эйчар тратит 5 секунд. Письмо должно цеплять с первого абзаца техническим сленгом ("изнанка", "под капотом", "логи", "контракты" — в зависимости от стека).

ПОЛНЫЙ ЗАПРЕТ НА "ИИ-СТИЛЬ":
- Никаких маркированных списков (bullet points)! Пиши сплошными абзацами.
- Никаких штампов ("динамично развивающаяся", "буду рад внести вклад", "ознакомился с вакансией").
- Тон: уверенный, сухой, профессионально-разговорный (инженер пишет инженеру).

{stop_phrases_block}

СТРУКТУРА:
1. Приветствие. Просто напиши "Привет!" или "Добрый день!" и СРАЗУ переходи к своему опыту. Никаких вступлений про саму вакансию.
Пример ИДЕАЛЬНОГО старта: "Привет! У меня за плечами полный цикл разработки SaaS на React..."
СТРОГИЙ ЗАПРЕТ: Никогда не пиши "Откликаюсь на...", "Пишу по поводу...", "Рассматриваю позицию...", "Забираю вакансию в работу" и любой другой мусор, указывающий на факт отклика. HR и так знает, зачем ты пишешь.
2. Крючок (1 абзац): Заявление релевантного опыта. Главный угол атаки: не просто "исполнитель по ТЗ", а человек, понимающий архитектуру и бизнес-задачу.
3. Мясо стека: Собрать главные требования из описания и вписать их в живую речь. Использовать сленг.
4. Короткий CTA + Контакты: {tg} | {email} | {github}

VACANCY: {title} at {company}
{desc}

PROFILE: {name}, {role}
{summary}
Keywords: {keywords}
Exp: {exp}

{gold_examples_text}
{rejected_text}

WARNINGS: {warnings}

LANGUAGE: {language_name} only.

JSON only:
{{"short_dm": "...", "cover_letter": "...", "score": 85}}
"""
    raw_template = cfg.get("system_prompt_template")
    if not raw_template or not raw_template.strip():
        raw_template = default_template

    # Ensure JSON constraint is always present even if user deleted it
    if "JSON only" not in raw_template:
        raw_template += '\nJSON only:\n{"short_dm": "...", "cover_letter": "...", "score": 85}\n'
        
    def safe_replace(tmpl, replacements):
        res = tmpl
        for k, v in replacements.items():
            res = res.replace("{" + k + "}", str(v))
        return res

    prompt = safe_replace(raw_template, {
        "title": title,
        "company": company,
        "desc": desc[:1500],
        "name": name,
        "role": role,
        "summary": summary,
        "keywords": keywords,
        "exp": exp,
        "tg": tg,
        "email": email,
        "github": github,
        "linkedin": linkedin,
        "stop_phrases_block": stop_phrases_block,
        "gold_examples_text": gold_examples_text,
        "rejected_text": rejected_text,
        "warnings": warnings if warnings else "None",
        "language_name": language_name
    })


    # 1. If LM Studio is selected as the primary provider, call it directly
    if provider == "lm_studio":
        lm_resp = call_lm_studio(prompt, json_mode=True)
        if lm_resp:
            parsed = extract_json_payload(lm_resp)
            if parsed:
                return {
                    "success": True,
                    "short_dm": _sanitize_short_dm((parsed.get("short_dm") or "").strip(), stop_phrases),
                    "cover_letter": _sanitize_text((parsed.get("cover_letter") or "").strip(), stop_phrases),
                    "score": int(parsed.get("score", 80))
                }
        return {
            "success": False,
            "error": "Не удалось получить ответ от локального LM Studio. Убедитесь, что LM Studio запущен на " + cfg.get("lm_studio_url", "http://127.0.0.1:1234/v1")
        }

    # 2. Otherwise try Gemini API
    if not api_key:
        # Check if LM Studio fallback is running
        lm_resp = call_lm_studio(prompt, json_mode=True)
        if lm_resp:
            parsed = extract_json_payload(lm_resp)
            if parsed:
                return {
                    "success": True,
                    "short_dm": _sanitize_short_dm((parsed.get("short_dm") or "").strip(), stop_phrases),
                    "cover_letter": _sanitize_text((parsed.get("cover_letter") or "").strip(), stop_phrases),
                    "score": int(parsed.get("score", 80))
                }
        return {"success": False, "error": "Gemini API ключ не указан в Настройках ИИ"}

    models_to_try = GEMINI_MODELS[:]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": float(cfg.get("temperature", 0.7)),
            "responseMimeType": "application/json"
        }
    }

    last_error = ""

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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
                # Clean possible markdown wrapping if any
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text).strip()
                parsed = json.loads(text)
                return {
                    "success": True,
                    "short_dm": _sanitize_short_dm(parsed.get("short_dm", "").strip(), stop_phrases),
                    "cover_letter": _sanitize_text(parsed.get("cover_letter", "").strip(), stop_phrases),
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

    # 3. If Gemini models failed (e.g. rate limit 429 or 503), try LM Studio fallback
    lm_resp = call_lm_studio(prompt, json_mode=True)
    if lm_resp:
        parsed = extract_json_payload(lm_resp)
        if parsed:
            return {
                "success": True,
                "short_dm": _sanitize_short_dm((parsed.get("short_dm") or "").strip(), stop_phrases),
                "cover_letter": _sanitize_text((parsed.get("cover_letter") or "").strip(), stop_phrases),
                "score": int(parsed.get("score", 80))
            }

    return {
        "success": False,
        "error": last_error or "Не удалось получить ответ от Gemini API (проверьте VPN) или LM Studio"
    }
