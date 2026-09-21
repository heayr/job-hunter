# ⚙️ Configuration & Customization Guide

**[English](CONFIGURATION.md)** &nbsp;•&nbsp; **[Русский](ru/CONFIGURATION.md)**

This document details configuring AI providers (Gemini & LM Studio), managing multi-persona candidate profiles, tuning the Anti-BS filter, setting agent policies, and configuring the Chrome Live Bridge.

---

## 1. AI & LLM Settings (`config.json`)

Job Hunter supports both cloud-based (Google Gemini) and local offline (LM Studio / Ollama) LLM inference.

Create your local `config.json`:
```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "AIzaSy...",
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "policy_min_salary_rub": 300000,
  "policy_min_salary_usd": 3500,
  "policy_remote_only": true,
  "policy_daily_limit": 25
}
```

### Supported Providers:
- **Google Gemini (`"llm_provider": "gemini"`):**
  - Uses `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`, and `gemini-flash-latest` with automatic fallback.
  - Get a free key from [Google AI Studio](https://aistudio.google.com/).
- **Local LLM (`"llm_provider": "lm_studio"`):**
  - Connects to any OpenAI-compatible `/v1` endpoint (LM Studio, Ollama, vLLM, LocalAI).
  - Default URL: `http://127.0.0.1:1234/v1`.
  - Automatically queries `/models` to discover active chat models (e.g. `Qwen 2.5 14B`, `GLM-4`, `Llama 3.1`).
  - 100% offline, zero external requests, complete data privacy.

---

## 2. Agent Policy Guardrails (`config.json`)

The autonomous agent evaluates each vacancy against strict policy rules before submitting or proposing an application:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `policy_min_salary_rub` | Integer | `300000` | Minimum acceptable salary in RUB (vacancies below this are flagged). |
| `policy_min_salary_usd` | Integer | `3500` | Minimum acceptable salary in USD for international vacancies. |
| `policy_remote_only` | Boolean | `true` | Restrict applications to remote positions only. |
| `policy_daily_limit` | Integer | `25` | Maximum number of auto-applications per 24 hours to prevent spam flagging. |

---

## 3. Chrome Live Bridge Setup (`launch_chrome.sh`)

For deterministic auto-apply on platforms with heavy bot protection (HeadHunter, Habr Career, LinkedIn), use the Chrome Live Bridge:

```bash
./launch_chrome.sh
```

### How it works:
1. Launches Google Chrome / Chromium with `--remote-debugging-port=9222`.
2. Uses an isolated user data directory at `~/.jobhunter-chrome`.
3. **Session Persistence:** Log into HeadHunter, Habr, or LinkedIn once in this browser instance. Your cookies, 2FA sessions, and tokens remain permanently stored in `~/.jobhunter-chrome`.
4. The AI Career Agent communicates directly over Chrome DevTools Protocol (CDP), avoiding headless browser detection entirely.

---

## 4. Candidate Profiles (`generator/profiles.json`)

Job Hunter supports multi-persona profiles to target different markets with tailored messaging:

```json
[
  {
    "id": "fe_ru",
    "lang": "ru",
    "name": "Иван Иванов",
    "role": "Frontend / Fullstack Developer",
    "contacts_structured": {
      "telegram": "@your_handle",
      "email": "you@example.com",
      "github": "https://github.com/your_handle",
      "linkedin": "https://linkedin.com/in/your_handle"
    },
    "summary": "Fullstack-разработчик с фокусом на React, Next.js и TypeScript.",
    "keywords": "React, Next.js, TypeScript, Tailwind CSS, FastAPI, Docker"
  },
  {
    "id": "fe_en",
    "lang": "en",
    "name": "Ivan Ivanov",
    "role": "Senior Frontend Engineer",
    "contacts_structured": {
      "telegram": "@your_handle",
      "email": "you@example.com",
      "github": "https://github.com/your_handle",
      "linkedin": "https://linkedin.com/in/your_handle"
    },
    "summary": "Senior Software Engineer specializing in scalable web apps.",
    "keywords": "React, TypeScript, Next.js, Node.js, Cloud Architecture"
  }
]
```

### Canonical Profile Schema
The system also maintains a canonical profile schema (`generator/candidate_profile.py`) with verifiable evidence items:
- **Evidence Structure:** `id`, `problem`, `context`, `action`, `decision`, `result`, `technologies`, and `source`.
- Every claim in generated cover letters is mapped to an evidence item, eliminating LLM hallucinations.

---

## 5. Customizing the Anti-BS Filter (`anti_bs_filter.py`)

The Anti-BS filter flags recruiter traps before you spend time reviewing the vacancy:

```python
# Unpaid test assignment patterns
UNPAID_TEST_PATTERNS = [
    r"тестов(ое|ые)\s+задани[ея]\s+до\s+(собеседования|интервью)",
    r"выполнить\s+тестовое\s+на\s+\d+\s+(дня|дней|часов)",
    r"take-home\s+assignment\s+before\s+screening"
]

# Sham self-employment / tax evasion patterns
TAX_EVASION_PATTERNS = [
    r"только\s+(через\s+)?(ип|самозанят)",
    r"b2b\s+contract\s+only",
    r"оплата\s+в\s+крипте\s+без\s+договора"
]
```

Detected red flags are displayed as warning badges in the CRM and logged to [`SHAME_LIST.md`](../SHAME_LIST.md).

---

## 6. Port & Process Management (`start.sh`)

To avoid port conflicts with lingering processes on port `8115`, `start.sh` terminates any existing process before launching:

```bash
#!/bin/bash
lsof -ti :8115 | xargs kill -9 2>/dev/null || true
python3 crm.py
```
