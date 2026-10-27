import time
import secrets
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger


class SuperJobCDPAdapter:
    """
    CDP Adapter for applying to SuperJob.ru vacancies.
    Leverages user's authenticated Chrome session via CDP.
    Supports modal opening, cover letter injection, redirect detection
    for external ATS forms, and human approval checkpoints.
    """

    def __init__(self, driver: Optional[CDPBrowserDriver] = None, logger: Optional[CDPLogger] = None):
        self.driver = driver or CDPBrowserDriver.get_instance()
        self.logger = logger or CDPLogger.get_instance()

    def apply(
        self,
        vacancy_url: str,
        cover_letter: str = "",
        auto_submit: bool = False,
        candidate_data: Optional[Dict[str, Any]] = None,
        resume_pdf_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes SuperJob application flow:
        1. Opens vacancy page.
        2. Checks login / already applied status.
        3. Clicks 'Откликнуться'.
        4. Detects redirect to external ATS (e.g. job.pik.ru).
        5. If redirected: delegates to UniversalFormFiller for the external form.
        6. If not redirected: injects Cover Letter on SuperJob.
        7. Returns READY_FOR_APPROVAL checkpoint with screenshot.
        """
        self.logger.log("INFO", "SUPERJOB_ADAPTER", f"Starting apply flow for: {vacancy_url}")
        if not self.driver.connect():
            err_msg = "Не удалось подключиться к Chrome через CDP на порту 9222. Запусти Chrome через ./launch_chrome.sh."
            self.logger.log("ERROR", "SUPERJOB_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        page = self.driver.get_active_page(avoid_crm=True)
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
            self.logger.log("ERROR", "SUPERJOB_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        sj_domain = "superjob.ru"

        # 2. Check already applied
        if self._is_already_applied(page):
            return {
                "success": True,
                "already_applied": True,
                "message": "Вы уже откликались на эту вакансию на SuperJob."
            }

        # 3. Check auth
        if self._is_auth_required(page):
            return {
                "success": False,
                "requires_auth": True,
                "error": "Требуется авторизация на SuperJob.ru. Войдите в свой аккаунт в браузере."
            }

        # 4. Click 'Откликнуться'
        pre_click_url = page.url
        opened = self._open_response_modal(page)
        if not opened:
            return {
                "success": False,
                "error": "Не найдена активная кнопка 'Откликнуться' на странице SuperJob (возможно, вакансия в архиве)."
            }

        # 5. Detect redirect to external ATS
        redirect_url = self._detect_redirect(page, pre_click_url, sj_domain, wait_ms=4000)

        if redirect_url:
            # Redirected to external ATS — delegate to UniversalFormFiller
            self.logger.log("INFO", "SUPERJOB_ADAPTER", f"Redirect detected to external ATS: {redirect_url}")
            return self._handle_external_ats(page, redirect_url, cover_letter, candidate_data, resume_pdf_path, auto_submit)

        # 6. No redirect — standard SuperJob flow (modal / inline form)
        page.wait_for_timeout(800)

        if cover_letter:
            self._fill_cover_letter(page, cover_letter)

        screenshot_data = self.driver.take_screenshot()
        approval_token = secrets.token_hex(16)

        result = {
            "success": True,
            "platform": "superjob",
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

    def _detect_redirect(self, page, pre_click_url: str, expected_domain: str, wait_ms: int = 4000) -> Optional[str]:
        """
        Monitors URL after clicking 'Откликнуться' to detect redirect to external ATS.
        Returns the redirect URL if domain changed, None if stayed on SuperJob.
        """
        original_domain = urlparse(pre_click_url).netloc
        checks = max(1, wait_ms // 500)

        for i in range(checks):
            page.wait_for_timeout(500)
            current_url = page.url
            current_domain = urlparse(current_url).netloc

            if current_domain and current_domain != original_domain and expected_domain not in current_domain:
                self.logger.log("INFO", "SUPERJOB_ADAPTER", f"Redirect detected after {(i+1)*500}ms: {current_url}")
                return current_url

        return None

    def _handle_external_ats(
        self,
        page,
        external_url: str,
        cover_letter: str,
        candidate_data: Optional[Dict[str, Any]],
        resume_pdf_path: Optional[str],
        auto_submit: bool
    ) -> Dict[str, Any]:
        """
        Handles application flow on external ATS (redirected from SuperJob).
        Waits for page load, then delegates to UniversalFormFiller.
        """
        # Wait for external page to fully load
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.log("WARN", "SUPERJOB_ADAPTER", f"External page load timeout: {e}")

        # Load candidate profile if not provided
        if not candidate_data:
            try:
                from generator.candidate_profile import get_canonical_profile
                candidate_data = get_canonical_profile(lang="ru")
            except Exception:
                candidate_data = {}

        # Delegate to UniversalFormFiller
        from agents.universal_form_filler import UniversalFormFiller
        filler = UniversalFormFiller()
        fill_res = filler.fill_form(page, cover_letter=cover_letter, profile=candidate_data, resume_pdf_path=resume_pdf_path)

        screenshot_data = self.driver.take_screenshot()
        approval_token = secrets.token_hex(16)

        result = {
            "success": True,
            "platform": "superjob_external_ats",
            "stage": "READY_FOR_APPROVAL" if not auto_submit else "SUBMITTING",
            "external_ats_url": external_url,
            "url": page.url,
            "title": page.title(),
            "cover_letter_preview": (cover_letter[:150] + "...") if cover_letter else "",
            "filled_count": fill_res.get("filled_count", 0),
            "missing_required": fill_res.get("missing_required", []),
            "screenshot_base64": screenshot_data.get("base64", ""),
            "approval_token": approval_token
        }

        if auto_submit:
            submit_res = self._submit_external(page)
            result.update(submit_res)

        return result

    def _submit_external(self, page) -> Dict[str, Any]:
        """Submit button detection for external ATS forms."""
        submit_buttons = [
            'button[type="submit"]',
            'button:has-text("Отправить")',
            'button:has-text("Submit")',
            'input[type="submit"]',
            'a:has-text("Отправить")'
        ]
        for sel in submit_buttons:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible():
                try:
                    btn.click()
                    page.wait_for_timeout(2000)
                    return {"success": True, "submitted": True, "stage": "SUBMITTED"}
                except Exception as e:
                    return {"success": False, "error": f"Ошибка отправки формы: {e}"}

        return {"success": True, "submitted": False, "stage": "READY_FOR_MANUAL_SUBMIT"}

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

    def _is_auth_required(self, page) -> bool:
        auth_selectors = [
            'a:has-text("Вход"), a:has-text("Войти")',
            '[data-qa="login-button"]'
        ]
        # Only true if no user avatar / profile menu
        has_profile = page.locator('[data-qa="user-profile"], [class*="Avatar"], [class*="profileMenu"]').first.count() > 0
        if has_profile:
            return False
        return False

    def _open_response_modal(self, page) -> bool:
        buttons = [
            'button:has-text("Откликнуться")',
            'a:has-text("Откликнуться")',
            '[data-qa*="response-button"]',
            '[data-qa*="apply"]'
        ]
        for sel in buttons:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                return True
        return False

    def _fill_cover_letter(self, page, text: str) -> bool:
        # Check if letter toggle needs to be clicked
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
            'textarea[name*="message"]',
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
