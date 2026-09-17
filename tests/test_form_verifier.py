import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.form_verifier import verify_application_form


class TestFormVerifier(unittest.TestCase):
    def test_valid_form_passes(self):
        elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Full Name *", "value": "Егор Мышинский", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Email *", "value": "egormyshinsky@gmail.com", "required": True},
            {"element_id": "elem_3", "tag": "input", "type": "tel", "label": "Phone", "value": "+79998291788", "required": False},
            {"element_id": "elem_4", "tag": "input", "type": "file", "label": "Resume CV *", "value": "cv.txt", "has_file": True, "required": True},
            {"element_id": "elem_5", "tag": "input", "type": "checkbox", "label": "Consent to personal data processing *", "checked": True, "required": True},
            {"element_id": "elem_6", "tag": "button", "type": "submit", "label": "Submit Application"}
        ]
        res = verify_application_form(elements)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["can_submit"])
        self.assertEqual(len(res["missing_required"]), 0)
        self.assertEqual(len(res["validation_errors"]), 0)

    def test_missing_required_fails(self):
        elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Full Name *", "value": "", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Email *", "value": "egormyshinsky@gmail.com", "required": True},
            {"element_id": "elem_4", "tag": "input", "type": "file", "label": "Resume CV *", "value": "", "has_file": False, "required": True}
        ]
        res = verify_application_form(elements)
        self.assertFalse(res["is_valid"])
        self.assertFalse(res["can_submit"])
        self.assertEqual(len(res["missing_required"]), 2)
        missing_ids = [m["element_id"] for m in res["missing_required"]]
        self.assertIn("elem_1", missing_ids)
        self.assertIn("elem_4", missing_ids)

    def test_invalid_email_and_phone_format(self):
        elements = [
            {"element_id": "elem_1", "tag": "input", "type": "email", "label": "Email", "value": "not-an-email"},
            {"element_id": "elem_2", "tag": "input", "type": "tel", "label": "Phone", "value": "123"}
        ]
        res = verify_application_form(elements)
        self.assertFalse(res["is_valid"])
        self.assertEqual(len(res["validation_errors"]), 2)

    def test_dom_error_flagged(self):
        elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Name", "value": "Егор", "error": "Value too short"}
        ]
        res = verify_application_form(elements)
        self.assertFalse(res["is_valid"])
        self.assertEqual(len(res["dom_errors"]), 1)

    def test_captcha_detection(self):
        elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Name", "value": "Егор"},
            {"element_id": "elem_2", "tag": "div", "type": "captcha", "label": "Cloudflare Turnstile", "has_captcha": True}
        ]
        res = verify_application_form(elements)
        self.assertTrue(res["has_captcha"])
        self.assertFalse(res["can_submit"])


if __name__ == '__main__':
    unittest.main()
