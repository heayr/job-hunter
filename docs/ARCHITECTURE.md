# System Architecture

Job Hunter CRM — autonomous local-first AI career agent & application engine. Scrapes jobs across 14+ sources, generates evidence-grounded pitches via Gemini AI or local LLMs (LM Studio), auto-fills applications in the browser via Chrome DevTools Protocol (CDP) and Manifest V3 extension, streams rewrite progress in real-time, and tracks the full application lifecycle.

---

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         1. JOB MARKET INGESTION (14+ Sources)               │
│  Telegram · HH.ru · Habr · SuperJob · Rabota.ru · Setka · GetMatch          │
│  RemoteOK · Remotive · WWR · CryptoJobsList · HackerNews · Jobicy · ATS     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              2. PROCESSING PIPELINE                         │
│  Anti-BS Filter → Market Routing (RU/EN) → Tech Match Scorer (0–100%)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      3. AI COGNITIVE AGENT (6-Agent Pipeline)               │
│  JobAnalyst → CompanyResearcher → CandidateStrategist                       │
│  → Writer → Critic (Anti-Cliché) → FactChecker (Zero-Hallucination)        │
│                                                                             │
│  Outputs: understanding · thesis · strategy · resume · cover letter · DM    │
│  Real-time SSE progress streaming directly to Web UI                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              4. LOCAL STORAGE (SQLite)                      │
│  vacancies (with viewed_at, pitch_rating, FSM state)                        │
│  pitches (with granular ratings, auto-reset) · candidate_profiles           │
│  application_history · agent_tasks · agent_run_logs · company_dossiers      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              5. MODULAR CRM WEB UI                          │
│  Dashboard · Viewed Tracking · Profiles Editor · Settings · SSE Progress    │
│  Python stdlib HTTP server (:8115) + Modular Vanilla JS + Tailwind CSS      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              6. BROWSER AUTOMATION                          │
│  A. Chrome Live Bridge (CDP port 9222) via launch_chrome.sh                 │
│     Deterministic HeadHunter & Habr automation in user's active session     │
│  B. Chrome Extension (Manifest V3)                                          │
│     autofill · anti-detection · multi-step traversal · CAPTCHA detection    │
│  C. Smart Bookmarklet (Zero-install fallback)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | Python 3.10+ (`http.server`, `sqlite3`, `urllib`) | Zero external dependencies, instant cold start (<100ms), zero package rot. |
| **Frontend** | Modular Vanilla JS (`static/js/`) + Tailwind CSS (CDN) | Zero build step, instant reload on save, clean separation of concerns. |
| **Database** | SQLite (`jobs.db`) with auto-migrations | 100% local data ownership, zero server config. |
| **AI Engine** | Google Gemini API & Local LLMs (LM Studio / Ollama) | Low latency, structured output, option for 100% offline private inference. |
| **Automation** | Chrome CDP Bridge + Manifest V3 Extension + Bookmarklet | Runs in user's authenticated context, immune to Cloudflare and bot detection. |
| **Testing** | Pytest, Hypothesis, Coverage | Measurable Quality Score, property-based fuzzing, automated metrics. |

---

## Directory Structure

