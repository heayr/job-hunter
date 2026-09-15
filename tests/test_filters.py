import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filter.profile_filter import is_qualified_vacancy

class TestFilters(unittest.TestCase):
    def test_is_qualified_vacancy_rejects_python(self):
        ok, reason = is_qualified_vacancy("Python Developer", "Python, Django", "", "")
        self.assertFalse(ok)
        self.assertTrue("BLACKLIST" in reason or "blacklist" in reason.lower())

    def test_is_qualified_vacancy_accepts_international_and_internal(self):
        ok, reason = is_qualified_vacancy(
            "Senior Frontend Engineer",
            "React, Next.js, TypeScript",
            "We are an international product company building internal tools and internet services.",
            "Global Corp"
        )
        self.assertTrue(ok, f"Should accept international/internal vacancy but got: {reason}")

    def test_is_qualified_vacancy_accepts_intern_and_junior(self):
        from filter.profile_filter import detect_vacancy_grade
        ok1, reason1 = is_qualified_vacancy("Frontend Intern", "React", "Internship opportunity", "Company")
        self.assertTrue(ok1, f"Intern position should be accepted: {reason1}")
        self.assertEqual(detect_vacancy_grade("Frontend Intern"), "Intern")

        ok2, reason2 = is_qualified_vacancy("Junior Frontend Developer", "React", "", "Company")
        self.assertTrue(ok2, f"Junior position should be accepted: {reason2}")
        self.assertEqual(detect_vacancy_grade("Junior Frontend Developer"), "Junior")

        ok3, reason3 = is_qualified_vacancy("Стажер Frontend", "React", "", "Company")
        self.assertTrue(ok3, f"Стажер should be accepted: {reason3}")
        self.assertEqual(detect_vacancy_grade("Стажер Frontend"), "Intern")

    def test_is_qualified_vacancy_rejects_candidate_resumes(self):
        ok1, reason1 = is_qualified_vacancy("Frontend Developer", "", "Резюме: ищу работу на позицию React разработчик", "Кандидат")
        self.assertFalse(ok1)
        self.assertIn("Resume", reason1)

        ok2, reason2 = is_qualified_vacancy("Frontend Developer (React)", "", "Опыт работы: 3 года. Открыт к предложениям", "Резюме соискателя")
        self.assertFalse(ok2)
        self.assertIn("Resume", reason2)

        ok3, reason3 = is_qualified_vacancy(
            "Реальное снижение нагрузки",
            "React",
            "🔥 Резюме Frontend Developer (React) от @anna_akhmet, 160 000 руб. Ищу работу в Санкт-Петербурге",
            "🔥 Резюме Frontend Developer"
        )
        self.assertFalse(ok3)
        self.assertIn("Resume", reason3)

    def test_is_qualified_vacancy_rejects_ads_and_webinars(self):
        ok, reason = is_qualified_vacancy(
            "Тестовый собес на Frontend-разработчика со старшим разработчиком",
            "React",
            "Приходи на бесплатный эфир! Подарок для всех, кто зарегается",
            "TG: @channel"
        )
        self.assertFalse(ok)
        self.assertIn("Ad/Event", reason)

    def test_is_qualified_vacancy_accepts_vacancies_with_candidate_and_experience_requirements(self):
        ok, reason = is_qualified_vacancy(
            "Senior Frontend Developer (React / Next.js)",
            "React, TypeScript, Next.js",
            "Опыт работы: от 3 лет.\nТребования к кандидату: уверенное владение React и TypeScript. Идеальный кандидат умеет строить масштабируемый frontend.",
            "Yandex Cloud"
        )
        self.assertTrue(ok, f"Real vacancy with candidate requirements should be accepted, but got: {reason}")


if __name__ == "__main__":
    unittest.main()
