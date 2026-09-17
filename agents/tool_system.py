import json
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field


class ToolPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    REASONING = "REASONING"
    WRITE_LOCAL = "WRITE_LOCAL"
    NETWORK_BOUND = "NETWORK_BOUND"


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