```
job_hunter/
├── crm.py                     # HTTP server — REST API + SSE streaming endpoints
├── crm_v2_template.html       # Main CRM dashboard markup
├── start.sh                   # Launch script (kills previous instance, starts server)
├── launch_chrome.sh           # Launches Chrome with remote debugging on port 9222
├── run_objective_tests.sh     # Comprehensive test runner with coverage & quality score
├── harvest.py                 # Multi-source harvesting orchestrator
├── auto_enrich.py             # Vacancy enrichment pipeline
├── jobs.db                    # SQLite database (auto-migrated)
├── config.json                # API keys, LLM provider, policies
├── pytest.ini                 # Pytest configuration
│
├── scrapers/                  # 14 job source scrapers
│   ├── base.py                # BaseScraper interface
│   ├── hh_scraper.py          # HeadHunter API scraper
│   ├── habr_scraper.py        # Habr Career scraper
│   ├── superjob_scraper.py    # SuperJob scraper
│   ├── rabotaru_scraper.py    # Rabota.ru scraper
│   ├── setka_scraper.py       # Setka.ru scraper
│   ├── getmatch_scraper.py    # GetMatch scraper
│   ├── telegram_scraper.py    # Telegram channels & Telethon userbot
│   ├── remoteok_scraper.py    # RemoteOK API scraper
│   ├── remotive_scraper.py    # Remotive API scraper
│   ├── wwr_scraper.py         # WeWorkRemotely RSS scraper
│   ├── crypto_scraper.py      # CryptoJobsList scraper
│   ├── hackernews_scraper.py  # Hacker News "Who's Hiring" scraper
│   ├── jobicy_scraper.py      # Jobicy scraper
│   └── ats_scraper.py         # Greenhouse/Lever/Ashby/Workable scraper
│
├── enricher/                  # Data enrichment
│   ├── lead_finder.py         # Contact extraction (Telegram, email, phone)
│   └── ai_parser.py           # AI vacancy parser + CRM ingester
│
├── filter/                    # Vacancy filtering
│   └── profile_filter.py      # Anti-BS filter, grade detection, blacklist checks
│
├── generator/                 # AI content generation & cognitive pipeline
│   ├── pitch_builder.py       # Pitch orchestrator & keyword matcher
│   ├── cover_letter_engine.py # Multi-stage cover letter generation & fact-checking
│   ├── tailored_resume_engine.py # ATS-compliant resume builder
│   ├── ats_analyzer.py        # ATS keyword scoring & match analysis
│   ├── llm_generator.py       # Gemini API & LM Studio wrapper + model fallback
│   ├── candidate_profile.py   # Canonical profile schema + validator
│   ├── job_understanding.py   # Facts vs hypotheses extraction
│   ├── company_researcher.py  # Bounded company intelligence
│   ├── thesis_generator.py    # Application thesis formulation
│   ├── thesis_critic.py       # Adversarial thesis validator & anti-cliché critic
│   ├── evidence_retriever.py  # Pain-to-capability evidence mapping (STAR)
│   ├── application_strategy.py # Positioning & narrative strategy
│   └── resume_parser.py       # PDF/DOCX resume parser
│
├── agents/                    # Multi-agent orchestration & browser automation
│   ├── runtime.py             # FSM runtime (9 states, retries, timeouts)
│   ├── multi_agent_roles.py   # 6 specialized agent roles
│   ├── agent_brain.py         # Autonomous agent brain & bridge coordinator
│   ├── tool_system.py         # Declarative tool registry
│   ├── universal_form_filler.py # Universal form filling coordinator
│   └── adapters/              # Platform-specific adapters
│       ├── hh_cdp_adapter.py  # Deterministic HeadHunter CDP adapter
│       ├── greenhouse_adapter.py # Greenhouse ATS adapter
│       └── base_adapter.py    # Base adapter interface
│
├── tracker/                   # Persistence layer
│   ├── db.py                  # SQLite schema, migrations, CRUD, FSM states
│   ├── shame_list.py          # Blacklist / Shame List exporter
│   └── cleanup_closed.py      # Closed vacancy cleanup
│
├── extension/                 # Chrome Extension (Manifest V3)
│   ├── manifest.json          # Extension manifest
│   ├── core.js                # Anti-detection, CAPTCHA detection, click simulation
│   ├── platform-adapters.js   # Platform-specific form detection (HH, LinkedIn, ATS)
│   ├── autofill.js            # Form filling engine
│   ├── automation.js          # Auto-submit & multi-step traversal
│   ├── content_script.js      # Message router
│   ├── background.js          # Background worker (task polling, cooldown)
│   ├── sidepanel.js           # Side panel UI controller
│   └── sidepanel.html         # Side panel markup
│
├── static/                    # Frontend assets
│   ├── favicon.svg            # CRM favicon
│   └── js/                    # Modular Vanilla JS
│       ├── api.js             # API client & SSE streaming reader
│       ├── app.js             # Entry point & state management
│       ├── bookmarklet.js     # Auto-apply bookmarklet script
│       └── views/
│           ├── vacancies.js   # Vacancy list, viewed state, ratings, rewrite stream
│           └── modals.js      # Settings, harvest, AI parser modals
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture (this document)
│   ├── AI_AGENT_ARCHITECTURE.md # 6-agent pipeline blueprint
│   ├── SCRAPERS_GUIDE.md      # Scrapers and harvesting guide
│   ├── CONFIGURATION.md       # Configuration and customization guide
│   └── ru/                    # Russian engineering documentation
│       ├── ARCHITECTURE.md
│       ├── SCRAPERS_GUIDE.md
│       └── CONFIGURATION.md
│
└── tests/                     # 100+ tests
    ├── conftest.py            # Test fixtures and factory functions
    ├── test_objective_core.py # Core unit tests (anti-BS, evidence, pitch, ATS)
    ├── test_objective_db.py   # Database CRUD, migrations, FSM states
    ├── test_objective_properties.py # Property-based tests (Hypothesis)
    ├── test_objective_integration.py # HTTP & SSE API integration tests
    ├── test_*.py              # Functional and regression test suites
    └── snapshot_*.json        # Regression fixtures
```

