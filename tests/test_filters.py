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

    def test_is_qualified_vacancy_rejects_intern_and_junior(self):
        ok1, reason1 = is_qualified_vacancy("Frontend Intern", "React", "Internship opportunity", "Company")
        self.assertFalse(ok1)
        self.assertIn("Junior/Intern", reason1)

        ok2, reason2 = is_qualified_vacancy("Junior Frontend Developer", "React", "", "Company")
        self.assertFalse(ok2)
        self.assertIn("Junior/Intern", reason2)

        ok3, reason3 = is_qualified_vacancy("Стажер Frontend", "React", "", "Company")
        self.assertFalse(ok3)
        self.assertIn("Junior/Intern", reason3)

    def test_is_qualified_vacancy_rejects_candidate_resumes(self):
        ok1, reason1 = is_qualified_vacancy("Frontend Developer", "", "Резюме: ищу работу на позицию React разработчик", "Кандидат")
        self.assertFalse(ok1)
        self.assertIn("Resume", reason1)

        ok2, reason2 = is_qualified_vacancy("Frontend Developer (React)", "", "Опыт работы: 3 года. Открыт к предложениям", "Резюме соискателя")
        self.assertFalse(ok2)
        self.assertIn("Resume", reason2)

if __name__ == "__main__":
    unittest.main()
