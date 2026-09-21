"""
Objective Testing Suite — Database Layer Tests
===============================================
Tests for tracker/db.py: CRUD operations, migrations, FSM state management.
Uses temp-file SQLite for isolation (in-memory is per-connection in SQLite).
"""

import sys
import os
import json
import sqlite3
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.conftest import make_vacancy, make_pitch


def _setup_temp_db():
    """Create a temp DB, init schema, set as active path."""
    from tracker.db import init_db, set_db_path
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    set_db_path(path)
    init_db(path)
    return path


def _cleanup(path):
    from tracker.db import reset_db_path
    reset_db_path()
    try:
        os.unlink(path)
    except Exception:
        pass


class TestDatabaseCRUD(unittest.TestCase):
    """CRUD operations for vacancies, pitches, and profiles."""

    def setUp(self):
        self.db_path = _setup_temp_db()
        self.vac = make_vacancy()

    def tearDown(self):
        _cleanup(self.db_path)

    def test_save_vacancy(self):
        from tracker.db import save_vacancy
        result = save_vacancy(self.vac)
        self.assertTrue(result)

    def test_save_vacancy_duplicate_ignored(self):
        from tracker.db import save_vacancy
        save_vacancy(self.vac)
        result = save_vacancy(self.vac)
        self.assertFalse(result)

    def test_get_vacancy_by_id(self):
        from tracker.db import save_vacancy, get_db_connection
        save_vacancy(self.vac)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM vacancies WHERE id = ?", (self.vac["id"],))
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], self.vac["title"])

    def test_update_vacancy_status(self):
        from tracker.db import save_vacancy, update_vacancy_status, get_db_connection
        save_vacancy(self.vac)
        update_vacancy_status(self.vac["id"], "applied")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM vacancies WHERE id = ?", (self.vac["id"],))
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row["status"], "applied")

    def test_update_vacancy_status_blacklist(self):
        from tracker.db import save_vacancy, update_vacancy_status, get_db_connection
        save_vacancy(self.vac)
        update_vacancy_status(self.vac["id"], "blacklist", "Toxic conditions")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status, blacklist_reason FROM vacancies WHERE id = ?", (self.vac["id"],))
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row["status"], "blacklist")
        self.assertEqual(row["blacklist_reason"], "Toxic conditions")

    def test_delete_vacancy(self):
        from tracker.db import save_vacancy, get_db_connection
        save_vacancy(self.vac)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM vacancies WHERE id = ?", (self.vac["id"],))
        conn.commit()
        cur.execute("SELECT COUNT(*) as cnt FROM vacancies WHERE id = ?", (self.vac["id"],))
        cnt = cur.fetchone()["cnt"]
        conn.close()
        self.assertEqual(cnt, 0)


class TestFSMStateManagement(unittest.TestCase):
    """FSM state transitions and persistence."""

    def setUp(self):
        self.db_path = _setup_temp_db()
        from tracker.db import save_vacancy
        self.vac = make_vacancy(vid="fsm_test_001")
        save_vacancy(self.vac)

    def tearDown(self):
        _cleanup(self.db_path)

    def test_initial_state_is_discovered(self):
        from tracker.db import get_vacancy_fsm_state
        state = get_vacancy_fsm_state(self.vac["id"])
        self.assertEqual(state, "DISCOVERED")

    def test_update_fsm_state(self):
        from tracker.db import update_vacancy_fsm_state, get_vacancy_fsm_state
        update_vacancy_fsm_state(self.vac["id"], "ANALYZING")
        state = get_vacancy_fsm_state(self.vac["id"])
        self.assertEqual(state, "ANALYZING")

    def test_fsm_state_full_lifecycle(self):
        from tracker.db import update_vacancy_fsm_state, get_vacancy_fsm_state
        states = ["ANALYZING", "RESEARCHING", "MATCHED", "STRATEGY_READY", "ARTIFACTS_READY", "WAITING_APPROVAL"]
        for state in states:
            update_vacancy_fsm_state(self.vac["id"], state)
        final = get_vacancy_fsm_state(self.vac["id"])
        self.assertEqual(final, "WAITING_APPROVAL")


