# ⚙️ Руководство по настройке и персонализации

**[English](../CONFIGURATION.md)** &nbsp;•&nbsp; **[Русский](CONFIGURATION.md)**

В этом документе описывается настройка ИИ-провайдеров (Gemini и LM Studio), управление мульти-профилями кандидата, параметры политик агента, настройка Chrome Live Bridge и кастомизация правил Anti-BS фильтра.

---

## 1. Настройка ИИ и LLM (`config.json`)

Job Hunter поддерживает как облачный вывод через Google Gemini API, так и полностью локальный запуск через LM Studio или Ollama.

Создайте локальный файл `config.json`:
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

### Поддерживаемые провайдеры:
- **Google Gemini (`"llm_provider": "gemini"`):**
  - Поддерживает модели `gemini-3.1-flash-lite`, `gemini-flash-lite-latest` и `gemini-flash-latest` с автоматическим переключением.
  - Бесплатный API-ключ можно получить в [Google AI Studio](https://aistudio.google.com/).
- **Локальные модели (`"llm_provider": "lm_studio"`):**
  - Подключение к любому OpenAI-совместимому эндпоинту `/v1` (LM Studio, Ollama, vLLM, LocalAI).
  - URL по умолчанию: `http://127.0.0.1:1234/v1`.
  - Автоматически опрашивает `/models` и определяет активную чат-модель (например, `Qwen 2.5 14B`, `GLM-4`, `Llama 3.1`).
  - 100% приватность: данные не покидают вашу локальную машину.

---

## 2. Политики и ограничения агента (`config.json`)

Автономный агент валидирует каждую вакансию по набору строгих правил перед отправкой или предложением отклика:

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `policy_min_salary_rub` | Число | `300000` | Минимально допустимая зарплата в рублях для рынка РФ/СНГ. |
| `policy_min_salary_usd` | Число | `3500` | Минимально допустимая зарплата в USD для международного рынка. |
| `policy_remote_only` | Булево | `true` | Ограничение поиска только удаленными позициями. |
| `policy_daily_limit` | Число | `25` | Максимальное количество автооткликов в сутки для защиты от спам-фильтров. |

---

## 3. Настройка Chrome Live Bridge (`launch_chrome.sh`)

Для надежных автооткликов на порталах с жесткой защитой от ботов (HeadHunter, Хабр Карьера, LinkedIn) используется прямое управление браузером:

```bash
./launch_chrome.sh
```

### Как это устроено:
1. Скрипт запускает Google Chrome / Chromium с флагом `--remote-debugging-port=9222`.
2. Используется изолированный каталог профиля: `~/.jobhunter-chrome`.
3. **Сохранение сессий:** Войдите в свои аккаунты на HH.ru, Хабре и LinkedIn один раз. Ваши куки, сессии и токены двухфакторной аутентификации останутся сохраненными.
4. AI Карьерный Агент управляет браузером через Chrome DevTools Protocol (CDP), полностью исключая блокировки антифродом.

---

## 4. Профили кандидата (`generator/profiles.json`)

Job Hunter поддерживает мульти-профили для точного позиционирования под разные рынки и роли:

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

### Каноническая схема профиля
В системе реализована строгая схема профиля (`generator/candidate_profile.py`) с подтвержденными доказательствами (Evidence Items):
- **Структура доказательства:** `id`, `problem`, `context`, `action`, `decision`, `result`, `technologies`, `source`.
- Каждое утверждение в сопроводительном письме связывается с реальным кейсом кандидата, исключая галлюцинации LLM.

---

## 5. Кастомизация Anti-BS фильтра (`anti_bs_filter.py`)

Anti-BS фильтр автоматически выявляет токсичные требования работодателей:

```python
# Паттерны неоплачиваемых тестовых заданий
UNPAID_TEST_PATTERNS = [
    r"тестов(ое|ые)\s+задани[ея]\s+до\s+(собеседования|интервью)",
    r"выполнить\s+тестовое\s+на\s+\d+\s+(дня|дней|часов)",
    r"take-home\s+assignment\s+before\s+screening"
]

# Паттерны серых схем оформления
TAX_EVASION_PATTERNS = [
    r"только\s+(через\s+)?(ип|самозанят)",
    r"b2b\s+contract\s+only",
    r"оплата\s+в\s+крипте\s+без\s+договора"
]
```

Выявленные нарушения подсвечиваются плашками в интерфейсе CRM и заносятся в реестр [`SHAME_LIST.md`](../../SHAME_LIST.md).

---

## 6. Управление портами и процессами (`start.sh`)

Скрипт `start.sh` автоматически завершает зависшие процессы на порту `8115` перед запуском сервера:

```bash
#!/bin/bash
lsof -ti :8115 | xargs kill -9 2>/dev/null || true
python3 crm.py
```
