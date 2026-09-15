# CHANGELOG

## 2026-09-16

### Anti-Hack Rules & Full Real-Time Publication Pipeline
- **Strict Project Rule Update (`.agents/AGENTS.md`):** Added explicit prohibition of half-baked features, placeholders, and mock heuristics in production code. Any UI feature (sorting, filtering, metrics) must be backed end-to-end by real data models, DB migrations, backend APIs, and scrapers.
- **Real Publication Timestamps (`published_at`):**
  - Added `published_at TEXT` column to `vacancies` table with automatic DB migration and backfill.
  - Scrapers (`HHScraper`, `TelegramScanner`, `SuperJobScraper`, `RabotaRuScraper`) extract actual publication timestamps from APIs and schema.org metadata.
  - CRM endpoint `/api/pitches` returns `published_at`.
  - Frontend sorts by actual milliseconds (`new Date(published_at)`), displays live relative time badges (`⏱ 15 мин назад`, `⏱ 2 ч назад`).
- **Junior/Intern Positions Retained:** Removed drop filters, added `detect_vacancy_grade()`, added grade badges.
- **SuperJob & Rabota.ru Integration:** Zero-auth scrapers with ld+json and SSR state extraction.
- **Multi-Persona Profiles:** Added active profile switcher in navbar wired to `config.json`.

---

## 2026-09-14

### Remote Job Platforms & International Market Separation

- **New Remote Scraper (`CryptoJobsList`):** Added `scrapers/crypto_scraper.py` extracting remote frontend, web3, and fullstack positions from CryptoJobsList RSS (`https://cryptojobslist.com/rss`).
- **New Remote Scraper (`Remotive`):** Added `scrapers/remotive_scraper.py` integrating the Remotive API (`https://remotive.com/api/remote-jobs?category=software-dev`) for worldwide remote developer positions.
- **Expanded Scrapers:** Enhanced `scrapers/remoteok_scraper.py` with multi-tag queries (`react`, `frontend`, `typescript`), added remote dev Russian Telegram channels (`@forfrontend`, `@normrabota`).
- **International vs Local Market Separation:**
  - Added `language` (`'ru'` | `'en'`) column to SQLite `vacancies` schema with automatic PRAGMA migration.
  - Added Market Filter Bar to CRM UI (`[ 🌐 Все ]`, `[ 🇷🇺 RU ]`, `[ 🌍 Remote ]`) with live counters.
  - Added distinct visual badges (`🌍 EN · Remote` vs `🇷🇺 RU`) on cards and in the detail pane.
  - Connected candidate persona routing: English remote vacancies auto-bind to the English international persona, Russian vacancies bind to the Russian persona.
  - Added 6 automated tests in `tests/test_new_scrapers.py` (total 20 unit tests, 20/20 PASS).

---

### Core Fixes & Stabilization

- **Filter bugfix:** Fixed regex word boundaries for `intern` (`\bintern\b|\binternship\b`) in `filter/profile_filter.py`. Vacancies mentioning `international`, `internal`, and `internet` are now properly retained.
- **Match Scoring Engine:** Implemented deterministic tech stack Match Score (30-98%) in `generator/pitch_builder.py` and updated Gemini JSON prompt. Recalculated match scores for all 54 vacancies (average score: 65.1%).
- **Contacts Fix:** Replaced fragile string-splitting in `pitch_builder.py` with direct `contacts_structured` mapping. Fixed bug where Telegram handle duplicated into Email. Corrected corrupted Telegram field in English profile (`profiles.json`).
- **Bookmarklet UI:** Integrated «🔖 Auto-Apply» button in CRM navbar with dynamic `window.location.origin` binding.
- **Scraper Cleanup:** Removed tech blog channel `@forwebdev` from `telegram_scraper.py` and added rejection of candidate resumes and noise lines.
- **Auto-Sender Fix:** Fixed SQL query in `auto_sender.py` (`JOIN pitches` on `pitch_type = 'short_dm'`).
- **Cleanup:** Removed dead `run_pipeline.py`, archived unused `personas.json`.
- **Testing:** Added 14 unit tests covering filter boundaries, contact generation, scoring, and CRM API endpoints (14/14 PASS).

---

## Previous

- Frontend rebuild & recovery
- Harvest v3 implemented
- Resume parser implemented
- Multi-persona profiles implemented