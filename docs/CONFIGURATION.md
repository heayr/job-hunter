# ⚙️ Configuration & Customization Guide

**[English](CONFIGURATION.md)** &nbsp;•&nbsp; **[Русский](ru/CONFIGURATION.md)**

This document covers configuring AI models, managing candidate profiles, and customizing the Anti-BS filter.

---

## 1. AI & LLM Settings (`config.json`)

The application connects to Google Gemini API for real-time pitch generation, scoring, and cover letter rewriting.

Create your local `config.json`:
```json
{
  "gemini_api_key": "AIzaSy..."
}
```

- **Supported Models:** Automatically falls back between `gemini-2.5-flash`, `gemini-flash-latest`, and `gemini-1.5-flash`.
- **Zero Token Waste:** AI generation is only triggered when explicitly requested via the **«Переписать через Gemini»** button or the `/api/vacancies/<id>/rewrite` endpoint, preserving your API quota.

---

## 2. Candidate Profiles (`generator/profiles.json`)

Job Hunter supports multi-persona profiles so you can target different markets with tailored messaging.

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

Profiles can also be edited and previewed directly inside the CRM UI under the **«👤 Профили»** tab.

---

## 3. Customizing the Anti-BS Filter (`anti_bs_filter.py`)

The Anti-BS filter flags recruiter traps before you spend time reviewing the vacancy. You can extend the blacklist rules directly in `anti_bs_filter.py`:

```python
# Custom Red Flag Patterns
UNPAID_TEST_PATTERNS = [
    r"тестов(ое|ые)\s+задани[ея]\s+до\s+(собеседования|интервью)",
    r"выполнить\s+тестовое\s+на\s+\d+\s+(дня|дней|часов)",
    r"take-home\s+assignment\s+before\s+screening"
]

TAX_EVASION_PATTERNS = [
    r"только\s+(через\s+)?(ип|самозанят)",
    r"b2b\s+contract\s+only",
    r"оплата\s+в\s+крипте\s+без\s+договора"
]
```

When a trap is detected, the CRM attaches a prominent warning banner to the pitch:
`[⚠️ Внимание: Требуется неоплачиваемое тестовое до первого собеседования]`

---

## 4. Port & Process Management (`start.sh`)

To prevent port conflicts with lingering processes, `start.sh` automatically finds and frees port `8115` before starting the server:

```bash
#!/bin/bash
lsof -ti :8115 | xargs kill -9 2>/dev/null || true
python3 crm.py
```
