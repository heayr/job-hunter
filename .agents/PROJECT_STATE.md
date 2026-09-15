# PROJECT STATE

Last updated: 2026-09-14
Current phase: Stabilization & Auto-Apply Implementation

---

# SYSTEM STATUS

## Backend

Status: STABLE

Working:
- SQLite integration (vacancies, pitches)
- Endpoints (pitches, upload, rewrite, status)
- Safe startup via `start.sh` (kills zombie processes on port 8105)
- Venv auto-injection in `crm.py`
- CORS headers for Bookmarklet support

Broken:
- None identified.

Known issues:
- Needs graceful shutdown handling (SIGINT).

---

## Frontend

Status: STABLE

Working:
- Single-page Vanilla JS + Tailwind
- Tab routing (Inbox, Sent, Replied, Profiles)
- Profile management (CRUD, Avatar Cropper)
- Modals (Settings, Harvest, Cropper)
- Gemini rewrite with simulated progress bar
- Bookmarklet installation button

Broken:
- None identified.

Known issues:
- None identified.

---

## Database

Status: STABLE
- schema: `jobs.db` initialized with vacancies and pitches.
- migrations: None currently required. Added `score` to vacancies recently.
- known issues: None.

---

## AI

Status: WORKING (IMPROVEMENTS REQUIRED / ТРЕБУЕТСЯ ДОРАБОТКА)

- Gemini integration: Working via `llm_generator.py` (model `gemini-1.5-flash`).
- scoring: Match % calculation working.
- generation: Cover Letters and Short DMs.
- structured output: JSON forced for resume parser.
- **Identified Flaw / Needs Work:** Output feeling too generic and repetitive across vacancies. Next phase requires prompt rewriting, dynamic persona injection, tone-of-voice adaptation, and deeper matching against company pain points.

---

## Resume Parser

Status: STABLE

- PDF: Working (via `pypdf`)
- DOCX: Working (via `python-docx`)
- JSON extraction: Working (extracts Role, Summary, Experience, Keywords).

---

## Auto-Apply (Bookmarklet)

Status: WORKING
- Smart JS Bookmarklet button «🔖 Auto-Apply» integrated into CRM Navbar.
- Dynamic origin detection via `window.location.origin` (supports 8115 and any port).
- Multi-selector fallback for HH.ru, LinkedIn, Habr Career, and generic forms.
- Automatic clipboard copy fallback if no form field is detected.

---

# CURRENT BLOCKER

None. All 72 vacancies categorized into RU and International Remote, scored, contacts verified, scrapers and filters stabilized.

---

# RECENTLY FIXED

- Added Remote Job Platforms: `CryptoJobsList` (`crypto_scraper.py`), `Remotive` (`remotive_scraper.py`), expanded `RemoteOK` (`remoteok_scraper.py`), and Russian dev channels (`telegram_scraper.py`).
- Market Separation: Added `language` column to database, Market Filter buttons (`[ 🌐 Все ]`, `[ 🇷🇺 RU ]`, `[ 🌍 Remote ]`), market card badges, and automatic persona routing.
- Fixed `intern` regex bug in `filter/profile_filter.py` (word boundaries added, preventing false positive drops on `international`, `internal`, `internet`).
- Added deterministic tech stack Match Score (30-98%) in `generator/pitch_builder.py` + added `score` to Gemini prompt.
- Fixed contact formatting in Cover Letter and profiles (isolated Telegram handle from Email, eliminating handle duplication).
- Cleaned Telegram scraper (removed tech article channel `@forwebdev`, improved title/company heuristic).
- Integrated drag-and-drop Bookmarklet button into CRM Navbar with dynamic origin binding.
- Fixed `auto_sender.py` SQL query (`JOIN pitches` on `pitch_type = 'short_dm'`).
- Removed broken `run_pipeline.py` and archived unused `personas.json`.
- Added 20 automated unit tests (20/20 PASS).

---

# CURRENTLY WORKING

- UI Navigation, Market Filtering (`All`, `RU`, `EN`), and Profile Parsing.
- Multi-Source Harvest (Telegram, Habr, CryptoJobsList, Remotive, RemoteOK, WWR).
- Database CRUD, Scoring & Market Separation (52 RU, 20 EN remote vacancies).
- Bookmarklet Auto-Apply base logic.
- Automated test suite (20 tests passing).

---

# CURRENTLY BROKEN

- None.

---

# DO NOT TOUCH

- `crm_v2_template.html` core architecture.
- `start.sh` port handling.

---

# NEXT ACTION

The next concrete task is:
> Test the Auto-Apply Bookmarklet in a live browser session on target portals (HH.ru / LinkedIn) and calibrate portal-specific form selectors.

---

# VERIFICATION

Last tests:
- `python -m unittest discover tests` -> 20 tests PASS (0.031s)
- UI script syntax check (`node -c`) -> PASS
- Endpoints check (`/api/pitches`, `/api/profiles`, `/api/config`) -> PASS
- Playwright render & visual interactive testing (RU & Remote market filtering) -> PASS