---

## Database Schema (jobs.db)

### Core Tables

#### `vacancies` — Job listings & processing state
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | Unique ID (`tg:...`, `hh:...`, `ai:...`) |
| `source` | TEXT | Source identifier (`hh`, `habr`, `tg_job_react`, etc.) |
| `title` | TEXT | Job title |
| `company` | TEXT | Company name |
| `url` | TEXT | Direct vacancy URL |
| `salary` | TEXT | Salary string or "Не указана" |
| `location` | TEXT | Location string |
| `is_remote` | INTEGER | 1 if remote, 0 otherwise |
| `description` | TEXT | Full job description |
| `skills` | TEXT | Comma-separated tech stack |
| `contact_name` | TEXT | Contact person name |
| `contact_handle` | TEXT | Direct contact (Telegram handle, email) |
| `contact_type` | TEXT | `telegram` / `email` / `portal` / `ats` |
| `score` | INTEGER | Match score 0–100 |
| `status` | TEXT | `new` / `inbox` / `sent` / `replied` / `archive` / `blacklist` |
| `language` | TEXT | `ru` or `en` |
| `grade` | TEXT | `Junior` / `Middle` / `Senior` / `Lead` |
| `fsm_state` | TEXT | Agent FSM state (`DISCOVERED`, `ANALYZING`, etc.) |
| `pitch_rating` | INTEGER | Overall pitch rating (0–5) |
| `viewed_at` | TIMESTAMP | Timestamp when vacancy was viewed by user |
| `ats_report_json` | TEXT | ATS analysis report JSON |
| `created_at` | TIMESTAMP | Creation timestamp |

#### `pitches` — Tailored pitches per vacancy
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-incrementing pitch ID |
| `vacancy_id` | TEXT | FK → vacancies.id |
| `pitch_type` | TEXT | `short_dm`, `cover_letter`, or `tailored_cv` |
| `language` | TEXT | `ru` or `en` |
| `content` | TEXT | Generated pitch content |
| `rating` | INTEGER | Pitch rating (0–5), resets on rewrite |
| `status` | TEXT | `DRAFT`, `APPROVED`, or `SENT` |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

#### `candidate_profiles` — Multi-persona profiles
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | Profile ID (`fe_ru`, `fe_en`, etc.) |
| `lang` | TEXT | `ru` or `en` |
| `target_role` | TEXT | Role title (e.g. "Frontend", "Fullstack") |
| `data_json` | TEXT | Full profile JSON (contacts, experience, evidence) |

#### `application_history` — Audit trail
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `company` | TEXT | Company name |
| `portal` | TEXT | Platform used (`hh`, `habr`, `linkedin`, etc.) |
| `mode` | TEXT | `ASSIST`, `SEMI_AUTO`, or `AUTO` |
| `fsm_state` | TEXT | Final FSM state |
| `metadata_json` | TEXT | Execution metadata |

