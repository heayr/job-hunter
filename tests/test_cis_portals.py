import unittest
from unittest.mock import MagicMock, patch
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
        adapter._detect_redirect = MagicMock(return_value=None)
        adapter._fill_cover_letter = MagicMock(return_value=True)

        res = adapter.apply("https://superjob.ru/vakansii/123.html", "Dear team")
        self.assertTrue(res["success"])
        self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
        self.assertEqual(res["platform"], "superjob")
        self.assertTrue(bool(res["approval_token"]))

    def test_superjob_adapter_detects_redirect_to_external_ats(self):
        adapter = SuperJobCDPAdapter(driver=self.mock_driver)
        adapter._is_already_applied = MagicMock(return_value=False)
        adapter._is_auth_required = MagicMock(return_value=False)
        adapter._open_response_modal = MagicMock(return_value=True)
        adapter._detect_redirect = MagicMock(return_value="https://job.pik.ru/about")
        adapter._handle_external_ats = MagicMock(return_value={
            "success": True,
            "platform": "superjob_external_ats",
            "stage": "READY_FOR_APPROVAL",
            "external_ats_url": "https://job.pik.ru/about",
            "filled_count": 4,
            "approval_token": "mock_token"
        })

        res = adapter.apply("https://superjob.ru/vakansii/123.html", "Dear team")
        self.assertTrue(res["success"])
        self.assertEqual(res["platform"], "superjob_external_ats")
        self.assertEqual(res["external_ats_url"], "https://job.pik.ru/about")
        adapter._handle_external_ats.assert_called_once()

    def test_detect_redirect_returns_url_on_domain_change(self):
        adapter = SuperJobCDPAdapter(driver=self.mock_driver)
        self.mock_page.url = "https://job.pik.ru/about"
        result = adapter._detect_redirect(self.mock_page, "https://superjob.ru/vakansii/123.html", "superjob.ru", wait_ms=500)
        self.assertEqual(result, "https://job.pik.ru/about")

    def test_detect_redirect_returns_none_when_staying_on_superjob(self):
        adapter = SuperJobCDPAdapter(driver=self.mock_driver)
        self.mock_page.url = "https://superjob.ru/response/123"
        result = adapter._detect_redirect(self.mock_page, "https://superjob.ru/vakansii/123.html", "superjob.ru", wait_ms=500)
        self.assertIsNone(result)

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
