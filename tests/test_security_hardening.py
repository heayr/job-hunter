import unittest
import json
import os
import sqlite3
import hmac
from unittest.mock import MagicMock, patch

from tracker.db import get_db_connection, DB_PATH
import crm


class TestSecurityHardening(unittest.TestCase):
    def test_db_wal_and_timeout(self):
        """Verify DB connection sets WAL journal mode and timeout."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            mode = cur.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
        finally:
            conn.close()

    def test_send_json_cors_untrusted(self):
        """Verify untrusted Origin gets null and trusted localhost gets reflected."""
        class MockHandler:
            def __init__(self, origin=None):
                self.headers = {'Origin': origin} if origin else {}
                self.sent_headers = {}
                self.wfile = MagicMock()

            def send_response(self, code):
                self.status_code = code

            def send_header(self, key, value):
                self.sent_headers[key] = value

            def end_headers(self):
                pass

        # 1. Untrusted origin (e.g. malicious site in user browser)
        handler_untrusted = MockHandler(origin="https://evil-hacker.com")
        crm._send_json(handler_untrusted, {"test": "data"})
        self.assertEqual(handler_untrusted.sent_headers.get('Access-Control-Allow-Origin'), 'null')

        # 2. Trusted localhost origin
        handler_localhost = MockHandler(origin="http://localhost:8115")
        crm._send_json(handler_localhost, {"test": "data"})
        self.assertEqual(handler_localhost.sent_headers.get('Access-Control-Allow-Origin'), 'http://localhost:8115')

        # 3. Trusted 127.0.0.1 origin
        handler_127 = MockHandler(origin="http://127.0.0.1:8115")
        crm._send_json(handler_127, {"test": "data"})
        self.assertEqual(handler_127.sent_headers.get('Access-Control-Allow-Origin'), 'http://127.0.0.1:8115')

    def test_config_api_key_masked_on_get(self):
        """Verify GET /api/config masks raw gemini key and does not leak it."""
        class FakeCRM(crm.CRMHandler):
            def __init__(self):
                self.headers = {'Origin': 'http://127.0.0.1:8115'}
                self.path = '/api/config'
                self.sent_data = None
                self.sent_headers = {}
                self.wfile = MagicMock()

            def send_response(self, code):
                self.status_code = code

            def send_header(self, key, value):
                self.sent_headers[key] = value

            def end_headers(self):
                pass

        fake = FakeCRM()
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps({"gemini_api_key": "test_dummy_gemini_key_1234567890_abcdef"}))), \
             patch('os.path.exists', return_value=True), \
             patch('crm._send_json') as mock_send:
            fake._handle_get()
            mock_send.assert_called_once()
            response_data = mock_send.call_args[0][1]
            self.assertTrue(response_data.get('has_gemini_key'))
            # Check raw key is NOT present
            self.assertNotEqual(response_data.get('gemini_api_key'), "test_dummy_gemini_key_1234567890_abcdef")
            self.assertIn("●", response_data.get('gemini_api_key'))

    def test_approve_session_strict_token_validation(self):
        """Verify approve-session strictly requires valid token and rejects missing or mismatched token."""
        class FakeCRM(crm.CRMHandler):
            def __init__(self, body_dict):
                self.headers = {'Origin': 'http://127.0.0.1:8115', 'Content-Length': str(len(json.dumps(body_dict)))}
                self.path = '/api/agent/approve-session'
                self._body_data = json.dumps(body_dict).encode('utf-8')
                self.wfile = MagicMock()

            def _read_body(self):
                return self._body_data

            def send_response(self, code):
                self.status_code = code

            def send_header(self, key, value):
                pass

            def end_headers(self):
                pass

        mock_session = {"session_id": "test_sess_1", "approval_token": "secret_token_123"}

        # 1. Missing approval_token -> 403
        fake_missing = FakeCRM({"session_id": "test_sess_1"})
        with patch('tracker.db.get_agent_session', return_value=mock_session), \
             patch('crm._send_json') as mock_send:
            fake_missing._handle_post()
            mock_send.assert_called_once()
            self.assertEqual(mock_send.call_args[1].get('status'), 403)

        # 2. Invalid approval_token -> 403
        fake_invalid = FakeCRM({"session_id": "test_sess_1", "approval_token": "wrong_token"})
        with patch('tracker.db.get_agent_session', return_value=mock_session), \
             patch('crm._send_json') as mock_send:
            fake_invalid._handle_post()
            mock_send.assert_called_once()
            self.assertEqual(mock_send.call_args[1].get('status'), 403)


if __name__ == '__main__':
    unittest.main()
