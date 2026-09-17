import json
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field


class ToolPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    REASONING = "REASONING"
    WRITE_LOCAL = "WRITE_LOCAL"
    NETWORK_BOUND = "NETWORK_BOUND"
    BROWSER_ACTION = "BROWSER_ACTION"
    PRIVILEGED_SUBMIT = "PRIVILEGED_SUBMIT"


class ToolValidationError(Exception):
    pass


class ToolExecutionError(Exception):
    pass


@dataclass
class ToolDefinition:
    name: str
    description: str
    permission: ToolPermission
    parameters_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]

    def validate_args(self, arguments: Dict[str, Any]) -> None:
        """Validates arguments against parameters_schema."""
        if not isinstance(arguments, dict):
            raise ToolValidationError(f"Tool '{self.name}' arguments must be a dictionary")

        required = self.parameters_schema.get("required", [])
        for req_field in required:
            if req_field not in arguments or arguments[req_field] is None:
                raise ToolValidationError(f"Tool '{self.name}' missing required argument: '{req_field}'")

        props = self.parameters_schema.get("properties", {})
        for key, val in arguments.items():
            if key in props:
                expected_type = props[key].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    raise ToolValidationError(f"Argument '{key}' must be a string")
                elif expected_type == "integer" and not isinstance(val, int):
                    raise ToolValidationError(f"Argument '{key}' must be an integer")
                elif expected_type == "boolean" and not isinstance(val, bool):
                    raise ToolValidationError(f"Argument '{key}' must be a boolean")
                elif expected_type == "array" and not isinstance(val, list):
                    raise ToolValidationError(f"Argument '{key}' must be a list")
                elif expected_type == "object" and not isinstance(val, dict):
                    raise ToolValidationError(f"Argument '{key}' must be a dict")

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Safely executes tool handler with arguments validation and error containment."""
        try:
            self.validate_args(arguments)
            res = self.handler(arguments)
            return {"success": True, "result": res}
        except ToolValidationError as e:
            return {"success": False, "error_type": "VALIDATION_ERROR", "error": str(e)}
        except Exception as e:
            return {"success": False, "error_type": "EXECUTION_ERROR", "error": str(e)}


class ToolRegistry:
    """Singleton registry for declarative career agent tools."""
    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission": t.permission.value,
                "schema": t.parameters_schema
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def execute_tool(cls, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = cls.get(name)
        if not tool:
            return {"success": False, "error_type": "NOT_FOUND", "error": f"Tool '{name}' not registered"}
        return tool.execute(arguments)


# ── BUILT-IN CAREER AGENT TOOLS ───────────────────────────────────────────────

def _handle_understand_job(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.job_understanding import heuristic_job_understanding
    return heuristic_job_understanding(
        title=args["title"],
        description=args.get("description", ""),
        company=args.get("company", "Company")
    )

def _handle_research_company(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.company_researcher import heuristic_company_dossier
    return heuristic_company_dossier(
        company_name=args["company_name"],
        company_url=args.get("domain", ""),
        description=args.get("description", "")
    )

def _handle_reframe_evidence(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.evidence_retriever import heuristic_evidence_retrieval
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    job_understanding = args.get("job_understanding", {})
    return heuristic_evidence_retrieval(profile, job_understanding, lang=args.get("lang", "ru"))

def _handle_generate_tailored_resume(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.tailored_resume_engine import heuristic_tailored_resume, render_tailored_resume_markdown
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    ju = args.get("job_understanding", {})
    strat = args.get("strategy", {})
    lang = args.get("lang", "ru")
    res = heuristic_tailored_resume(profile, ju, strat, lang=lang)
    md = render_tailored_resume_markdown(res, lang=lang)
    return {"resume": res, "markdown": md}

def _handle_audit_ats(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.ats_analyzer import heuristic_ats_analysis
    return heuristic_ats_analysis(
        resume_dict=args["resume_dict"],
        job_understanding=args["job_understanding"],
        lang=args.get("lang", "ru")
    )

def _handle_verify_facts(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.cover_letter_engine import fact_check_cover_letter
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    ok, warnings = fact_check_cover_letter(args["text"], profile)
    return {"verified": ok, "warnings": warnings}


# Initialize and register core tools
ToolRegistry.register(ToolDefinition(
    name="understand_job",
    description="Extracts structured technical requirements and identifies team engineering bottlenecks",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "company": {"type": "string"}
        }
    },
    handler=_handle_understand_job
))

ToolRegistry.register(ToolDefinition(
    name="research_company",
    description="Gathers bounded corporate background, business model, and tech stack signals",
    permission=ToolPermission.READ_ONLY,
    parameters_schema={
        "type": "object",
        "required": ["company_name"],
        "properties": {
            "company_name": {"type": "string"},
            "domain": {"type": "string"},
            "description": {"type": "string"}
        }
    },
    handler=_handle_research_company
))

ToolRegistry.register(ToolDefinition(
    name="reframe_evidence",
    description="Matches candidate verified evidence to employer pain points with aggressive strategic framing",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["job_understanding"],
        "properties": {
            "job_understanding": {"type": "object"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_reframe_evidence
))

ToolRegistry.register(ToolDefinition(
    name="generate_tailored_resume",
    description="Generates an ATS-compliant tailored resume view based on candidate profile and strategy",
    permission=ToolPermission.WRITE_LOCAL,
    parameters_schema={
        "type": "object",
        "required": ["job_understanding", "strategy"],
        "properties": {
            "job_understanding": {"type": "object"},
            "strategy": {"type": "object"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_generate_tailored_resume
))

ToolRegistry.register(ToolDefinition(
    name="audit_ats",
    description="Calculates ATS keyword coverage, parseability, bullet density, and anti-stuffing checks",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["resume_dict", "job_understanding"],
        "properties": {
            "resume_dict": {"type": "object"},
            "job_understanding": {"type": "object"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_audit_ats
))

ToolRegistry.register(ToolDefinition(
    name="verify_facts",
    description="Checks that all technical claims in text are backed by canonical candidate evidence",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_verify_facts
))


# ── BROWSER TOOLS (Phase 1: Browser Hands) ───────────────────────────────────

def _handle_browser_open_page(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().open_page(args["url"])

def _handle_browser_inspect_page(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().inspect_page()

def _handle_browser_fill_field(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().fill_field(
        element_id=args["element_id"],
        value=args["value"],
        human_like=args.get("human_like", False)
    )

def _handle_browser_select_option(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().select_option(
        element_id=args["element_id"],
        option=args["option"]
    )

def _handle_browser_click_element(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().click_element(
        element_id=args["element_id"]
    )

def _handle_browser_upload_cv(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().upload_file(
        element_id=args["element_id"],
        file_base64=args["file_base64"],
        file_name=args.get("file_name", "resume.pdf"),
        mime_type=args.get("mime_type", "application/pdf")
    )

def _handle_browser_scroll(args: Dict[str, Any]) -> Dict[str, Any]:
    from agents.browser_bridge import get_browser_bridge
    return get_browser_bridge().scroll_page(
        direction=args.get("direction", "down"),
        pixels=args.get("pixels", 400)
    )


ToolRegistry.register(ToolDefinition(
    name="browser_open_page",
    description="Opens a URL in the user's active Chrome browser window",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string"}
        }
    },
    handler=_handle_browser_open_page
))

ToolRegistry.register(ToolDefinition(
    name="browser_inspect_page",
    description="Semantically inspects the active page forms, inputs, buttons, and validation errors",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "properties": {
            "mode": {"type": "string"}
        }
    },
    handler=_handle_browser_inspect_page
))

ToolRegistry.register(ToolDefinition(
    name="browser_fill_field",
    description="Fills a form field by its assigned element_id and observes whether errors were triggered",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "required": ["element_id", "value"],
        "properties": {
            "element_id": {"type": "string"},
            "value": {"type": "string"},
            "human_like": {"type": "boolean"}
        }
    },
    handler=_handle_browser_fill_field
))

ToolRegistry.register(ToolDefinition(
    name="browser_select_option",
    description="Selects an option in a dropdown <select> element by assigned element_id",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "required": ["element_id", "option"],
        "properties": {
            "element_id": {"type": "string"},
            "option": {"type": "string"}
        }
    },
    handler=_handle_browser_select_option
))

ToolRegistry.register(ToolDefinition(
    name="browser_click_element",
    description="Clicks a button, link, or interactive element by assigned element_id and observes changes",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "required": ["element_id"],
        "properties": {
            "element_id": {"type": "string"}
        }
    },
    handler=_handle_browser_click_element
))

ToolRegistry.register(ToolDefinition(
    name="browser_upload_cv",
    description="Uploads a resume file (base64 encoded) into an input[type=file] by assigned element_id",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "required": ["element_id", "file_base64"],
        "properties": {
            "element_id": {"type": "string"},
            "file_base64": {"type": "string"},
            "file_name": {"type": "string"},
            "mime_type": {"type": "string"}
        }
    },
    handler=_handle_browser_upload_cv
))

ToolRegistry.register(ToolDefinition(
    name="browser_scroll",
    description="Scrolls the active browser page view up or down",
    permission=ToolPermission.BROWSER_ACTION,
    parameters_schema={
        "type": "object",
        "properties": {
            "direction": {"type": "string"},
            "pixels": {"type": "integer"}
        }
    },
    handler=_handle_browser_scroll
))


# ── APPLICATION INTELLIGENCE TOOLS (Phase 3) ─────────────────────────────────

def _handle_candidate_classify_form(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.form_classifier import classify_form_elements
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    elements = args.get("elements", [])
    classified = classify_form_elements(elements, profile)
    return {"classified_elements": classified, "total": len(classified)}

def _handle_candidate_answer_question(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.question_answerer import answer_application_question
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    return answer_application_question(
        question=args["question"],
        profile=profile,
        job_understanding=args.get("job_understanding"),
        lang=args.get("lang", "en")
    )

def _handle_candidate_compile_resume(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.candidate_profile import get_canonical_profile
    from generator.tailored_resume_engine import compile_tailored_cv_artifact
    profile = get_canonical_profile(profile_id=args.get("profile_id"), lang=args.get("lang", "ru"))
    ju = args.get("job_understanding", {"role_overview": {"title": "Engineer", "company": "Company"}})
    strat = args.get("strategy", {})
    session_id = args.get("session_id")
    lang = args.get("lang", "ru")
    return compile_tailored_cv_artifact(profile, ju, strat, lang=lang, session_id=session_id)


ToolRegistry.register(ToolDefinition(
    name="candidate_classify_form",
    description="Semantically classifies inspected form fields, mapping each to a verified candidate value or action",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["elements"],
        "properties": {
            "elements": {"type": "array"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_candidate_classify_form
))

ToolRegistry.register(ToolDefinition(
    name="candidate_answer_question",
    description="Generates a truthful first-person answer to a screening question strictly grounded in Master Experience",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["question"],
        "properties": {
            "question": {"type": "string"},
            "job_understanding": {"type": "object"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_candidate_answer_question
))

ToolRegistry.register(ToolDefinition(
    name="candidate_compile_resume",
    description="Compiles an ATS tailored CV into a base64 file ready for upload, recording evidence provenance links",
    permission=ToolPermission.WRITE_LOCAL,
    parameters_schema={
        "type": "object",
        "properties": {
            "job_understanding": {"type": "object"},
            "strategy": {"type": "object"},
            "session_id": {"type": "string"},
            "profile_id": {"type": "string"},
            "lang": {"type": "string"}
        }
    },
    handler=_handle_candidate_compile_resume
))


# ── FORM VERIFICATION & PRIVILEGED SUBMIT TOOLS (Phases 4 & 5) ─────────────────

def _handle_candidate_verify_form(args: Dict[str, Any]) -> Dict[str, Any]:
    from generator.form_verifier import verify_application_form
    elements = args.get("elements", [])
    classified = args.get("classified_elements")
    return verify_application_form(elements, classified)


def _handle_browser_submit_application(args: Dict[str, Any]) -> Dict[str, Any]:
    from urllib.parse import urlparse
    from tracker.db import get_agent_session, update_agent_session, record_application_event, update_vacancy_status
    from agents.browser_bridge import get_browser_bridge
    from agents.event_bus import get_event_bus

    session_id = args.get("session_id")
    approval_token = args.get("approval_token")
    elem_id = args.get("element_id")

    session = get_agent_session(session_id)
    if not session:
        raise ToolExecutionError(f"Agent session '{session_id}' not found")

    # In Supervised mode, verify approval token
    if session.get("mode") == "SUPERVISED":
        if not approval_token or approval_token != session.get("approval_token"):
            raise ToolExecutionError("CRITICAL SECURITY VIOLATION: Missing or invalid human approval token. Submission rejected.")

    # Execute submit click in browser
    cmd_params = {}
    if elem_id:
        cmd_params["elem_id"] = elem_id
        cmd_params["selector"] = f"[data-jh-agent-id='{elem_id}']"
    else:
        cmd_params["selector"] = "button[type='submit'], input[type='submit'], button.submit-btn"

    bridge_res = get_browser_bridge().send_command("CLICK_ELEMENT", cmd_params, timeout=15.0)

    # Update session status
    update_agent_session(session_id, state="COMPLETED")

    # Record application in CRM
    vac_id = session.get("vacancy_id")
    target_url = session.get("target_url", "")
    portal = urlparse(target_url).netloc or "web"

    try:
        record_application_event(
            vacancy_id=vac_id or ("session_" + session_id[:8]),
            company="Applied via Agent",
            role_title="Applied Position",
            portal=portal,
            mode=session.get("mode", "SUPERVISED"),
            fsm_state="SUBMITTED",
            metadata={"session_id": session_id, "url": target_url}
        )
        if vac_id:
            update_vacancy_status(vac_id, "sent", reason="Autonomous agent application completed")
    except Exception as e:
        print(f"[SUBMIT_TOOL] CRM sync notice: {e}")

    get_event_bus().publish(session_id, "agent.completed", {
        "session_id": session_id,
        "target_url": target_url,
        "status": "COMPLETED"
    })

    return {
        "success": True,
        "submitted": True,
        "session_id": session_id,
        "browser_result": bridge_res
    }


ToolRegistry.register(ToolDefinition(
    name="candidate_verify_form",
    description="Automated verification engine checking completeness of required fields, formats, absence of errors, and CAPTCHA",
    permission=ToolPermission.REASONING,
    parameters_schema={
        "type": "object",
        "required": ["elements"],
        "properties": {
            "elements": {"type": "array"},
            "classified_elements": {"type": "array"}
        }
    },
    handler=_handle_candidate_verify_form
))

ToolRegistry.register(ToolDefinition(
    name="browser_submit_application",
    description="Privileged tool executing final form submission in browser. Strictly requires verified human approval token.",
    permission=ToolPermission.PRIVILEGED_SUBMIT,
    parameters_schema={
        "type": "object",
        "required": ["session_id", "approval_token"],
        "properties": {
            "session_id": {"type": "string"},
            "approval_token": {"type": "string"},
            "element_id": {"type": "string"}
        }
    },
    handler=_handle_browser_submit_application
))



