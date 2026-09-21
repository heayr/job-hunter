<div align="center">

# ⚡️ Job Hunter CRM

**Autonomous, local-first AI career agent & application engine for engineers.**  
*14+ Source Harvester · Anti-BS Filter · 6-Agent Cognitive Pipeline · Anti-Cliché Evidence Grounding · Real-Time SSE Streaming · CDP & Chrome Extension Auto-Apply*

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Frontend: Vanilla JS](https://img.shields.io/badge/Frontend-Vanilla--JS-yellow.svg)](static/js/)
[![Architecture: Local--First](https://img.shields.io/badge/Architecture-Local--First-purple.svg)](docs/ARCHITECTURE.md)
[![Backend: Zero--Dependency](https://img.shields.io/badge/Backend-Zero--Dependency-brightgreen.svg)](crm.py)
[![Tests: 100+ Objective Tests](https://img.shields.io/badge/Tests-100%2B%20Passing-success.svg)](run_objective_tests.sh)

<br/>

**[English](#-english)** &nbsp;•&nbsp; **[Русский](#-русский)**

<br/>

<img src="docs/assets/preview.png" alt="Job Hunter CRM Preview" width="100%" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);" />

</div>

---

# 🇬🇧 English

## 🎯 The Problem & The Solution

- **The Problem:** Tech job hunting has become exhausting and inefficient. Developers waste dozens of hours copying and pasting details across fragmented job portals (HeadHunter, Habr Career, LinkedIn, SuperJob, Rabota.ru, RemoteOK, Telegram), navigating HR "red flags" (unpaid multi-day test tasks, sham self-employment/tax evasion schemes, absurd experience requirements), and writing generic cover letters by hand. Meanwhile, automated headless bots (Playwright/Selenium) get blocked immediately by Cloudflare Turnstile, DataDome, and 2FA captchas.
- **The Solution:** A high-performance, local-first desktop CRM and autonomous AI Career Agent. It aggregates vacancies across 14+ sources, filters out recruiter bullshit, calculates deterministic tech stack match scores (0–100%), dynamically routes candidate personas (Russian vs. International Remote English), generates evidence-grounded pitches via AI with real-time SSE progress streaming, tracks viewed vacancies, and auto-fills applications in 1 click through Chrome DevTools Protocol (CDP) and a Manifest V3 browser extension.

---

## 🚀 Key Features

### 1. 🌐 14+ Source Harvester
Aggregates tech vacancies across local and global platforms into a unified inbox:
- **CIS & Russian Market:** HeadHunter (HH.ru), Хабр Карьера, SuperJob, Работа.ру, Сетка (Setka.ru), GetMatch, Telegram Channels & Telethon Userbot.
- **Global Remote Market:** RemoteOK, Remotive, WeWorkRemotely, CryptoJobsList, Hacker News ("Who's Hiring"), Jobicy, ATS scrapers (Greenhouse, Lever, Ashby, Workable).
- Automated segmentation into **🇷🇺 Local (RU)** and **🌍 International Remote (EN)**.

### 2. 🛡 Anti-BS & Red-Flag Filter
Automatically inspects job descriptions and flags recruiter toxicity before you waste time:
- 🚫 **Unpaid take-home assignments** required prior to technical interviews.
- 🚫 **Forced self-employment / B2B schemes** (ИП / самозанятость) masking employee roles.
- 🚫 **Unrealistic experience traps** (e.g. 5+ years for junior roles) or commission-only compensation.
- 📋 **Integrated Blacklist & Shame List** ([`SHAME_LIST.md`](SHAME_LIST.md)) with in-CRM management.

### 3. 🤖 AI Career Agent (6-Agent Cognitive Pipeline)
A multi-agent reasoning architecture that processes each vacancy systematically:
- **JobAnalyst** — parses explicit requirements, implicit expectations, team context, and risks.
- **CompanyResearcher** — conducts bounded web research for engineering signals and stack realities.
- **CandidateStrategist** — maps candidate evidence directly to company pain points.
- **Writer** — generates tailored resumes, cover letters, and high-impact short DMs.
- **Critic** — adversarial quality assurance, ATS scoring, and anti-cliché inspection.
- **FactChecker** — zero-hallucination verification against the Canonical Candidate Profile.

### 4. 🔍 Anti-Cliché Engine & Evidence Retriever
- Eliminates generic filler and "captain obvious" phrases (*"I am a motivated professional...", "I have great communication skills..."*).
- Anchors every thesis strictly in verified candidate achievements formatted as STAR (Situation, Task, Action, Result) with verifiable metrics.

### 5. ⚡️ Real-Time SSE Streaming & Pitch Rating Loop
- **Server-Sent Events (SSE):** Live progress bar (0–100%) and streaming text updates during AI generation directly in the CRM UI.
- **Granular Pitch Rating:** Rate Cover Letters and Short DMs (1–5 stars) to build an active feedback loop.
- **Self-Correcting Generator:** Ratings inform subsequent rewrites to prevent repetitive mistakes; ratings reset automatically on regeneration.

### 6. 🧠 Dual LLM Engine (Gemini & Local LLM / LM Studio)
- **Google Gemini API:** Native support for `gemini-3.1-flash-lite`, `gemini-flash-latest`, and automatic model fallbacks.
- **Local LLM Support:** Compatible with LM Studio, Ollama, or any OpenAI-compatible `/v1` endpoint for 100% offline, private inference with zero data leakage.

### 7. 🌐 Browser Automation & Stealth Auto-Apply
- **Chrome Live Bridge (CDP):** Connects to your authenticated browser session via Chrome DevTools Protocol (`--remote-debugging-port=9222`) for deterministic, human-like auto-apply on HH.ru and Habr Career.
- **Chrome Extension (Manifest V3):** Multi-step wizard traversal (LinkedIn Easy Apply, ATS portals), CAPTCHA detection, React/Vue/Angular DOM injection, and anti-detection delays.
- **Smart Bookmarklet:** Zero-install fallback for instant 1-click form filling.

### 8. 👤 Canonical Profiles & Resume Parser
- Manage multiple candidate personas (e.g. *Frontend Specialist* vs. *Fullstack / Team Lead*; *Russian* vs. *English*).
- Built-in local parser for PDF and DOCX resumes with automatic entity extraction into canonical JSON schemas.

### 9. 📊 CRM Dashboard & Viewed Vacancies Tracking
- Fast, single-page interface with tabbed views, search, market filters, and sort options.
- **Viewed Vacancies Tracking:** Automatic `viewed_at` timestamps and visual indicators so you never review the same vacancy twice.

### 10. 🧪 Objective Testing Framework
- Comprehensive test suite with 100+ tests spanning unit logic, database migrations, FSM state lifecycles, and Hypothesis property-based fuzzing.
- Automated Quality Score and branch coverage reporting via `./run_objective_tests.sh`.

---

## 🛠 Tech Stack & Architecture

Built with a **zero-dependency, local-first** engineering philosophy:

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ (`http.server`, `sqlite3`, `urllib`) | Zero heavy frameworks, instant cold start (<100ms), no package rot. |
| **Frontend** | Modular Vanilla JS + Tailwind CSS (CDN) | Extremely fast, zero build step, instant reload on save. |
| **Database** | SQLite (`jobs.db`) with auto-migrations | 100% local data ownership, zero server config. |
| **AI Engine** | Google Gemini API & Local LLM (LM Studio / Ollama) | Fast, structured reasoning with offline privacy option. |
| **Automation** | Chrome CDP Bridge + Manifest V3 Extension + Bookmarklet | Runs in user's authenticated context, immune to Cloudflare & bot blocks. |
| **Testing** | Pytest, Hypothesis, Coverage | Objective, quantifiable quality score and property-based verification. |

---

## 🏁 Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/heayr/job-hunter.git
cd job-hunter

# Create local configs from templates
cp config.example.json config.json
cp generator/profiles.example.json generator/profiles.json
```

Configure `config.json` with your preferred AI provider:
```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "lm_studio_url": "http://127.0.0.1:1234/v1"
}
```
*(Get a free Gemini key from [Google AI Studio](https://aistudio.google.com/), or start LM Studio locally for offline inference).*

### 2. Launch CRM
```bash
./start.sh
```
Open **`http://localhost:8115`** in your browser.

### 3. Launch Chrome for AI Agent (Optional, for CDP Automation)
```bash
./launch_chrome.sh
```
Starts Chrome with remote debugging on port `9222` and an isolated profile at `~/.jobhunter-chrome` so your logins remain saved.

### 4. Harvest Vacancies
```bash
python3 harvest.py
```
Runs all configured scrapers, filters vacancies through Anti-BS rules, scores match percentages, and populates `jobs.db`.

---

## 🧪 Testing

Run the full Objective Testing Suite with coverage metrics:
```bash
./run_objective_tests.sh
```
Or run directly via pytest:
```bash
./.venv/bin/pytest tests/ -v
```

The test suite covers:
- **Core Unit Tests:** Anti-BS filter, evidence retriever, pitch builder, ATS analyzer, fact checker.
- **Database Tests:** CRUD operations, schema migrations, FSM state machine transitions.
- **Property-Based Tests:** Hypothesis fuzzing on arbitrary unicode, extreme edge cases, and invariant validation.
- **Integration Tests:** REST endpoints, Server-Sent Events (SSE) streaming, and API contracts.

---

## 📁 Documentation

- 🏗 **[Architecture Overview](docs/ARCHITECTURE.md)** &nbsp;•&nbsp; **[Русская версия](docs/ru/ARCHITECTURE.md)** — Data flows, SQLite schema, CDP bridge, and modular frontend.
- 🧠 **[AI Agent Architecture](docs/AI_AGENT_ARCHITECTURE.md)** — 6-agent cognitive loop, evidence graphs, and anti-hallucination guardrails.
- 🔌 **[Scrapers & Harvester Guide](docs/SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[Русская версия](docs/ru/SCRAPERS_GUIDE.md)** — Guide to all 14 scrapers and adding custom sources in 5 minutes.
- ⚙️ **[Configuration Guide](docs/CONFIGURATION.md)** &nbsp;•&nbsp; **[Русская версия](docs/ru/CONFIGURATION.md)** — Gemini, LM Studio, agent policies, and Anti-BS filter customization.
- 💩 **[Shame List / Blacklist](SHAME_LIST.md)** — Registry of non-compliant and toxic job listings.

---

# 🇷🇺 Русский

<div align="center">
  <img src="docs/assets/preview_ru.png" alt="Job Hunter CRM Russian Market" width="100%" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);" />
</div>

<br/>

## 🎯 Проблема и Решение

- **Проблема:** Поиск работы в IT превратился в изматывающую рутину. Разработчики тратят десятки часов на копирование данных между десятками порталов (HH.ru, Хабр Карьера, SuperJob, Работа.ру, LinkedIn, RemoteOK, Telegram-каналы), сталкиваются с токсичными HR-практиками (неоплачиваемые тестовые задания на несколько дней до первого скрининга, навязывание ИП/самозанятости для ухода от ТК РФ, абсурдный требуемый опыт) и вручную переписывают сопроводительные письма. Обычные боты на Playwright/Selenium моментально блокируются Cloudflare Turnstile, DataDome и капчами.
- **Решение:** Автономная локальная CRM-система и AI Карьерный Агент. Система агрегирует вакансии из 14+ источников, отсеивает неадекватные предложения через Anti-BS фильтр, детерминированно рассчитывает совпадение со стеком (0–100%), переключает персоны кандидата (RU / EN), генерирует выверенные питчи с реальными фактами и потоковым SSE-прогрессом, отслеживает просмотренные вакансии и отправляет отклики в 1 клик через Chrome DevTools Protocol (CDP) и расширение браузера.

---

## 🚀 Ключевые возможности

### 1. 🌐 Мульти-парсер из 14+ источников
Единый инбокс IT-вакансий со всех популярных платформ:
- **РФ и СНГ:** HeadHunter (HH.ru), Хабр Карьера, SuperJob, Работа.ру, Сетка (Setka.ru), GetMatch, Telegram-каналы и Telethon Userbot.
- **Международный Remote:** RemoteOK, Remotive, WeWorkRemotely, CryptoJobsList, Hacker News ("Who's Hiring"), Jobicy, ATS-парсеры (Greenhouse, Lever, Ashby, Workable).
- Автоматическая маршрутизация на рынки: **🇷🇺 РФ и СНГ (RU)** и **🌍 International Remote (EN)**.

### 2. 🛡 Anti-BS фильтр и черный список
Автоматический анализ текста вакансий и выявление красных флагов:
- 🚫 **Неоплачиваемые объемные тестовые задания** до первого технического интервью.
- 🚫 **Серые схемы оформления** (принудительное ИП / самозанятость вместо ТК РФ).
- 🚫 **Ловушки опыта** (например, 5+ лет на позицию джуниора) или работа только за процент.
- 📋 **Интегрированная Доска позора** ([`SHAME_LIST.md`](SHAME_LIST.md)) с управлением прямо из CRM.

### 3. 🤖 AI Карьерный Агент (6 агентов)
Многоагентная когнитивная система, рассуждающая о каждой вакансии:
- **JobAnalyst** — выделяет явные требования, скрытые ожидания, контекст команды и риски.
- **CompanyResearcher** — точечное веб-исследование компании, поиск сигналов о стеке и задачах.
- **CandidateStrategist** — сопоставляет подтвержденные факты кандидата с болями работодателя.
- **Writer** — пишет адаптированное резюме, сопроводительное письмо и краткий DM.
- **Critic** — состязательный контроль качества, ATS-скоринг и проверка на клише.
- **FactChecker** — верификация против галлюцинаций по каноническому профилю.

### 4. 🔍 Фильтр клише и движок доказательств (Evidence Retriever)
- Исключение пустых водянистых фраз (*«Я коммуникабельный, стрессоустойчивый профессионал...»*).
- Привязка каждого тезиса строго к подтвержденным результатам кандидата в формате STAR (Ситуация, Задача, Действие, Измеримый результат).

### 5. ⚡️ Потоковая генерация через SSE и цикл оценки питчей
- **Server-Sent Events (SSE):** Отображение прогресса переписывания в реальном времени (0–100%) прямо в интерфейсе.
- **Оценка питчей:** Выставление оценок (1–5 звезд) для Cover Letter и Short DM.
- **Обратная связь:** Оценки учитываются генератором при повторных итерациях, а при перезапуске рейтинг автоматически сбрасывается.

### 6. 🧠 Поддержка двух LLM-движков (Gemini и локальные модели)
- **Google Gemini API:** Поддержка `gemini-3.1-flash-lite`, `gemini-flash-latest` с умным фолбэком.
- **Локальные нейросети (LM Studio / Ollama):** Работа через OpenAI-совместимый эндпоинт `/v1` для 100% приватности и работы без доступа к внешним сетям.

### 7. 🌐 Автоматизация браузера и скрытный автоотклик
- **Chrome Live Bridge (CDP):** Подключение к браузеру через Chrome DevTools Protocol (`--remote-debugging-port=9222`) для детерминированного отклика на HH.ru и Хабре.
- **Chrome Расширение (Manifest V3):** Прохождение многошаговых форм (LinkedIn Easy Apply, ATS), детектирование капчи, заполнение React/Vue/Angular форм и имитация действий человека.
- **Умная закладка (Bookmarklet):** Быстрое заполнение формы в 1 клик без установки расширения.

### 8. 👤 Мульти-профили и локальный парсер резюме
- Раздельные персоны кандидата под разные рынки и роли (*Frontend* vs. *Fullstack*; *RU* vs. *EN*).
- Встроенный локальный парсер PDF и DOCX резюме в канонический JSON-формат.

### 9. 📊 CRM-дашборд и учет просмотренных вакансий
- Быстрый интерфейс на чистом Vanilla JS без шага сборки (`npm build`).
- **Учет просмотренных:** Фиксация отметки `viewed_at` и визуальная индикация просмотренных карточек.

### 10. 🧪 Комплексный тестовый фреймворк
- 100+ тестов: юнит-тесты модулей, миграции и CRUD базы данных, FSM-машина состояний, фаззинг Hypothesis.
- Автоматический расчет покрытия и метрики качества (Quality Score) через `./run_objective_tests.sh`.

---

## 🛠 Архитектурный манифест

Проект создан на базе философии **Zero-dependency & Local-first**:

| Слой | Технология | Почему именно так |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ (`http.server`, `sqlite3`, `urllib`) | Никаких тяжелых фреймворков. Мгновенный холодный запуск (<100мс). |
| **Frontend** | Модульный Vanilla JS + Tailwind CSS (CDN) | Максимальная скорость, отсутствие сборщиков и `node_modules`. |
| **База данных** | SQLite (`jobs.db`) с автомиграциями | 100% суверенитет данных, всё хранится локально. |
| **AI Engine** | Google Gemini API + Local LLM (LM Studio / Ollama) | Точный структурированный вывод с возможностью полной автономности. |
| **Автоматизация** | Chrome CDP Bridge + Расширение V3 + Букмарклет | Работа в авторизованном браузере в обход Cloudflare и капчей. |
| **Тестирование** | Pytest, Hypothesis, Coverage | Измеримый Quality Score, расчет покрытия и фаззинг граничных условий. |

---

## 🏁 Быстрый старт

### 1. Клонирование и настройка
```bash
git clone https://github.com/heayr/job-hunter.git
cd job-hunter

# Создание конфигов из шаблонов
cp config.example.json config.json
cp generator/profiles.example.json generator/profiles.json
```

Укажи параметры в `config.json`:
```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "ТВОЙ_GEMINI_API_KEY",
  "lm_studio_url": "http://127.0.0.1:1234/v1"
}
```

### 2. Запуск CRM
```bash
./start.sh
```
Открой **`http://localhost:8115`** в браузере.

### 3. Запуск Chrome для AI-агента (Опционально, для CDP)
```bash
./launch_chrome.sh
```
Запустит Chrome с открытым портом отладки `9222` и отдельным профилем в `~/.jobhunter-chrome`.

### 4. Запуск сбора вакансий
```bash
python3 harvest.py
```

---

## 🧪 Тестирование

Запуск полного набора тестов с генерацией отчета о покрытии:
```bash
./run_objective_tests.sh
```
Или напрямую через pytest:
```bash
./.venv/bin/pytest tests/ -v
```

---

## 📁 Документация

- 🏗 **[Архитектура системы](docs/ru/ARCHITECTURE.md)** &nbsp;•&nbsp; **[English](docs/ARCHITECTURE.md)** — Потоки данных, схема SQLite, CDP-мост и веб-интерфейс.
- 🧠 **[Архитектура AI-агента](docs/AI_AGENT_ARCHITECTURE.md)** — 6-агентный цикл рассуждений, граф доказательств и защита от галлюцинаций.
- 🔌 **[Создание своих парсеров](docs/ru/SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[English](docs/SCRAPERS_GUIDE.md)** — Обзор 14 парсеров и руководство по добавлению новых площадок.
- ⚙️ **[Руководство по настройке](docs/ru/CONFIGURATION.md)** &nbsp;•&nbsp; **[English](docs/CONFIGURATION.md)** — Настройка Gemini, LM Studio, политик агента и Anti-BS фильтра.
- 💩 **[Доска позора](SHAME_LIST.md)** — Реестр токсичных вакансий и недобросовестных работодателей.

---

## 🤝 Вклад в проект (Contributing)

Пулл-реквесты, новые парсеры и идеи приветствуются! 

Если проект помогает тебе в поиске работы — **поставь звезду ⭐ на GitHub**, это мотивирует развивать проект дальше!

---

## 📄 Лицензия

Распространяется под лицензией **MIT**. Подробнее в файле [`LICENSE`](LICENSE).
