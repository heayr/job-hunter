# System Architecture

Job Hunter CRM — autonomous local-first AI career agent. Scrapes jobs, generates tailored pitches via Gemini AI, auto-fills application forms in the browser with anti-detection, and tracks the full application lifecycle.

---

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        1. JOB MARKET INGESTION                      │
│  Telegram · HH.ru · Habr · RemoteOK · Remotive · WWR · Crypto     │
│  SuperJob · Rabota.ru · HackerNews · Jobicy · ATS (Greenhouse etc) │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     2. PROCESSING PIPELINE                          │
│  Anti-BS Filter → Market Segmentation (RU/EN) → Score Matcher      │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     3. AI COGNITIVE AGENT (6 agents)                │
│  JobAnalyst → CompanyResearcher → CandidateStrategist              │
│  → Writer → Critic → FactChecker                                   │
│                                                                     │
│  Outputs: understanding · thesis · strategy · resume · cover letter │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     4. LOCAL STORAGE (SQLite)                       │
│  vacancies · pitches · candidate_profiles · application_history     │
│  agent_tasks · agent_run_logs · company_dossiers                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     5. CRM WEB UI                                   │
│  Dashboard · Vacancy Details · Profiles · Settings · Modals         │
│  Python HTTP server (:8115) + Vanilla JS + Tailwind CSS            │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     6. BROWSER AUTOMATION                           │
│  Chrome Extension (Manifest V3)                                     │
│  ├── core.js            — anti-detection utilities                  │
│  ├── platform-adapters.js — HH, LinkedIn, ATS, Generic adapters    │
│  ├── autofill.js        — form filling engine                      │
│  ├── automation.js      — CAPTCHA detect, auto-submit, multi-step  │
│  ├── content_script.js  — message orchestrator                     │
│  ├── background.js      — autonomous agent worker                  │
│  └── sidepanel.js       — side panel UI controller                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.x (`http.server`, `sqlite3`, `urllib`) | Zero dependencies, instant cold start |
| Frontend | Vanilla JS + Tailwind CSS (CDN) | No build step, instant reload |
| Database | SQLite (`jobs.db`) | 100% local, zero config |
| AI | Google Gemini API (`gemini-flash`) | Fast, cheap, structured output |
| Automation | Chrome Extension (Manifest V3) | Runs in user's authenticated browser, immune to bot detection |

---

## Directory Structure

