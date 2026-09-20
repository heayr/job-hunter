import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker.db import init_db
from generator.agent_policy import AgentPolicyConfig, evaluate_vacancy_policy


class TestAgentPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_compliant_remote_vacancy_passes(self):
        vac = {
            "title": "Senior Frontend Engineer",
            "company": "RemoteTech",
            "is_remote": True,
            "location": "Worldwide / Remote",
            "salary": "$5,500 - $7,000",
            "description": "We are seeking a senior React engineer for 100% remote work."
        }
        res = evaluate_vacancy_policy(vac, policy=AgentPolicyConfig(daily_application_limit=1000))
        self.assertTrue(res.can_apply)
        self.assertEqual(len(res.violations), 0)

    def test_strict_office_violation(self):
        vac = {
            "title": "Frontend Engineer",
            "company": "OfficeCorp",
            "is_remote": False,
            "location": "Moscow",
            "description": "Работа в офисе, strict on-site 5 дней в неделю."
        }
        res = evaluate_vacancy_policy(vac, policy=AgentPolicyConfig())
        self.assertFalse(res.can_apply)
        self.assertTrue(any("mandatory on-site" in v for v in res.violations))

    def test_salary_below_floor_violation(self):
        vac = {
            "title": "Frontend Developer",
            "company": "BudgetCorp",
            "is_remote": True,
            "salary": "$2000",
            "description": "Remote work worldwide."
        }
        res = evaluate_vacancy_policy(vac, policy=AgentPolicyConfig())
        self.assertFalse(res.can_apply)
        self.assertTrue(any("below policy floor" in v for v in res.violations))

    def test_forbidden_term_violation(self):
        vac = {
            "title": "Fullstack Developer",
            "company": "ScamCorp",
            "is_remote": True,
            "description": "Обязательно неоплачиваемое тестовое до собеседования на 40 часов."
        }
        res = evaluate_vacancy_policy(vac, policy=AgentPolicyConfig())
        self.assertFalse(res.can_apply)
        self.assertTrue(any("Forbidden" in v for v in res.violations))


if __name__ == '__main__':
    unittest.main()
