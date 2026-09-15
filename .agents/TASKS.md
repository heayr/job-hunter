# TASKS

## CURRENT

### TASK-007 — AI Processing & Pitch Refinement (Требуется доработка работы с ИИ)

Status: REQUIRED / PLANNED FOR NEXT SPRINT

Goal:
Make AI generation less generic/soulless, improve personalization depth, and refine how Gemini interacts with candidate profiles and vacancy context.

Steps:
- [ ] Audit current prompts in `generator/llm_generator.py` to remove robotic clichés.
- [ ] Add deep vacancy decomposition: extract exact company pain points, tech stack nuances, and tone-of-voice before writing pitch.
- [ ] Feed richer candidate background (specific projects, achievements, Github repos) into the prompt context.
- [ ] Support prompt style templates (e.g. "Confident Senior", "Concise Engineer", "Enthusiastic Starter").
- [ ] Improve fallback handling and retry mechanisms for Gemini API (timeouts, VPN proxy).

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

- [x] TASK-001 — Restore Frontend (Clean rewrite of `crm_v2_template.html`).
- [x] TASK-002 — Backend Stabilization (`start.sh`, CORS, port 8115).
- [x] TASK-003 — Auto-Apply Implementation (Pivoted to Bookmarklet).
- [x] TASK-004 — Auto-Apply Bookmarklet UI Integration & Dynamic Origin Binding.
- [x] Bugfix: `intern` regex word boundaries in `filter/profile_filter.py`.
- [x] Bugfix: Deterministic & AI Match Scoring (avg 65.1% across vacancies).
- [x] Bugfix: Contacts formatting in Cover Letter and profiles.
- [x] Scraper cleanup: Removed `@forwebdev`, improved Telegram title heuristic.
- [x] SQLite foundation & 14 Automated Unit Tests.
- [x] Harvest v3.
- [x] Anti-BS filtering.
- [x] profiles.json & resume parser.