```
job_hunter/
├── crm.py                    # HTTP server — all API endpoints (682 lines)
├── crm_v2_template.html      # Single-file CRM UI
├── start.sh                  # Launch script (kills old, starts new)
├── jobs.db                   # SQLite database
├── config.json               # Gemini API key + settings
│
├── scrapers/                 # 11 job source scrapers
│   ├── base.py               # BaseScraper interface
│   ├── telegram_scraper.py   # Telegram channel parser
│   ├── hh_scraper.py         # HeadHunter API
│   ├── habr_scraper.py       # Habr Career
│   ├── remoteok_scraper.py   # RemoteOK API
│   ├── remotive_scraper.py   # Remotive API
│   ├── wwr_scraper.py        # WeWorkRemotely RSS
│   ├── crypto_scraper.py     # CryptoJobsList
│   ├── superjob_scraper.py   # SuperJob
│   ├── rabotaru_scraper.py   # Rabota.ru
│   ├── hackernews_scraper.py # HN Who's Hiring
│   ├── jobicy_scraper.py     # Jobicy
│   └── ats_scraper.py        # Greenhouse/Lever/Ashby/Workable
│
├── enricher/                 # Data enrichment
│   ├── lead_finder.py        # Contact extraction (TG, email, phone)
│   └── ai_parser.py          # AI vacancy parser + CRM ingester
│
├── filter/                   # Vacancy filtering
│   └── profile_filter.py     # Anti-BS filter, grade detection
│
├── generator/                # AI content generation (13 modules)
│   ├── pitch_builder.py      # Orchestrator — assembles final pitch
│   ├── cover_letter_engine.py # Multi-stage cover letter (Draft→Critic→Final)
│   ├── tailored_resume_engine.py # ATS-compliant resume builder
│   ├── ats_analyzer.py       # ATS keyword scoring
│   ├── llm_generator.py      # Gemini API wrapper + model fallback
│   ├── candidate_profile.py  # Canonical profile schema + validator
│   ├── job_understanding.py  # Facts vs hypotheses extraction
│   ├── company_researcher.py # Bounded company intelligence
│   ├── thesis_generator.py   # Application thesis formulation
│   ├── thesis_critic.py      # Adversarial thesis validator
│   ├── evidence_retriever.py # Pain-to-capability evidence mapping
│   ├── application_strategy.py # Positioning + narrative strategy
│   └── resume_parser.py      # PDF/DOCX resume parser
│
├── agents/                   # Multi-agent orchestration
│   ├── runtime.py            # FSM runtime (9 states, retries, timeouts)
│   ├── multi_agent_roles.py  # 6 specialized agent roles
│   └── tool_system.py        # Declarative tool registry (6 tools)
│
├── tracker/                  # Persistence layer
│   ├── db.py                 # SQLite schema, migrations, CRUD functions
│   ├── shame_list.py         # Blacklist/shame list generator
│   └── cleanup_closed.py     # Closed vacancy cleanup
│
├── auto_sender.py            # Telegram DM auto-send (Telethon)
│
├── extension/                # Chrome Extension (Manifest V3)
│   ├── manifest.json         # Permissions, content scripts, icons
│   ├── core.js               # Shared utilities (anti-detection, CAPTCHA, click simulation)
│   ├── platform-adapters.js  # Platform-specific form detection (HH, LinkedIn, ATS, Generic)
│   ├── autofill.js           # Form filling engine (backward compatible)
│   ├── automation.js         # Auto-submit, multi-step traversal, CAPTCHA handling
│   ├── content_script.js     # Message orchestrator (27 lines)
│   ├── background.js         # Autonomous agent worker (polling, cooldown, retries)
│   ├── sidepanel.js          # Side panel UI controller
│   └── sidepanel.html        # Side panel markup
│
├── static/js/                # CRM frontend modules
│   ├── app.js                # Entry point, state management
│   └── views/
│       ├── vacancies.js      # Vacancy list, details, agent trigger
│       └── modals.js         # Settings, harvest, AI parser modals
│
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # This file
│   ├── AI_AGENT_ARCHITECTURE.md # Full 20-phase transformation roadmap
│   ├── SCRAPERS_GUIDE.md     # How to add new scrapers
│   └── CONFIGURATION.md      # Setup guide
│
└── tests/                    # 122 unit tests
    ├── test_*.py             # Tests for scrapers, filters, CRM, agents, etc.
    └── snapshot_*.json       # Test fixtures
```

---

## Database Schema (jobs.db)

### Core Tables

#### `vacancies` — All scraped/parsed job records
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | Unique ID (`tg:...`, `hh:...`, `ai:...`) |
| `source` | TEXT | Source identifier (`tg_job_react`, `hh`, `ai_import`) |
| `title` | TEXT | Job title |
| `company` | TEXT | Company name |
| `url` | TEXT | Direct vacancy URL |
| `salary` | TEXT | Salary string or "Не указана" |
| `location` | TEXT | Location |
| `is_remote` | INTEGER | 1 if remote |
| `description` | TEXT | Full job description |
| `skills` | TEXT | Comma-separated tech stack |
| `contact_name` | TEXT | Contact person name |
| `contact_handle` | TEXT | Direct contact (TG handle, email) |
| `contact_type` | TEXT | `telegram` / `email` / `portal` / `ats` |
| `score` | INTEGER | Match score 0–100 |
| `status` | TEXT | `new` / `inbox` / `sent` / `replied` / `archive` / `blacklist` |
| `language` | TEXT | `ru` or `en` |
| `grade` | TEXT | `Junior` / `Middle` / `Senior` / `Lead` |
| `fsm_state` | TEXT | Agent FSM state |
| `understanding_json` | TEXT | Job understanding analysis (Phase 2) |
| `application_thesis_json` | TEXT | Application thesis (Phase 4) |
| `application_strategy_json` | TEXT | Application strategy (Phase 7) |
| `ats_report_json` | TEXT | ATS analysis report |

#### `pitches` — Generated content per vacancy
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `pitch_type` | TEXT | `short_dm` / `cover_letter` / `tailored_cv` |
| `language` | TEXT | `ru` or `en` |
| `content` | TEXT | Generated text |
| `status` | TEXT | `DRAFT` / `APPROVED` / `SENT` |

#### `candidate_profiles` — Multi-persona profiles
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | Profile UUID |
| `lang` | TEXT | `ru` or `en` |
| `target_role` | TEXT | e.g. "Frontend", "Fullstack" |
| `data_json` | TEXT | Full profile JSON (contacts, experience, evidence) |

