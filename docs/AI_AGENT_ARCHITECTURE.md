# 🧠 AI CAREER AGENT ARCHITECTURE & TRANSFORMATION BLUEPRINT

> **Job Hunter Evolution:** From a Local Job Scraper & Pitch Template Generator to an Autonomous, Reasoning-Driven **AI Career Agent**.

---

## 1. Executive Summary & Audit Findings (Phase 0)

### 1.1 Existing System Overview
Job Hunter currently operates as a lightweight, zero-dependency, local-first Python application with:
- **Backend:** Standard library `http.server.BaseHTTPRequestHandler` running on port `8115` (`crm.py`), backed by SQLite (`jobs.db`).
- **Frontend:** Single-page dashboard (`crm_v2_template.html`) styled with Tailwind CSS via CDN and modularized Vanilla JS (`static/js/`).
- **Scrapers:** Multi-source scrapers (`scrapers/`) pulling from Telegram, HH.ru, Habr Career, RemoteOK, Remotive, WWR, CryptoJobsList.
- **AI Integration:** Direct HTTP calls (`urllib.request`) to Google Gemini API (`gemini-flash-latest`, `gemini-flash-lite-latest`) in `generator/llm_generator.py` and `enricher/ai_parser.py`.
- **Profiles & Parsing:** Candidates manage multiple persona profiles stored in `generator/profiles.json`. Resumes in PDF/DOCX can be parsed into profile schemas via `generator/resume_parser.py` (using `pypdf` and `python-docx`).
- **Pitches & Applications:** Generates `short_dm`, `cover_letter`, and `tailored_cv` (markdown) per vacancy.
- **Browser Outreach:** An auto-apply JavaScript bookmarklet (`static/js/bookmarklet.js`) injected into the active browser DOM on HH.ru, LinkedIn, Greenhouse, Lever, etc.

### 1.2 The Architectural Bottleneck
Today's pipeline is largely **linear, heuristic, and prompt-coupled**:
```
Job Description + Flat Resume Profile 
   → Single Gemini Prompt 
   → Generated Cover Letter & DM (Text) + Rough Match Score (0-100)
```
**Critical Deficiencies:**
1. **No Deep Cognitive Loop:** No reasoning stage, no hypothesis formation, no thesis validation.
2. **No Evidence Verification:** The LLM receives a flat text block of profile experience and can hallucinate achievements, skills, or metrics without strict provenance.
3. **No Dynamic Company Research:** The LLM knows only what is pasted in the vacancy description; it cannot investigate the company's real engineering blog, tech stack signals, or actual product problems.
4. **No Criticism or Fact-Checking:** Whatever the model outputs in one shot is accepted and saved to the database.
5. **No True Browser Agency:** The bookmarklet relies on hardcoded string heuristics in DOM fields and cannot handle multi-step flows, dynamic validation, or feedback loops.

---

## 2. Target Architecture: The AI Career Agent

The new paradigm replaces one-shot text generation with an **Observability & Evidence-Grounded Agentic Cycle**:

```mermaid
flowchart TD
    subgraph Observability ["1. OBSERVE & UNDERSTAND"]
        Job[Raw Vacancy Description / URL] --> JobEngine[Job Understanding Engine]
        Company[Company Domain / Info] --> CompEngine[Company Research Engine]
        JobEngine --> JobFacts[Explicit & Implicit Requirements, Risks, Unknowns]
        CompEngine --> CompFacts[Engineering Signals, Stack Realities, Business Context]
    end

    subgraph Grounding ["2. EVIDENCE & REASONING"]
        Prof[Canonical Candidate Profile] --> EvRetriever[Evidence Retriever]
        JobFacts --> EvRetriever
        EvRetriever --> MatchedEvidence[Evidence Graph & Fact Bindings]
        MatchedEvidence --> ThesisGen[Application Thesis Generator]
        ThesisGen --> ThesisCritic[Thesis Critic & Fact Checker]
        ThesisCritic -->|Weak/Hallucinated| ThesisGen
        ThesisCritic -->|Approved| AppStrategy[Application Strategy]
    end

    subgraph Generation ["3. TAILORED ARTIFACT CREATION"]
        AppStrategy --> CVEngine[Tailored CV Engine (View of Profile)]
        AppStrategy --> CLEngine[Cover Letter Engine (Narrative)]
        CVEngine --> ATSCheck[ATS Analysis & Keyword Density Verification]
        CLEngine --> LetterCritic[No-Cliche Quality Critic]
    end

    subgraph Action ["4. ACT & VERIFY (HUMAN-IN-THE-LOOP)"]
        Browser[Browser Adapter / Extension] --> FormInspector[Semantic Form Inspection]
        ATSCheck --> FormMapper[Field Mapping & Pre-Fill]
        LetterCritic --> FormMapper
        FormMapper --> UserPreview[User Inspection & Approval (Assist/Semi-Auto)]
        UserPreview -->|Approved| SubmitAction[Execution & Submission]
        SubmitAction --> CRMTrack[CRM History & Agent Run Log]
    end
```

