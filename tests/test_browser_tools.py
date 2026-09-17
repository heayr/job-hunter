import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.tool_system import ToolRegistry, ToolPermission


class TestBrowserTools(unittest.TestCase):

    def test_browser_tools_registered(self):
        registered_names = [t["name"] for t in ToolRegistry.list_tools()]
        expected_tools = [
            "browser_open_page",
            "browser_inspect_page",
            "browser_fill_field",
            "browser_select_option",
            "browser_click_element",
            "browser_upload_cv",
            "browser_scroll"
        ]
        for name in expected_tools:
            self.assertIn(name, registered_names, f"Tool '{name}' must be registered in ToolRegistry")

    def test_browser_tools_permission_is_browser_action(self):
        tool = ToolRegistry.get("browser_fill_field")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.permission, ToolPermission.BROWSER_ACTION)

    def test_argument_validation_missing_required(self):
        # browser_fill_field requires element_id and value
        res = ToolRegistry.execute_tool("browser_fill_field", {"element_id": "elem_1"})
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "VALIDATION_ERROR")
        self.assertIn("value", res["error"])

    def test_argument_validation_invalid_type(self):
        res = ToolRegistry.execute_tool("browser_fill_field", {"element_id": 12345, "value": "test"})
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "VALIDATION_ERROR")

    @patch("agents.browser_bridge.BrowserBridge.open_page")
    def test_browser_open_page_execution(self, mock_open):
        mock_open.return_value = {"success": True, "tab_id": 101, "url": "https://example.com"}
        res = ToolRegistry.execute_tool("browser_open_page", {"url": "https://example.com"})
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["tab_id"], 101)
        mock_open.assert_called_once_with("https://example.com")

    @patch("agents.browser_bridge.BrowserBridge.inspect_page")
    def test_browser_inspect_page_execution(self, mock_inspect):
        mock_inspect.return_value = {
            "success": True,
            "observation": {
                "url": "https://company.com/apply",
                "interactive_elements": [{"element_id": "elem_1", "tag": "input", "label": "Email"}]
            }
        }
        res = ToolRegistry.execute_tool("browser_inspect_page", {})
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["observation"]["url"], "https://company.com/apply")

    @patch("agents.browser_bridge.BrowserBridge.fill_field")
    def test_browser_fill_field_execution(self, mock_fill):
        mock_fill.return_value = {"success": True, "element_id": "elem_1", "applied_value": "test@test.com"}
        res = ToolRegistry.execute_tool("browser_fill_field", {
            "element_id": "elem_1",
            "value": "test@test.com",
            "human_like": True
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["applied_value"], "test@test.com")
        mock_fill.assert_called_once_with(element_id="elem_1", value="test@test.com", human_like=True)

    @patch("agents.browser_bridge.BrowserBridge.upload_file")
    def test_browser_upload_cv_execution(self, mock_upload):
        mock_upload.return_value = {"success": True, "file_name": "my_cv.pdf", "file_size": 1024}
        res = ToolRegistry.execute_tool("browser_upload_cv", {
            "element_id": "elem_file",
            "file_base64": "SGVsbG8gV29ybGQ=",
            "file_name": "my_cv.pdf",
            "mime_type": "application/pdf"
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["file_name"], "my_cv.pdf")


if __name__ == '__main__':
    unittest.main()