class TestPitchOperations(unittest.TestCase):
    """Pitch upsert and retrieval operations."""

    def setUp(self):
        self.db_path = _setup_temp_db()
        from tracker.db import save_vacancy
        self.vac = make_vacancy(vid="pitch_test_001")
        save_vacancy(self.vac)

    def tearDown(self):
        _cleanup(self.db_path)

    def test_insert_pitch(self):
        from tracker.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        pitch = make_pitch(vacancy_id=self.vac["id"])
        cur.execute(
            "INSERT INTO pitches (vacancy_id, pitch_type, language, content) VALUES (?, ?, ?, ?)",
            (pitch["vacancy_id"], pitch["pitch_type"], pitch["language"], pitch["content"])
        )
        conn.commit()
        cur.execute("SELECT COUNT(*) as cnt FROM pitches WHERE vacancy_id = ?", (self.vac["id"],))
        cnt = cur.fetchone()["cnt"]
        conn.close()
        self.assertEqual(cnt, 1)

    def test_update_pitch_content(self):
        from tracker.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        # Insert a pitch
        cur.execute(
            "INSERT INTO pitches (vacancy_id, pitch_type, language, content) VALUES (?, ?, ?, ?)",
            (self.vac["id"], "cover_letter", "ru", "Initial content")
        )
        conn.commit()
        # Update it
        cur.execute(
            "UPDATE pitches SET content = ? WHERE vacancy_id = ? AND pitch_type = ?",
            ("Updated content", self.vac["id"], "cover_letter")
        )
        conn.commit()
        cur.execute("SELECT content FROM pitches WHERE vacancy_id = ? AND pitch_type = 'cover_letter'", (self.vac["id"],))
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row["content"], "Updated content")


class TestApplicationHistory(unittest.TestCase):
    """Application history recording and retrieval."""

    def setUp(self):
        self.db_path = _setup_temp_db()
        from tracker.db import save_vacancy
        self.vac = make_vacancy(vid="hist_test_001")
        save_vacancy(self.vac)

    def tearDown(self):
        _cleanup(self.db_path)

    def test_record_application_event(self):
        from tracker.db import record_application_event
        event_id = record_application_event(
            vacancy_id=self.vac["id"],
            company="TestCorp",
            role_title="Frontend Developer",
            portal="hh.ru",
            mode="SEMI_AUTO",
            fsm_state="SUBMITTED"
        )
        self.assertIsNotNone(event_id)
        self.assertGreater(event_id, 0)

    def test_get_application_history(self):
        from tracker.db import record_application_event, get_application_history
        record_application_event(
            vacancy_id=self.vac["id"],
            company="TestCorp",
            role_title="Frontend Developer",
            portal="hh.ru",
            mode="SEMI_AUTO",
            fsm_state="SUBMITTED"
        )
        history = get_application_history(limit=10)
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)


class TestDatabaseMigrations(unittest.TestCase):
    """Schema migration compatibility tests."""

    def test_init_db_creates_all_tables(self):
        db_path = _setup_temp_db()
        try:
            from tracker.db import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cur.fetchall()]
            conn.close()
            expected = ["vacancies", "pitches", "candidate_profiles", "application_history", "agent_sessions"]
            for t in expected:
                self.assertIn(t, tables, f"Table '{t}' not found")
        finally:
            _cleanup(db_path)

    def test_init_db_idempotent(self):
        db_path = _setup_temp_db()
        try:
            from tracker.db import init_db, get_db_connection
            init_db(db_path)
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM vacancies")
            cnt = cur.fetchone()["cnt"]
            conn.close()
            self.assertEqual(cnt, 0)
        finally:
            _cleanup(db_path)


if __name__ == "__main__":
    unittest.main()
