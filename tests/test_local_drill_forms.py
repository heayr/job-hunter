import unittest
import os
import sys
import uuid
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tracker.db import (
    init_db, get_agent_session, get_provenance_links,
    get_db_connection, save_vacancy
)
from agents.tool_system import ToolRegistry
from agents.browser_bridge import get_browser_bridge
from agents.agent_brain import CareerAgentBrain


class TestLocalDrillForms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self._bridge = get_browser_bridge()
        self._orig_cdp = getattr(self._bridge, 'enable_cdp', True)
        self._bridge.enable_cdp = False

    def tearDown(self):
        self._bridge.enable_cdp = self._orig_cdp

    def _simulate_extension_worker(self, form_elements: list, stop_event: threading.Event):
        """Simulates Chrome Extension content script answering DOM actions."""
        bridge = get_browser_bridge()
        while not stop_event.is_set():
            cmd = bridge.get_next_pending_command()
            if not cmd:
                time.sleep(0.02)
                continue

            action = cmd["action"]
            cmd_id = cmd["command_id"]
            params = cmd.get("params", {})

            if action == "OPEN_PAGE":
                bridge.complete_command(cmd_id, {"success": True, "url": params.get("url")})
            elif action == "INSPECT_PAGE":
                bridge.complete_command(cmd_id, {
                    "success": True,
                    "observation": {
                        "interactive_elements": form_elements,
                        "url": "http://localhost:8115/static/test_forms/form_test.html"
                    }
                })
            elif action in ("FILL_FIELD", "SELECT_OPTION", "UPLOAD_FILE", "CLICK_ELEMENT"):
                # Mark element as filled in DOM
                eid = params.get("element_id") or params.get("elem_id")
                val = params.get("value") or params.get("option")
                for el in form_elements:
                    if el.get("element_id") == eid:
                        if action == "UPLOAD_FILE":
                            el["has_file"] = True
                            el["value"] = params.get("file_name", "cv.txt")
                        else:
                            el["value"] = val
                bridge.complete_command(cmd_id, {"success": True, "element_id": eid})
            else:
                bridge.complete_command(cmd_id, {"success": True})

    def test_end_to_end_drill_form_a(self):
        """Tests end-to-end ReAct loop on Form A (Standard Single Page Form)."""
        form_elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "First Name *", "value": "", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "text", "label": "Last Name *", "value": "", "required": True},
            {"element_id": "elem_3", "tag": "input", "type": "email", "label": "Email Address *", "value": "", "required": True},
            {"element_id": "elem_4", "tag": "input", "type": "tel", "label": "Phone Number", "value": "", "required": False},
            {"element_id": "elem_5", "tag": "input", "type": "file", "label": "Resume / CV *", "value": "", "has_file": False, "required": True},
            {"element_id": "elem_6", "tag": "textarea", "type": "textarea", "label": "Cover Letter", "value": "", "required": False},
            {"element_id": "elem_7", "tag": "button", "type": "submit", "label": "Submit Application"}
        ]

        stop_worker = threading.Event()
        worker = threading.Thread(target=self._simulate_extension_worker, args=(form_elements, stop_worker), daemon=True)
        worker.start()

        try:
            vac_id = f"vac_drill_a_{uuid.uuid4().hex[:6]}"
            save_vacancy({
                "id": vac_id,
                "title": "Senior Frontend Engineer",
                "company": "Acme Corp",
                "url": "http://localhost:8115/static/test_forms/form_a.html",
                "status": "new"
            })

            brain = CareerAgentBrain(
                vacancy_id=vac_id,
                target_url="http://localhost:8115/static/test_forms/form_a.html",
                mode="SUPERVISED",
                max_steps=15
            )
            # Ensure deterministic execution in unit test
            brain._call_llm_decision = brain._heuristic_fallback_decision

            # Run autonomous agent loop
            result = brain.run()

            # In SUPERVISED mode, agent must halt at WAITING_FOR_USER_APPROVAL
            self.assertTrue(result["success"])
            self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")
            self.assertIn("approval_token", result)
            approval_token = result["approval_token"]

            # Verify that CV provenance links were generated and stored
            links = get_provenance_links(brain.session_id)
            self.assertGreater(len(links), 0)

            # Verify that all required fields were filled in simulated DOM
            self.assertTrue(bool(form_elements[0]["value"])) # First Name
            self.assertTrue(bool(form_elements[1]["value"])) # Last Name
            self.assertTrue("@" in form_elements[2]["value"]) # Email
            self.assertTrue(form_elements[4]["has_file"])    # CV uploaded

            # Verify that user approval submits the form and syncs CRM
            submit_res = ToolRegistry.execute_tool("browser_submit_application", {
                "session_id": brain.session_id,
                "approval_token": approval_token,
                "element_id": "elem_7"
            })
            self.assertTrue(submit_res["success"])
            self.assertTrue(submit_res["result"]["submitted"])

            # Verify session is COMPLETED in DB
            sess = get_agent_session(brain.session_id)
            self.assertEqual(sess["state"], "COMPLETED")

            # Verify CRM vacancy status is 'sent'
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT status FROM vacancies WHERE id = ?", (vac_id,))
            v_row = cur.fetchone()
            self.assertEqual(v_row["status"], "sent")
            conn.close()

        finally:
            stop_worker.set()
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM pitches WHERE vacancy_id = ?", (vac_id,))
                cur.execute("DELETE FROM agent_sessions WHERE vacancy_id = ?", (vac_id,))
                cur.execute("DELETE FROM vacancies WHERE id = ?", (vac_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def test_end_to_end_drill_form_b_dynamic_react(self):
        """Tests end-to-end ReAct loop on Form B (Dynamic React-like controlled form)."""
        form_elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Full Name *", "value": "", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Work Email *", "value": "", "required": True},
            {"element_id": "elem_3", "tag": "select", "type": "select", "label": "Primary Tech Stack", "value": "", "options": ["react_ts", "vue_ts"]},
            {"element_id": "elem_4", "tag": "input", "type": "radio", "label": "Are you legally authorized to work remotely?", "value": "yes"},
            {"element_id": "elem_5", "tag": "input", "type": "file", "label": "Attach Resume (PDF)", "value": "", "has_file": False},
            {"element_id": "elem_6", "tag": "button", "type": "button", "label": "Apply Now"}
        ]

        stop_worker = threading.Event()
        worker = threading.Thread(target=self._simulate_extension_worker, args=(form_elements, stop_worker), daemon=True)
        worker.start()

        try:
            vac_id = f"vac_drill_b_{uuid.uuid4().hex[:6]}"
            brain = CareerAgentBrain(
                vacancy_id=vac_id,
                target_url="http://localhost:8115/static/test_forms/form_b.html",
                mode="SUPERVISED",
                max_steps=15
            )
            brain._call_llm_decision = brain._heuristic_fallback_decision

            result = brain.run()
            self.assertTrue(result["success"])
            self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")

            # Check full name and work email filled
            self.assertTrue(len(form_elements[0]["value"].split()) >= 2)
            self.assertTrue("@" in form_elements[1]["value"])
            # Check CV uploaded
            self.assertTrue(form_elements[4]["has_file"])

        finally:
            stop_worker.set()

    def test_end_to_end_drill_form_c_custom_questions(self):
        """Tests end-to-end ReAct loop on Form C (Form with custom screening questions)."""
        form_elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Full Name *", "value": "", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Email *", "value": "", "required": True},
            {"element_id": "elem_3", "tag": "textarea", "type": "textarea", "label": "Describe your experience with web performance and page load speed *", "value": "", "required": True},
            {"element_id": "elem_4", "tag": "button", "type": "submit", "label": "Submit"}
        ]

        stop_worker = threading.Event()
        worker = threading.Thread(target=self._simulate_extension_worker, args=(form_elements, stop_worker), daemon=True)
        worker.start()

        try:
            vac_id = f"vac_drill_c_{uuid.uuid4().hex[:6]}"
            brain = CareerAgentBrain(
                vacancy_id=vac_id,
                target_url="http://localhost:8115/static/test_forms/form_c.html",
                mode="SUPERVISED",
                max_steps=15
            )
            brain._call_llm_decision = brain._heuristic_fallback_decision

            result = brain.run()
            self.assertTrue(result["success"])
            self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")

            # Check question was answered with grounded engineering evidence
            q_answer = form_elements[2]["value"]
            self.assertTrue(len(q_answer) > 20)

        finally:
            stop_worker.set()

    def test_end_to_end_drill_form_d_unorthodox(self):
        """Tests end-to-end ReAct loop on Form D (Unorthodox layout without standard form tags)."""
        form_elements = [
            {"element_id": "elem_1", "tag": "input", "type": "text", "label": "Applicant Name", "value": "", "required": False},
            {"element_id": "elem_2", "tag": "input", "type": "email", "label": "Direct Contact Email", "value": "", "required": False},
            {"element_id": "elem_3", "tag": "input", "type": "url", "label": "LinkedIn Profile URL", "value": "", "required": False},
            {"element_id": "elem_4", "tag": "input", "type": "file", "label": "Curriculum Vitae", "value": "", "has_file": False, "required": False},
            {"element_id": "elem_5", "tag": "div", "type": "button", "label": "Dispatch Candidacy"}
        ]

        stop_worker = threading.Event()
        worker = threading.Thread(target=self._simulate_extension_worker, args=(form_elements, stop_worker), daemon=True)
        worker.start()

        try:
            vac_id = f"vac_drill_d_{uuid.uuid4().hex[:6]}"
            brain = CareerAgentBrain(
                vacancy_id=vac_id,
                target_url="http://localhost:8115/static/test_forms/form_d.html",
                mode="SUPERVISED",
                max_steps=15
            )
            brain._call_llm_decision = brain._heuristic_fallback_decision

            result = brain.run()
            self.assertTrue(result["success"])
            self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")

            # Check fields were mapped and filled despite unorthodox container
            self.assertTrue(bool(form_elements[0]["value"]))  # Name
            self.assertTrue("@" in form_elements[1]["value"]) # Email
            self.assertTrue("linkedin" in form_elements[2]["value"]) # LinkedIn
            self.assertTrue(form_elements[3]["has_file"])     # CV uploaded

        finally:
            stop_worker.set()

    def test_end_to_end_drill_form_e_salary_and_screening(self):
        """Tests end-to-end ReAct loop on Form E (Salary range, outage protocol, custom question)."""
        form_elements = [
            {"element_id": "elem_1", "tag": "input", "type": "email", "label": "Candidate Email *", "value": "", "required": True},
            {"element_id": "elem_2", "tag": "input", "type": "number", "label": "Expected Monthly Salary (USD) *", "value": "", "required": True},
            {"element_id": "elem_3", "tag": "textarea", "type": "textarea", "label": "Describe your most difficult production outage and how you resolved it *", "value": "", "required": True},
            {"element_id": "elem_4", "tag": "textarea", "type": "textarea", "label": "Do you have prior experience with custom WebRTC video pipelines? *", "value": "", "required": True},
            {"element_id": "elem_5", "tag": "button", "type": "button", "label": "Submit Responses"}
        ]

        stop_worker = threading.Event()
        worker = threading.Thread(target=self._simulate_extension_worker, args=(form_elements, stop_worker), daemon=True)
        worker.start()

        try:
            vac_id = f"vac_drill_e_{uuid.uuid4().hex[:6]}"
            brain = CareerAgentBrain(
                vacancy_id=vac_id,
                target_url="http://localhost:8115/static/test_forms/form_e.html",
                mode="SUPERVISED",
                max_steps=15
            )
            brain._call_llm_decision = brain._heuristic_fallback_decision

            result = brain.run()
            self.assertTrue(result["success"])
            self.assertEqual(result["state"], "WAITING_FOR_USER_APPROVAL")

            # Check email filled
            self.assertTrue("@" in form_elements[0]["value"])

            # Check salary filled with valid USD range (e.g. 5000)
            sal_val = int(form_elements[1]["value"])
            self.assertGreaterEqual(sal_val, 1000)
            self.assertLessEqual(sal_val, 25000)

            # Check outage question answered with protocol
            outage_ans = form_elements[2]["value"].lower()
            self.assertTrue(any(w in outage_ans for w in ["мониторинг", "откат", "логи", "post-mortem", "rollback", "incident", "production"]))

            # Check unverified question answered with honest adjacent tech (zero hallucination)
            unverified_ans = form_elements[3]["value"].lower()
            self.assertTrue(any(w in unverified_ans for w in ["нет прямого", "do not claim direct", "do not have direct", "no direct", "освоить", "ramp up", "готов"]))

        finally:
            stop_worker.set()


if __name__ == '__main__':
    unittest.main()

