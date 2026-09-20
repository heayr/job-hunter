import unittest
import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestCRMEndpoints(unittest.TestCase):
    def setUp(self):
        port_file = os.path.join(os.path.dirname(__file__), '..', '.current_port')
        self.port = 8115
        if os.path.exists(port_file):
            try:
                with open(port_file) as pf:
                    self.port = int(pf.read().strip())
            except Exception:
                pass
        self.base_url = f"http://127.0.0.1:{self.port}"

    def test_get_pitches(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/pitches", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            self.assertIsInstance(data, list)
            if data:
                v = data[0]
                self.assertIn("id", v)
                self.assertIn("score", v)
                self.assertGreaterEqual(v["score"], 0)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_get_profiles(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/profiles", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)
            p = data[0]
            self.assertIn("contacts_structured", p)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_get_tailored_cv(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/pitches", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            if not data:
                self.skipTest("No vacancies available in DB")
            v_id = data[0]["id"]
            cv_res = urllib.request.urlopen(f"{self.base_url}/api/vacancies/{v_id}/tailored_cv", timeout=3)
            cv_data = json.loads(cv_res.read().decode('utf-8'))
            self.assertTrue(cv_data.get("success"))
            self.assertIn("resume", cv_data)
            self.assertIn("markdown", cv_data)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_get_runtime_state(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/pitches", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            if not data:
                self.skipTest("No vacancies available in DB")
            v_id = data[0]["id"]
            state_res = urllib.request.urlopen(f"{self.base_url}/api/vacancies/{v_id}/runtime_state", timeout=3)
            state_data = json.loads(state_res.read().decode('utf-8'))
            self.assertTrue(state_data.get("success"))
            self.assertIn("fsm_state", state_data)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_get_agent_tools(self):
        try:
            tools_res = urllib.request.urlopen(f"{self.base_url}/api/agent/tools", timeout=3)
            tools_data = json.loads(tools_res.read().decode('utf-8'))
            self.assertTrue(tools_data.get("success"))
            self.assertIn("tools", tools_data)
            self.assertGreaterEqual(len(tools_data["tools"]), 6)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_get_harvest_status_structure(self):
        try:
            status_res = urllib.request.urlopen(f"{self.base_url}/api/harvest/status", timeout=3)
            status_data = json.loads(status_res.read().decode('utf-8'))
            self.assertIn("is_running", status_data)
            self.assertIn("logs", status_data)
            self.assertIn("metrics", status_data)
            metrics = status_data["metrics"]
            self.assertIn("step", metrics)
            self.assertIn("total", metrics)
            self.assertIn("saved", metrics)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_cdp_apply_endpoint_validation(self):
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/agent/cdp/apply",
                data=json.dumps({}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected 400 for empty request")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            data = json.loads(e.read().decode('utf-8'))
            self.assertFalse(data.get("success"))
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_rate_pitch_endpoint(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/pitches", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            if not data:
                self.skipTest("No vacancies available in DB")
            v_id = data[0]["id"]
            req = urllib.request.Request(
                f"{self.base_url}/api/pitches/rate",
                data=json.dumps({"vacancy_id": v_id, "rating": 1, "pitch_type": "cover_letter"}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            r_res = urllib.request.urlopen(req, timeout=3)
            r_data = json.loads(r_res.read().decode('utf-8'))
            self.assertTrue(r_data.get("success"))
            self.assertEqual(r_data.get("rating"), 1)
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")

    def test_save_pitch_endpoint(self):
        try:
            res = urllib.request.urlopen(f"{self.base_url}/api/pitches", timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            if not data:
                self.skipTest("No vacancies available in DB")
            v_id = data[0]["id"]
            req = urllib.request.Request(
                f"{self.base_url}/api/pitches/save",
                data=json.dumps({"vacancy_id": v_id, "cover_letter": "Custom edited cover letter"}).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )
            s_res = urllib.request.urlopen(req, timeout=3)
            s_data = json.loads(s_res.read().decode('utf-8'))
            self.assertTrue(s_data.get("success"))
        except urllib.error.URLError:
            self.skipTest("CRM server is not running on test port")


if __name__ == "__main__":
    unittest.main()
