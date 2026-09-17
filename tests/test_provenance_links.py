import unittest
import os
import sys
import uuid
import base64

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.candidate_profile import get_canonical_profile
from generator.tailored_resume_engine import compile_tailored_cv_artifact
from tracker.db import init_db, save_provenance_links, get_provenance_links


class TestProvenanceLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.profile = get_canonical_profile(lang="ru")

    def test_compile_tailored_cv_creates_provenance_links(self):
        session_id = str(uuid.uuid4())
        job_understanding = {
            "role_overview": {"title": "Senior Frontend Developer", "company": "Fintech Global"},
            "facts": {"explicit_requirements": ["React", "TypeScript", "Performance"]}
        }

        artifact = compile_tailored_cv_artifact(
            self.profile,
            job_understanding,
            lang="ru",
            session_id=session_id
        )

        self.assertTrue(artifact["success"])
        self.assertTrue(len(artifact["file_base64"]) > 100)
        self.assertTrue(artifact["file_name"].endswith(".txt") or artifact["file_name"].endswith(".pdf"))

        # Verify decoding base64 produces markdown text
        decoded = base64.b64decode(artifact["file_base64"]).decode("utf-8")
        self.assertTrue("егор мышинский" in decoded.lower())
        self.assertIn("Целевая позиция", decoded)

        # Check provenance links
        links = artifact["provenance_links"]
        self.assertGreater(len(links), 0)
        for link in links:
            self.assertIn("statement", link)
            self.assertIn("source_evidence_id", link)
            self.assertTrue(link["source_evidence_id"].startswith("ev_"))

        # Verify links were persisted in SQLite
        db_links = get_provenance_links(session_id)
        self.assertEqual(len(db_links), len(links))
        self.assertEqual(db_links[0]["session_id"], session_id)


if __name__ == '__main__':
    unittest.main()
