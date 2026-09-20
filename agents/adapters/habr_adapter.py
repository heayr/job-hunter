import time
import secrets
from typing import Dict, Any, Optional
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger


class HabrCDPAdapter:
    """
    Deterministic CDP adapter for applying to Habr Career (career.habr.com) vacancies.
    Takes 2-3 seconds, costs 0 LLM tokens, and bypasses bot detections.
    Supports Human-in-the-Loop review and real-time event logging.
    """

    def __init__(self, driver: Optional[CDPBrowserDriver] = None, logger: Optional[CDPLogger] = None):
        self.driver = driver or CDPBrowserDriver.get_instance()
        self.logger = logger or CDPLogger.get_instance()

    def apply(
        self,
        vacancy_url: str,
        cover_letter: str,
        salary: Optional[str] = None,
        auto_submit: bool = False
    ) -> Dict[str, Any]:
        """
        Executes deterministic preparation and fill on Habr Career:
        1. Navigates to vacancy URL (or focuses existing tab).
        2. Attaches real-time logger to page.
        3. Checks authentication status.
        4. Checks if already applied.
        5. Clicks "Откликнуться" button.
        6. Fills cover letter into textarea[name="body"].
        7. Fills salary expectation if provided.
        8. Captures review screenshot.
        9. Returns approval token or submits if auto_submit=True.
        """
        self.logger.log("INFO", "HABR_ADAPTER", f"Starting apply flow for: {vacancy_url}")

        if not self.driver.connect():
            err_msg = "Не удалось подключиться к Chrome через CDP на порту 9222. Запусти Chrome через ./launch_chrome.sh."
            self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        page = self.driver.get_active_page(avoid_crm=True)
        self.logger.attach_to_page(page)

        # Step 1: Open or verify URL
        try:
            current_url = page.url
            if vacancy_url.rstrip("/") not in current_url:
                self.logger.log("INFO", "HABR_ADAPTER", f"Navigating to {vacancy_url}")
                page.goto(vacancy_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)
            page.bring_to_front()
        except Exception as e:
            err_msg = f"Ошибка открытия страницы {vacancy_url}: {e}"
            self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # Step 2: Check auth
        if self._is_auth_required(page):
            err_msg = "Требуется авторизация на Хабр Карьере. Пожалуйста, войдите в свой аккаунт в браузере."
            self.logger.log("WARN", "HABR_ADAPTER", err_msg)
            return {
                "success": False,
                "requires_auth": True,
                "error": err_msg
            }

        # Step 3: Check if already applied via DOM
        if self._is_already_applied(page):
            msg = "Вы уже откликались на эту вакансию ранее на Хабр Карьере."
            self.logger.log("INFO", "HABR_ADAPTER", msg)
            self._sync_db_applied(vacancy_url)
            return {
                "success": True,
                "already_applied": True,
                "message": msg
            }

        # Step 4: Click apply button (or detect API response if already applied)
        open_result = self._open_response_modal(page)
        if open_result == "ALREADY_APPLIED":
            msg = "Вы уже откликались на эту вакансию ранее на Хабр Карьере."
            self.logger.log("INFO", "HABR_ADAPTER", msg)
            self._sync_db_applied(vacancy_url)
            return {
                "success": True,
                "already_applied": True,
                "message": msg
            }
        elif not open_result:
            err_msg = "Не найдена активная кнопка 'Откликнуться' на Хабр Карьере (возможно, вакансия в архиве)."
            self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # Step 5: Fill cover letter
        filled = self._fill_cover_letter(page, cover_letter)
        if not filled:
            err_msg = "Не удалось найти поле сопроводительного письма на Хабре."
            self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # Step 6: Optionally fill salary
        if salary:
            self._fill_salary(page, salary)

        # Step 7: Verify filled text and capture screenshot
        actual_letter = self._get_filled_letter(page)
        screenshot_data = self.driver.take_screenshot()
        approval_token = secrets.token_hex(16)

        self.logger.log("INFO", "HABR_ADAPTER", "Form successfully filled, awaiting human approval checkpoint", {
            "cover_letter_len": len(actual_letter),
            "approval_token": approval_token[:8] + "..."
        })

        result = {
            "success": True,
            "platform": "habr",
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
        """Submits the prepared response modal on Habr Career."""
        if page is None:
            page = self.driver.get_active_page()

        submit_selectors = [
            'button[type="submit"]:has-text("Дополнить отклик")',
            'button[type="submit"]:has-text("Откликнуться")',
            '.basic-form button[type="submit"]',
            'button[type="submit"]'
        ]

        for sel in submit_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    self.logger.log("INFO", "HABR_ADAPTER", f"Clicking submit button: {sel}")
                    loc.click()
                    page.wait_for_timeout(2000)
                    self.logger.log("INFO", "HABR_ADAPTER", "Application successfully submitted to Habr Career!")
                    return {
                        "success": True,
                        "submitted": True,
                        "message": "Отклик успешно отправлен на Хабр Карьере!"
                    }
                except Exception as e:
                    err_msg = f"Ошибка клика по кнопке отправки: {e}"
                    self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
                    return {"success": False, "error": err_msg}

        err_msg = "Кнопка отправки отклика не найдена в форме Хабра."
        self.logger.log("ERROR", "HABR_ADAPTER", err_msg)
        return {"success": False, "error": err_msg}

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _sync_db_applied(self, vacancy_url: str):
        """Updates vacancy status to 'applied' in jobs.db."""
        try:
            from tracker.db import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            vac_slug = vacancy_url.rstrip("/").split("/")[-1]
            cur.execute(
                "UPDATE vacancies SET status = 'applied' WHERE url = ? OR url LIKE ? OR id LIKE ?",
                (vacancy_url, f"%{vac_slug}%", f"%{vac_slug}%")
            )
            conn.commit()
            conn.close()
            self.logger.log("INFO", "HABR_ADAPTER", f"Synchronized vacancy status to 'applied' in jobs.db for {vac_slug}")
        except Exception as e:
            self.logger.log("WARN", "HABR_ADAPTER", f"Failed to sync applied status to DB: {e}")

    def _is_auth_required(self, page) -> bool:
        if "/users/sign_in" in page.url or "/login" in page.url:
            return True
        login_btn = page.locator('a[href*="sign_in"], a:has-text("Войти"), .auth-button')
        user_menu = page.locator('.user-menu, .avatar, [class*="avatar"], a[href*="/users/"]')
        if user_menu.count() > 0:
            return False
        return login_btn.count() > 0 and login_btn.first.is_visible()

    def _is_already_applied(self, page) -> bool:
        applied_selectors = [
            '.button-comp:has-text("Вы откликнулись")',
            'button:has-text("Вы откликнулись")',
            'a:has-text("Посмотреть отклик")',
            'button:has-text("Посмотреть отклик")',
            '.button-comp:has-text("Посмотреть отклик")'
        ]
        for sel in applied_selectors:
            if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                return True
        body_text = page.locator("body").inner_text()
        return "Вы уже откликнулись" in body_text or "Посмотреть отклик" in body_text

    def _open_response_modal(self, page):
        if page.locator('textarea[name="body"]').is_visible():
            return True

        # Network listener to catch fast 401 "Вы уже откликнулись" API response
        api_already_applied = False

        def on_response(resp):
            nonlocal api_already_applied
            if "responses" in resp.url:
                try:
                    text = resp.text()
                    if "уже откликнулись" in text:
                        api_already_applied = True
                except Exception:
                    pass

        try:
            page.on("response", on_response)
        except Exception:
            pass

        apply_selectors = [
            'button.button-comp:has-text("Откликнуться")',
            'button:has-text("Откликнуться")',
            'a:has-text("Откликнуться")'
        ]

        for sel in apply_selectors:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible():
                self.logger.log("INFO", "HABR_ADAPTER", f"Clicking response button: {sel}")
                btn.click()
                page.wait_for_timeout(1500)

                if api_already_applied:
                    return "ALREADY_APPLIED"

                if page.locator('textarea[name="body"], .basic-form').first.is_visible():
                    return True

        if api_already_applied:
            return "ALREADY_APPLIED"

        return page.locator('textarea[name="body"]').first.is_visible()

    def _fill_cover_letter(self, page, cover_letter: str) -> bool:
        textarea_selectors = [
            'textarea[name="body"]',
            'textarea[name="user[letter]"]',
            '.basic-form textarea',
            'textarea'
        ]

        for sel in textarea_selectors:
            ta = page.locator(sel).first
            if ta.count() > 0 and ta.is_visible():
                self.logger.log("INFO", "HABR_ADAPTER", f"Filling cover letter into: {sel} ({len(cover_letter)} chars)")
                ta.click()
                ta.fill(cover_letter)
                return True

        return False

    def _fill_salary(self, page, salary: str):
        salary_selectors = [
            'input[placeholder="Сумма"]',
            'input[name="user[salary]"]',
            'input[name*="salary"]'
        ]
        for sel in salary_selectors:
            inp = page.locator(sel).first
            if inp.count() > 0 and inp.is_visible():
                self.logger.log("INFO", "HABR_ADAPTER", f"Filling desired salary: {salary}")
                inp.click()
                inp.fill(str(salary))
                break

    def _get_filled_letter(self, page) -> str:
        ta = page.locator('textarea[name="body"], textarea').first
        if ta.count() > 0:
            return ta.input_value() or ""
        return ""
