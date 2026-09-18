import time
import secrets
from typing import Dict, Any, Optional
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger


class RabotaRuCDPAdapter:
    """
    CDP Adapter for applying to Rabota.ru vacancies.
    Leverages user's authenticated Chrome session via CDP.
    Supports modal opening, cover letter injection, and human approval checkpoints.
    """

    def __init__(self, driver: Optional[CDPBrowserDriver] = None, logger: Optional[CDPLogger] = None):
        self.driver = driver or CDPBrowserDriver.get_instance()
        self.logger = logger or CDPLogger.get_instance()

    def apply(self, vacancy_url: str, cover_letter: str = "", auto_submit: bool = False) -> Dict[str, Any]:
        """
        Executes Rabota.ru application flow:
        1. Opens vacancy page.
        2. Checks login / already applied status.
        3. Clicks 'Откликнуться'.
        4. Injects Cover Letter.
        5. Returns READY_FOR_APPROVAL checkpoint with screenshot.
        """
        self.logger.log("INFO", "RABOTA_ADAPTER", f"Starting apply flow for: {vacancy_url}")
        if not self.driver.connect():
            err_msg = "Не удалось подключиться к Chrome через CDP на порту 9222. Запусти Chrome через ./launch_chrome.sh."
            self.logger.log("ERROR", "RABOTA_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        page = self.driver.get_active_page()
        self.logger.attach_to_page(page)

        # 1. Open page
        try:
            current_url = page.url
            if vacancy_url.rstrip("/") not in current_url:
                page.goto(vacancy_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1200)
            page.bring_to_front()
        except Exception as e:
            err_msg = f"Ошибка открытия страницы {vacancy_url}: {e}"
            self.logger.log("ERROR", "RABOTA_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # 2. Check already applied
        if self._is_already_applied(page):
            return {
                "success": True,
                "already_applied": True,
                "message": "Вы уже откликались на эту вакансию на Rabota.ru."
            }

        # 3. Click 'Откликнуться'
        opened = self._open_response_modal(page)
        if not opened:
            return {
                "success": False,
                "error": "Не найдена активная кнопка 'Откликнуться' на Rabota.ru (возможно, вакансия в архиве)."
            }

        page.wait_for_timeout(800)

        # 4. Fill Cover Letter if present
        if cover_letter:
            self._fill_cover_letter(page, cover_letter)

        screenshot_data = self.driver.take_screenshot()
        approval_token = secrets.token_hex(16)

        result = {
            "success": True,
            "platform": "rabota_ru",
            "stage": "READY_FOR_APPROVAL" if not auto_submit else "SUBMITTING",
            "url": page.url,
            "title": page.title(),
            "cover_letter_preview": (cover_letter[:150] + "...") if cover_letter else "",
            "screenshot_base64": screenshot_data.get("base64", ""),
            "approval_token": approval_token
        }

        if auto_submit:
            submit_res = self.submit(page)
            result.update(submit_res)

        return result

    def _is_already_applied(self, page) -> bool:
        indicators = [
            'button:has-text("Вы уже откликнулись")',
            ':has-text("Отклик отправлен")',
            ':has-text("Вы откликались")'
        ]
        for sel in indicators:
            if page.locator(sel).first.count() > 0:
                return True
        return False

    def _open_response_modal(self, page) -> bool:
        buttons = [
            'button:has-text("Откликнуться")',
            'a:has-text("Откликнуться")',
            '[data-qa*="apply"]',
            '[data-qa*="response"]'
        ]
        for sel in buttons:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                return True
        return False

    def _fill_cover_letter(self, page, text: str) -> bool:
        toggles = [
            'button:has-text("сопроводительное")',
            'a:has-text("сопроводительное")',
            'span:has-text("Добавить сопроводительное")'
        ]
        for t in toggles:
            loc = page.locator(t).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    page.wait_for_timeout(400)
                except Exception:
                    pass

        textareas = [
            'textarea[name*="letter"]',
            'textarea[placeholder*="сопроводительн"]',
            'textarea[placeholder*="письмо"]',
            'textarea'
        ]
        for sel in textareas:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.fill(text)
                return True
        return False

    def submit(self, page=None) -> Dict[str, Any]:
        if page is None:
            if not self.driver.connect():
                return {"success": False, "error": "CDP connection lost"}
            page = self.driver.get_active_page()

        submit_buttons = [
            'button[type="submit"]:has-text("Отправить")',
            'button:has-text("Отправить отклик")',
            'button:has-text("Откликнуться")'
        ]
        for sel in submit_buttons:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible():
                try:
                    btn.click()
                    page.wait_for_timeout(1500)
                    return {"success": True, "submitted": True, "stage": "SUBMITTED"}
                except Exception as e:
                    return {"success": False, "error": f"Ошибка нажатия кнопки отправки: {e}"}

        return {"success": True, "submitted": False, "stage": "READY_FOR_MANUAL_SUBMIT"}