#### `application_history` — Audit trail
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `company` | TEXT | Company name |
| `portal` | TEXT | Platform used |
| `mode` | TEXT | `ASSIST` / `SEMI_AUTO` / `AUTO` |
| `fsm_state` | TEXT | Final state |
| `metadata_json` | TEXT | Additional details |

#### `agent_tasks` — Browser automation queue
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `url` | TEXT | Target URL |
| `status` | TEXT | `PENDING` / `IN_PROGRESS` / `COMPLETED` / `FAILED` |
| `result_message` | TEXT | Execution result |

#### `agent_run_logs` — Agent execution trace
| Column | Type | Description |
|---|---|---|
| `vacancy_id` | TEXT | FK → vacancies.id |
| `step_name` | TEXT | Agent role name |
| `status` | TEXT | `SUCCESS` / `FAILED` |
| `duration_ms` | INTEGER | Step execution time |

---

## AI Agent Pipeline (6 Agents)

The multi-agent system runs 6 specialized agents in sequence:

```
Input: Raw vacancy text/URL
    │
    ▼
┌─────────────────────────┐
│ 1. JobAnalystAgent       │  understand_job_posting()
│    Facts vs Hypotheses   │  → explicit/implicit requirements
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 2. CompanyResearcher     │  research_company_context()
│    Bounded web fetch     │  → stack signals, engineering blog
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 3. CandidateStrategist   │  reframe_evidence() → thesis → strategy
│    Evidence mapping      │  → positioning, narrative tone
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 4. WriterAgent           │  generate_tailored_resume()
│    Content creation      │  + cover letter + short DM
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 5. CriticAgent           │  audit_ats() + fluff detection
│    Quality control       │  → refinement pass
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ 6. FactCheckerAgent      │  verify_facts() against canonical profile
│    Anti-hallucination    │  → confidence score
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

## Browser Extension Architecture

### Module System (Manifest V3)

Content scripts load in order:
```
core.js → platform-adapters.js → autofill.js → automation.js → content_script.js
```

Each module attaches to the global `JH` namespace:

| Module | Responsibility | Key Functions |
|---|---|---|
| `core.js` | Shared utilities | `setFieldValue()`, `humanType()`, `simulateClick()`, `detectCaptcha()`, `findSubmitButton()`, `findNextButton()`, `detectStepProgress()`, `checkDomainRate()` |
| `platform-adapters.js` | Platform detection + extraction | `HeadHunterAdapter`, `LinkedInAdapter`, `ModernATSAdapter`, `GenericWebAdapter` |
| `autofill.js` | Form filling (backward compatible) | `autofillFormOnPage()` — identical to original |
| `automation.js` | Auto-submit + anti-detection | `autoSubmitWithDetection()`, `traverseMultiStep()` |
| `content_script.js` | Message router (27 lines) | Routes `AUTOFILL_PAGE`, `AUTO_SUBMIT_PAGE`, `EXTRACT_PAGE_DATA`, `SHOW_RESULT_OVERLAY` |

### Message Types

| Message | Source | Handler | Behavior |
|---|---|---|---|
| `EXTRACT_PAGE_DATA` | Side Panel | `platform-adapters.js` | Extract job metadata from page DOM |
| `AUTOFILL_PAGE` | Side Panel / Background | `autofill.js` | Fill form fields only (SEMI_AUTO) |
| `AUTO_SUBMIT_PAGE` | Background | `automation.js` | Fill + CAPTCHA check + auto-submit (AUTO) |
| `SHOW_RESULT_OVERLAY` | Background | `core.js` | Show floating result notification |

### Anti-Detection Measures

| Measure | Implementation |
|---|---|
| Randomized delays | `randomDelay(1500, 4000)` after page load |
| Human-like typing | `humanType()` — character-by-character with 25-90ms delay |
| Click simulation | `simulateClick()` — mouse trajectory + mousedown/mouseup |
| Inter-task cooldown | 5-15s random delay between tasks |
| Domain rate limiting | Max 3 applications per domain per hour |
| CAPTCHA detection | Cloudflare Turnstile, reCAPTCHA, hCaptcha, DataDome |
| Framework-aware input | React/Vue/Angular prototype setter bypass |

### Task Lifecycle (background.js)

```
1. Poll CRM /api/agent/pending-tasks (every 3.5s)
2. Fetch candidate profile
3. Create tab (active: true)
4. Wait for tab load (25s timeout)
5. Randomized delay (1.5-4s)
6. Send AUTO_SUBMIT_PAGE or AUTOFILL_PAGE based on mode
7. Content script:
   a. CAPTCHA pre-check → block if detected
   b. Domain rate check → block if exceeded
   c. Fill form fields
   d. CAPTCHA re-check before submit
   e. Find and click submit button
   f. Return result
