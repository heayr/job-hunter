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
- **Phase 0: Codebase Audit & Architectural Blueprint** *(CURRENT)*
  - Complete project inventory.
  - Formulate `docs/AI_AGENT_ARCHITECTURE.md`.
  - Establish regression test baseline (`Ran 38 tests in 3.918s OK`).
- **Phase 1: Canonical Candidate Profile & Evidence Store**
  - Define structured schema: `Identity`, `Experience`, `Projects`, `Skills`, `Domains`, and `Evidence` (Problem, Context, Action, Result, Tech, Verified Fact vs AI Interpretation).
  - SQLite table `candidate_profiles` + migration from existing `profiles.json`.
  - Strict validator ensuring no fabricated experience is permitted.
- **Phase 2: Job Understanding Engine**
  - Structured extraction: explicit requirements, implicit requirements, seniority, engineering culture signals, team risks, and unknowns.
  - Distinguish verifiable Facts from Hypotheses.
- **Phase 3: Semantic Evidence Retrieval Layer**
  - Map `Job Problem ↔ Candidate Evidence ↔ Proven Experience ↔ Narrative Story`.
  - Move beyond keyword intersection (`React = React`) to contextual capability matching.
- **Phase 4: Application Thesis Generator**
  - Formulate the core strategic argument: *"Why this specific candidate is the ideal hire for this specific team's challenges."*
  - Output candidate theses, alternative theses, risks, and confidence scores.
- **Phase 5: Thesis Critic & Hallucination Gate**
  - Dedicated AI Critic evaluating thesis uniqueness, evidence sufficiency, and generic cliche avoidance.
  - Reject weak or unsupported theses before any writing begins.

### Milestone II: Contextual Research & Strategy (Phases 6–7)
- **Phase 6: Bounded Company Research Engine**
  - Safe, rate-limited enrichment of company context (homepage, public tech stack, engineering signals).
  - Strict separation of public facts from inferred business challenges.
- **Phase 7: Application Strategy Layer**
  - Synthesize Job Understanding + Company Research + Validated Thesis.
  - Decide narrative tone, emphasis order, skills hierarchy, and which facts to deliberately omit.

### Milestone III: Precision Artifact Generation & Quality Control (Phases 8–11)
- **Phase 8: Tailored Resume Engine (Profile View)**
  - Dynamic generation of tailored CV views from the canonical profile without mutating master profile data.
  - Versioned storage linked to vacancy ID (`base`, `tailored_for_job_X`).
- **Phase 9: ATS Analysis Engine**
  - Measure terminology coverage, parseability, and section structure without unethical keyword stuffing.
- **Phase 10: Evidence-Driven Cover Letter & Pitch Engine**
  - Multi-stage writer: Draft → Critic → Fact-Check → Final Polish.
  - Zero AI tropes, authentic human tone, direct peer-to-peer engineering voice.
- **Phase 11: Multi-Agent Specialized Roles**
  - Decouple prompt/reasoning pipelines into explicit roles: Job Analyst, Company Researcher, Candidate Researcher, Application Strategist, Resume Strategist, Writer, Critic, and Fact Checker.

### Milestone IV: Agent Runtime & Browser Infrastructure (Phases 12–16)
- **Phase 12: Agent Runtime & Finite State Machine**
  - Implement agent loop with explicit states: `DISCOVERED`, `ANALYZING`, `RESEARCHING`, `MATCHED`, `STRATEGY_READY`, `CV_READY`, `LETTER_READY`, `FORM_INSPECTED`, `WAITING_APPROVAL`, `SUBMITTED`.
  - Timeouts, max iterations, error recovery, and failure bounds.
- **Phase 13: Strict Tool System**
  - Formal tool execution interfaces with validated schemas (no arbitrary code execution).
- **Phase 14: Browser Extension (Side Panel & Content Bridge)**
  - Manifest V3 Chrome Extension providing a semantic DOM representation while preserving backward compatibility with the Bookmarklet.
- **Phase 15: Platform Adapters (HH.ru, LinkedIn, Greenhouse, Lever)**
  - Modular `JobPlatformAdapter` interface: `detect()`, `extract_job()`, `inspect_form()`, `fill_fields()`, `validate()`.
- **Phase 16: Human-in-the-Loop & Execution Guardrails**
  - Three operation modes: `ASSIST` (drafts only), `SEMI_AUTO` (pre-fill, await 1-click user review), `AUTO` (rules-restricted).

### Milestone V: Observability, Enterprise CRM & End-to-End Delivery (Phases 17–20)
- **Phase 17: Application CRM History**
  - Persist complete audit trail: company, URL, thesis, CV version, letter, answers, agent actions, approvals.
- **Phase 18: Observability & Agent Run Logs**
  - Step-by-step visual timeline in UI showing the reasoning progression of each run.
- **Phase 19: Automated Quality Control Pipeline**
  - Automated test suite validating fact checks, evidence integrity, and hallucination absence before user presentation.
- **Phase 20: End-to-End MVP Verification**
  - Complete live drill: Open vacancy → Extension detects → Agent reasons & produces tailored assets → Form pre-filled → User approves → Submission recorded.

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
