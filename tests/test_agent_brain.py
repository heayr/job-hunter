import unittest
import os
import sys
import uuid
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent_brain import CareerAgentBrain
from tracker.db import get_agent_session, get_session_trace, init_db


class TestCareerAgentBrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_brain_initialization(self):
        session_id = str(uuid.uuid4())
        brain = CareerAgentBrain(session_id=session_id, target_url="http://localhost:8115/static/test_forms/form_a.html")
        self.assertEqual(brain.session_id, session_id)
        self.assertEqual(brain.mode, "SUPERVISED")
        self.assertEqual(brain.max_steps, 25)

    @patch("agents.tool_system.ToolRegistry.execute_tool")
    def test_react_loop_execution_with_fallback(self, mock_tool):
        # Mock tool responses:
        # Step 1: browser_open_page -> success
        # Step 2: browser_inspect_page -> returns elements
        # Step 1: browser_open_page -> success
        # Step 2: browser_inspect_page -> finds interactive element
        # Step 3: candidate_classify_form -> classified elements
        # Step 4: candidate_verify_form -> valid verification
        # Step 5: request_human_approval -> stops
        mock_tool.side_effect = [
            {"success": True, "result": {"loaded": True}},
            {"success": True, "result": {
                "observation": {
                    "interactive_elements": [
                        {"element_id": "elem_1", "tag": "input", "type": "email", "label": "Email"}
                    ]
                }
            }},
            {"success": True, "result": {"classified_elements": []}},
            {"success": True, "result": {
                "is_valid": True,
                "can_submit": True,
                "total_fields_checked": 1,
                "summary": "All 1 fields verified."
            }}
        ]

        session_id = str(uuid.uuid4())
        brain = CareerAgentBrain(
            session_id=session_id,
            target_url="http://localhost:8115/static/test_forms/form_a.html",
            mode="SUPERVISED",
            max_steps=5
        )

        # Force heuristic decisions by mocking _call_llm_decision to call _heuristic_fallback_decision
        with patch.object(brain, '_call_llm_decision', side_effect=brain._heuristic_fallback_decision):
            result = brain.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")
        self.assertIsNotNone(result.get("approval_token"))

        # Verify database records
        session = get_agent_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["state"], "WAITING_FOR_USER")

        trace = get_session_trace(session_id)
        self.assertGreaterEqual(len(trace), 3)
        step_names = [s["tool_name"] for s in trace]
        self.assertIn("browser_open_page", step_names)
        self.assertIn("browser_inspect_page", step_names)
        self.assertIn("request_human_approval", step_names)

    @patch("agents.tool_system.ToolRegistry.execute_tool")
    def test_react_loop_max_steps_limit(self, mock_tool):
        mock_tool.return_value = {"success": True, "result": {}}

        session_id = str(uuid.uuid4())
        brain = CareerAgentBrain(
            session_id=session_id,
            target_url="http://localhost:8115/test",
            max_steps=2
        )

        # Mock LLM to return a non-terminal action continuously
        dummy_decision = {
            "thought": "Keep scrolling",
            "action": "browser_scroll",
            "arguments": {"direction": "down"}
        }

        with patch.object(brain, '_call_llm_decision', return_value=dummy_decision):
            result = brain.run()

        self.assertFalse(result["success"])
        self.assertEqual(result["state"], "FAILED")
        self.assertIn("exceeded maximum step limit", result["error"])

    @patch("agents.tool_system.ToolRegistry.execute_tool")
    def test_modal_entry_button_flow(self, mock_tool):
        # Test realistic job board flow (SuperJob, HH, Habr):
        # 1. browser_open_page -> ok
        # 2. browser_inspect_page -> returns only "Откликнуться" button
        # 3. candidate_classify_form -> classified as APPLY_ENTRY_BUTTON
        # 4. browser_click_element -> clicks "Откликнуться"
        # 5. browser_inspect_page -> observes opened modal with textarea
        # 6. candidate_classify_form -> classified as COVER_LETTER
        # 7. browser_fill_field -> fills cover letter
        # 8. browser_inspect_page -> re-inspects filled DOM
        # 9. candidate_verify_form -> verifies valid
        mock_tool.side_effect = [
            {"success": True, "result": {"loaded": True}},
            {"success": True, "result": {
                "observation": {
                    "interactive_elements": [
                        {"element_id": "btn_apply", "tag": "button", "button_text": "Откликнуться", "is_submit": True}
                    ]
                }
            }},
            {"success": True, "result": {
                "classified_elements": [
                    {"element_id": "btn_apply", "category": "APPLY_ENTRY_BUTTON", "action": "click", "label": "Откликнуться"}
                ]
            }},
            {"success": True, "result": {"clicked": True}},
            {"success": True, "result": {
                "observation": {
                    "interactive_elements": [
                        {"element_id": "txt_letter", "tag": "textarea", "label": "Сопроводительное письмо", "current_value": ""},
                        {"element_id": "btn_send", "tag": "button", "button_text": "Отправить отклик", "is_submit": True}
                    ]
                }
            }},
            {"success": True, "result": {
                "classified_elements": [
                    {"element_id": "txt_letter", "category": "COVER_LETTER", "action": "generate_cover_letter", "label": "Сопроводительное письмо"},
                    {"element_id": "btn_send", "category": "SUBMIT_BUTTON", "action": "submit_gate", "label": "Отправить отклик"}
                ]
            }},
            {"success": True, "result": {"applied_value": "Письмо"}},
            {"success": True, "result": {
                "observation": {
                    "interactive_elements": [
                        {"element_id": "txt_letter", "tag": "textarea", "label": "Сопроводительное письмо", "current_value": "Письмо"}
                    ]
                }
            }},
            {"success": True, "result": {
                "is_valid": True,
                "can_submit": True,
                "total_fields_checked": 1,
                "summary": "1 field verified."
            }}
        ]

        session_id = str(uuid.uuid4())
        brain = CareerAgentBrain(
            session_id=session_id,
            target_url="https://russia.superjob.ru/vakansii/frontend-12345",
            mode="SUPERVISED",
            max_steps=12
        )

        with patch.object(brain, '_call_llm_decision', side_effect=brain._heuristic_fallback_decision):
            result = brain.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")
        self.assertIsNotNone(result.get("approval_token"))

        trace = get_session_trace(session_id)
        step_names = [s["tool_name"] for s in trace]
        self.assertIn("browser_open_page", step_names)
        self.assertIn("browser_click_element", step_names)
        self.assertIn("browser_fill_field", step_names)
        self.assertIn("candidate_verify_form", step_names)
        self.assertIn("request_human_approval", step_names)

    @patch("agents.tool_system.ToolRegistry.execute_tool")
    def test_auth_barrier_detection_halts_cleanly(self, mock_tool):
        # Test auth wall detection (e.g. HH.ru login or Habr login):
        mock_tool.side_effect = [
            {"success": True, "result": {"loaded": True}},
            {"success": True, "result": {
                "observation": {
                    "auth_required": True,
                    "auth_reason": "Требуется вход в аккаунт на HH.ru",
                    "interactive_elements": []
                }
            }}
        ]

        session_id = str(uuid.uuid4())
        brain = CareerAgentBrain(
            session_id=session_id,
            target_url="https://hh.ru/vacancy/999999",
            mode="SUPERVISED",
            max_steps=5
        )

        with patch.object(brain, '_call_llm_decision', side_effect=brain._heuristic_fallback_decision):
            result = brain.run()

        self.assertFalse(result["success"])
        self.assertEqual(result["state"], "ERROR")
        self.assertIn("Требуется вход в аккаунт на HH.ru", result["error"])


if __name__ == '__main__':
    unittest.main()
