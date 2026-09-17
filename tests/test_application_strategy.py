import unittest
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.company_researcher import heuristic_company_dossier
from generator.thesis_generator import heuristic_application_thesis
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.application_strategy import (
    validate_application_strategy,
    heuristic_application_strategy,
    plan_application_strategy
)
from tracker.db import (
    init_db, get_db_connection, save_vacancy,
    save_application_strategy, get_application_strategy
)

class TestApplicationStrategy(unittest.TestCase):
    def setUp(self):
        init_db()
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_validate_valid_strategy(self):
        valid = {
            "positioning_archetype": "Autonomous Lead Product Engineer",
            "narrative_tone": "Peer-to-peer, crisp, pragmatic",
            "highlight_priorities": [
                "Next.js 16 App Router streaming",
                "Modular component architecture"
            ],
            "deliberate_omissions": [
                "Do not mention founder role",
                "Omit legacy WordPress"
            ],
            "tailored_artifacts_required": {
                "tailored_cv": True,
                "custom_cover_letter": True,
                "short_dm": True
            },
            "screening_questions_guidance": [
                "Anchor salary to seniority level"
            ],
            "strategic_thesis_refinement": "Modernize frontend without downtime"
        }
        is_valid, errors = validate_application_strategy(valid)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_missing_fields(self):
        broken = {
            "positioning_archetype": "Lead",
            "highlight_priorities": []
        }
        is_valid, errors = validate_application_strategy(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("deliberate_omissions" in e for e in errors))

    def test_heuristic_strategy_omissions_and_tone(self):
        ju = heuristic_job_understanding("Senior Frontend Developer", "React, Next.js, Docker", "FinTechGlobal")
        cd = heuristic_company_dossier("FinTechGlobal", "fintechglobal.com", "Financial services")
        re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")

        res = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru")
        is_valid, errors = validate_application_strategy(res)
        self.assertTrue(is_valid, f"Heuristic strategy invalid: {errors}")

        # Check deliberate omissions (Anti-founder & anti-unfocused rules)
        omissions = [o.lower() for o in res["deliberate_omissions"]]
        self.assertTrue(any("фаундер" in o or "основатель" in o for o in omissions))
        self.assertTrue(any("бэкенд" in o or "устаревш" in o for o in omissions))

        # Check required artifacts
        artifacts = res["tailored_artifacts_required"]
        self.assertTrue(artifacts["tailored_cv"])
        self.assertTrue(artifacts["custom_cover_letter"])

    def test_db_persistence_of_application_strategy(self):
        vac = {
            "id": "test_strategy_vac_01",
            "title": "Lead Engineer",
            "company": "StrategyCorp",
            "source": "manual",
            "url": "https://example.com/job/strategy"
        }
        try:
            save_vacancy(vac)
            ju = heuristic_job_understanding(vac["title"], "React 19, TypeScript", vac["company"])
            cd = heuristic_company_dossier(vac["company"], "strategycorp.com", "B2B SaaS")
            re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
            thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")

            strategy = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru")
            save_application_strategy(vac["id"], strategy)

            loaded = get_application_strategy(vac["id"])
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["positioning_archetype"], strategy["positioning_archetype"])
            self.assertEqual(len(loaded["deliberate_omissions"]), len(strategy["deliberate_omissions"]))
        finally:
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM vacancies WHERE id = ?", (vac["id"],))
            conn.commit()
            conn.close()

    def test_seniority_alignment_for_middle_and_junior(self):
        # 1. Middle vacancy with seniority_alignment=True should soften Lead archetype
        ju_middle = heuristic_job_understanding("Middle Frontend Developer", "React, TypeScript", "MidTech")
        cd = heuristic_company_dossier("MidTech", "midtech.example.com", "SaaS")
        re = heuristic_evidence_retrieval(self.profile_ru, ju_middle, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju_middle, re, lang="ru")

        strat_aligned = heuristic_application_strategy(self.profile_ru, ju_middle, cd, thesis, lang="ru", seniority_alignment=True)
        self.assertNotIn("Lead", strat_aligned["positioning_archetype"])
        self.assertIn("Middle", strat_aligned["positioning_archetype"])

        # 2. Middle vacancy with seniority_alignment=False keeps Lead archetype
        strat_unaligned = heuristic_application_strategy(self.profile_ru, ju_middle, cd, thesis, lang="ru", seniority_alignment=False)
        self.assertIn("Middle", strat_unaligned["positioning_archetype"])

    def test_highload_guardrail_toggle(self):
        ju = heuristic_job_understanding("Senior Frontend Developer", "React, Next.js", "ScaleUp")
        cd = heuristic_company_dossier("ScaleUp", "scaleup.com", "Fintech")
        re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")

        strat_guarded = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru", highload_guardrail=True)
        self.assertTrue(any("бэкенд-хайлоад" in o or "распределен" in o for o in strat_guarded["deliberate_omissions"]))

        strat_unguarded = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru", highload_guardrail=False)
        self.assertFalse(any("бэкенд-хайлоад" in o for o in strat_unguarded["deliberate_omissions"]))

if __name__ == "__main__":
    unittest.main()
