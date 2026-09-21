# 🏗 Системная архитектура

**[English](../ARCHITECTURE.md)** &nbsp;•&nbsp; **[Русский](ARCHITECTURE.md)**

Job Hunter CRM — автономный локальный AI карьерный агент и движок откликов. Система агрегирует вакансии из 14+ источников, генерирует персонализированные питчи на основе подтвержденных фактов через Gemini AI или локальные нейросети (LM Studio), отправляет отклики через Chrome DevTools Protocol (CDP) и расширение браузера, транслирует прогресс генерации в реальном времени через SSE и отслеживает полный жизненный цикл вакансий.

---

## 🧭 Высокоуровневая диаграмма потоков данных

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       1. СБОР ВАКАНСИЙ (14+ Источников)                     │
│  Telegram · HH.ru · Хабр · SuperJob · Работа.ру · Сетка · GetMatch          │
│  RemoteOK · Remotive · WWR · CryptoJobsList · HackerNews · Jobicy · ATS     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           2. ПАЙПЛАЙН ОБРАБОТКИ                             │
│  Anti-BS фильтр → Маршрутизация рынков (RU/EN) → Расчет скоринга (0–100%)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   3. AI КАРЬЕРНЫЙ АГЕНТ (6-Агентный пайплайн)               │
│  JobAnalyst → CompanyResearcher → CandidateStrategist                       │
│  → Writer → Critic (Фильтр клише) → FactChecker (Защита от галлюцинаций)   │
│                                                                             │
│  Артефакты: анализ · тезис · стратегия · резюме · сопроводительное · DM     │
│  Потоковая передача прогресса генерации через SSE в веб-интерфейс           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          4. ЛОКАЛЬНОЕ ХРАНИЛИЩЕ (SQLite)                    │
│  vacancies (с viewed_at, pitch_rating, FSM-состоянием)                      │
│  pitches (с детальными оценками, автосбросом) · candidate_profiles          │
│  application_history · agent_tasks · agent_run_logs · company_dossiers      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           5. МОДУЛЬНЫЙ CRM ВЕБ-ИНТЕРФЕЙС                    │
│  Дашборд · Учет просмотренных · Редактор профилей · Настройки · SSE-прогресс│
│  Python stdlib HTTP-сервер (:8115) + Модульный Vanilla JS + Tailwind CSS    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           6. АВТОМАТИЗАЦИЯ БРАУЗЕРА                         │
│  A. Chrome Live Bridge (CDP порт 9222) через launch_chrome.sh               │
│     Детерминированная работа с HH.ru и Хабр в активной сессии пользователя │
│  B. Chrome Расширение (Manifest V3)                                         │
│     автозаполнение · обход антифрода · многошаговые формы · детект капчи    │
│  C. Умная закладка (Bookmarklet) как быстрый фолбэк                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Технологический стек

| Слой | Технология | Обоснование |
|---|---|---|
| **Backend** | Python 3.10+ (`http.server`, `sqlite3`, `urllib`) | Никаких внешних фреймворков, запуск <100мс, отсутствие проблем с зависимостями. |
| **Frontend** | Модульный Vanilla JS (`static/js/`) + Tailwind CSS (CDN) | Нулевой шаг сборки, мгновенная перезагрузка при сохранении, чистая структура. |
| **База данных** | SQLite (`jobs.db`) с автомиграциями | 100% суверенитет данных, работа без настройки СУБД. |
| **AI Engine** | Google Gemini API и локальные LLM (LM Studio / Ollama) | Низкая задержка, структурированный вывод, возможность 100% офлайн-работы. |
| **Автоматизация** | Chrome CDP Bridge + Расширение V3 + Букмарклет | Работа в авторизованном браузере в обход Cloudflare и капчей. |
| **Тестирование** | Pytest, Hypothesis, Coverage | Измеримый Quality Score, фаззинг граничных значений, автоматический расчет метрик. |

---

## 🗂 Структура проекта

