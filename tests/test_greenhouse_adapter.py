import unittest
from unittest.mock import MagicMock, patch
from agents.adapters.greenhouse_adapter import GreenhouseCDPAdapter
from agents.cdp_logger import CDPLogger


class TestGreenhouseCDPAdapter(unittest.TestCase):

    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_page = MagicMock()
        self.mock_driver.get_active_page.return_value = self.mock_page
        self.mock_driver.connect.return_value = True
        self.mock_driver.take_screenshot.return_value = {"base64": "fake_img"}
        self.logger = CDPLogger(log_dir="/tmp/test_jh_logs")
        self.adapter = GreenhouseCDPAdapter(driver=self.mock_driver, logger=self.logger)

    def test_cdp_not_connected(self):
        self.mock_driver.connect.return_value = False
        res = self.adapter.apply("https://job-boards.greenhouse.io/gitlab/jobs/123", "Hello")
        self.assertFalse(res["success"])
        self.assertIn("Не удалось подключиться к Chrome", res["error"])

    def test_successful_fill_ready_for_approval(self):
        self.mock_page.url = "https://job-boards.greenhouse.io/gitlab/jobs/123"
        self.mock_page.title.return_value = "Fullstack Engineer at GitLab"

        mock_file_input = MagicMock()
        mock_file_input.count.return_value = 1
        self.mock_page.locator.return_value.first = mock_file_input

        with patch.object(self.adapter, '_fill_first_matching', return_value=True):
            with patch.object(self.adapter, '_get_or_create_sample_resume', return_value="/tmp/fake_resume.pdf"):
                with patch("os.path.exists", return_value=True):
                    res = self.adapter.apply(
                        "https://job-boards.greenhouse.io/gitlab/jobs/123",
                        "Dear GitLab Team, I'm excited to apply!",
                        auto_submit=False
                    )

                    self.assertTrue(res["success"])
                    self.assertEqual(res["platform"], "greenhouse")
                    self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
                    self.assertIn("Egor", res["candidate"])
                    self.assertTrue(len(res["approval_token"]) > 10)

    def test_submit_success(self):
        btn_mock = MagicMock()
        btn_mock.count.return_value = 1
        btn_mock.is_visible.return_value = True
        self.mock_page.locator.return_value.first = btn_mock

        res = self.adapter.submit(self.mock_page)
        self.assertTrue(res["success"])
        self.assertTrue(res["submitted"])
        btn_mock.click.assert_called_once()


if __name__ == "__main__":
    unittest.main()
