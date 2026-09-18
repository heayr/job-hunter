import unittest
from unittest.mock import MagicMock, patch
from agents.adapters.hh_adapter import HeadHunterCDPAdapter


class TestHeadHunterCDPAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.adapter = HeadHunterCDPAdapter(driver=self.mock_driver)
        self.mock_page = MagicMock()
        self.mock_driver.connect.return_value = True
        self.mock_driver.get_active_page.return_value = self.mock_page
        self.mock_driver.take_screenshot.return_value = {"base64": "fake_shot"}

    def test_auth_required_detection(self):
        self.mock_page.url = "https://hh.ru/account/login"
        res = self.adapter.apply("https://hh.ru/vacancy/12345", "Здравствуйте!")
        self.assertFalse(res["success"])
        self.assertTrue(res.get("requires_auth"))

    def test_already_applied_detection(self):
        self.mock_page.url = "https://hh.ru/vacancy/12345"
        with patch.object(self.adapter, "_is_auth_required", return_value=False), \
             patch.object(self.adapter, "_is_already_applied", return_value=True):
            res = self.adapter.apply("https://hh.ru/vacancy/12345", "Здравствуйте!")
            self.assertTrue(res["success"])
            self.assertTrue(res.get("already_applied"))

    def test_successful_form_fill_ready_for_approval(self):
        self.mock_page.url = "https://hh.ru/vacancy/12345"
        self.mock_page.title.return_value = "Python Team Lead"

        with patch.object(self.adapter, "_is_auth_required", return_value=False), \
             patch.object(self.adapter, "_is_already_applied", return_value=False), \
             patch.object(self.adapter, "_open_response_modal", return_value=True), \
             patch.object(self.adapter, "_fill_cover_letter", return_value=True), \
             patch.object(self.adapter, "_get_filled_letter", return_value="Здравствуйте! Я готов."):

            res = self.adapter.apply("https://hh.ru/vacancy/12345", "Здравствуйте! Я готов.", auto_submit=False)
            self.assertTrue(res["success"])
            self.assertEqual(res["stage"], "READY_FOR_APPROVAL")
            self.assertIn("approval_token", res)
            self.assertIn("cover_letter_preview", res)

    def test_submit_action(self):
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.is_visible.return_value = True
        mock_loc.first = mock_loc
        self.mock_page.locator.return_value = mock_loc

        res = self.adapter.submit(self.mock_page)
        self.assertTrue(res["success"])
        self.assertTrue(res.get("submitted"))
        mock_loc.click.assert_called()


if __name__ == "__main__":
    unittest.main()
