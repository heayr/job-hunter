import os
import time
import secrets
import tempfile
from typing import Dict, Any, Optional
from agents.cdp_browser import CDPBrowserDriver
from agents.cdp_logger import CDPLogger
from generator.candidate_profile import get_canonical_profile


class GreenhouseCDPAdapter:
    """
    Deterministic CDP adapter for applying to Greenhouse ATS job boards (greenhouse.io).
    Handles standard application forms, native PDF resume uploads, candidate data mapping,
    and Human-in-the-Loop review checkpoints.
    """

    def __init__(self, driver: Optional[CDPBrowserDriver] = None, logger: Optional[CDPLogger] = None):
        self.driver = driver or CDPBrowserDriver.get_instance()
        self.logger = logger or CDPLogger.get_instance()

    def apply(
        self,
        vacancy_url: str,
        cover_letter: str = "",
        resume_pdf_path: Optional[str] = None,
        auto_submit: bool = False,
        candidate_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fills a standard Greenhouse ATS job application form:
        1. Navigates to vacancy page.
        2. Fills First Name, Last Name, Email, Phone.
        3. Fills LinkedIn / GitHub / Website URLs if present.
        4. Uploads PDF resume into file input.
        5. Fills Cover Letter text / textarea.
        6. Captures review screenshot and generates approval token.
        """
        self.logger.log("INFO", "GREENHOUSE_ADAPTER", f"Starting apply flow for Greenhouse: {vacancy_url}")

        if not self.driver.connect():
            err_msg = "Не удалось подключиться к Chrome через CDP на порту 9222. Запусти Chrome через ./launch_chrome.sh."
            self.logger.log("ERROR", "GREENHOUSE_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        page = self.driver.get_active_page(avoid_crm=True)
        self.logger.attach_to_page(page)

        try:
            current_url = page.url
            if vacancy_url.rstrip("/") not in current_url:
                self.logger.log("INFO", "GREENHOUSE_ADAPTER", f"Navigating to {vacancy_url}")
                page.goto(vacancy_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
            page.bring_to_front()
        except Exception as e:
            err_msg = f"Ошибка открытия страницы {vacancy_url}: {e}"
            self.logger.log("ERROR", "GREENHOUSE_ADAPTER", err_msg)
            return {"success": False, "error": err_msg}

        # Check if form is visible or needs to click "Apply"
        apply_btn = page.locator('button:has-text("Apply"), a:has-text("Apply"), [data-qa="apply-button"]').first
        if apply_btn.count() > 0 and apply_btn.is_visible():
            try:
                apply_btn.click()
                page.wait_for_timeout(800)
            except Exception:
                pass

        # Load canonical candidate data
        lang = "en"
        if candidate_data:
            candidate = candidate_data
            lang = candidate.get("lang", "en")
        else:
            candidate = get_canonical_profile(lang="en")
        ident = candidate.get("identity", {})
        contacts = ident.get("contacts", {})
        first_name = "Egor"
        last_name = "Myshinsky"
        email = contacts.get("email", "egormyshinsky@gmail.com")
        phone = contacts.get("phone", "+79998291788")
        linkedin = contacts.get("linkedin", "https://linkedin.com/in/egor-myshinsky")
        github = contacts.get("github", "https://github.com/heayr")

        # 1. Fill First Name
        self._fill_first_matching(page, [
            'input[name*="first_name"]', 'input#first_name', 'input[autocomplete="given-name"]',
            'input[aria-label*="First Name"]', 'input[placeholder*="First Name"]'
        ], first_name, "First Name")

        # 2. Fill Last Name
        self._fill_first_matching(page, [
            'input[name*="last_name"]', 'input#last_name', 'input[autocomplete="family-name"]',
            'input[aria-label*="Last Name"]', 'input[placeholder*="Last Name"]'
        ], last_name, "Last Name")

        # 3. Fill Email
        self._fill_first_matching(page, [
            'input[name*="email"]', 'input#email', 'input[type="email"]',
            'input[aria-label*="Email"]', 'input[placeholder*="Email"]'
        ], email, "Email")

        # 4. Fill Phone
        self._fill_first_matching(page, [
            'input[name*="phone"]', 'input#phone', 'input[type="tel"]',
            'input[aria-label*="Phone"]', 'input[placeholder*="Phone"]'
        ], phone, "Phone")

        # 5. Fill LinkedIn
        self._fill_first_matching(page, [
            'input[id*="linkedin"]', 'input[name*="linkedin"]', 'input[aria-label*="LinkedIn"]'
        ], linkedin, "LinkedIn")

        # 6. Fill GitHub
        self._fill_first_matching(page, [
            'input[id*="github"]', 'input[name*="github"]', 'input[aria-label*="GitHub"]'
        ], github, "GitHub")

        # 7. Upload Resume PDF
        lang = candidate_data.get("lang", "en") if candidate_data else "en"
        resume_file = resume_pdf_path
        if not resume_file or not os.path.exists(resume_file):
            resume_file = self._get_or_create_sample_resume(lang=lang)

        # Clear existing attached file if any
        try:
            for rem_btn in page.locator('button[aria-label="Remove file"], button:has-text("Remove")').all():
                if rem_btn.is_visible():
                    rem_btn.click()
                    page.wait_for_timeout(400)
        except Exception:
            pass

        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0 and resume_file and os.path.exists(resume_file):
            try:
                self.logger.log("INFO", "GREENHOUSE_ADAPTER", f"Uploading resume file: {resume_file}")
                file_input.set_input_files(resume_file)
                # Allow time for async upload to complete (especially for large PDFs)
                page.wait_for_timeout(2500)
            except Exception as e:
                self.logger.log("WARN", "GREENHOUSE_ADAPTER", f"File upload warning: {e}")

        # 8. Fill Cover Letter
        if cover_letter:
            self._fill_first_matching(page, [
                'textarea[name*="cover_letter"]', 'textarea#cover_letter_text',
                'textarea[aria-label*="Cover Letter"]', 'textarea'
            ], cover_letter, "Cover Letter")

        # 9. Autonomously fill all custom screening questions & react-select fields
        try:
            from agents.universal_form_filler import UniversalFormFiller
            filler = UniversalFormFiller(logger=self.logger)
            filler.fill_form(page, cover_letter=cover_letter, profile=candidate, resume_pdf_path=resume_file)
        except Exception as e:
            self.logger.log("WARN", "GREENHOUSE_ADAPTER", f"UniversalFormFiller warning: {e}")

        screenshot_data = self.driver.take_screenshot()
        approval_token = secrets.token_hex(16)

        self.logger.log("INFO", "GREENHOUSE_ADAPTER", "Form successfully filled, awaiting human approval checkpoint", {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "approval_token": approval_token[:8] + "..."
        })

        result = {
            "success": True,
            "platform": "greenhouse",
            "stage": "READY_FOR_APPROVAL" if not auto_submit else "SUBMITTING",
            "url": page.url,
            "title": page.title(),
            "candidate": f"{first_name} {last_name} ({email})",
            "cover_letter_preview": (cover_letter[:150] + "...") if cover_letter else "",
            "screenshot_base64": screenshot_data.get("base64", ""),
            "approval_token": approval_token
        }

        if auto_submit:
            submit_res = self.submit(page)
            result.update(submit_res)

        return result

    def submit(self, page=None) -> Dict[str, Any]:
        """Submits the prepared Greenhouse form."""
        if page is None:
            page = self.driver.get_active_page()

        submit_selectors = [
            'button#submit_app',
            'button[type="submit"]:has-text("Submit")',
            'input[type="submit"][value*="Submit"]',
            'button[type="submit"]',
            'input[type="submit"]'
        ]

        for sel in submit_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    self.logger.log("INFO", "GREENHOUSE_ADAPTER", f"Clicking submit button: {sel}")
                    loc.click()
                    page.wait_for_timeout(2000)
                    self.logger.log("INFO", "GREENHOUSE_ADAPTER", "Application successfully submitted to Greenhouse ATS!")
                    return {
                        "success": True,
                        "submitted": True,
                        "message": "Отклик успешно отправлен в Greenhouse ATS!"
                    }
                except Exception as e:
                    err_msg = f"Ошибка клика по кнопке отправки: {e}"
                    self.logger.log("ERROR", "GREENHOUSE_ADAPTER", err_msg)
                    return {"success": False, "error": err_msg}

        err_msg = "Кнопка отправки формы не найдена на странице Greenhouse."
        self.logger.log("ERROR", "GREENHOUSE_ADAPTER", err_msg)
        return {"success": False, "error": err_msg}

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _fill_first_matching(self, page, selectors, value: str, field_name: str):
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    self.logger.log("INFO", "GREENHOUSE_ADAPTER", f"Filling {field_name} into {sel}")
                    loc.click()
                    loc.fill(value)
                    return True
                except Exception:
                    pass
        return False

    def _get_or_create_sample_resume(self, lang: str = "en") -> str:
        """Returns path to candidate canonical resume PDF."""
        # 1. Try config.json
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(project_root, "config.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                key = "resume_pdf_path_en" if lang == "en" else "resume_pdf_path_ru"
                pdf_rel = cfg.get(key) or cfg.get("resume_pdf_path")
                if pdf_rel:
                    candidate_pdf = os.path.abspath(os.path.join(project_root, pdf_rel)) if not os.path.isabs(pdf_rel) else pdf_rel
                    if os.path.exists(candidate_pdf):
                        return candidate_pdf
            except Exception as e:
                self.logger.log("WARNING", "GREENHOUSE_ADAPTER", f"Error reading config resume path: {e}")

        # 2. Check resumes/ folder in project
        resumes_dir = os.path.join(project_root, "resumes")
        preferred_name = "Egor_Myshinsky_CV_frontend.pdf" if lang == "en" else "Egor_Myshinsky_CV_ru.pdf"
        direct_path = os.path.join(resumes_dir, preferred_name)
        if os.path.exists(direct_path):
            return direct_path

        # 3. Check user's Downloads directory directly
        downloads_pdf = os.path.expanduser(f"~/Downloads/{preferred_name}")
        if os.path.exists(downloads_pdf):
            return downloads_pdf

        # 4. Fallback to static sample if nothing exists
        resume_dir = os.path.join(project_root, "static")
        os.makedirs(resume_dir, exist_ok=True)
        pdf_path = os.path.join(resume_dir, "resume_egor_myshinsky.pdf")
        if not os.path.exists(pdf_path):
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n")
        return pdf_path
