# ⚙️ Руководство по настройке и персонализации

**[English](../CONFIGURATION.md)** &nbsp;•&nbsp; **[Русский](CONFIGURATION.md)**

В этом документе описывается настройка ИИ-моделей, управление профилями кандидата и кастомизация правил Anti-BS фильтра.

---

## 1. Настройка ИИ и LLM (`config.json`)

Приложение обращается к Google Gemini API для генерации сопроводительных писем, коротких питчей и расчета мэтчинга.

Создайте локальный файл `config.json`:
```json
{
  "gemini_api_key": "AIzaSy..."
}
```

- **Поддерживаемые модели:** Автоматическое переключение между `gemini-2.5-flash`, `gemini-flash-latest` и `gemini-1.5-flash`.
- **Экономия токенов:** Запросы к нейросети отправляются только при явном нажатии кнопки **«Переписать через Gemini»** в интерфейсе CRM или вызове эндпоинта `/api/vacancies/<id>/rewrite`. Фонового сжигания токенов нет.

---

## 2. Профили кандидата (`generator/profiles.json`)

Job Hunter поддерживает систему мульти-профилей (персон), что позволяет таргетировать разные рынки с разным позиционированием.

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

Профили можно редактировать прямо в веб-интерфейсе CRM на вкладке **«👤 Профили»**.

---

## 3. Кастомизация Anti-BS фильтра (`anti_bs_filter.py`)

Anti-BS фильтр автоматически отлавливает токсичные условия работодателей до того, как вы потратите время на чтение вакансии. Вы можете расширить паттерны правил в файле `anti_bs_filter.py`:

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

При обнаружении стоп-слов CRM добавляет заметную предупреждающую плашку к карточке вакансии:
`[⚠️ Внимание: Требуется неоплачиваемое тестовое до первого собеседования]`

---

## 4. Управление портами и процессами (`start.sh`)

Чтобы исключить зависание старых процессов на порту `8115`, скрипт `start.sh` автоматически находит и освобождает порт перед запуском:

```bash
#!/bin/bash
lsof -ti :8115 | xargs kill -9 2>/dev/null || true
python3 crm.py
```
