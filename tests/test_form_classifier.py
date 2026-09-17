import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.candidate_profile import get_canonical_profile
from generator.form_classifier import classify_form_elements, FieldCategory


class TestFormClassifier(unittest.TestCase):
    def setUp(self):
        self.profile = get_canonical_profile(lang="ru")

    def test_classify_standard_contacts(self):
        elements = [
            {"element_id": "e1", "tag": "input", "type": "text", "label": "First Name"},
            {"element_id": "e2", "tag": "input", "type": "text", "label": "Last Name"},
            {"element_id": "e3", "tag": "input", "type": "email", "label": "Email"},
            {"element_id": "e4", "tag": "input", "type": "tel", "label": "Phone Number"},
            {"element_id": "e5", "tag": "input", "type": "file", "label": "Upload Resume (PDF)"},
            {"element_id": "e6", "tag": "textarea", "label": "Cover Letter"}
        ]
        classified = classify_form_elements(elements, self.profile)

        cats = {c["element_id"]: c["category"] for c in classified}
        self.assertEqual(cats["e1"], FieldCategory.CONTACT_FIRST_NAME)
        self.assertEqual(cats["e2"], FieldCategory.CONTACT_LAST_NAME)
        self.assertEqual(cats["e3"], FieldCategory.CONTACT_EMAIL)
        self.assertEqual(cats["e4"], FieldCategory.CONTACT_PHONE)
        self.assertEqual(cats["e5"], FieldCategory.RESUME_FILE)
        self.assertEqual(cats["e6"], FieldCategory.COVER_LETTER)

        # Check values
        c3 = next(c for c in classified if c["element_id"] == "e3")
        self.assertEqual(c3["recommended_value"], "egormyshinsky@gmail.com")

    def test_classify_screening_facts(self):
        elements = [
            {"element_id": "s1", "tag": "input", "type": "text", "label": "Expected Monthly Salary (USD)"},
            {"element_id": "s2", "tag": "input", "type": "text", "label": "Notice Period"},
            {"element_id": "s3", "tag": "input", "type": "text", "label": "Are you legally authorized to work?"},
            {"element_id": "s4", "tag": "select", "label": "English Level"}
        ]
        classified = classify_form_elements(elements, self.profile)
        cats = {c["element_id"]: c["category"] for c in classified}

        self.assertEqual(cats["s1"], FieldCategory.SCREENING_SALARY)
        self.assertEqual(cats["s2"], FieldCategory.SCREENING_NOTICE)
        self.assertEqual(cats["s3"], FieldCategory.SCREENING_AUTHORIZATION)
        self.assertEqual(cats["s4"], FieldCategory.SCREENING_ENGLISH)

    def test_classify_custom_question(self):
        elements = [
            {"element_id": "q1", "tag": "textarea", "label": "Describe your most difficult production outage and how you resolved it"}
        ]
        classified = classify_form_elements(elements, self.profile)
        self.assertEqual(classified[0]["category"], FieldCategory.CUSTOM_TECHNICAL_QUESTION)
        self.assertEqual(classified[0]["action"], "generate_answer")


if __name__ == '__main__':
    unittest.main()
