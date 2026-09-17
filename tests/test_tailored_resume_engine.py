import unittest
import json
from generator.candidate_profile import get_canonical_profile
from generator.job_understanding import heuristic_job_understanding
from generator.company_researcher import heuristic_company_dossier
from generator.thesis_generator import heuristic_application_thesis
from generator.evidence_retriever import heuristic_evidence_retrieval
from generator.application_strategy import heuristic_application_strategy
from generator.tailored_resume_engine import (
    validate_tailored_resume,
    apply_deliberate_omissions,
    heuristic_tailored_resume,
    generate_tailored_resume,
    render_tailored_resume_markdown
)
from tracker.db import init_db, save_vacancy, save_pitch, get_pending_pitches

class TestTailoredResumeEngine(unittest.TestCase):
    def setUp(self):
        init_db()
        self.profile_ru = get_canonical_profile(lang="ru")
        self.profile_en = get_canonical_profile(lang="en")

    def test_validate_valid_tailored_resume(self):
        valid = {
            "candidate_identity": {
                "name": "Егор Мышинский",
                "target_title": "Senior Frontend Developer",
                "contacts": "Telegram: @PotatoChipasu | Email: egormyshinsky@gmail.com"
            },
            "professional_summary": "Senior Product Engineer specializing in React 19, Next.js 16, and high-performance applications.",
            "highlighted_skills": ["React 19", "Next.js 16", "TypeScript", "FastAPI", "Docker"],
            "relevant_experience": [
                {
                    "role": "Lead Frontend Engineer",
                    "company": "TechCorp",
                    "period": "2023 — настоящее время",
                    "accomplishments": [
                        "Architected core client application",
                        "Boosted Core Web Vitals to 100/100"
                    ]
                }
            ],
            "education": [{"degree": "Higher Technical Education", "institution": "BMSTU", "years": "2016 — 2020"}],
            "deliberate_omissions_applied": ["Excluded founder references"],
            "defensibility_anchors": ["Core Web Vitals 100/100 benchmarks"]
        }
        is_valid, errors = validate_tailored_resume(valid)
        self.assertTrue(is_valid, f"Validation failed: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_missing_fields(self):
        broken = {
            "candidate_identity": {"name": "Егор"},
            "professional_summary": "Too short",
            "highlighted_skills": []
        }
        is_valid, errors = validate_tailored_resume(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("candidate_identity" in e or "professional_summary" in e or "highlighted_skills" in e for e in errors))

    def test_apply_deliberate_omissions_cleans_founder_terms(self):
        dirty = "Я основатель и фаундер стартапа NoLogs. Мой стартап развивался успешно."
        cleaned = apply_deliberate_omissions(dirty, ["Exclude founder"])
        self.assertNotIn("фаундер", cleaned.lower())
        self.assertNotIn("основатель", cleaned.lower())
        self.assertNotIn("мой стартап", cleaned.lower())
        self.assertIn("Ведущий инженер", cleaned)

    def test_heuristic_tailored_resume_prioritizes_stack_and_omits_founder(self):
        ju = heuristic_job_understanding("Senior Frontend Developer", "React, Next.js, Core Web Vitals", "FinTechGlobal")
        cd = heuristic_company_dossier("FinTechGlobal", "fintechglobal.com", "Financial services")
        re = heuristic_evidence_retrieval(self.profile_ru, ju, lang="ru")
        thesis = heuristic_application_thesis(self.profile_ru, ju, re, lang="ru")
        strategy = heuristic_application_strategy(self.profile_ru, ju, cd, thesis, lang="ru")

        tailored = heuristic_tailored_resume(self.profile_ru, ju, strategy, lang="ru")
        is_valid, errors = validate_tailored_resume(tailored)
        self.assertTrue(is_valid, f"Heuristic tailored resume invalid: {errors}")

        # Check target title alignment
        self.assertIn("Senior Frontend Developer", tailored["candidate_identity"]["target_title"])

        # Check skills priority
        skills = tailored["highlighted_skills"]
        self.assertTrue(any("react" in s.lower() or "next.js" in s.lower() for s in skills[:3]))

        # Render markdown check
        md = render_tailored_resume_markdown(tailored, lang="ru")
        self.assertIn("# ЕГОР МЫШИНСКИЙ", md)
        self.assertIn("## Профессиональное саммари", md)
        self.assertIn("## Профессиональный опыт", md)
        self.assertNotIn("фаундер", md.lower())
        self.assertNotIn("основатель", md.lower())

    def test_tailored_resume_english_variant(self):
        ju = heuristic_job_understanding("Lead Product Engineer", "Next.js, TypeScript, Docker", "GlobalScale")
        cd = heuristic_company_dossier("GlobalScale", "globalscale.com", "SaaS scaleup")
        re = heuristic_evidence_retrieval(self.profile_en, ju, lang="en")
        thesis = heuristic_application_thesis(self.profile_en, ju, re, lang="en")
        strategy = heuristic_application_strategy(self.profile_en, ju, cd, thesis, lang="en")

        tailored = heuristic_tailored_resume(self.profile_en, ju, strategy, lang="en")
        is_valid, errors = validate_tailored_resume(tailored)
        self.assertTrue(is_valid, f"English tailored resume invalid: {errors}")

        md = render_tailored_resume_markdown(tailored, lang="en")
        self.assertIn("## Professional Summary", md)
        self.assertIn("## Professional Experience", md)
        self.assertIn("**Core Stack:**", md)

    def test_database_persistence_of_tailored_cv(self):
        vac = {
            "id": "test_cv_tailor_01",
            "title": "Senior Frontend Developer",
            "company": "ScaleTech",
            "url": "https://scaletech.example.com/jobs/1",
            "source": "test",
            "description": "Next.js performance optimization"
        }
        save_vacancy(vac)
        try:
            sample_cv_content = "# EGOR MYSHINSKY\nTarget: Senior Frontend Developer"
            pitch_id = save_pitch(vac["id"], "tailored_cv", "en", sample_cv_content)
            self.assertGreater(pitch_id, 0)

            from tracker.db import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT content FROM pitches WHERE id = ?", (pitch_id,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["content"], sample_cv_content)
            conn.close()
        finally:
            from tracker.db import get_db_connection
            conn = get_db_connection()
            conn.execute("DELETE FROM pitches WHERE vacancy_id = ?", (vac["id"],))
            conn.execute("DELETE FROM vacancies WHERE id = ?", (vac["id"],))
            conn.commit()
            conn.close()

if __name__ == "__main__":
    unittest.main()
