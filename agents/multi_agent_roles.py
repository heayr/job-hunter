import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from generator.job_understanding import understand_job_posting, heuristic_job_understanding
from generator.company_researcher import research_company_context, heuristic_company_dossier
from generator.candidate_profile import get_canonical_profile
from generator.evidence_retriever import retrieve_and_reframe_evidence, heuristic_evidence_retrieval
from generator.thesis_generator import generate_application_thesis, heuristic_application_thesis
from generator.thesis_critic import evaluate_and_refine_thesis, detect_generic_fluff
from generator.application_strategy import plan_application_strategy, heuristic_application_strategy
from generator.tailored_resume_engine import generate_tailored_resume, render_tailored_resume_markdown
from generator.ats_analyzer import analyze_resume_for_ats
from generator.cover_letter_engine import generate_cover_letter, fact_check_cover_letter, critic_refine_letter


class AgentRole:
    """Abstract base for specialized Career Agents."""
    name: str = "BaseAgent"
    system_role: str = "Generic Assistant"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class JobAnalystAgent(AgentRole):
    """Specialized in analyzing job requirements and separating facts from inferences."""
    name = "JobAnalyst"
    system_role = "Senior Technical Recruiter & Requirement Architect"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        title = context.get("title", "")
        description = context.get("description", "")
        company = context.get("company", "Company")
        source_url = context.get("url", "")
        use_ai = context.get("use_ai", False)

        if use_ai:
            result = understand_job_posting(title, description, company, source_url)
        else:
            result = heuristic_job_understanding(title, description, company)

        return {"job_understanding": result}


class CompanyResearcherAgent(AgentRole):
    """Specialized in gathering bounded company context, business model, and tech stack."""
    name = "CompanyResearcher"
    system_role = "Corporate Intelligence & Market Analyst"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        company = context.get("company", "")
        url = context.get("url", "")
        desc = context.get("description", "")
        use_ai = context.get("use_ai", False)

        if use_ai:
            result = research_company_context(company, vacancy_url=url, description=desc)
        else:
            result = heuristic_company_dossier(company, "", desc)

        return {"company_dossier": result}


class CandidateStrategistAgent(AgentRole):
    """Specialized in matching candidate evidence to job pains and formulating strategy."""
    name = "CandidateStrategist"
    system_role = "Principal Career Strategist & Tech Lead Advocate"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = context.get("profile") or get_canonical_profile(profile_id=context.get("profile_id"), lang=context.get("lang", "ru"))
        job_understanding = context.get("job_understanding", {})
        company_dossier = context.get("company_dossier", {})
        lang = context.get("lang", "ru")
        use_ai = context.get("use_ai", False)

        # 1. Retrieve & reframe evidence
        if use_ai:
            reframed = retrieve_and_reframe_evidence(profile, job_understanding, lang=lang)
            thesis = evaluate_and_refine_thesis(profile, job_understanding, reframed, lang=lang)
            strategy = plan_application_strategy(profile, job_understanding, company_dossier, thesis, lang=lang)
        else:
            reframed = heuristic_evidence_retrieval(profile, job_understanding, lang=lang)
            thesis = evaluate_and_refine_thesis(profile, job_understanding, reframed, lang=lang, use_ai=False)
            strategy = heuristic_application_strategy(profile, job_understanding, company_dossier, thesis, lang=lang)

        return {
            "evidence_reframed": reframed,
            "application_thesis": thesis,
            "application_strategy": strategy
        }


class WriterAgent(AgentRole):
    """Specialized in generating high-impact tailored resumes, cover letters, and short DMs."""
    name = "Writer"
    system_role = "Elite Technical Ghostwriter"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = context.get("profile") or get_canonical_profile(profile_id=context.get("profile_id"), lang=context.get("lang", "ru"))
        job_understanding = context.get("job_understanding", {})
        strategy = context.get("application_strategy", {})
        thesis = context.get("application_thesis", {})
        lang = context.get("lang", "ru")
        use_ai = context.get("use_ai", False)

        tailored_resume = generate_tailored_resume(profile, job_understanding, strategy, lang=lang, use_ai=use_ai)
        resume_markdown = render_tailored_resume_markdown(tailored_resume, lang=lang)

        cover_pkg = generate_cover_letter(profile, job_understanding, strategy, thesis, lang=lang, use_ai=use_ai)

        return {
            "tailored_resume": tailored_resume,
            "resume_markdown": resume_markdown,
            "cover_letter": cover_pkg.get("cover_letter", ""),
            "short_dm": cover_pkg.get("short_dm", "")
        }


class CriticAgent(AgentRole):
    """Specialized in adversarially reviewing artifacts for fluff, tone, and ATS compliance."""
    name = "Critic"
    system_role = "Adversarial Technical Reviewer & ATS Auditor"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tailored_resume = context.get("tailored_resume", {})
        job_understanding = context.get("job_understanding", {})
        cover_letter = context.get("cover_letter", "")
        strategy = context.get("application_strategy", {})
        lang = context.get("lang", "ru")

        # 1. ATS Audit
        ats_report = analyze_resume_for_ats(tailored_resume, job_understanding, lang=lang, use_ai=False)

        # 2. Cliché & Subservience Review
        fluff = detect_generic_fluff(cover_letter)
        refined_cl, notes = critic_refine_letter(cover_letter, strategy, lang=lang)

        return {
            "ats_report": ats_report,
            "critic_refined_cover_letter": refined_cl,
            "fluff_detected": fluff,
            "critique_notes": notes
        }


class FactCheckerAgent(AgentRole):
    """Specialized in verifying claims against canonical profile to guarantee zero hallucinations."""
    name = "FactChecker"
    system_role = "Truth Verification Officer"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = context.get("profile") or get_canonical_profile(profile_id=context.get("profile_id"), lang=context.get("lang", "ru"))
        cover_letter = context.get("critic_refined_cover_letter") or context.get("cover_letter", "")
        
        ok, warnings = fact_check_cover_letter(cover_letter, profile)

        return {
            "fact_check_passed": ok,
            "hallucination_warnings": warnings
        }


class CareerOrchestrator:
    """
    Coordinates the multi-agent cognitive workflow across specialized roles:
    JobAnalyst -> CompanyResearcher -> CandidateStrategist -> Writer -> Critic -> FactChecker
    """
    def __init__(self):
        self.job_analyst = JobAnalystAgent()
        self.company_researcher = CompanyResearcherAgent()
        self.candidate_strategist = CandidateStrategistAgent()
        self.writer = WriterAgent()
        self.critic = CriticAgent()
        self.fact_checker = FactCheckerAgent()

    def process_application(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        trace = []
        context = dict(initial_context)

        # Ensure canonical profile is loaded
        profile_id = context.get("profile_id")
        lang = context.get("lang", "ru")
        profile = context.get("profile") or get_canonical_profile(profile_id=profile_id, lang=lang)
        context["profile"] = profile

        pipeline = [
            self.job_analyst,
            self.company_researcher,
            self.candidate_strategist,
            self.writer,
            self.critic,
            self.fact_checker
        ]

        for agent in pipeline:
            start_t = time.time()
            res = agent.execute(context)
            duration_ms = int((time.time() - start_t) * 1000)

            context.update(res)
            trace.append({
                "agent": agent.name,
                "role": agent.system_role,
                "duration_ms": duration_ms,
                "outputs": list(res.keys()),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        context["execution_trace"] = trace
        return context
