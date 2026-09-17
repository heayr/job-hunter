import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.candidate_profile import get_canonical_profile
from generator.question_answerer import answer_application_question


class TestQuestionAnswerer(unittest.TestCase):
    def setUp(self):
        self.profile = get_canonical_profile(lang="ru")

    def test_answer_with_direct_evidence(self):
        q = "How do you optimize web performance and page load speed?"
        res = answer_application_question(q, self.profile, lang="en")
        self.assertIn("answer", res)
        self.assertTrue(len(res["answer"]) > 30)
        # Should cite real evidence or tech
        self.assertTrue(res["has_direct_evidence"])
        self.assertGreater(len(res["matched_evidence_ids"]), 0)

    def test_answer_incident_question(self):
        q = "Describe a critical production outage and your mitigation steps"
        res = answer_application_question(q, self.profile, lang="en")
        self.assertIn("answer", res)
        ans_lower = res["answer"].lower()
        self.assertTrue(any(w in ans_lower for w in ["incident", "outage", "issue", "system", "mitigat", "protocol"]))

    def test_zero_hallucination_on_unverified_tech(self):
        # Candidate has no Rust or Unreal Engine evidence
        q = "Do you have 5 years of production experience writing custom Rust kernel drivers?"
        res = answer_application_question(q, self.profile, lang="en")
        self.assertIn("answer", res)
        # Crucial: agent must NOT claim direct production ownership!
        self.assertFalse(res["has_direct_evidence"])
        ans_lower = res["answer"].lower()
        self.assertTrue("do not claim direct" in ans_lower or "not" in ans_lower or "ready" in ans_lower)


if __name__ == '__main__':
    unittest.main()
