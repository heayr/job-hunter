import unittest
from unittest.mock import MagicMock
from agents.adapters.superjob_adapter import SuperJobCDPAdapter
from agents.adapters.rabota_adapter import RabotaRuCDPAdapter


class TestCISPortalsAdapters(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_driver.connect.return_value = True
        self.mock_page = MagicMock()
        self.mock_page.url = "https://superjob.ru/vakansii/frontend-developer-123.html"
        self.mock_page.title.return_value = "Frontend Developer — SuperJob"
        self.mock_driver.get_active_page.return_value = self.mock_page
        self.mock_driver.take_screenshot.return_value = {"base64": "mock_data"}

    def test_superjob_adapter_already_applied(self):
        adapter = SuperJobCDPAdapter(driver=self.mock_driver)
        adapter._is_already_applied = MagicMock(return_value=True)
        res = adapter.apply("https://superjob.ru/vakansii/123.html", "Hello")
        self.assertTrue(res["success"])
        self.assertTrue(res.get("already_applied"))

    def test_superjob_adapter_ready_for_approval(self):
        adapter = SuperJobCDPAdapter(driver=self.mock_driver)
        adapter._is_already_applied = MagicMock(return_value=False)
        adapter._is_auth_required = MagicMock(return_value=False)
        adapter._open_response_modal = MagicMock(return_value=True)
        adapter._fill_cover_letter = MagicMock(return_value=True)

        res = adapter.apply("https://superjob.ru/vakansii/123.html", "Dear team")
        self.assertTrue(res["success"])
        self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
        self.assertEqual(res["platform"], "superjob")
        self.assertTrue(bool(res["approval_token"]))

    def test_rabota_adapter_ready_for_approval(self):
        self.mock_page.url = "https://rabota.ru/vacancy/123"
        self.mock_page.title.return_value = "Frontend Developer — Rabota.ru"
        adapter = RabotaRuCDPAdapter(driver=self.mock_driver)
        adapter._is_already_applied = MagicMock(return_value=False)
        adapter._open_response_modal = MagicMock(return_value=True)
        adapter._fill_cover_letter = MagicMock(return_value=True)

        res = adapter.apply("https://rabota.ru/vacancy/123", "Dear team")
        self.assertTrue(res["success"])
        self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
        self.assertEqual(res["platform"], "rabota_ru")
        self.assertTrue(bool(res["approval_token"]))


if __name__ == "__main__":
    unittest.main()
