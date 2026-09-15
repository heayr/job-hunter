import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.pitch_builder import extract_target_keywords, generate_pitch, calculate_match_score

class TestPitchBuilder(unittest.TestCase):
    def test_extract_target_keywords(self):
        desc = "Требуется React, TypeScript. Плюсом будет знание Docker и Webpack."
        kw = extract_target_keywords("Frontend", "React", desc)
        lower_kw = [k.lower() for k in kw]
        self.assertIn("react", lower_kw)
        self.assertIn("typescript", lower_kw)

    def test_generate_pitch_contacts_never_duplicate(self):
        vac = {
            "title": "Lead Frontend Developer",
            "company": "Tech Corp",
            "skills": "React, Next.js, TypeScript",
            "description": "Building modern web applications."
        }
        pitch = generate_pitch(vac)
        cl = pitch["cover_letter"]
        # Telegram and Email must both be present and distinct
        self.assertIn("Telegram:", cl)
        self.assertIn("Email:", cl)
        # Check that we do not have Telegram in place of Email
        self.assertNotIn("Email: @", cl)
        self.assertNotIn("Telegram: @https", cl)

    def test_generate_pitch_score_positive(self):
        vac = {
            "title": "Senior React Engineer",
            "company": "NextApp",
            "skills": "React, TypeScript, Tailwind",
            "description": "Looking for React & TypeScript expert."
        }
        pitch = generate_pitch(vac)
        score = pitch["score"]
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 40)
        self.assertLessEqual(score, 100)

if __name__ == "__main__":
    unittest.main()
