import urllib.request
import urllib.error
import json
import os
import re
from typing import Dict, Any, Optional

DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-reasoner"]
GEMINI_MODELS = DEEPSEEK_MODELS  # Alias for backward compatibility

def _sanitize_text(text: str, custom_stop_phrases: list = None) -> str:
    """Anti-BS & Anti-Bullet sanitizer."""
    # Remove bullets
    text = re.sub(r'(?m)^[\s]*[-*•]\s*', '', text)
    text = re.sub(r'(?m)^[\s]*\d+\.\s*', '', text)
    # Remove cliches - hardcoded list
    cliches = [
        r"(?i)буду рад(а)? внести (свой )?вклад",
        r"(?i)динамично развивающ\w+ компани",
        r"(?i)ознакомился с (вашей )?вакансией",
        r"(?i)с большим интересом прочитал",
        r"(?i)могу принести пользу",
        r"(?i)нацелен(а)? на результат",
        r"(?i)откликаюсь на (?:позицию|вакансию)",
        r"(?i)пишу по поводу (?:позиции|вакансию)",
        r"(?i)рассматриваю (?:вашу )?(?:позицию|вакансию)",
        r"(?i)забираю (?:вакансию|позицию) в работу",
        r"(?i)наткнулся на (?:вашу )?(?:вакансию|позицию)",
        r"(?i)увидел(?:а)? (?:вашу )?(?:вакансию|позицию)",
        r"(?i)меня заинтересовала (?:ваша )?(?:вакансию|позиция)",
        r"(?i)ознакомился с описанием",
        r"(?i)с интересом изучил",
        r"(?i)буду рад(а)? присоединиться",
        r"(?i)готов включиться в работу",
        r"(?i)меня зовут \w+,\s*(?:и\s+)?(?:хочу|желаю|готов|хотел)",
        r"(?i)ваша компания ищет",
        r"(?i)вы ищете",
        r"(?i)your company is looking",
        r"(?i)you are looking for",
        r"(?i)you're looking for",
        r"(?i)applying for the (?:position|role)",
        r"(?i)i am thrilled to apply",
        r"(?i)i believe i am the ideal candidate",
        r"(?i)saw your .*?opening",
        r"(?i)i see .*?looking for",
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
        "provider": "deepseek",  # "deepseek" | "lm_studio"
        "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", "").strip(),
        "deepseek_base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
        "deepseek_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "lm_studio_url": "http://127.0.0.1:1234/v1"
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in data.items():
                    if k in ("deepseek_api_key", "api_key") and v:
                        cfg["deepseek_api_key"] = str(v).strip()
                    elif k == "deepseek_base_url" and v:
                        cfg["deepseek_base_url"] = str(v).strip().rstrip("/")
                    elif k == "deepseek_model" and v:
                        cfg["deepseek_model"] = str(v).strip()
                    elif k == "lm_studio_url" and v:
                        cfg[k] = str(v).strip()
                    elif k == "llm_provider" and v:
                        cfg["provider"] = "deepseek" if v == "gemini" else str(v)
                    else:
                        cfg[k] = v
        except Exception:
            pass
    return cfg

def get_api_key() -> str:
    return get_llm_config().get("deepseek_api_key", "")

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


def call_deepseek(prompt: str, system_prompt: str = "", json_mode: bool = True, timeout: float = 60.0, model: str = None) -> Optional[str]:
    """Calls DeepSeek API via standard OpenAI-compatible endpoint."""
    cfg = get_llm_config()
    api_key = cfg.get("deepseek_api_key", "")
    if not api_key:
        return None
    base_url = cfg.get("deepseek_base_url", "https://api.deepseek.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    chosen_model = model or cfg.get("deepseek_model") or "deepseek-chat"

    payload = {
        "model": chosen_model,
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.2)),
        "max_tokens": 4000
    }
    if json_mode and "reasoner" not in chosen_model:
        payload["response_format"] = {"type": "json_object"}

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
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
        print(f"DEBUG: DeepSeek request failed: {type(e).__name__}: {e}")
        return None
    return None


def call_llm(prompt: str, system_prompt: str = "", json_mode: bool = True, timeout: float = 60.0) -> Optional[str]:
    """Calls configured LLM provider (DeepSeek cloud or LM Studio local) with seamless fallback."""
    cfg = get_llm_config()
    provider = cfg.get("provider", "deepseek")

    if provider == "lm_studio":
        resp = call_lm_studio(prompt, system_prompt=system_prompt, json_mode=json_mode, timeout=timeout)
        if resp:
            return resp
        if cfg.get("deepseek_api_key"):
            return call_deepseek(prompt, system_prompt=system_prompt, json_mode=json_mode, timeout=timeout)
        return None
    else:
        # Default: DeepSeek
        resp = call_deepseek(prompt, system_prompt=system_prompt, json_mode=json_mode, timeout=timeout)
        if resp:
            return resp
        # Fallback to LM Studio
        return call_lm_studio(prompt, system_prompt=system_prompt, json_mode=json_mode, timeout=timeout)


def call_llm_json(prompt: str, system_prompt: str = "", timeout: float = 60.0) -> Optional[Dict[str, Any]]:
    """Helper that queries LLM and extracts parsed JSON dictionary."""
    raw = call_llm(prompt, system_prompt=system_prompt, json_mode=True, timeout=timeout)
    if raw:
        return extract_json_payload(raw)
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
    
    provider = cfg.get("provider", "deepseek")
    api_key = cfg.get("deepseek_api_key", "")


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

    # 2. DeepSeek API (Cloud)
    if api_key:
        ds_resp = call_deepseek(prompt, json_mode=True)
        if ds_resp:
            parsed = extract_json_payload(ds_resp)
            if parsed:
                return {
                    "success": True,
                    "short_dm": _sanitize_short_dm((parsed.get("short_dm") or "").strip(), stop_phrases),
                    "cover_letter": _sanitize_text((parsed.get("cover_letter") or "").strip(), stop_phrases),
                    "score": int(parsed.get("score", 85))
                }

    # 3. Fallback to LM Studio
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

    if not api_key:
        return {"success": False, "error": "DeepSeek API ключ не указан в Настройках ИИ"}

    return {
        "success": False,
        "error": "Не удалось получить ответ от DeepSeek API или LM Studio"
    }
