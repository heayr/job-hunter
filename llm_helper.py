import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def get_llm_config(config_path: str = "config.json") -> Dict[str, Any]:
    cfg = {
        "enabled": True,
        "provider": "deepseek",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", "").strip(),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "lm_studio_url": "http://127.0.0.1:1234/v1"
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                llm_cfg = data.get("llm", {})
                for k in ("enabled", "provider", "api_key", "base_url", "model", "lm_studio_url"):
                    if k in llm_cfg:
                        cfg[k] = llm_cfg[k]
        except Exception:
            pass

    return cfg


def call_chat_completion(messages: list, config: Optional[Dict[str, Any]] = None, temperature: float = 0.4) -> str:
    """Calls DeepSeek or LM Studio chat completions endpoint."""
    cfg = config or get_llm_config()

    if not cfg.get("enabled", True):
        return ""

    provider = cfg.get("provider", "deepseek")
    if provider == "lm_studio":
        url = f"{cfg.get('lm_studio_url', 'http://127.0.0.1:1234/v1').rstrip('/')}/chat/completions"
        api_key = "lm-studio"
        model = cfg.get("model", "local-model")
    else:
        url = f"{cfg.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions"
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "deepseek-chat")
        if not api_key:
            return ""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 300
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return ""


def clean_cover_letter(text: str) -> str:
    """Removes annoying bot cliches and bullet points."""
    # Remove markdown bullets
    text = re.sub(r'(?m)^[\s]*[-*•]\s*', '', text)
    text = re.sub(r'(?m)^[\s]*\d+\.\s*', '', text)
    # Remove quotes
    text = text.strip('"\'')
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


def generate_cover_letter(
    vacancy_title: str,
    company: str,
    description: str,
    user_skills: str = "",
    default_template: str = ""
) -> str:
    """
    Generates a concise 2-3 sentence cover letter targeted at the vacancy.
    Falls back to default_template if LLM is disabled or call fails.
    """
    cfg = get_llm_config()
    if not cfg.get("enabled", True) or (cfg.get("provider") == "deepseek" and not cfg.get("api_key")):
        return default_template

    system_prompt = (
        "Ты — опытный специалист, пишущий сопроводительное письмо на отклик. "
        "Правила: пиши строго на русском языке, максимум 2-3 коротких предложения. "
        "Без пафоса, без буллетов, без фраз 'я идеальный кандидат', 'буду рад внести вклад' или 'увидел вашу вакансию'. "
        "Сразу к сути: покажи соответствие стека и готовность обсудить задачи на интервью."
    )

    user_prompt = (
        f"Вакансия: {vacancy_title} в компании {company}\n"
        f"Стек кандидата: {user_skills or 'Python, Backend, PostgreSQL, Docker'}\n"
        f"Краткие требования вакансии: {description[:800]}\n\n"
        "Напиши 2-3 предложения для сопроводительного письма:"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    generated = call_chat_completion(messages, config=cfg)
    if generated:
        cleaned = clean_cover_letter(generated)
        if len(cleaned) > 20:
            return cleaned

    return default_template