8. Report status to CRM
9. Show overlay + notification
10. Inter-task cooldown (5-15s)
```

---

## API Endpoints (crm.py)

### Vacancies
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/pitches` | All vacancies with joined pitches |
| POST | `/api/vacancies/ai-parse` | Universal AI vacancy parser |
| POST | `/api/vacancies/{id}/rewrite` | Regenerate pitches via AI |
| POST | `/api/vacancies/{id}/status` | Update vacancy status |
| GET | `/api/vacancies/{id}/runtime_state` | Get FSM state |
| GET | `/api/vacancies/{id}/thesis` | Application thesis |
| GET | `/api/vacancies/{id}/strategy` | Application strategy |
| GET | `/api/vacancies/{id}/tailored_cv` | On-demand tailored resume |
| GET | `/api/vacancies/{id}/ats_report` | ATS analysis |

### Agent
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/agent/queue-task` | Queue auto-apply task |
| GET | `/api/agent/pending-tasks` | Get pending tasks (for extension) |
| POST | `/api/agent/task-status` | Report task completion |
| GET | `/api/agent/tools` | Registered agent tools |

### Profiles & Config
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/profiles` | All candidate profiles |
| POST | `/api/profiles` | Save profile |
| GET | `/api/config` | Get configuration |
| POST | `/api/config` | Save configuration |
| POST | `/api/upload_resume` | Parse PDF/DOCX resume |

### Other
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/applications/record` | Record application event |
| GET | `/api/applications/history` | Application audit trail |
| GET | `/api/harvest/status` | Harvest run status |
| POST | `/api/harvest` | Start harvest |
| GET | `/api/shame_list` | Blacklist export |
| POST | `/api/vacancies/{id}/apply_tg` | Telegram auto-send |

---

## What's Implemented vs What's Missing

### Fully Implemented (Production Ready)
- [x] 11 source scrapers with anti-BS filtering
- [x] Multi-persona profile system with PDF/DOCX parsing
- [x] AI vacancy parsing (Gemini + heuristic fallback)
- [x] 6-agent cognitive pipeline (understand → research → strategy → write → critique → verify)
- [x] FSM runtime with states, retries, timeouts
- [x] CRM web UI with filtering, sorting, analytics
- [x] Chrome extension with 4 platform adapters
- [x] Auto-fill engine (React/Vue/Angular compatible)
- [x] Auto-submit with CAPTCHA detection
- [x] Multi-step form traversal
- [x] Anti-detection (random delays, click simulation, rate limiting)
- [x] Application audit trail
- [x] Telegram auto-send via Telethon
- [x] Blacklist/shame list system

### Partially Implemented
- [ ] Multi-step form traversal (basic, needs platform-specific adapters)
- [ ] LinkedIn Easy Apply (detects button, fills fields, but LinkedIn blocks automation frequently)
- [ ] File upload automation (highlights input, can't programmatically attach files)

### Not Implemented (Future Work)
- [ ] CAPTCHA solving (detection works, no solver integrated)
- [ ] Email applications via SMTP
- [ ] Webhook/API-based ATS applications
- [ ] Rate-limited retry with exponential backoff for failed tasks
- [ ] Task priority/scheduling in agent_tasks table
- [ ] Application confirmation tracking (verify receipt by employer)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Docker containerization
- [ ] Code quality tooling (ruff, mypy, pre-commit)

---

## Configuration

### config.json
```json
{
  "gemini_api_key": "AIzaSy...",
  "active_profile_id": null,
  "seniority_alignment": true,
  "highload_guardrail": true
}
```

### Environment Variables (for Telegram auto-send)
```bash
export TG_API_ID=12345
export TG_API_HASH=abc123def456
```

---

## Testing

```bash
python3 -m unittest discover tests
```

122 unit tests covering:
- All 11 scrapers
- Anti-BS filter logic
- AI parser heuristic fallback
- CRM API endpoints
- Agent FSM runtime
- Database migrations
- Contact extraction
- Profile validation
- End-to-end drill

Some tests require Gemini API access and may fail with 429/503 errors.