#### `agent_tasks` — Browser automation queue
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `url` | TEXT | Target URL |
| `status` | TEXT | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED` |
| `result_message` | TEXT | Execution result |

#### `agent_run_logs` — Agent execution trace
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `step_name` | TEXT | Agent role or step name |
| `status` | TEXT | `SUCCESS` or `FAILED` |
| `duration_ms` | INTEGER | Step execution duration in milliseconds |

---

## AI Agent Pipeline (6 Agents)

The multi-agent system runs 6 specialized agents in sequence:

```
Input: Raw vacancy description / URL
    │
    ▼
┌─────────────────────────┐
│ 1. JobAnalystAgent       │  understand_job_posting()
│    Facts vs Hypotheses   │  → explicit/implicit requirements, risks
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 2. CompanyResearcher     │  research_company_context()
│    Bounded web search    │  → stack signals, engineering realities
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 3. CandidateStrategist   │  reframe_evidence() → thesis → strategy
│    Evidence mapping      │  → STAR alignment, positioning, tone
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 4. WriterAgent           │  generate_tailored_resume()
│    Content creation      │  + cover letter + short DM
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 5. CriticAgent           │  audit_ats() + anti-cliché detection
│    Quality control       │  → eliminates generic fluff & buzzwords
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 6. FactCheckerAgent      │  verify_facts() against canonical profile
│    Anti-hallucination    │  → zero unverified claims
└───────────┬─────────────┘
            ▼
Output: score + short_dm + cover_letter + tailored_cv
```

### FSM States (9 states)
```
DISCOVERED → ANALYZING → RESEARCHING → MATCHED → STRATEGY_READY
    → ARTIFACTS_READY → WAITING_APPROVAL → SUBMITTED / FAILED
```

---

## Real-Time SSE Streaming Architecture

The CRM supports real-time streaming of AI pitch generation via Server-Sent Events:
- **Endpoint:** `GET /api/vacancies/{id}/rewrite-stream`
- **Events Emitted:**
  - `event: progress` — Current stage (e.g. `understanding`, `retrieval`, `drafting`, `critic`, `complete`) and percentage (0–100%).
  - `event: update` — Live text chunk updates for Cover Letter and Short DM.
  - `event: done` — Generation completed with final payload.
  - `event: error` — Error details if generation failed.
- **Frontend Consumer:** `static/js/api.js` (`streamRewrite`) connects using `EventSource` and dynamically renders progress bars and live preview in `static/js/views/vacancies.js`.

---

## Chrome Live Bridge & Browser Automation

### 1. Chrome Live Bridge (CDP)
- Launched via `./launch_chrome.sh` with `--remote-debugging-port=9222`.
- Stores user credentials in `~/.jobhunter-chrome` so authenticated sessions (HH.ru, Habr, LinkedIn) persist.
- `agents/adapters/hh_cdp_adapter.py` communicates directly over Chrome DevTools Protocol for deterministic DOM interaction without headless detection.

### 2. Chrome Extension (Manifest V3)
- Runs content scripts in order: `core.js → platform-adapters.js → autofill.js → automation.js → content_script.js`.
- Features:
  - Framework-aware input injection (bypasses React/Vue/Angular synthetic event wrappers).
  - Human-like typing simulation (`humanType`) with randomized 25–90ms delays.
  - CAPTCHA detection (Cloudflare Turnstile, reCAPTCHA, hCaptcha, DataDome).
  - Multi-step form traversal with safety rate limits (max 3 submissions per domain/hour).

---

## Objective Testing Framework

The testing framework guarantees quality through quantifiable metrics:
1. **Measurable:** Line and branch coverage quantified per module; Objective Quality Score (0–100) calculated on every run.
2. **Isolated:** Temp SQLite databases and mocked external APIs eliminate side effects.
3. **Property-Based:** Hypothesis generates hundreds of random inputs to fuzz boundary conditions, unicode, and extreme payloads.
4. **Reproducible:** Run `./run_objective_tests.sh` locally or in CI with zero setup.
