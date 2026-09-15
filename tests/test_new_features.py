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

if __name__ == "__main__":
    unittest.main()