```
job_hunter/
├── crm.py                     # HTTP-сервер — REST API + эндпоинты SSE-стриминга
├── crm_v2_template.html       # Главный шаблон разметки CRM-дашборда
├── start.sh                   # Скрипт запуска (завершает старый процесс, стартует сервер)
├── launch_chrome.sh           # Запуск Chrome с открытым CDP портом 9222
├── run_objective_tests.sh     # Запуск тестов с расчетом покрытия и Quality Score
├── harvest.py                 # Оркестратор сбора вакансий из всех источников
├── auto_enrich.py             # Пайплайн обогащения вакансий
├── jobs.db                    # База данных SQLite с автоматическими миграциями
├── config.json                # API-ключи, провайдер LLM, параметры политик
├── pytest.ini                 # Конфигурация pytest
│
├── scrapers/                  # 14 модулей сбора вакансий
│   ├── base.py                # Базовый интерфейс скрапера BaseScraper
│   ├── hh_scraper.py          # Сборщик HeadHunter (HH.ru API)
│   ├── habr_scraper.py        # Сборщик Хабр Карьера
│   ├── superjob_scraper.py    # Сборщик SuperJob
│   ├── rabotaru_scraper.py    # Сборщик Работа.ру
│   ├── setka_scraper.py       # Сборщик Сетка (Setka.ru)
│   ├── getmatch_scraper.py    # Сборщик GetMatch
│   ├── telegram_scraper.py    # Telegram-каналы и Telethon Userbot
│   ├── remoteok_scraper.py    # Сборщик RemoteOK API
│   ├── remotive_scraper.py    # Сборщик Remotive API
│   ├── wwr_scraper.py         # Сборщик WeWorkRemotely RSS
│   ├── crypto_scraper.py      # Сборщик CryptoJobsList
│   ├── hackernews_scraper.py  # Сборщик Hacker News "Who's Hiring"
│   ├── jobicy_scraper.py      # Сборщик Jobicy
│   └── ats_scraper.py         # Сборщик ATS (Greenhouse/Lever/Ashby/Workable)
│
├── enricher/                  # Модули обогащения данных
│   ├── lead_finder.py         # Поиск прямых контактов (Telegram, email, телефон)
│   └── ai_parser.py           # Универсальный ИИ-парсер вакансий
│
├── filter/                    # Фильтрация вакансий
│   └── profile_filter.py      # Anti-BS фильтр, определение грейда, черный список
│
├── generator/                 # Генерация контента и когнитивный пайплайн
│   ├── pitch_builder.py       # Сборщик питчей и сопоставление ключевых слов
│   ├── cover_letter_engine.py # Сопроводительные письма (Черновик → Критика → Итог)
│   ├── tailored_resume_engine.py # Генератор ATS-совместимого резюме
│   ├── ats_analyzer.py        # Анализ плотности ключевых слов для ATS
│   ├── llm_generator.py       # Обертка для Gemini API и LM Studio + фолбэки
│   ├── candidate_profile.py   # Каноническая схема профиля кандидата и валидатор
│   ├── job_understanding.py   # Извлечение фактов и гипотез из описания
│   ├── company_researcher.py  # Точечное исследование профиля компании
│   ├── thesis_generator.py    # Формулирование тезиса отклика
│   ├── thesis_critic.py       # Состязательная валидация тезиса и фильтр клише
│   ├── evidence_retriever.py  # Поиск подтвержденных фактов под боли компании (STAR)
│   ├── application_strategy.py # Стратегия позиционирования и тон повествования
│   └── resume_parser.py       # Парсер резюме из форматов PDF и DOCX
│
├── agents/                    # Оркестрация агентов и автоматизация браузера
│   ├── runtime.py             # FSM-машина состояний (9 состояний, ретраи, таймауты)
│   ├── multi_agent_roles.py   # 6 специализированных ролей агентов
│   ├── agent_brain.py         # Координатор агента и браузерного моста
│   ├── tool_system.py         # Реестр инструментов агента
│   ├── universal_form_filler.py # Универсальный координатор заполнения форм
│   └── adapters/              # Адаптеры платформ
│       ├── hh_cdp_adapter.py  # Детерминированный CDP-адаптер для HeadHunter
│       ├── greenhouse_adapter.py # Адаптер для Greenhouse ATS
│       └── base_adapter.py    # Базовый интерфейс адаптера
│
├── tracker/                   # Слой хранения и базы данных
│   ├── db.py                  # Схема SQLite, миграции, CRUD, FSM-состояния
│   ├── shame_list.py          # Генератор Доски позора недобросовестных компаний
│   └── cleanup_closed.py      # Очистка архивных вакансий
│
├── extension/                 # Браузерное расширение Chrome (Manifest V3)
│   ├── manifest.json          # Манифест расширения
│   ├── core.js                # Утилиты обхода антифрода, симуляция кликов и ввода
│   ├── platform-adapters.js   # Адаптеры страниц (HH, LinkedIn, ATS)
│   ├── autofill.js            # Движок заполнения полей
│   ├── automation.js          # Автоотправка и обход многошаговых визардов
│   ├── content_script.js      # Маршрутизатор сообщений
│   ├── background.js          # Фоновый воркер (опрос очереди, задержки)
│   ├── sidepanel.js           # Контроллер боковой панели
│   └── sidepanel.html         # Разметка боковой панели
│
├── static/                    # Статические файлы интерфейса
│   ├── favicon.svg            # Иконка CRM
│   └── js/                    # Модульный JavaScript
│       ├── api.js             # Клиент REST API и чтение SSE-потока
│       ├── app.js             # Точка входа и управление состоянием
│       ├── bookmarklet.js     # Скрипт умной закладки Auto-Apply
│       └── views/
│           ├── vacancies.js   # Список вакансий, статус просмотра, оценки, стриминг
│           └── modals.js      # Модальные окна настроек, сбора и парсинга
│
├── docs/                      # Документация
│   ├── ARCHITECTURE.md        # Архитектура системы (на английском)
│   ├── AI_AGENT_ARCHITECTURE.md # 6-агентный цикл рассуждений
│   ├── SCRAPERS_GUIDE.md      # Руководство по парсерам
│   ├── CONFIGURATION.md       # Руководство по настройке
│   └── ru/                    # Документация на русском языке
│       ├── ARCHITECTURE.md
│       ├── SCRAPERS_GUIDE.md
│       └── CONFIGURATION.md
│
└── tests/                     # 100+ тестов
    ├── conftest.py            # Фикстуры и фабрики тестовых данных
    ├── test_objective_core.py # Юнит-тесты ядра (Anti-BS, доказательства, питчи, ATS)
    ├── test_objective_db.py   # Тесты CRUD, миграций и состояний БД
    ├── test_objective_properties.py # Тесты свойств и фаззинг (Hypothesis)
    ├── test_objective_integration.py # Интеграционные тесты REST и SSE API
    ├── test_*.py              # Функциональные и регрессионные наборы тестов
    └── snapshot_*.json        # Фикстуры снэпшотов
```

