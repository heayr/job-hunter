import unittest
import json
from generator.job_understanding import (
    validate_job_understanding,
    heuristic_job_understanding,
    understand_job_posting
)
from tracker.db import init_db, get_db_connection, save_vacancy, save_job_understanding, get_job_understanding

class TestJobUnderstanding(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_validate_valid_job_understanding(self):
        sample = {
            "role_overview": {
                "title": "Lead Frontend Engineer",
                "company": "Fintech Global",
                "seniority": "Lead",
                "domain": "Fintech / Payments",
                "work_format": "Remote"
            },
            "facts": {
                "explicit_requirements": ["React 19", "TypeScript", "Next.js", "Docker"],
                "responsibilities": ["Lead frontend architecture", "Code review"],
                "stated_constraints": ["B2B contract"]
            },
            "reasoning": {
                "implicit_requirements": ["Autonomy without micromanagement"],
                "engineering_signals": ["Mentions legacy migration"],
                "likely_team_problems": ["Slowing sprint velocity due to state fragmentation"],
                "hiring_priorities": ["Experience in zero-downtime refactoring"],
                "risks": ["High initial on-call load"],
                "unknowns": ["Team size"]
            },
            "boilerplate_vs_signal": {
                "boilerplate": ["Friendly team", "Competitive compensation"],
                "high_signal": ["React 19", "Next.js 16"]
            }
        }
        is_valid, errors = validate_job_understanding(sample)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_missing_facts_or_reasoning(self):
        broken = {
            "role_overview": {"title": "Engineer"},
            "facts": {"explicit_requirements": ["React"]}
            # Missing responsibilities, reasoning, boilerplate
        }
        is_valid, errors = validate_job_understanding(broken)
        self.assertFalse(is_valid)
        self.assertTrue(any("reasoning" in err for err in errors))

    def test_heuristic_fallback_separates_facts_and_hypotheses(self):
        text = """
        Ищем Senior Frontend Developer в команду платежей.
        Стек: React, TypeScript, Next.js, Tailwind CSS, Docker.
        Мы занимаемся миграцией старого монолита и рефакторингом легаси на современный стек.
        Обязанности: проектирование компонентов, оптимизация производительности Core Web Vitals.
        Только ИП или самозанятость.
        """
        res = heuristic_job_understanding("Senior Frontend Developer", text, "PayTech")
        is_valid, errors = validate_job_understanding(res)
        self.assertTrue(is_valid, f"Heuristic output invalid: {errors}")

        # Check facts
        facts = res["facts"]
        self.assertIn("React", facts["explicit_requirements"])
        self.assertIn("TypeScript", facts["explicit_requirements"])
        self.assertTrue(any("ип" in c.lower() or "самозанятость" in c.lower() for c in facts["stated_constraints"]))

        # Check reasoning hypotheses
        reasoning = res["reasoning"]
        self.assertTrue(any("legacy" in s.lower() or "миграц" in s.lower() or "рефакторинг" in s.lower() for s in reasoning["engineering_signals"]))
        self.assertTrue(any("модернизирова" in p.lower() or "legacy" in p.lower() or "производительн" in p.lower() for p in reasoning["likely_team_problems"]))

    def test_db_persistence_of_job_understanding(self):
        vac = {
            "id": "test_understanding_vac_01",
            "title": "Lead Engineer",
            "company": "TestCorp",
            "source": "manual",
            "url": "https://example.com/job/1"
        }
        try:
            save_vacancy(vac)
            sample_understanding = heuristic_job_understanding(vac["title"], "React, Next.js, Docker", vac["company"])
            save_job_understanding(vac["id"], sample_understanding)

            loaded = get_job_understanding(vac["id"])
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["role_overview"]["title"], "Lead Engineer")
            self.assertIn("React", loaded["facts"]["explicit_requirements"])
        finally:
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM vacancies WHERE id = ?", (vac["id"],))
            conn.commit()
            conn.close()

if __name__ == "__main__":
    unittest.main()
