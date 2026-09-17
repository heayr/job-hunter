import unittest
import os
import json
import sqlite3
from tracker.db import (
    init_db,
    get_db_connection,
    record_application_event,
    get_application_history,
    log_agent_run_step,
    get_agent_run_timeline,
    DB_PATH
)

class TestApplicationHistoryAndLogs(unittest.TestCase):
    def setUp(self):
        init_db()
        self.test_vac_id = "test:vac:history:001"

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM application_history WHERE vacancy_id = ?", (self.test_vac_id,))
        cur.execute("DELETE FROM agent_run_logs WHERE vacancy_id = ?", (self.test_vac_id,))
        conn.commit()
        conn.close()

    def test_record_and_get_application_history(self):
        rec_id = record_application_event(
            vacancy_id=self.test_vac_id,
            company="FintechCorp",
            role_title="Senior Frontend Engineer",
            portal="hh.ru",
            mode="SEMI_AUTO",
            fsm_state="SUBMITTED",
            metadata={"match_score": 92, "tailored_cv": True}
        )
        self.assertGreater(rec_id, 0)

        history = get_application_history(limit=10)
        self.assertIsInstance(history, list)
        matching = [h for h in history if h["vacancy_id"] == self.test_vac_id]
        self.assertEqual(len(matching), 1)
        event = matching[0]
        self.assertEqual(event["company"], "FintechCorp")
        self.assertEqual(event["portal"], "hh.ru")
        self.assertEqual(event["mode"], "SEMI_AUTO")
        self.assertEqual(event["fsm_state"], "SUBMITTED")

        meta = json.loads(event["metadata_json"])
        self.assertEqual(meta["match_score"], 92)

    def test_log_and_get_agent_run_timeline(self):
        log_id1 = log_agent_run_step(
            vacancy_id=self.test_vac_id,
            step_name="JobAnalyst",
            status="SUCCESS",
            duration_ms=45,
            details={"facts_found": 3}
        )
        self.assertGreater(log_id1, 0)

        log_id2 = log_agent_run_step(
            vacancy_id=self.test_vac_id,
            step_name="Critic",
            status="SUCCESS",
            duration_ms=120,
            details={"fluff_removed": 2}
        )
        self.assertGreater(log_id2, 0)

        timeline = get_agent_run_timeline(self.test_vac_id)
        self.assertEqual(len(timeline), 2)
        steps = [t["step_name"] for t in timeline]
        self.assertEqual(steps, ["JobAnalyst", "Critic"])
        self.assertEqual(timeline[0]["duration_ms"], 45)
        self.assertEqual(timeline[1]["duration_ms"], 120)

if __name__ == "__main__":
    unittest.main()
