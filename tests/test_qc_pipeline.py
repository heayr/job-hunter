import unittest
import os
import json
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.tailored_resume_engine import heuristic_tailored_resume
from generator.ats_analyzer import analyze_resume_for_ats
from generator.cover_letter_engine import fact_check_cover_letter
from agents.multi_agent_roles import CareerOrchestrator

class TestQualityControlPipeline(unittest.TestCase):
    """
    Automated Quality Control Pipeline (Phase 19):
    Validates fact checks, evidence integrity, and hallucination absence
    before any artifact is presented to the user.
    """

    def setUp(self):
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_qc_zero_unverified_claims_in_russian_evidence(self):
        evidence_list = self.profile_ru.get("evidence", [])
        self.assertGreaterEqual(len(evidence_list), 2)
        for ev in evidence_list:
            self.assertTrue(ev.get("verified", False), f"Evidence {ev.get('id')} must be verified")
            self.assertNotIn("Kafka", ev.get("action", ""))
            self.assertNotIn("Solidity", ev.get("action", ""))

    def test_qc_hallucination_gate_rejects_foreign_technologies(self):
        # Highload distributed backend hallucination simulation
        fake_letter = (
            "Управлял кластером Kafka и настраивал kafka cluster и solidity smart contract "
            "для обработки 100 000 RPS на бэкенде."
        )
        passed, warnings = fact_check_cover_letter(fake_letter, self.profile_ru)
        self.assertFalse(passed)
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("kafka cluster" in w for w in warnings))

    def test_qc_clean_pass_for_authentic_engineering_claims(self):
        valid_letter = (
            "Оптимизировал скорость загрузки на React 19 и Next.js 16 до 100/100 Core Web Vitals, "
            "разрабатывал архитектуру дизайн-системы и проектировал API контракты на FastAPI."
        )
        passed, warnings = fact_check_cover_letter(valid_letter, self.profile_ru)
        self.assertTrue(passed)
        self.assertEqual(len(warnings), 0)

    def test_qc_end_to_end_orchestrator_pipeline_invariant(self):
        orchestrator = CareerOrchestrator()
        result = orchestrator.process_application({
            "title": "Senior Frontend Developer",
            "company": "ScaleFintech",
            "description": "React 19, TypeScript, Core Web Vitals, Design System.",
            "url": "https://example.com/job/qc1",
            "lang": "ru",
            "use_ai": False
        })

        # Pipeline must satisfy all quality gates
        self.assertTrue(result.get("fact_check_passed"), "Final artifact must pass QC fact check")
        self.assertIn("ats_report", result)
        self.assertGreater(result["ats_report"]["ats_score"], 50)
        self.assertIn("execution_trace", result)
        self.assertEqual(len(result["execution_trace"]), 6)

if __name__ == "__main__":
    unittest.main()
