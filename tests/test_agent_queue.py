import unittest
import json
from tracker.db import (
    init_db,
    get_db_connection,
    create_agent_task,
    get_pending_agent_tasks,
    update_agent_task_status
)

class TestAgentQueue(unittest.TestCase):
    def setUp(self):
        init_db()
        self.vac_id = "test:queue:vac:001"

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_tasks WHERE vacancy_id = ?", (self.vac_id,))
        conn.commit()
        conn.close()

    def test_queue_lifecycle(self):
        # 1. Create task
        task_id = create_agent_task(
            vacancy_id=self.vac_id,
            url="https://hh.ru/vacancy/12345678",
            company="FintechApp",
            role_title="Senior Frontend Engineer",
            portal="hh.ru",
            cover_letter="Здравствуйте! Опыт React 19 и Next.js 16."
        )
        self.assertGreater(task_id, 0)

        # 2. Retrieve pending tasks
        pending = get_pending_agent_tasks(limit=10)
        matching = [t for t in pending if t["id"] == task_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "PENDING")
        self.assertEqual(matching[0]["company"], "FintechApp")
        self.assertIn("React 19", matching[0]["cover_letter"])

        # 3. Update task to COMPLETED
        update_agent_task_status(task_id, "COMPLETED", "Заполнено 4 поля")

        # 4. Verify no longer pending
        pending_after = get_pending_agent_tasks(limit=10)
        matching_after = [t for t in pending_after if t["id"] == task_id]
        self.assertEqual(len(matching_after), 0)

if __name__ == "__main__":
    unittest.main()
