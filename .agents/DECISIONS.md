# ARCHITECTURAL DECISIONS

## ADR-001 — Vanilla JS Frontend

Decision:

Use Vanilla JS instead of React.

Reason:

The project is intentionally lightweight and local.

Do not introduce React without explicit approval.

---

## ADR-002 — SQLite

Decision:

Use SQLite.

Reason:

The project is local/lightweight and does not require a database server.

---

## ADR-003 — Python http.server

Decision:

Use Python standard library HTTP server.

Reason:

Avoid unnecessary backend framework overhead.

---

## ADR-004 — Single Frontend File

Decision:

Current CRM frontend remains a single HTML file.

Reason:

Simple deployment and lightweight architecture.

If this decision becomes problematic, document a new ADR before changing it.
## ADR-005 — Bookmarklet instead of Playwright

Decision:

Use a JS Bookmarklet injected from the CRM UI instead of a backend Python Playwright bot for auto-applying.

Reason:

1. **Environment Constraints:** Python 3.14 in the sandbox lacked pre-compiled Playwright wheels, and npm access was blocked (403).
2. **Anti-Bot Defenses:** Job boards like HH.ru and LinkedIn heavily block headless browsers (Cloudflare Turnstile, DataDome) and require complex session sharing to bypass 2FA/Captchas.
3. **Simplicity:** A Bookmarklet executes in the user's existing authenticated browser context, entirely bypassing bot detection while natively auto-filling the DOM.

---

## ADR-006 — Modular Vanilla JS Frontend (Supersedes ADR-004)

Decision:

Split the 2000+ line monolithic `crm_v2_template.html` into clean, focused Vanilla JS modules served from `/static/js/`.

Reason:

1. `crm_v2_template.html` grew to over 2000 lines (1500 lines of JS inside an HTML `<script>` tag), leading to escaping bugs and severe maintainability issues.
2. Separation into modules (`api.js`, `state.js`, `bookmarklet.js`, `views/`, `app.js`) adheres to Single Responsibility Principle while strictly preserving ADR-001 (Zero frameworks, 100% Vanilla JS).