---

## 3. Detailed Component Audit & Reusability Matrix

| Subsystem | Existing File(s) | Current State | Reusable Assets | Required Changes for Agent Evolution |
| :--- | :--- | :--- | :--- | :--- |
| **Candidate Profile** | `generator/profiles.json`, `resume_parser.py` | Flat JSON array with loose `experience` text. | Name, contacts structure, PDF/DOCX text extraction routines. | Upgrade to **Canonical Profile Schema**: structured entities for Projects, Experience, and strictly verifiable **Evidence** items (Problem → Context → Action → Decision → Result → Tech → Source). |
| **Job Understanding** | `enricher/ai_parser.py`, `anti_bs_filter.py` | Regex traps (anti-BS) + single JSON extraction prompt. | Trap detection, clean HTML text fetching from URL. | Split into a dedicated `JobUnderstandingEngine` producing explicit vs. implicit requirements, team context, unknowns, and risks. |
| **Company Research** | *None* (only URL text fetch) | Missing. | `fetch_clean_text_from_url` in `enricher/ai_parser.py`. | Build `CompanyResearchEngine` with bounded search / web scrape to extract tech stack signals and engineering blog insights. |
| **Matching & Reasoning** | `generator/pitch_builder.py` | Static keyword intersection (`KNOWN_TECH_KEYWORDS`). | Base tech dictionary. | Replace keyword matching with **Semantic Evidence Retrieval** and **Application Thesis Generation & Critique**. |
| **Pitch & Content Gen** | `generator/llm_generator.py` | Single prompt generating `short_dm`, `cover_letter`, `score`. | Low-level Gemini HTTP invocation and model fallback logic. | Modularize into discrete roles: Strategist, Writer, Critic, Fact-Checker. Eliminate generic templates and enforce evidence citation. |
| **Tailored CV** | `pitch_builder.py:build_tailored_cv` | Hardcoded string interpolation template. | Clean formatting concepts. | Treat Tailored CV as a transient **View** of the Canonical Profile with semantic ordering, rephrasing, and ATS alignment. |
| **Storage & Tracking** | `tracker/db.py`, `jobs.db` | SQLite tables: `vacancies`, `pitches`. | Connection pooling, auto-migration helper, status flags. | Add tables: `candidate_profiles`, `application_theses`, `agent_runs`, `company_dossiers`. |
| **Browser Execution** | `static/js/bookmarklet.js` | Single-shot heuristic DOM filler script. | DOM context extraction, input/change event dispatching, HH.ru modal handling. | Migrate toward a structured **Browser Platform Adapter** and Manifest V3 Chrome Extension side-panel with semantic representation. |
| **CRM Web UI** | `crm_v2_template.html`, `static/js/` | Tabbed dashboard with modals and profiles editor. | Layout, modals, toast system, API clients, Tailwind styling. | Add Agent Run Log inspector, Thesis Review card, and Interactive Assist/Approval drawer. |

---

## 4. Phased Implementation Roadmap (Phases 0 to 20)

To adhere strictly to Engineering Standards (stability, data safety, backward compatibility, and testability), the transformation is structured into 5 major milestones comprising 21 bite-sized phases:

### Milestone I: Knowledge Foundation & Semantic Reasoning (Phases 0–5)
- **Phase 0: Codebase Audit & Architectural Blueprint** ✅ COMPLETE
- **Phase 1: Canonical Candidate Profile & Evidence Store** ✅ COMPLETE
  - `generator/candidate_profile.py` — structured schema, zero-hallucination invariants, legacy upgrade
  - SQLite table `candidate_profiles` with `data_json` blob
- **Phase 2: Job Understanding Engine** ✅ COMPLETE
  - `generator/job_understanding.py` — explicit/implicit requirements, facts vs hypotheses