---

## 🗄 Схема базы данных (jobs.db)

### Таблица `vacancies` (Вакансии)
| Колонка | Тип | Описание |
|---|---|---|
| `id` | TEXT PK | Уникальный идентификатор (`tg:...`, `hh:...`, `ai:...`) |
| `source` | TEXT | Идентификатор источника (`hh`, `habr`, `tg_job_react` и др.) |
| `title` | TEXT | Название вакансии |
| `company` | TEXT | Название компании |
| `url` | TEXT | Прямая ссылка на вакансию |
| `salary` | TEXT | Зарплатная вилка или "Не указана" |
| `location` | TEXT | Локация |
| `is_remote` | INTEGER | 1 если удаленка, 0 если офис/гибрид |
| `description` | TEXT | Полное описание вакансии |
| `skills` | TEXT | Стек технологий через запятую |
| `contact_name` | TEXT | Имя контактного лица |
| `contact_handle` | TEXT | Прямой контакт (Telegram, email) |
| `contact_type` | TEXT | `telegram` / `email` / `portal` / `ats` |
| `score` | INTEGER | Совпадение со стеком кандидата (0–100) |
| `status` | TEXT | `new` / `inbox` / `sent` / `replied` / `archive` / `blacklist` |
| `language` | TEXT | `ru` или `en` |
| `grade` | TEXT | `Junior` / `Middle` / `Senior` / `Lead` |
| `fsm_state` | TEXT | Состояние FSM-агента (`DISCOVERED`, `ANALYZING` и др.) |
| `pitch_rating` | INTEGER | Общий рейтинг сгенерированного питча (0–5) |
| `viewed_at` | TIMESTAMP | Метка времени, когда вакансия была просмотрена |
| `ats_report_json` | TEXT | Отчет анализа ATS в формате JSON |
| `created_at` | TIMESTAMP | Время добавления вакансии |

