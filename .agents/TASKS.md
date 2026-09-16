# TASKS

## CURRENT

### TASK-007 — AI Processing & Pitch Refinement (Требуется доработка работы с ИИ)

Status: REQUIRED / PLANNED FOR NEXT SPRINT

Goal:
Make AI generation less generic/soulless, improve personalization depth, and refine how Gemini interacts with candidate profiles and vacancy context.

Steps:
- [ ] Audit current prompts in `generator/llm_generator.py` to remove robotic clichés.
- [x] Add deep vacancy decomposition: extract exact company pain points, tech stack nuances, and tone-of-voice before writing pitch.
- [x] Feed richer candidate background (specific projects, achievements, Github repos) into the prompt context.
- [x] Abstract away "startup founder/creator" framing to avoid recruiter red flags; position purely as Lead Frontend / Product Engineer.
- [x] Improve fallback handling and multi-model retry mechanisms for Gemini API (503 capacity spikes, timeouts, VPN).

---

### TASK-006 — Live Form Testing (HH.ru / LinkedIn)

Status: IN PROGRESS

Goal:
Test the installed Bookmarklet in a live user browser session on HH.ru and LinkedIn modals to verify native autofill events.

Steps:
- [ ] User drags «🔖 Auto-Apply» bookmarklet to browser bookmarks bar.
- [ ] Open a job on HH.ru or LinkedIn and click Bookmarklet.
- [ ] Verify that cover letter fills and changes submit button state.

---

## NEXT

### TASK-005 — Telegram Swipe-Bot Integration

Status: TODO

Goal:
Create a Telegram bot UI for swiping/approving vacancies on the go (Tinder-style), syncing with the local SQLite DB.

Steps:
- [ ] Define Telegram Bot API architecture (polling vs webhook).
- [ ] Create `/api/telegram/pending` endpoint or local DB access script.
- [ ] Implement Approve/Reject logic in Python.
- [ ] Add Telegram bot token to `config.json` and Settings Modal.

---

# COMPLETED

- [x] TASK-009 — Frontend Monolith Decomposition (ADR-006: `crm_v2_template.html` 2023 lines -> 533 lines + static/js/ modules).
- [x] TASK-008 — Architecture & Refactoring Rules (`.agents/REFACTORING_RULES.md`, `generator/resume_parser.py` decomposed with snapshot tests).
- [x] TASK-001 — Restore Frontend (Clean rewrite of `crm_v2_template.html`).
- [x] TASK-002 — Backend Stabilization (`start.sh`, CORS, port 8115).
- [x] TASK-003 — Auto-Apply Implementation (Pivoted to Bookmarklet).
- [x] TASK-004 — Auto-Apply Bookmarklet UI Integration & Dynamic Origin Binding.
- [x] Bugfix: `intern` regex word boundaries in `filter/profile_filter.py`.
- [x] Bugfix: Deterministic & AI Match Scoring (avg 65.1% across vacancies).
- [x] Bugfix: Role mismatch penalty (-55 pts for QA, SDET, DevOps, PM, Designer) dropping non-target vacancies from 85% to <10%.
- [x] Auto-Apply 2.0: Auto-expanding HH.ru cover letter toggle, numeric vacancy ID matching across subdomains/redirects, in-page feedback toast, interactive setup modal with one-click code copy.
- [x] Scraper & DB Hardening: Filtered out archived/closed vacancies across Habr (`sort=date`), HH (`order_by=publication_time&period=14`, `archived` check), GeekJob (`status` check).
- [x] Automated DB Cleanup: Implemented concurrent `tracker/cleanup_closed.py` and auto-hooked it to `harvest.py` to purge dead/closed links from the feed.
- [x] Purge RemoteOK: Decommissioned `RemoteOKScraper` and archived 12 paywalled vacancies from database.
- [x] Direct Sourcing & OSINT Dorks: Smart company brand cleaner, direct ATS (Greenhouse/Lever/Ashby) search, Setka.ru (Сетка) integration, multi-channel HR/CTO/Email search.
- [x] Bugfix: Contacts formatting in Cover Letter and profiles.
- [x] Scraper cleanup: Removed `@forwebdev`, improved Telegram title heuristic.
- [x] SQLite foundation & 14 Automated Unit Tests.
- [x] Harvest v3.
- [x] Anti-BS filtering.
- [x] profiles.json & resume parser.
