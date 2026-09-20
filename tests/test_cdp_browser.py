import unittest
from unittest.mock import MagicMock, patch
import os
import base64

from agents.cdp_browser import CDPBrowserDriver, SEMANTIC_INSPECTION_JS


class TestCDPBrowserDriver(unittest.TestCase):
    def test_singleton(self):
        d1 = CDPBrowserDriver.get_instance()
        d2 = CDPBrowserDriver.get_instance()
        self.assertIs(d1, d2)

    def test_cdp_available_when_offline(self):
        driver = CDPBrowserDriver()
        # Port 9222 is closed initially, so is_cdp_available should safely return False
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            self.assertFalse(driver.is_cdp_available())

    def test_atomic_actions_mocked(self):
        driver = CDPBrowserDriver()
        mock_page = MagicMock()
        mock_page.url = "https://hh.ru/vacancy/123456"
        mock_page.title.return_value = "Python Developer - HH.ru"
        mock_page.evaluate.return_value = {
            "url": "https://hh.ru/vacancy/123456",
            "title": "Python Developer",
            "elements_count": 2,
            "elements": [
                {"element_id": "elem_1", "tag": "textarea", "type": "textarea", "label": "Сопроводительное письмо"},
                {"element_id": "elem_2", "tag": "button", "type": "submit", "label": "Откликнуться"}
            ]
        }

        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.first = mock_locator

        with patch.object(driver, "connect", return_value=True), \
             patch.object(driver, "get_active_page", return_value=mock_page):
            # 1. open_page
            res_open = driver.open_page("https://hh.ru/vacancy/123456")
            self.assertTrue(res_open["success"])
            mock_page.goto.assert_called_with("https://hh.ru/vacancy/123456", wait_until="domcontentloaded", timeout=30000)

            # 2. inspect_page
            res_inspect = driver.inspect_page()
            self.assertTrue(res_inspect["success"])
            self.assertEqual(res_inspect["elements_count"], 2)

            # 3. fill_field
            res_fill = driver.fill_field("elem_1", "Здравствуйте! Вот мой отклик.")
            self.assertTrue(res_fill["success"])
            mock_locator.fill.assert_called_with("Здравствуйте! Вот мой отклик.")

            # 4. click_element
            res_click = driver.click_element("elem_2")
            self.assertTrue(res_click["success"])
            mock_locator.click.assert_called()

            # 5. upload_file
            fake_pdf = base64.b64encode(b"%PDF-1.4 fake pdf content").decode("utf-8")
            res_upload = driver.upload_file("elem_file", fake_pdf, "resume.pdf")
            self.assertTrue(res_upload["success"])
            mock_locator.set_input_files.assert_called()

            # 6. take_screenshot
            mock_page.screenshot.return_value = b"fake_png_bytes"
            res_shot = driver.take_screenshot()
            self.assertTrue(res_shot["success"])
            self.assertIn("base64", res_shot)

    def test_browser_bridge_delegates_to_cdp(self):
        from agents.browser_bridge import BrowserBridge
        bridge = BrowserBridge()
        mock_cdp = MagicMock()
        mock_cdp.open_page.return_value = {"success": True, "url": "https://hh.ru", "via": "cdp"}
        mock_cdp.inspect_page.return_value = {"success": True, "elements": [], "via": "cdp"}

        with patch.object(bridge, "_get_cdp", return_value=mock_cdp):
            self.assertTrue(bridge.is_connected())
            res = bridge.open_page("https://hh.ru")
            self.assertEqual(res.get("via"), "cdp")
            mock_cdp.open_page.assert_called_with("https://hh.ru")

            res_inspect = bridge.inspect_page()
            self.assertEqual(res_inspect.get("via"), "cdp")
            mock_cdp.inspect_page.assert_called()

    def test_crm_tab_protected(self):
        driver = CDPBrowserDriver()
        mock_crm_page = MagicMock()
        mock_crm_page.url = "http://127.0.0.1:8115/"
        mock_crm_page.title.return_value = "Job Hunter CRM V3"

        mock_new_page = MagicMock()
        mock_new_page.url = "about:blank"
        mock_new_page.title.return_value = "New Tab"

        mock_context = MagicMock()
        mock_context.pages = [mock_crm_page]
        mock_context.new_page.return_value = mock_new_page

        driver._context = mock_context
        with patch.object(driver, "connect", return_value=True):
            active_p = driver.get_active_page(avoid_crm=True)
            self.assertIsNot(active_p, mock_crm_page)
            self.assertIs(active_p, mock_new_page)
            mock_context.new_page.assert_called_once()


if __name__ == "__main__":
    unittest.main()
