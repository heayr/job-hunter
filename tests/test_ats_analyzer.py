import unittest
import json
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.company_researcher import heuristic_company_dossier
from generator.thesis_generator import heuristic_application_thesis
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.application_strategy import heuristic_application_strategy
from generator.tailored_resume_engine import heuristic_tailored_resume
from generator.ats_analyzer import (
    validate_ats_report,
    extract_target_terms,
    detect_keyword_stuffing,
    heuristic_ats_analysis,
    analyze_resume_for_ats
)
from tracker.db import init_db, save_vacancy, save_ats_report, get_ats_report

class TestATSAnalyzer(unittest.TestCase):
    def setUp(self):
        init_db()
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_validate_valid_ats_report(self):
        valid = {
            "ats_score": 88,
            "keyword_coverage": {
                "matched_keywords": ["React", "TypeScript", "Next.js"],
                "missing_keywords": ["GraphQL"],
                "coverage_percentage": 75
            },
            "structural_parseability": {
                "detected_sections": ["candidate_identity", "professional_summary", "highlighted_skills", "relevant_experience", "education"],
                "missing_sections": [],
                "is_standard_compliant": True
            },
            "readability_metrics": {
                "average_bullet_length": 140,
                "action_verb_ratio": 0.85,
                "wall_of_text_detected": False
            },
            "stuffing_flags": [],
            "recommendations": ["Optimize missing keywords"]
        }
        is_valid, errors = validate_ats_report(valid)
        self.assertTrue(is_valid, f"Validation failed: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_broken_report(self):
        broken = {
            "ats_score": "high",
            "keyword_coverage": {}
        }
        is_valid, errors = validate_ats_report(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("ats_score" in e or "keyword_coverage" in e for e in errors))

    def test_extract_target_terms_from_job(self):
        ju = heuristic_job_understanding("Senior React Developer", "React, TypeScript, Next.js, Docker", "Acme")
        terms = extract_target_terms(ju)
        self.assertIsInstance(terms, list)
        self.assertTrue(any("react" in t.lower() for t in terms))
        self.assertTrue(any("typescript" in t.lower() for t in terms))

    def test_detect_keyword_stuffing(self):
        # Normal text with normal repetition
        clean_text = "Experienced with React and TypeScript, building production Next.js apps."
        self.assertEqual(len(detect_keyword_stuffing(clean_text)), 0)

        # Spammed keyword text
        stuffed_text = "React React React React React React React React React developer with React"
        flags = detect_keyword_stuffing(stuffed_text)
        self.assertGreater(len(flags), 0)
        self.assertTrue(any("react" in f.lower() for f in flags))

    def test_heuristic_ats_analysis_coverage_and_score(self):
        ju = heuristic_job_understanding("Senior Frontend Developer", "React, Next.js, TypeScript", "FinTechGlobal")
        cd = heuristic_company_dossier("FinTechGlobal", "fintechglobal.com", "Financial services")
        re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")
        strategy = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru")
        tailored = heuristic_tailored_resume(self.profile_ru, ju, strategy, lang="ru")

        report = heuristic_ats_analysis(tailored, ju, lang="ru")
        is_valid, errors = validate_ats_report(report)
        self.assertTrue(is_valid, f"ATS report invalid: {errors}")

        # Tailored resume should have solid ATS match score >= 70
        self.assertGreaterEqual(report["ats_score"], 70)
        self.assertGreaterEqual(report["keyword_coverage"]["coverage_percentage"], 60)
        self.assertTrue(report["structural_parseability"]["is_standard_compliant"])

    def test_db_persistence_of_ats_report(self):
        vac = {
            "id": "test_ats_vac_01",
            "title": "Senior Frontend Developer",
            "company": "ATSTech",
            "url": "https://example.com/job/ats",
            "source": "test",
            "description": "Next.js and TypeScript"
        }
        save_vacancy(vac)
        try:
            report_data = {
                "ats_score": 92,
                "keyword_coverage": {
                    "matched_keywords": ["React", "TypeScript"],
                    "missing_keywords": [],
                    "coverage_percentage": 100
                },
                "structural_parseability": {
                    "detected_sections": ["candidate_identity", "professional_summary", "highlighted_skills", "relevant_experience", "education"],
                    "missing_sections": [],
                    "is_standard_compliant": True
                },
                "readability_metrics": {
                    "average_bullet_length": 120,
                    "action_verb_ratio": 0.9,
                    "wall_of_text_detected": False
                },
                "stuffing_flags": [],
                "recommendations": ["Excellent match"]
            }
            save_ats_report(vac["id"], report_data)
            loaded = get_ats_report(vac["id"])
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["ats_score"], 92)
            self.assertEqual(loaded["keyword_coverage"]["coverage_percentage"], 100)
        finally:
            from tracker.db import get_db_connection
            conn = get_db_connection()
            conn.execute("DELETE FROM vacancies WHERE id = ?", (vac["id"],))
            conn.commit()
            conn.close()

if __name__ == "__main__":
    unittest.main()