### Таблица `pitches` (Сгенерированные отклики)
| Колонка | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | Автоинкрементный ID отклика |
| `vacancy_id` | TEXT | Внешний ключ на vacancies.id |
| `pitch_type` | TEXT | `short_dm`, `cover_letter` или `tailored_cv` |
| `language` | TEXT | `ru` или `en` |
| `content` | TEXT | Текст отклика |
| `rating` | INTEGER | Оценка пользователем (0–5), сбрасывается при повторной генерации |
| `status` | TEXT | `DRAFT`, `APPROVED` или `SENT` |
| `created_at` | TIMESTAMP | Время создания |
| `updated_at` | TIMESTAMP | Время последнего обновления |

---

## ⚡️ Потоковая генерация через Server-Sent Events (SSE)

CRM поддерживает трансляцию процесса генерации питчей через SSE:
- **Эндпоинт:** `GET /api/vacancies/{id}/rewrite-stream`
- **Типы событий:**
  - `event: progress` — Текущий шаг генерации (`understanding`, `retrieval`, `drafting`, `critic`, `complete`) и прогресс в процентах (0–100%).
  - `event: update` — Текстовые чанки в реальном времени для Cover Letter и Short DM.
  - `event: done` — Финальный пейлоад с готовыми питчами.
  - `event: error` — Описание ошибки в случае сбоя.
- **Интеграция в UI:** Модуль `static/js/api.js` слушает события через `EventSource`, а `static/js/views/vacancies.js` динамически обновляет прогресс-бар и превью текста.

---

## 🌐 Chrome Live Bridge и автоматизация браузера

### 1. Chrome Live Bridge (CDP)
- Запуск выполняется командой `./launch_chrome.sh` с аргументом `--remote-debugging-port=9222`.
- Профиль браузера изолированно хранится в `~/.jobhunter-chrome`, сохраняя авторизованные сессии на HH.ru, Хабре и LinkedIn.
- Модуль `agents/adapters/hh_cdp_adapter.py` отправляет команды напрямую через протокол Chrome DevTools Protocol, полностью исключая риски блокировок headless-браузеров.

### 2. Расширение Chrome (Manifest V3)
- Порядок загрузки скриптов: `core.js → platform-adapters.js → autofill.js → automation.js → content_script.js`.
- Возможности:
  - Корректная эмуляция событий ввода для фреймворков React, Vue и Angular.
  - Симуляция естественного ввода текста (`humanType`) со случайными задержками 25–90мс.
  - Распознавание капчи (Cloudflare Turnstile, reCAPTCHA, hCaptcha, DataDome).
  - Лимиты безопасности (не более 3 откликов на один домен в час).

---

## 🧪 Фреймворк объективного тестирования

1. **Измеримость:** Автоматический расчет покрытия строк и веток по каждому модулю и формирование Quality Score (0–100).
2. **Изолированность:** Тестовые временные базы данных SQLite и моки внешних вызовов.
3. **Фаззинг на основе свойств (Hypothesis):** Проверка устойчивости к случайным юникод-строкам, граничным значениям и невалидным входным данным.
4. **Воспроизводимость:** Запуск единой командой `./run_objective_tests.sh`.
