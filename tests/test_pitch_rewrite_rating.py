import unittest
import sqlite3
from crm import CRMHandler

class MockCRMHandler(CRMHandler):
    def __init__(self):
        # Do not initialize base HTTPServer
        pass

class TestPitchRewriteRating(unittest.TestCase):
    def setUp(self):
        # Use isolated in-memory database to prevent locking against live server
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.handler = MockCRMHandler()

        # Create schema
        self.cur.execute("""
            CREATE TABLE vacancies (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                source TEXT NOT NULL,
                description TEXT,
                score INTEGER DEFAULT 0,
                pitch_rating INTEGER DEFAULT 0
            )
        """)
        self.cur.execute("""
            CREATE TABLE pitches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vacancy_id TEXT,
                pitch_type TEXT,
                language TEXT,
                content TEXT,
                rating INTEGER DEFAULT 0,
                status TEXT DEFAULT 'DRAFT',
                user_edited_content TEXT,
                UNIQUE(vacancy_id, pitch_type)
            )
        """)

        # Insert a test vacancy with disliked pitch_rating (-1)
        self.vac_id = "test_vac_rewrite_001"
        self.cur.execute("""
            INSERT INTO vacancies (id, title, company, source, description, score, pitch_rating)
            VALUES (?, 'Senior Frontend Engineer', 'TestCo', 'hh', 'React, Next.js, TypeScript', 85, -1)
        """, (self.vac_id,))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_upsert_pitch_resets_rating_on_update(self):
        # 1. Initial pitch rated as disliked (-1)
        self.cur.execute("""
            INSERT INTO pitches (vacancy_id, pitch_type, language, content, rating, status)
            VALUES (?, 'short_dm', 'ru', 'Старый плохой питч', -1, 'REJECTED')
        """, (self.vac_id,))
        self.conn.commit()

        # Verify it was disliked
        self.cur.execute("SELECT rating, status FROM pitches WHERE vacancy_id = ? AND pitch_type = 'short_dm'", (self.vac_id,))
        row = self.cur.fetchone()
        self.assertEqual(row["rating"], -1)
        self.assertEqual(row["status"], "REJECTED")

        # 2. Upsert newly generated pitch
        self.handler.upsert_pitch(self.cur, self.vac_id, 'short_dm', 'ru', 'Новый улучшенный питч')
        self.conn.commit()

        # 3. Verify rating was reset to 0 and status to DRAFT
        self.cur.execute("SELECT content, rating, status FROM pitches WHERE vacancy_id = ? AND pitch_type = 'short_dm'", (self.vac_id,))
        row = self.cur.fetchone()
        self.assertEqual(row["content"], "Новый улучшенный питч")
        self.assertEqual(row["rating"], 0)
        self.assertEqual(row["status"], "DRAFT")

    def test_rewrite_resets_vacancy_pitch_rating(self):
        # Vacancy pitch_rating starts as -1
        self.cur.execute("SELECT pitch_rating FROM vacancies WHERE id = ?", (self.vac_id,))
        self.assertEqual(self.cur.fetchone()["pitch_rating"], -1)

        # Simulate rewrite logic from crm.py
        self.cur.execute("UPDATE vacancies SET pitch_rating = 0 WHERE id = ?", (self.vac_id,))
        self.cur.execute("UPDATE pitches SET rating = 0, status = 'DRAFT' WHERE vacancy_id = ?", (self.vac_id,))
        self.conn.commit()

        self.cur.execute("SELECT pitch_rating FROM vacancies WHERE id = ?", (self.vac_id,))
        self.assertEqual(self.cur.fetchone()["pitch_rating"], 0)

if __name__ == "__main__":
    unittest.main()
