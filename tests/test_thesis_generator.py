import unittest
import json
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.thesis_generator import (
    validate_application_thesis,
    heuristic_application_thesis,
    generate_application_thesis
)
from tracker.db import (
    init_db, get_db_connection, save_vacancy,
    save_application_thesis, get_application_thesis
)

class TestThesisGenerator(unittest.TestCase):
    def setUp(self):
        init_db()
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_validate_valid_thesis(self):
        sample = {
            "thesis": "Кандидат обладает подтвержденным опытом оптимизации Core Web Vitals до 100/100 на Next.js 16, что решает проблему конверсии.",
            "strategic_rationale": "Удар в техническую боль компании с доказанной метрикой.",
            "supporting_evidence": ["ev_01: Next.js 16 App Router streaming"],
            "alternative_theses": ["Позиционирование через Fullstack-автономию"],
            "potential_risks": ["Необходимость онбординга в легаси"],
            "confidence": 0.92
        }
        is_valid, errors = validate_application_thesis(sample)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_missing_or_short_thesis(self):
        broken = {
            "thesis": "Short",
            "strategic_rationale": "ok",
            "supporting_evidence": [],
            "alternative_theses": [],
            "potential_risks": [],
            "confidence": 0.5
        }
        is_valid, errors = validate_application_thesis(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("thesis" in err for err in errors))
        self.assertTrue(any("supporting_evidence" in err for err in errors))

    def test_heuristic_thesis_generation(self):
        job_understanding = heuristic_job_understanding(
            "Senior Frontend Developer",
            "Ищем Senior инженера для миграции легаси на React 19 и Next.js 16. Важна оптимизация скорости.",
            "PayTech"
        )
        reframed_evidence = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
        res = heuristic_application_thesis(self.profile_ru, job_understanding, reframed_evidence, lang="ru")

        is_valid, errors = validate_application_thesis(res)
        self.assertTrue(is_valid, f"Heuristic thesis invalid: {errors}")

        self.assertIn("PayTech", res["thesis"])
        self.assertGreaterEqual(len(res["alternative_theses"]), 2)
        self.assertGreaterEqual(len(res["supporting_evidence"]), 1)
        self.assertGreaterEqual(res["confidence"], 0.7)

    def test_db_persistence_of_application_thesis(self):
        vac = {
            "id": "test_thesis_vac_01",
            "title": "Lead Product Engineer",
            "company": "ThesisCorp",
            "source": "manual",
            "url": "https://example.com/job/thesis"
        }
        try:
            save_vacancy(vac)
            job_understanding = heuristic_job_understanding(vac["title"], "React, FastAPI, Docker", vac["company"])
            reframed_evidence = heuristic_evidence_retrieval(self.profile_ru, job_understanding, lang="ru")
            thesis = heuristic_application_thesis(self.profile_ru, job_understanding, reframed_evidence, lang="ru")

            save_application_thesis(vac["id"], thesis)

            loaded = get_application_thesis(vac["id"])
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["confidence"], thesis["confidence"])
            self.assertIn("ThesisCorp", loaded["thesis"])
        finally:
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM vacancies WHERE id = ?", (vac["id"],))
            conn.commit()
            conn.close()

if __name__ == "__main__":
    unittest.main()
