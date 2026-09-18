import unittest
from unittest.mock import MagicMock, patch
from agents.adapters.habr_adapter import HabrCDPAdapter
from agents.cdp_logger import CDPLogger


class TestHabrCDPAdapter(unittest.TestCase):

    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_page = MagicMock()
        self.mock_driver.get_active_page.return_value = self.mock_page
        self.mock_driver.connect.return_value = True
        self.mock_driver.take_screenshot.return_value = {"base64": "fake_img"}
        self.logger = CDPLogger(log_dir="/tmp/test_jh_logs")
        self.adapter = HabrCDPAdapter(driver=self.mock_driver, logger=self.logger)

    def test_cdp_not_connected(self):
        self.mock_driver.connect.return_value = False
        res = self.adapter.apply("https://career.habr.com/vacancies/123", "Привет!")
        self.assertFalse(res["success"])
        self.assertIn("Не удалось подключиться к Chrome", res["error"])

    def test_auth_required_detected(self):
        self.mock_page.url = "https://career.habr.com/users/sign_in"
        res = self.adapter.apply("https://career.habr.com/vacancies/123", "Привет!")
        self.assertFalse(res["success"])
        self.assertTrue(res.get("requires_auth"))

    def test_already_applied_detected(self):
        self.mock_page.url = "https://career.habr.com/vacancies/123"
        # mock auth false
        with patch.object(self.adapter, '_is_auth_required', return_value=False):
            with patch.object(self.adapter, '_is_already_applied', return_value=True):
                res = self.adapter.apply("https://career.habr.com/vacancies/123", "Привет!")
                self.assertTrue(res["success"])
                self.assertTrue(res["already_applied"])

    def test_successful_fill_ready_for_approval(self):
        self.mock_page.url = "https://career.habr.com/vacancies/123"
        self.mock_page.title.return_value = "Frontend Вакансия"

        with patch.object(self.adapter, '_is_auth_required', return_value=False):
            with patch.object(self.adapter, '_is_already_applied', return_value=False):
                with patch.object(self.adapter, '_open_response_modal', return_value=True):
                    with patch.object(self.adapter, '_fill_cover_letter', return_value=True):
                        with patch.object(self.adapter, '_get_filled_letter', return_value="Здравствуйте! Меня зовут Егор."):
                            res = self.adapter.apply(
                                "https://career.habr.com/vacancies/123",
                                "Здравствуйте! Меня зовут Егор.",
                                auto_submit=False
                            )

                            self.assertTrue(res["success"])
                            self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
                            self.assertEqual(res["platform"], "habr")
                            self.assertTrue(len(res["approval_token"]) > 10)
                            self.assertIn("Егор", res["cover_letter_preview"])

    def test_submit_success(self):
        btn_mock = MagicMock()
        btn_mock.count.return_value = 1
        btn_mock.is_visible.return_value = True
        self.mock_page.locator.return_value.first = btn_mock

        res = self.adapter.submit(self.mock_page)
        self.assertTrue(res["success"])
        self.assertTrue(res["submitted"])
        btn_mock.click.assert_called_once()

    def test_cdp_logger_records_events(self):
        self.logger.clear()
        self.logger.log("INFO", "TEST_SUITE", "Test message", {"key": "val"})
        logs = self.logger.get_recent_logs(limit=10)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["source"], "TEST_SUITE")
        self.assertEqual(logs[0]["message"], "Test message")


if __name__ == "__main__":
    unittest.main()
