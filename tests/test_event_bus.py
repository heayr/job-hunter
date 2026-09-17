import unittest
import json
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.event_bus import AgentEventBus, get_event_bus


class TestAgentEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = AgentEventBus()

    def test_publish_and_subscribe(self):
        session_id = "test-session-123"
        q = self.bus.subscribe(session_id)

        self.bus.publish(session_id, "agent.thinking", {"step": 1, "thought": "Testing"})

        # Queue should receive formatted SSE string
        msg = q.get(timeout=1.0)
        self.assertIn("event: agent.thinking\n", msg)
        self.assertIn('"thought": "Testing"', msg)
        self.assertIn(session_id, msg)

        self.bus.unsubscribe(session_id, q)

    def test_wildcard_subscription(self):
        q_all = self.bus.subscribe("*")

        self.bus.publish("session-a", "agent.started", {"mode": "SUPERVISED"})
        msg_a = q_all.get(timeout=1.0)
        self.assertIn("session-a", msg_a)

        self.bus.publish("session-b", "browser.field_filled", {"element": "email"})
        msg_b = q_all.get(timeout=1.0)
        self.assertIn("session-b", msg_b)

        self.bus.unsubscribe("*", q_all)

    def test_unsubscribe(self):
        session_id = "test-unsub"
        q = self.bus.subscribe(session_id)
        self.bus.unsubscribe(session_id, q)

        self.bus.publish(session_id, "agent.thinking", {"step": 2})
        self.assertTrue(q.empty())


if __name__ == '__main__':
    unittest.main()
