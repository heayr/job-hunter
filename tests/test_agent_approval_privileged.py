import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker.db import init_db, create_agent_session, update_agent_session, get_agent_session, save_vacancy
from agents.tool_system import ToolRegistry, ToolExecutionError
from agents.browser_bridge import get_browser_bridge
from agents.agent_brain import CareerAgentBrain


class TestAgentApprovalPrivileged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session_id = str(uuid.uuid4())
        self.approval_token = "secret_approval_token_123"
        self.vacancy_id = f"vac_{uuid.uuid4().hex[:8]}"

        save_vacancy({
            "id": self.vacancy_id,
            "title": "Senior Staff Engineer",
            "company": "Apex Fintech",
            "url": "https://example.com/apply",
            "status": "new"
        })

        create_agent_session(
            self.session_id,
            self.vacancy_id,
            target_url="https://example.com/apply",
            mode="SUPERVISED"
        )
        update_agent_session(self.session_id, state="WAITING_FOR_USER", approval_token=self.approval_token)

    def test_submit_rejects_missing_or_invalid_token(self):
        # 1. Invalid token
        res1 = ToolRegistry.execute_tool("browser_submit_application", {
            "session_id": self.session_id,
            "approval_token": "wrong_token"
        })
        self.assertFalse(res1["success"])
        self.assertIn("Missing or invalid human approval token", res1["error"])

        # 2. Non-existent session
        res2 = ToolRegistry.execute_tool("browser_submit_application", {
            "session_id": "non_existent_session",
            "approval_token": "any"
        })
        self.assertFalse(res2["success"])
        self.assertIn("not found", res2["error"])

    def test_submit_succeeds_with_valid_token_and_syncs_crm(self):
        # Prime the browser bridge response so command does not hang
        bridge = get_browser_bridge()

        # Simulate background extension answering command
        import threading
        import time

        def _answer_cmd():
            for _ in range(30):
                cmd = bridge.get_next_pending_command()
                if cmd:
                    bridge.complete_command(cmd["command_id"], {"clicked": True, "success": True})
                    break
                time.sleep(0.05)

        t = threading.Thread(target=_answer_cmd, daemon=True)
        t.start()

        res = ToolRegistry.execute_tool("browser_submit_application", {
            "session_id": self.session_id,
            "approval_token": self.approval_token,
            "element_id": "elem_submit"
        })

        self.assertTrue(res["success"])
        self.assertTrue(res.get("result", {}).get("submitted", False))

        # Check session updated to COMPLETED
        session = get_agent_session(self.session_id)
        self.assertEqual(session["state"], "COMPLETED")

        # Check vacancy status updated to sent in CRM
        from tracker.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM vacancies WHERE id = ?", (self.vacancy_id,))
        row = cursor.fetchone()
        self.assertEqual(row["status"], "sent")

        # Check application_history record
        cursor.execute("SELECT * FROM application_history WHERE vacancy_id = ?", (self.vacancy_id,))
        app_row = cursor.fetchone()
        self.assertIsNotNone(app_row)
        self.assertEqual(app_row["fsm_state"], "SUBMITTED")
        conn.close()

    def test_agent_brain_verifies_before_approval(self):
        # Verify that brain triggers verification before requesting human approval
        brain = CareerAgentBrain(
            vacancy_id=self.vacancy_id,
            target_url="https://example.com/apply",
            mode="SUPERVISED",
            max_steps=10
        )

        # Seed scratchpad as if fields were filled
        brain.scratchpad.append({
            "step": 1,
            "thought": "Inspecting page",
            "tool_name": "browser_inspect_page",
            "arguments": {},
            "observation": {
                "interactive_elements": [
                    {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Name *", "value": "Егор Мышинский", "required": True},
                    {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Email *", "value": "egor@example.com", "required": True}
                ]
            }
        })
        brain.scratchpad.append({
            "step": 2,
            "thought": "Classifying fields",
            "tool_name": "candidate_classify_form",
            "arguments": {"elements": []},
            "observation": {
                "classified_elements": [
                    {"element_id": "elem_1", "category": "FULL_NAME", "action": "fill", "recommended_value": "Егор Мышинский"},
                    {"element_id": "elem_2", "category": "EMAIL", "action": "fill", "recommended_value": "egor@example.com"}
                ]
            }
        })
        brain.scratchpad.append({
            "step": 3,
            "thought": "Filling name",
            "tool_name": "browser_fill_field",
            "arguments": {"element_id": "elem_1", "value": "Егор Мышинский"},
            "observation": {"success": True}
        })
        brain.scratchpad.append({
            "step": 4,
            "thought": "Filling email",
            "tool_name": "browser_fill_field",
            "arguments": {"element_id": "elem_2", "value": "egor@example.com"},
            "observation": {"success": True}
        })

        # Next decision should be re-inspecting live DOM to observe filled values
        decision_insp = brain._heuristic_fallback_decision()
        self.assertEqual(decision_insp["action"], "browser_inspect_page")

        brain.scratchpad.append({
            "step": 5,
            "thought": "Re-inspecting filled fields",
            "tool_name": "browser_inspect_page",
            "arguments": {},
            "observation": {
                "observation": {
                    "interactive_elements": [
                        {"element_id": "elem_1", "tag": "input", "label": "Full Name", "current_value": "Егор Мышинский", "required": True},
                        {"element_id": "elem_2", "tag": "input", "label": "Email", "current_value": "egor@example.com", "required": True}
                    ]
                }
            }
        })

        # Next decision should be candidate_verify_form
        decision = brain._heuristic_fallback_decision()
        self.assertEqual(decision["action"], "candidate_verify_form")

        # Now simulate candidate_verify_form execution
        brain.scratchpad.append({
            "step": 6,
            "thought": "Running verification",
            "tool_name": "candidate_verify_form",
            "arguments": {},
            "observation": {"is_valid": True, "can_submit": True, "summary": "All fields valid"}
        })

        # Now subsequent decision MUST be request_human_approval
        decision2 = brain._heuristic_fallback_decision()
        self.assertEqual(decision2["action"], "request_human_approval")
        self.assertIn("verification", decision2["arguments"]["summary"])


if __name__ == '__main__':
    unittest.main()
