import unittest
from unittest.mock import MagicMock
from generator.question_answerer import answer_choice_question
from agents.universal_form_filler import UniversalFormFiller


class TestUniversalFormFiller(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "identity": {
                "name": "Egor Myshinsky",
                "location": "Москва, Россия",
                "contacts": {
                    "email": "egormyshinsky@gmail.com",
                    "phone": "+79998291788",
                    "linkedin": "https://linkedin.com/in/potatochipasu",
                    "github": "https://github.com/heayr"
                }
            },
            "skills": ["React", "Next.js", "TypeScript", "Node.js", "Python"],
            "screening_facts": {
                "years_of_experience_num": 5,
                "requires_visa_sponsorship": False,
                "location": "Россия"
            }
        }

    def test_answer_choice_experience_years(self):
        q = "Do you have over 3 years over professional software engineering experience?*"
        opts = ["Yes", "No"]
        ans = answer_choice_question(q, opts, self.profile)
        self.assertEqual(ans, "Yes")

    def test_answer_choice_restrictions(self):
        q = "Are you subject to any employment agreements and/or post-employment restrictions?*"
        opts = ["Yes", "No"]
        ans = answer_choice_question(q, opts, self.profile)
        self.assertEqual(ans, "No")

    def test_answer_choice_visa(self):
        q = "Will you now or in the future require sponsorship for a visa to remain in your current location?*"
        opts = ["Yes", "No"]
        ans = answer_choice_question(q, opts, self.profile)
        self.assertEqual(ans, "No")

    def test_answer_choice_rating_scale(self):
        q = "On a scale of 0–5, how would you rate your professional experience writing backend services in TypeScript/Node.js?*"
        opts = ["0", "1", "2", "3", "4", "5"]
        ans = answer_choice_question(q, opts, self.profile)
        self.assertIn(ans, ["4", "5"])

    def test_resume_path_resolution(self):
        filler = UniversalFormFiller()
        path_en = filler._resolve_resume_path("en")
        self.assertTrue(path_en.endswith(".pdf"))
        self.assertIn("Egor_Myshinsky", path_en)


if __name__ == "__main__":
    unittest.main()
