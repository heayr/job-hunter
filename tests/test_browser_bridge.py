import unittest
import threading
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.browser_bridge import BrowserBridge, get_browser_bridge


class TestBrowserBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = BrowserBridge()
        self.bridge._init_bridge(enable_cdp=False)

    def test_extension_liveness_detection(self):
        self.assertFalse(self.bridge.is_connected())
        self.bridge.mark_extension_alive()
        self.assertTrue(self.bridge.is_connected())

    def test_command_enqueue_and_poll(self):
        # Enqueue in background thread to avoid blocking
        result_holder = []

        def client_thread():
            res = self.bridge.send_command("INSPECT_PAGE", {}, timeout=2.0)
            result_holder.append(res)

        t = threading.Thread(target=client_thread)
        t.start()

        # Simulate extension polling
        time.sleep(0.05)
        cmd = self.bridge.get_next_pending_command()
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd["action"], "INSPECT_PAGE")

        # Simulate extension completing the command
        completed = self.bridge.complete_command(cmd["command_id"], {
            "success": True,
            "observation": {"url": "http://localhost/test", "interactive_elements": []}
        })
        self.assertTrue(completed)

        t.join(timeout=1.0)
        self.assertEqual(len(result_holder), 1)
        self.assertTrue(result_holder[0]["success"])
        self.assertEqual(result_holder[0]["observation"]["url"], "http://localhost/test")

    def test_command_timeout(self):
        # Send command with very short timeout and no extension response
        res = self.bridge.send_command("FILL_FIELD", {"element_id": "elem_1", "value": "test"}, timeout=0.1)
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "TIMEOUT")
        self.assertIn("timed out", res["error"])

    def test_convenience_methods(self):
        # Verify helper methods form correct command structure
        cmd_received = []

        def worker():
            cmd = self.bridge.get_next_pending_command()
            while not cmd:
                time.sleep(0.02)
                cmd = self.bridge.get_next_pending_command()
            cmd_received.append(cmd)
            self.bridge.complete_command(cmd["command_id"], {"success": True, "handled": True})

        t = threading.Thread(target=worker)
        t.start()

        res = self.bridge.fill_field("elem_99", "Egor", human_like=True, timeout=2.0)
        t.join(timeout=1.0)

        self.assertTrue(res["success"])
        self.assertEqual(len(cmd_received), 1)
        self.assertEqual(cmd_received[0]["action"], "FILL_FIELD")
        self.assertEqual(cmd_received[0]["params"]["element_id"], "elem_99")
        self.assertEqual(cmd_received[0]["params"]["value"], "Egor")
        self.assertTrue(cmd_received[0]["params"]["human_like"])


if __name__ == '__main__':
    unittest.main()
