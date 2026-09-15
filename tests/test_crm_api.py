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
                self.assertGreater(v["score"], 0)
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

if __name__ == "__main__":
    unittest.main()
