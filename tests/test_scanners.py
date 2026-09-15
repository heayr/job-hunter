import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanners.telegram_scanner import parse_telegram_html

class TestScanners(unittest.TestCase):
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
        self.assertTrue("Frontend" in res["title"])
        self.assertTrue("Tech Corp" in res["company"])
        self.assertEqual(res["contact_handle"], "@hr_techcorp")
        self.assertEqual(res["id"], "tg:job_react_123")

if __name__ == "__main__":
    unittest.main()
