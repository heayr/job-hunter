import unittest
from agents.multi_agent_roles import (
    JobAnalystAgent,
    CompanyResearcherAgent,
    CandidateStrategistAgent,
    WriterAgent,
    CriticAgent,
    FactCheckerAgent,
    CareerOrchestrator
)
from generator.candidate_profile import get_canonical_profile

class TestMultiAgentRoles(unittest.TestCase):
    def setUp(self):
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_job_analyst_agent(self):
        agent = JobAnalystAgent()
        ctx = {
            "title": "Senior React Developer",
            "description": "Must know React 19, TypeScript, Docker. Optimize performance.",
            "company": "ScaleApp",
            "use_ai": False
        }
        res = agent.execute(ctx)
        self.assertIn("job_understanding", res)
        ju = res["job_understanding"]
        self.assertEqual(ju["role_overview"]["title"], "Senior React Developer")
        self.assertIn("explicit_requirements", ju["facts"])

    def test_company_researcher_agent(self):
        agent = CompanyResearcherAgent()
        ctx = {
            "company": "ScaleApp",
            "url": "https://scaleapp.com/jobs/1",
            "description": "Fintech payment processing",
            "use_ai": False
        }
        res = agent.execute(ctx)
        self.assertIn("company_dossier", res)
        dossier = res["company_dossier"]
        self.assertEqual(dossier["company_name"], "ScaleApp")

    def test_candidate_strategist_agent(self):
        agent = CandidateStrategistAgent()
        ju = {
            "role_overview": {"title": "Senior Frontend Developer", "company": "ScaleApp", "seniority": "Senior"},
            "facts": {"explicit_requirements": ["React 19", "TypeScript", "Next.js 16"]},
            "reasoning": {"likely_team_problems": ["Performance bottlenecks"]}
        }
        cd = {"company_name": "ScaleApp", "public_facts": {}, "engineering_signals": {}}
        ctx = {
            "profile": self.profile_ru,
            "job_understanding": ju,
            "company_dossier": cd,
            "lang": "ru",
            "use_ai": False
        }
        res = agent.execute(ctx)
        self.assertIn("evidence_reframed", res)
        self.assertIn("application_thesis", res)
        self.assertIn("application_strategy", res)
        # Verify deliberate omissions contain rule to exclude founder
        omissions = [o.lower() for o in res["application_strategy"]["deliberate_omissions"]]
        self.assertTrue(any("фаундер" in o or "основатель" in o for o in omissions))

    def test_writer_agent(self):
        agent = WriterAgent()
        ju = {
            "role_overview": {"title": "Senior Frontend Developer", "company": "ScaleApp", "seniority": "Senior"},
            "facts": {"explicit_requirements": ["React", "Next.js"]},
            "reasoning": {"likely_team_problems": []}
        }
        strategy = {
            "positioning_archetype": "Autonomous Senior Product Engineer",
            "deliberate_omissions": ["Exclude founder"],
            "highlight_priorities": ["Next.js 16 App Router streaming", "PageSpeed 100/100"]
        }
        thesis = {"thesis": "Next.js 16 architecture for ScaleApp"}
        ctx = {
            "profile": self.profile_ru,
            "job_understanding": ju,
            "application_strategy": strategy,
            "application_thesis": thesis,
            "lang": "ru",
            "use_ai": False
        }
        res = agent.execute(ctx)
        self.assertIn("tailored_resume", res)
        self.assertIn("resume_markdown", res)
        self.assertIn("cover_letter", res)
        self.assertIn("short_dm", res)
        self.assertIn("# ЕГОР МЫШИНСКИЙ", res["resume_markdown"])

    def test_critic_agent(self):
        agent = CriticAgent()
        tailored_resume = {
            "candidate_identity": {"name": "Егор", "target_title": "Senior Frontend", "contacts": "@PotatoChipasu"},
            "professional_summary": "Autonomous Senior Product Engineer specializing in React 19.",
            "highlighted_skills": ["React 19", "TypeScript", "Next.js 16"],
            "relevant_experience": [{"role": "Senior Engineer", "company": "TechCorp", "accomplishments": ["Built core client apps"]}],
            "education": [{"degree": "Technical", "institution": "BMSTU", "years": "2020"}]
        }
        ju = {
            "role_overview": {"title": "Senior Frontend Developer"},
            "facts": {"explicit_requirements": ["React 19", "TypeScript"]}
        }
        ctx = {
            "tailored_resume": tailored_resume,
            "job_understanding": ju,
            "cover_letter": "Здравствуйте! Меня зовут Егор, и я опытный специалист. Буду рад обсудить задачи!",
            "application_strategy": {"deliberate_omissions": []},
            "lang": "ru"
        }
        res = agent.execute(ctx)
        self.assertIn("ats_report", res)
        self.assertIn("critic_refined_cover_letter", res)
        # Cliché "опытный специалист" must be detected and removed
        self.assertNotIn("опытный специалист", res["critic_refined_cover_letter"].lower())

    def test_fact_checker_agent(self):
        agent = FactCheckerAgent()
        ctx_clean = {
            "profile": self.profile_ru,
            "critic_refined_cover_letter": "React 19 and Next.js 16 architecture."
        }
        res_clean = agent.execute(ctx_clean)
        self.assertTrue(res_clean["fact_check_passed"])

        ctx_dirty = {
            "profile": self.profile_ru,
            "critic_refined_cover_letter": "I built a distributed Kafka cluster with Solidity smart contracts."
        }
        res_dirty = agent.execute(ctx_dirty)
        self.assertFalse(res_dirty["fact_check_passed"])
        self.assertGreater(len(res_dirty["hallucination_warnings"]), 0)

    def test_career_orchestrator_full_cycle(self):
        orchestrator = CareerOrchestrator()
        initial_ctx = {
            "title": "Senior Frontend Engineer",
            "description": "Next.js 16, React 19, TypeScript, Core Web Vitals optimization.",
            "company": "FintechVelocity",
            "url": "https://fintechvelocity.example.com/jobs/1",
            "lang": "ru",
            "use_ai": False
        }
        result = orchestrator.process_application(initial_ctx)

        # Check that all stages contributed to context
        self.assertIn("job_understanding", result)
        self.assertIn("company_dossier", result)
        self.assertIn("application_thesis", result)
        self.assertIn("application_strategy", result)
        self.assertIn("tailored_resume", result)
        self.assertIn("resume_markdown", result)
        self.assertIn("cover_letter", result)
        self.assertIn("short_dm", result)
        self.assertIn("ats_report", result)
        self.assertIn("fact_check_passed", result)
        self.assertTrue(result["fact_check_passed"])

        # Check execution trace
        trace = result.get("execution_trace", [])
        self.assertEqual(len(trace), 6)
        agent_names = [step["agent"] for step in trace]
        self.assertEqual(agent_names, [
            "JobAnalyst",
            "CompanyResearcher",
            "CandidateStrategist",
            "Writer",
            "Critic",
            "FactChecker"
        ])

if __name__ == "__main__":
    unittest.main()
