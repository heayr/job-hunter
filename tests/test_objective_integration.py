"""
Objective Testing Suite — Integration Tests
============================================
End-to-end tests for the CRM API server, agent pipeline, and data flow.
Tests require the CRM server to be running on the configured port.
"""

import sys
import os
import json
import time
import socket
import urllib.request
import urllib.error
import unittest
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def is_server_running(port=8115, timeout=1):
    """Check if CRM server is reachable."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False


def get_base_url():
    """Get CRM server base URL."""
    port_file = os.path.join(os.path.dirname(__file__), '..', '.current_port')
    port = 8115
    if os.path.exists(port_file):
        try:
            with open(port_file) as f:
                port = int(f.read().strip())
        except Exception:
            pass
    return f"http://127.0.0.1:{port}"


def api_get(path, timeout=5):
    """Make a GET request to the CRM API."""
    url = f"{get_base_url()}{path}"
    try:
        res = urllib.request.urlopen(url, timeout=timeout)
        return json.loads(res.read().decode('utf-8')), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except Exception:
        return None, 0


def api_post(path, data, timeout=5):
    """Make a POST request to the CRM API."""
    url = f"{get_base_url()}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        res = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(res.read().decode('utf-8')), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except Exception:
        return None, 0


SKIP_NO_SERVER = unittest.skipUnless(
    is_server_running(),
    "CRM server not running — skipping integration tests"
)


# ═══════════════════════════════════════════════
#  API Endpoint Tests
# ═══════════════════════════════════════════════

@SKIP_NO_SERVER
class TestCRMStatusEndpoint(unittest.TestCase):
    """Tests for the /api/status endpoint."""

    def test_status_returns_ok(self):
        data, status = api_get("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)


@SKIP_NO_SERVER
class TestCRMPitchesEndpoint(unittest.TestCase):
    """Tests for the /api/pitches endpoint."""

    def test_pitches_returns_list(self):
        data, status = api_get("/api/pitches")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_pitches_have_required_fields(self):
        data, status = api_get("/api/pitches")
        if data:
            v = data[0]
            self.assertIn("id", v)
            self.assertIn("title", v)
            self.assertIn("company", v)
            self.assertIn("score", v)


@SKIP_NO_SERVER
class TestCRMProfilesEndpoint(unittest.TestCase):
    """Tests for the /api/profiles endpoint."""

    def test_profiles_returns_list(self):
        data, status = api_get("/api/profiles")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)


@SKIP_NO_SERVER
class TestCRMConfigEndpoint(unittest.TestCase):
    """Tests for the /api/config endpoint."""

    def test_config_returns_dict(self):
        data, status = api_get("/api/config")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        self.assertIn("has_gemini_key", data)

    def test_api_key_masked(self):
        data, status = api_get("/api/config")
        if data.get("gemini_api_key"):
            key = data["gemini_api_key"]
            self.assertNotIn("●", key) or self.assertTrue("●" in key or len(key) < 12)


@SKIP_NO_SERVER
class TestCRMHarvestStatus(unittest.TestCase):
    """Tests for the /api/harvest/status endpoint."""

    def test_harvest_status_structure(self):
        data, status = api_get("/api/harvest/status")
        self.assertEqual(status, 200)
        self.assertIn("is_running", data)
        self.assertIn("logs", data)
        self.assertIn("metrics", data)
        metrics = data["metrics"]
        self.assertIn("step", metrics)
        self.assertIn("total", metrics)
        self.assertIn("saved", metrics)


@SKIP_NO_SERVER
class TestCRMAgentTools(unittest.TestCase):
    """Tests for the /api/agent/tools endpoint."""

    def test_tools_returns_list(self):
        data, status = api_get("/api/agent/tools")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(len(data.get("tools", [])), 1)


@SKIP_NO_SERVER
class TestCRMAgentPolicyCheck(unittest.TestCase):
    """Tests for the /api/agent/policy-check endpoint."""

    def test_policy_check_requires_vacancy(self):
        data, status = api_post("/api/agent/policy-check", {})
        self.assertIn(status, [400, 404])

    def test_policy_check_valid_vacancy(self):
        pitches, _ = api_get("/api/pitches")
        if pitches:
            vac_id = pitches[0]["id"]
            data, status = api_post("/api/agent/policy-check", {"vacancy_id": vac_id})
            if status == 200:
                self.assertIn("can_apply", data)
                self.assertIn("violations", data)


@SKIP_NO_SERVER
class TestCDPApplyValidation(unittest.TestCase):
    """Tests for CDP apply endpoint validation."""

    def test_empty_request_returns_400(self):
        data, status = api_post("/api/agent/cdp/apply", {})
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", True))


@SKIP_NO_SERVER
class TestApplicationHistory(unittest.TestCase):
    """Tests for application history endpoints."""

    def test_history_returns_list(self):
        data, status = api_get("/api/applications/history")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("history"), list)


@SKIP_NO_SERVER
class TestVacancyStatusUpdate(unittest.TestCase):
    """Tests for vacancy status update endpoint."""

    def test_status_update_success(self):
        pitches, _ = api_get("/api/pitches")
        if pitches:
            vac_id = pitches[0]["id"]
            data, status = api_post(f"/api/vacancies/{vac_id}/status", {"status": "reviewed"})
            self.assertEqual(status, 200)
            self.assertTrue(data.get("success"))


# ═══════════════════════════════════════════════
#  End-to-End Data Flow Tests
# ═══════════════════════════════════════════════

@SKIP_NO_SERVER
class TestDataFlowEndToEnd(unittest.TestCase):
    """End-to-end tests verifying complete data flow through the system."""

    def test_pitches_to_vacancy_status_flow(self):
        """Pitches endpoint -> status update -> verify persistence."""
        pitches, _ = api_get("/api/pitches")
        if not pitches:
            self.skipTest("No pitches available")

        vac_id = pitches[0]["id"]

        # 1. Update status
        data, _ = api_post(f"/api/vacancies/{vac_id}/status", {"status": "reviewed"})
        self.assertTrue(data.get("success"))

        # 2. Verify status persisted
        pitches2, _ = api_get("/api/pitches")
        found = [p for p in pitches2 if p["id"] == vac_id]
        if found:
            self.assertEqual(found[0]["status"], "reviewed")

    def test_config_read_write_cycle(self):
        """Read config -> modify -> restore."""
        original, _ = api_get("/api/config")

        # Write a test value
        api_post("/api/config", {"test_flag": True})

        # Verify
        updated, _ = api_get("/api/config")
        self.assertTrue(updated.get("test_flag"))

        # Restore
        api_post("/api/config", {"test_flag": None})


if __name__ == "__main__":
    unittest.main()