- **Phase 3: Semantic Evidence Retrieval Layer** ✅ COMPLETE
  - `generator/evidence_retriever.py` — pain-to-capability mapping with 5 strategic presets
- **Phase 4: Application Thesis Generator** ✅ COMPLETE
  - `generator/thesis_generator.py` — singular compelling argument with alternatives
- **Phase 5: Thesis Critic & Hallucination Gate** ✅ COMPLETE
  - `generator/thesis_critic.py` — adversarial validator (APPROVED/NEEDS_REVISION/REJECTED)

### Milestone II: Contextual Research & Strategy (Phases 6–7)
- **Phase 6: Bounded Company Research Engine** ✅ COMPLETE
  - `generator/company_researcher.py` — bounded web fetch, 7-day cache, heuristic fallback
- **Phase 7: Application Strategy Layer** ✅ COMPLETE
  - `generator/application_strategy.py` — positioning, tone, emphasis, deliberate omissions

### Milestone III: Precision Artifact Generation & Quality Control (Phases 8–11)
- **Phase 8: Tailored Resume Engine (Profile View)** ✅ COMPLETE
  - `generator/tailored_resume_engine.py` — ATS-compliant structured resume JSON → Markdown
- **Phase 9: ATS Analysis Engine** ✅ COMPLETE
  - `generator/ats_analyzer.py` — keyword coverage, parseability, stuffing detection
- **Phase 10: Evidence-Driven Cover Letter & Pitch Engine** ✅ COMPLETE
  - `generator/cover_letter_engine.py` — Draft → Adversarial Critic → Fact-Check → Final
- **Phase 11: Multi-Agent Specialized Roles** ✅ COMPLETE
  - `agents/multi_agent_roles.py` — 6 agents (JobAnalyst, CompanyResearcher, CandidateStrategist, Writer, Critic, FactChecker)

### Milestone IV: Agent Runtime & Browser Infrastructure (Phases 12–16)
- **Phase 12: Agent Runtime & Finite State Machine** ✅ COMPLETE
  - `agents/runtime.py` — 9-state FSM, timeouts (30s), retries (max 2)
- **Phase 13: Strict Tool System** ✅ COMPLETE
  - `agents/tool_system.py` — 6 declarative tools with validation
- **Phase 14: Browser Extension (Side Panel & Content Bridge)** ✅ COMPLETE
  - `extension/` — Manifest V3, modular architecture (core, adapters, autofill, automation)
- **Phase 15: Platform Adapters (HH.ru, LinkedIn, Greenhouse, Lever)** ✅ COMPLETE
  - `extension/platform-adapters.js` — 4 adapters with detect/extract/prepare/customFill
- **Phase 16: Human-in-the-Loop & Execution Guardrails** ✅ COMPLETE
  - Three modes: ASSIST (drafts only), SEMI_AUTO (pre-fill), AUTO (fill + submit + anti-detection)

### Milestone V: Observability, Enterprise CRM & End-to-End Delivery (Phases 17–20)
- **Phase 17: Application CRM History** ✅ COMPLETE
  - `application_history` table + `/api/applications/record` endpoint
- **Phase 18: Observability & Agent Run Logs** ✅ COMPLETE
  - `agent_run_logs` table + step-by-step trace in UI
- **Phase 19: Automated Quality Control Pipeline** ⚠️ PARTIAL
  - 122 unit tests exist, but no CI/CD pipeline, no coverage reporting
- **Phase 20: End-to-End MVP Verification** ✅ COMPLETE
  - Full drill: scrape → AI parse → agent reason → form fill → submit → audit trail

---

## 5. Architectural Principles & Invariants

1. **Zero Hallucination Invariant:**
   The AI is strictly prohibited from inventing companies, employment dates, skills, metrics, or achievements. If an engineering capability is not present in the Canonical Profile evidence graph, the AI cannot claim it.
2. **Backward Compatibility:**
   Existing SQLite records (`vacancies`, `pitches`), the current CRM UI, and the JS Bookmarklet must continue to function uninterrupted at each phase.
3. **Local Sovereignty:**
   Candidate data and database records remain 100% on the user's machine (`jobs.db`).
4. **Structured Reasoning over Raw Text:**
   Inter-agent communication and intermediate pipeline states must be strongly typed JSON objects, not unstructured markdown. Final human text is produced only at the final writer step.
