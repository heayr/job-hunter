import unittest
from generator.company_researcher import (
    extract_company_domain,
    heuristic_company_dossier,
    research_company_context
)
from tracker.db import init_db, save_company_dossier, get_cached_company_dossier

class TestCompanyResearcher(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_extract_company_domain(self):
        # 1. From description with "Сайт: ..."
        desc1 = "Компания FinTech. Сайт: https://fintech-pay.io/about. Работаем над платежами."
        dom1 = extract_company_domain("FinTech", description=desc1)
        self.assertEqual(dom1, "fintech-pay.io")

        # 2. From company vacancy url (direct employer)
        v_url = "https://careers.stripe.com/jobs/123"
        dom2 = extract_company_domain("Stripe", vacancy_url=v_url)
        self.assertEqual(dom2, "careers.stripe.com")

        # 3. Ignoring aggregator job boards
        desc_hh = "Отклик на hh.ru/vacancy/123"
        dom3 = extract_company_domain("Acme Inc", description=desc_hh)
        self.assertEqual(dom3, "acmeinc.com")

    def test_heuristic_dossier_facts_vs_signals(self):
        desc = """
        Команда PayMaster разрабатывает глобальную систему платежей и биллинга.
        Стек: React, TypeScript, FastAPI, PostgreSQL, Docker.
        Высокие нагрузки, микросервисы, распределенная команда (Remote).
        """
        dossier = heuristic_company_dossier("PayMaster", "paymaster.com", desc)
        self.assertEqual(dossier["company_name"], "PayMaster")
        self.assertEqual(dossier["domain"], "paymaster.com")

        # Verify public facts
        self.assertIn("Fintech", dossier["public_facts"]["business_model"])
        self.assertIn("Remote", dossier["public_facts"]["headquarters_or_geo"])

        # Verify engineering signals
        eng = dossier["engineering_signals"]
        self.assertIn("React", eng["declared_tech_stack"])
        self.assertIn("FastAPI", eng["declared_tech_stack"])
        self.assertTrue(any("масштабируем" in c.lower() or "асинхрон" in c.lower() for c in eng["team_culture"]))

    def test_sqlite_dossier_caching_and_ttl(self):
        dossier = {
            "company_name": "CacheTestCorp",
            "domain": "cachetest.io",
            "public_facts": {"business_model": "SaaS"},
            "engineering_signals": {"declared_tech_stack": ["Python"]}
        }
        save_company_dossier("cachetest.io", "CacheTestCorp", dossier)

        # Retrieve within TTL
        cached = get_cached_company_dossier("cachetest.io", ttl_days=7)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["company_name"], "CacheTestCorp")
        self.assertEqual(cached["public_facts"]["business_model"], "SaaS")

        # Expired TTL check (0 days)
        expired = get_cached_company_dossier("cachetest.io", ttl_days=-1)
        self.assertIsNone(expired)

if __name__ == "__main__":
    unittest.main()
