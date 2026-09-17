import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filter.profile_filter import is_qualified_vacancy


class TestFilters(unittest.TestCase):
    def test_is_qualified_vacancy_rejects_python(self):
        ok, reason = is_qualified_vacancy("Python Developer", "Python, Django", "", "")
        self.assertFalse(ok)
        self.assertIn("BLACKLIST", reason.upper())

    def test_is_qualified_vacancy_accepts_react(self):
        ok, reason = is_qualified_vacancy("Frontend Developer", "React, TypeScript", "", "")
        self.assertTrue(ok)
        self.assertIn("MATCHED ROLE", reason.upper())


if __name__ == "__main__":
    unittest.main()
