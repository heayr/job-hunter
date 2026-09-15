import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filter.profile_filter import is_qualified_vacancy
from scanners.telegram_scanner import parse_telegram_html

class TestFilters(unittest.TestCase):
    def test_is_qualified_vacancy_rejects_python(self):
        ok, reason = is_qualified_vacancy("Python Developer", "Python, Django", "", "")
        self.assertFalse(ok)
        self.assertIn("BLACKLIST", reason.upper())

    def test_is_qualified_vacancy_accepts_react(self):
        ok, reason = is_qualified_vacancy("Frontend Developer", "React, TypeScript", "", "")
        self.assertTrue(ok)
        self.assertIn("MATCHED ROLE", reason.upper())

class TestTelegramScanner(unittest.TestCase):
    def test_parse_telegram_html(self):
        message_html = """
        <div class="tgme_widget_message js-widget_message" data-post="job_react/123">
            <div class="tgme_widget_message_text js-message_text" dir="auto">
                Frontend Developer (React)<br>
                Company: Tech Corp<br>
                Salary: $4000-$5000<br>
                Location: Remote<br>
                Contact: @hr_techcorp
            </div>
        </div>
        """
        result = parse_telegram_html(message_html, "job_react")
        self.assertEqual(len(result), 1)
        res = result[0]
        self.assertIn("Frontend", res["title"])
        self.assertIn("Tech Corp", res["company"])
        self.assertEqual(res["contact_handle"], "@hr_techcorp")
        self.assertEqual(res["id"], "tg:job_react_123")

if __name__ == "__main__":
    unittest.main()
