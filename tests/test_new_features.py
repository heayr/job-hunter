import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filter.profile_filter import detect_vacancy_grade, is_qualified_vacancy
from generator.pitch_builder import calculate_match_score, select_profile, generate_pitch
from scrapers.superjob_scraper import SuperJobScraper
from scrapers.rabotaru_scraper import RabotaRuScraper

class TestNewFeatures(unittest.TestCase):
    def test_detect_vacancy_grade(self):
        self.assertEqual(detect_vacancy_grade("Team Lead Frontend Developer"), "Lead")
        self.assertEqual(detect_vacancy_grade("Senior React Engineer"), "Senior")
        self.assertEqual(detect_vacancy_grade("Middle Frontend Developer"), "Middle")
        self.assertEqual(detect_vacancy_grade("Junior Web Developer"), "Junior")
        self.assertEqual(detect_vacancy_grade("Стажер-разработчик React"), "Intern")
        self.assertEqual(detect_vacancy_grade("Frontend Developer"), "Middle")

    def test_mixed_stack_tolerance_and_penalty(self):
        # 1. Qualified vacancy accepts fullstack even with php in company or mixed stack
        ok, reason = is_qualified_vacancy("Fullstack Developer (React/PHP)", "React, PHP, PostgreSQL", "Desc", "Web Agency")
        self.assertTrue(ok, f"Should accept fullstack: {reason}")

        # 2. Pure React vacancy gets high match score
        react_vac = {
            "title": "Senior Frontend Engineer (React/Next.js)",
            "company": "Tech Corp",
            "skills": "React, Next.js, TypeScript, Tailwind CSS",
            "description": "Looking for Senior React/Next.js engineer"
        }
        react_score = calculate_match_score(react_vac)

        # 3. Vacancy with foreign tech (e.g. PHP / Bitrix) receives score penalty
        mixed_vac = {
            "title": "Fullstack Engineer (React, PHP, Bitrix)",
            "company": "Agency",
            "skills": "React, PHP, Bitrix, MySQL",
            "description": "Develop client sites with Bitrix and React"
        }
        mixed_score = calculate_match_score(mixed_vac)

        self.assertGreater(react_score, mixed_score, "Mixed foreign tech should have lower score than pure stack")
        self.assertLessEqual(mixed_score, 65, "Mixed tech should be ranked lower to sort to the bottom")

    def test_active_profile_selection(self):
        # Test selecting profile by language and fallback
        p_ru = select_profile("ru")
        self.assertIn("lang", p_ru)

        p_en = select_profile("en")
        self.assertIn("lang", p_en)

    def test_superjob_scraper_parsing(self):
        scraper = SuperJobScraper()
        sample_html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Frontend разработчик (React)",
                "description": "Разработка SPA на React и TypeScript",
                "hiringOrganization": { "@type": "Organization", "name": "SuperCorp" },
                "jobLocation": { "@type": "Place", "address": { "@type": "PostalAddress", "addressLocality": "Москва" } },
                "baseSalary": { "@type": "MonetaryAmount", "value": { "minValue": 150000, "maxValue": 200000, "unitText": "MONTH" }, "currency": "RUB" },
                "url": "https://www.superjob.ru/vakansii/frontend-12345.html"
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        vacancies = scraper.parse_html(sample_html)
        self.assertEqual(len(vacancies), 1)
        v = vacancies[0]
        self.assertEqual(v["title"], "Frontend разработчик (React)")
        self.assertEqual(v["company"], "SuperCorp")
        self.assertEqual(v["source"], "superjob")
        self.assertIn("150 000", v["salary"])

    def test_rabotaru_scraper_parsing(self):
        scraper = RabotaRuScraper()
        sample_html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "React Developer",
                "description": "Создание современных интерфейсов на React",
                "hiringOrganization": { "@type": "Organization", "name": "RabotaCorp" },
                "jobLocation": { "@type": "Place", "address": { "@type": "PostalAddress", "addressLocality": "Удаленно" } },
                "baseSalary": { "@type": "MonetaryAmount", "value": { "value": 180000 }, "currency": "RUR" },
                "url": "https://www.rabota.ru/vacancy/998877"
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        vacancies = scraper.parse_html(sample_html)
        self.assertEqual(len(vacancies), 1)
        v = vacancies[0]
        self.assertEqual(v["title"], "React Developer")
        self.assertEqual(v["company"], "RabotaCorp")
        self.assertEqual(v["source"], "rabotaru")
        self.assertIn("180 000", v["salary"])

    def test_clean_company_name_and_direct_sourcing(self):
        from enricher.lead_finder import clean_company_name, generate_direct_sourcing_links
        self.assertEqual(clean_company_name("Банк ВТБ (ПАО)"), "Банк ВТБ")
        self.assertEqual(clean_company_name("ООО «Яндекс Крауд»"), "Яндекс Крауд")
        self.assertEqual(clean_company_name("Aliexpress Russia LLC"), "Aliexpress Russia")
        self.assertEqual(clean_company_name("Компания на Habr", title="Frontend Developer | Sber"), "Sber")

        links = generate_direct_sourcing_links("ООО «Яндекс Крауд»", "Frontend Developer", "ru")
        self.assertEqual(links["clean_company"], "Яндекс Крауд")
        self.assertIn("greenhouse.io", links["direct_ats"])
        self.assertIn("site%3Asetka.ru", links["setka"])
        self.assertIn("CTO", links["cto"])

    def test_ats_scraper_targeted_filtering(self):
        from scrapers.ats_scraper import ATSScraper
        scraper = ATSScraper()
        # Irrelevant defense / systems / non-web roles must be excluded
        self.assertFalse(scraper._is_relevant("Software Engineer, New Grad - Defense"))
        self.assertFalse(scraper._is_relevant("Software Engineer, Infrastructure - Core"))
        self.assertFalse(scraper._is_relevant("Staff C++ Systems Engineer"))
        self.assertFalse(scraper._is_relevant("DevOps / SRE Lead"))
        self.assertFalse(scraper._is_relevant("Senior iOS Developer"))

        # Targeted Web / Frontend / Fullstack roles must be included
        self.assertTrue(scraper._is_relevant("Senior Frontend Engineer (React)"))
        self.assertTrue(scraper._is_relevant("Full Stack Engineer - React/Node"))
        self.assertTrue(scraper._is_relevant("UI Software Engineer"))
        self.assertTrue(scraper._is_relevant("Software Engineer, Web Platform"))

    def test_blacklist_and_shame_list(self):
        import sqlite3
        from tracker.db import get_db_connection, save_vacancy
        from tracker.shame_list import generate_shame_list_markdown

        test_vac = {
            "id": "test:toxic:corp:001",
            "title": "Frontend Developer (React)",
            "company": "Toxic ИП Company",
            "url": "https://example.com/job/toxic001",
            "salary": "от 100 000 руб.",
            "source": "test",
            "description": "Оформление строго через ИП"
        }
        save_vacancy(test_vac)

        # Update to blacklist
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE vacancies
            SET status = 'blacklist',
                blacklist_reason = 'Оформление по ИП с 1-го дня (уклонение от ТК РФ)',
                blacklisted_at = '2026-09-16 20:00:00'
            WHERE id = ?
        """, (test_vac["id"],))
        conn.commit()

        # Check DB columns
        cur.execute("SELECT status, blacklist_reason FROM vacancies WHERE id = ?", (test_vac["id"],))
        row = cur.fetchone()
        self.assertEqual(row[0], "blacklist")
        self.assertIn("Оформление по ИП", row[1])
        conn.close()

        # Check markdown generation
        md = generate_shame_list_markdown()
        self.assertIn("Toxic ИП Company", md)
        self.assertIn("Оформление по ИП с 1-го дня", md)
        self.assertIn("Доска позора", md)

        # Cleanup
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM vacancies WHERE id = ?", (test_vac["id"],))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    unittest.main()

