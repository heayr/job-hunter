import unittest
from generator.candidate_profile import load_canonical_profiles, get_canonical_profile
from generator.evidence_retriever import (
    retrieve_and_reframe_evidence,
    heuristic_evidence_retrieval
)

class TestEvidenceRetriever(unittest.TestCase):
    def setUp(self):
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_reframe_performance_pain(self):
        job_understanding = {
            "role_overview": {"title": "Senior Frontend Engineer", "company": "SpeedCorp"},
            "facts": {"explicit_requirements": ["React", "Next.js", "Performance"]},
            "reasoning": {
                "likely_team_problems": ["Slow page loading times and low Core Web Vitals score", "Large JS bundle"]
            }
        }
        res = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
        self.assertIn("matched_evidence", res)
        self.assertIn("strategic_narrative", res)

        bullets = [m["aggressive_framing"] for m in res["matched_evidence"]]
        self.assertTrue(any("PageSpeed" in b or "100/100" in b or "производительн" in b for b in bullets))
        self.assertTrue(any("Lead" in m["seniority_signal"] or "Architect" in m["seniority_signal"] for m in res["matched_evidence"]))

    def test_reframe_design_system_pain(self):
        job_understanding = {
            "role_overview": {"title": "UI Engineer", "company": "DesignCo"},
            "facts": {"explicit_requirements": ["TypeScript", "Tailwind CSS", "Figma"]},
            "reasoning": {
                "likely_team_problems": ["Missing consistent UI kit and design tokens across squads"]
            }
        }
        res = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
        bullets = [m["aggressive_framing"] for m in res["matched_evidence"]]
        self.assertTrue(any("дизайн-систем" in b.lower() or "компонент" in b.lower() for b in bullets))

    def test_reframe_fullstack_ownership_pain(self):
        job_understanding = {
            "role_overview": {"title": "Product Fullstack Developer", "company": "SaaS Factory"},
            "facts": {"explicit_requirements": ["React", "FastAPI", "Docker", "PostgreSQL"]},
            "reasoning": {
                "likely_team_problems": ["Frontend developers blocked by slow backend API deliveries"]
            }
        }
        res = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
        bullets = [m["aggressive_framing"] for m in res["matched_evidence"]]
        self.assertTrue(any("FastAPI" in b or "Docker" in b or "End-to-End" in b for b in bullets))

    def test_reframe_english_version(self):
        job_understanding = {
            "role_overview": {"title": "Senior Frontend Developer", "company": "Global Inc"},
            "facts": {"explicit_requirements": ["React 19", "Next.js", "TypeScript"]},
            "reasoning": {
                "likely_team_problems": ["Need autonomous engineer to ship high-speed MVPs"]
            }
        }
        res = heuristic_evidence_retrieval(self.profile_en, job_understanding, lang="en")
        narrative = res["strategic_narrative"]
        self.assertIn("End-to-End Ownership", narrative["positioning_angle"])
        self.assertGreaterEqual(len(narrative["leverage_points"]), 2)

if __name__ == "__main__":
    unittest.main()
