import time
import secrets
from typing import Dict, Any, Optional
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger


class HeadHunterCDPAdapter:
    """
    Fast, deterministic CDP adapter for applying to HH.ru vacancies.
    Takes 2-3 seconds, costs 0 LLM tokens, and bypasses anti-bot heuristics.
    Supports Human-in-the-Loop approval checkpoints before submitting.
    """

    def __init__(self, driver: Optional[CDPBrowserDriver] = None, logger: Optional[CDPLogger] = None):
        self.driver = driver or CDPBrowserDriver.get_instance()
        self.logger = logger or CDPLogger.get_instance()

    def apply(self, vacancy_url: str, cover_letter: str, auto_submit: bool = False) -> Dict[str, Any]:
        """
        Executes deterministic preparation and fill on HH.ru:
        1. Navigates to vacancy URL.
        2. Checks login status.
        3. Checks if vacancy was already applied to.
        4. Clicks "Откликнуться".
        5. Reveals and fills cover letter textarea.
        6. Captures screenshot for review.
        7. Returns approval token or executes submit if auto_submit=True.
        """
        self.logger.log("INFO", "HH_ADAPTER", f"Starting apply flow for: {vacancy_url}")
        if not self.driver.connect():
            err_msg = "Не удалось подключиться к Chrome через CDP на порту 9222. Запусти Chrome через ./launch_chrome.sh."
            self.logger.log("ERROR", "HH_ADAPTER", err_msg)
            return {
                "success": False,
                "error": err_msg
            }

        page = self.driver.get_active_page(avoid_crm=True)
        self.logger.attach_to_page(page)

        # Step 1: Open vacancy
        try:
            current_url = page.url
            if vacancy_url.rstrip("/") not in current_url:
                page.goto(vacancy_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)
            page.bring_to_front()
        except Exception as e:
            err_msg = f"Ошибка открытия страницы {vacancy_url}: {e}"
            self.logger.log("ERROR", "HH_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # Step 2: Check auth
        if self._is_auth_required(page):
            return {
                "success": False,
                "requires_auth": True,
                "error": "Требуется авторизация на HH.ru. Пожалуйста, войдите в свой аккаунт в браузере."
            }

        # Step 3: Check if already applied
        if self._is_already_applied(page):
            return {
                "success": True,
                "already_applied": True,
                "message": "Вы уже откликались на эту вакансию ранее на HH.ru."
            }

        # Step 4: Click apply button
        opened = self._open_response_modal(page)
        if not opened:
            return {
                "success": False,
                "error": "Не найдена активная кнопка 'Откликнуться' на странице HH.ru (возможно, вакансия в архиве)."
            }

        # Step 5: Reveal and fill cover letter
        filled = self._fill_cover_letter(page, cover_letter)
        if not filled:
            return {
                "success": False,
                "error": "Не удалось найти или открыть поле сопроводительного письма."
            }

        # Step 6: Verify filled text
        actual_letter = self._get_filled_letter(page)
        screenshot_data = self.driver.take_screenshot()

        approval_token = secrets.token_hex(16)

        result = {
            "success": True,
            "stage": "READY_FOR_APPROVAL" if not auto_submit else "SUBMITTING",
            "url": page.url,
            "title": page.title(),
            "cover_letter_preview": (actual_letter[:150] + "...") if actual_letter else "",
            "screenshot_base64": screenshot_data.get("base64", ""),
            "approval_token": approval_token
        }

        if auto_submit:
            submit_res = self.submit(page)
            result.update(submit_res)

        return result

    def submit(self, page=None) -> Dict[str, Any]:
        """Submits the prepared response modal."""
        if page is None:
            page = self.driver.get_active_page()

        submit_selectors = [
            '[data-qa="vacancy-response-submit-popup"]',
            'button[data-qa="vacancy-response-submit-popup"]',
            '.vacancy-response-popup-form button[type="submit"]',
            'button[data-qa="vacancy-response-popup-submit"]'
        ]

        for sel in submit_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    page.wait_for_timeout(1500)
                    return {"success": True, "submitted": True, "message": "Отклик успешно отправлен на HH.ru!"}
                except Exception as e:
                    return {"success": False, "error": f"Ошибка клика по кнопке отправки: {e}"}

        return {"success": False, "error": "Кнопка отправки отклика не найдена в модальном окне."}

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _is_auth_required(self, page) -> bool:
        if "/account/login" in page.url:
            return True
        login_loc = page.locator('[data-qa="account-login-input"], [data-qa="login-submit-form"]')
        return login_loc.count() > 0 and login_loc.first.is_visible()

    def _is_already_applied(self, page) -> bool:
        applied_loc = page.locator('[data-qa="vacancy-response-link-view-topic"]')
        if applied_loc.count() > 0 and applied_loc.first.is_visible():
            return True
        # Check text in response buttons
        body_text = page.locator("body").inner_text()
        return "Вы откликнулись" in body_text or "Отклик отправлен" in body_text

    def _open_response_modal(self, page) -> bool:
        # Check if modal is already open
        if page.locator('textarea, [data-qa="vacancy-response-popup-form"]').count() > 0:
            return True

        apply_selectors = [
            '[data-qa="vacancy-response-link-top"]',
            '[data-qa="vacancy-response-link-bottom"]',
            'a[data-qa="vacancy-response-link-top"]',
            'button[data-qa="vacancy-response-link-top"]'
        ]

        for sel in apply_selectors:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                page.wait_for_timeout(800)
                return True

        return False

    def _fill_cover_letter(self, page, cover_letter: str) -> bool:
        # Toggle cover letter accordion if hidden
        toggle_selectors = [
            '[data-qa="vacancy-response-letter-toggle"]',
            '[data-qa="vacancy-response-popup-letter-toggle"]',
            'button[data-qa="vacancy-response-letter-toggle"]'
        ]
        for sel in toggle_selectors:
            tog = page.locator(sel).first
            if tog.count() > 0 and tog.is_visible():
                try:
                    tog.click()
                    page.wait_for_timeout(400)
                except Exception:
                    pass

        textarea_selectors = [
            '[data-qa="vacancy-response-popup-form-letter-input"]',
            'textarea[name="message"]',
            '.vacancy-response-popup-form textarea',
            'textarea'
        ]

        for sel in textarea_selectors:
            ta = page.locator(sel).first
            if ta.count() > 0 and ta.is_visible():
                ta.click()
                ta.fill(cover_letter)
                return True

        return False

    def _get_filled_letter(self, page) -> str:
        ta = page.locator('[data-qa="vacancy-response-popup-form-letter-input"], textarea').first
        if ta.count() > 0:
            return ta.input_value() or ""
        return ""
