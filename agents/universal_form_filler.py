import os
import re
import json
import time
from typing import Dict, Any, List, Optional

from agents.cdp_logger import CDPLogger
from generator.form_classifier import classify_form_element, FieldCategory
from generator.question_answerer import answer_application_question, answer_choice_question
from generator.form_verifier import verify_application_form


class UniversalFormFiller:
    """
    Autonomous AI Form Filling Engine.
    Inspects any arbitrary job application form (Greenhouse, Lever, Ashby, 
    custom corporate ATS, or direct job forms) and fills all inputs, 
    choice dropdowns (HTML select & react-select), file uploads, and custom questionnaires
    grounded in candidate's Master Profile.
    """

    def __init__(self, logger: Optional[CDPLogger] = None):
        self.logger = logger or CDPLogger.get_instance()

    def fill_form(
        self,
        page,
        cover_letter: str = "",
        profile: Optional[Dict[str, Any]] = None,
        resume_pdf_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end form inspection, classification, grounded answering,
        and submission-readiness verification on the active Playwright page.
        """
        if not profile:
            from generator.candidate_profile import get_canonical_profile
            profile = get_canonical_profile(lang="en")

        lang = profile.get("lang", "en")
        ident = profile.get("identity", {})
        contacts = ident.get("contacts", {})
        screening = profile.get("screening_facts", {})

        first_name = ident.get("first_name") or (ident.get("name", "").split()[0] if ident.get("name") else "Egor")
        parts = ident.get("name", "").split()
        last_name = ident.get("last_name") or (" ".join(parts[1:]) if len(parts) > 1 else "Myshinsky")
        full_name = ident.get("name") or f"{first_name} {last_name}"
        email = contacts.get("email", "egormyshinsky@gmail.com")
        phone = contacts.get("phone", "+79998291788")
        linkedin = contacts.get("linkedin", "https://linkedin.com/in/potatochipasu")
        github = contacts.get("github", "https://github.com/heayr")
        portfolio = contacts.get("portfolio", "https://nologs.website")

        # 0. Ensure form is revealed if Apply button is present
        if page.locator('input[type="text"], input[type="email"]').count() == 0:
            apply_btn = page.locator('button:has-text("Apply"), a:has-text("Apply"), [data-qa="apply-button"]').first
            if apply_btn.count() > 0 and apply_btn.is_visible():
                try:
                    apply_btn.click(timeout=1500)
                    page.wait_for_timeout(800)
                except Exception:
                    pass

        # 1. Resolve canonical resume file
        resume_file = resume_pdf_path
        if not resume_file or not os.path.exists(resume_file):
            resume_file = self._resolve_resume_path(lang)

        # 2. Clear old file upload if any, then upload resume
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0 and resume_file and os.path.exists(resume_file):
            try:
                # Remove existing file widget if present
                for rem in page.locator('button[aria-label*="Remove file"], button:has-text("Remove")').all():
                    if rem.is_visible():
                        rem.click()
                        page.wait_for_timeout(300)
                self.logger.log("INFO", "UNIVERSAL_FILLER", f"Attaching resume: {os.path.basename(resume_file)}")
                file_input.set_input_files(resume_file)
                page.wait_for_timeout(1500)
            except Exception as e:
                self.logger.log("WARN", "UNIVERSAL_FILLER", f"File upload warning: {e}")

        # 3. Extract all DOM form elements for classification
        dom_elements = self._extract_dom_elements(page)
        self.logger.log("INFO", "UNIVERSAL_FILLER", f"Discovered {len(dom_elements)} form elements")

        filled_fields = 0

        # 4. Fill standard and classified fields
        for el in dom_elements:
            tag = el.get("tag", "").lower()
            itype = el.get("type", "").lower()
            elem_id = el.get("id") or el.get("name") or ""
            label = el.get("label", "")
            current_val = el.get("value", "")

            # Skip if already filled and non-empty
            if current_val and len(current_val.strip()) > 0:
                continue

            # Skip hidden or submit
            if itype in ("hidden", "submit", "button", "reset") or tag == "button":
                continue

            low_lbl = f"{label} {elem_id}".lower()

            # First Name / Given Name
            if re.search(r'\b(?:first\s*name|given\s*name|имя)\b', low_lbl) and not re.search(r'\b(?:last|фамилия)\b', low_lbl):
                self._fill_selector(page, el["selector"], first_name)
                filled_fields += 1

            # Preferred Name
            elif "preferred" in low_lbl and "name" in low_lbl:
                self._fill_selector(page, el["selector"], first_name)
                filled_fields += 1

            # Last Name
            elif re.search(r'\b(?:last\s*name|surname|family\s*name|фамилия)\b', low_lbl):
                self._fill_selector(page, el["selector"], last_name)
                filled_fields += 1

            # Full Name
            elif re.search(r'\b(?:full\s*name|your\s*name|фио)\b', low_lbl):
                self._fill_selector(page, el["selector"], full_name)
                filled_fields += 1

            # Email
            elif itype == "email" or re.search(r'\b(?:email|e-mail|почта)\b', low_lbl):
                self._fill_selector(page, el["selector"], email)
                filled_fields += 1

            # Phone
            elif itype == "tel" or re.search(r'\b(?:phone|mobile|телефон)\b', low_lbl):
                self._fill_selector(page, el["selector"], phone)
                filled_fields += 1

            # LinkedIn
            elif "linkedin" in low_lbl:
                self._fill_selector(page, el["selector"], linkedin)
                filled_fields += 1

            # GitHub
            elif "github" in low_lbl:
                self._fill_selector(page, el["selector"], github)
                filled_fields += 1

            # Portfolio / Website
            elif re.search(r'\b(?:portfolio|website|web\s*site|портфолио|сайт)\b', low_lbl):
                self._fill_selector(page, el["selector"], portfolio)
                filled_fields += 1

            # Cover Letter
            elif re.search(r'\b(?:cover\s*letter|сопроводительн|message|letter)\b', low_lbl):
                if cover_letter:
                    self._fill_selector(page, el["selector"], cover_letter)
                    filled_fields += 1

            # Standard HTML Select
            elif tag == "select":
                opts = el.get("options", [])
                if opts:
                    chosen = answer_choice_question(label, opts, profile, lang=lang)
                    if chosen:
                        self._select_option(page, el["selector"], chosen)
                        filled_fields += 1

            # React-Select or custom combobox
            elif el.get("is_react_select"):
                opts = self._get_react_select_options(page, el["selector"])
                if opts:
                    chosen = answer_choice_question(label, opts, profile, lang=lang)
                    if chosen:
                        self._click_react_select_option(page, el["selector"], chosen)
                        filled_fields += 1

            # Custom questions (Text input or Textarea)
            elif tag in ("input", "textarea") and el.get("required"):
                # Answer custom question via LLM / Grounded Answerer
                ans_data = answer_application_question(label, profile, lang=lang)
                ans_text = ans_data.get("answer", "")
                if ans_text:
                    # If single line input, keep it brief
                    if tag == "input" and len(ans_text) > 100:
                        # Extract first sentence or numerical ratio
                        if "split" in low_lbl or "%" in low_lbl or "80/20" in low_lbl:
                            ans_text = "30/70"
                        else:
                            ans_text = ans_text.split(".")[0]
                    self._fill_selector(page, el["selector"], ans_text)
                    filled_fields += 1

        # 4.5. Process all custom select / react-select controls
        try:
            controls = page.locator('.select__control')
            count = controls.count()
            for i in range(count):
                ctrl = controls.nth(i)
                lbl = page.evaluate('''(idx) => {
                    const c = document.querySelectorAll('.select__control')[idx];
                    const s = c ? c.closest('.select, .field-wrapper, [class*="field"]') : null;
                    const l = s ? s.querySelector('label') : null;
                    return l ? l.innerText : 'Question ' + idx;
                }''', i)
                ctrl.click(force=True, timeout=1000)
                page.wait_for_timeout(150)
                opts = page.evaluate('''() => Array.from(document.querySelectorAll('[class*="option"]')).map(o => o.innerText.trim()).filter(Boolean)''')
                if opts:
                    chosen = answer_choice_question(lbl, opts, profile, lang=lang)
                    opt_loc = page.locator(f'[class*="option"]:has-text("{chosen}")').first
                    if opt_loc.count() > 0:
                        opt_loc.click(force=True, timeout=1000)
                    else:
                        page.keyboard.press('Escape')
                    page.wait_for_timeout(150)
                    filled_fields += 1
                else:
                    page.keyboard.press('Escape')
        except Exception as e:
            self.logger.log("WARN", "UNIVERSAL_FILLER", f"Select controls error: {e}")

        # 5. Verification audit via form_verifier
        verified_elements = self._extract_dom_elements(page)
        verification_report = verify_application_form(verified_elements)

        self.logger.log("INFO", "UNIVERSAL_FILLER", "Form filling audit complete", {
            "filled_fields": filled_fields,
            "missing_required": len(verification_report.get("missing_required", [])),
            "errors": len(verification_report.get("validation_errors", []))
        })

        return {
            "success": len(verification_report.get("missing_required", [])) == 0,
            "filled_count": filled_fields,
            "missing_required": verification_report.get("missing_required", []),
            "validation_report": verification_report
        }

    def _resolve_resume_path(self, lang: str = "en") -> str:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resumes_dir = os.path.join(project_root, "resumes")
        preferred = "Egor_Myshinsky_CV_frontend.pdf" if lang == "en" else "Egor_Myshinsky_CV_ru.pdf"
        p = os.path.join(resumes_dir, preferred)
        if os.path.exists(p):
            return p
        # Fallback to config
        config_path = os.path.join(project_root, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                key = "resume_pdf_path_en" if lang == "en" else "resume_pdf_path_ru"
                rel = cfg.get(key) or cfg.get("resume_pdf_path")
                if rel:
                    full = os.path.abspath(os.path.join(project_root, rel)) if not os.path.isabs(rel) else rel
                    if os.path.exists(full):
                        return full
            except Exception:
                pass
        return os.path.expanduser(f"~/Downloads/{preferred}")

    def _extract_dom_elements(self, page) -> List[Dict[str, Any]]:
        return page.evaluate('''() => {
            const results = [];
            const interactive = 'input:not([type=hidden]):not([type=file]):not([type=submit]):not([type=button]), textarea, select, [role=combobox]';
            document.querySelectorAll(interactive).forEach((el, idx) => {
                let label = '';
                if (el.id) {
                    const l = document.querySelector('label[for="' + el.id + '"]');
                    if (l) label = l.innerText;
                }
                if (!label && el.closest('.field, .form-group, .question, [class*="field"], [class*="select"]')) {
                    const l = el.closest('.field, .form-group, .question, [class*="field"], [class*="select"]').querySelector('label, .label, legend');
                    if (l) label = l.innerText;
                }
                if (!label) label = el.getAttribute('aria-label') || el.placeholder || el.name || '';
                
                const isReactSelect = !!el.closest('[class*="select-shell"], [class*="remix-css"], [class*="select__control"]');
                let val = el.value || el.innerText || '';
                if (isReactSelect) {
                    const ctrl = el.closest('.select, [class*="select"], .field-wrapper')?.querySelector('.select__control');
                    if (ctrl && ctrl.innerText && !ctrl.innerText.includes('Select...')) {
                        val = ctrl.innerText.trim();
                    }
                }
                const req = el.required || el.getAttribute('aria-required') === 'true' || label.includes('*');

                let selector = el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : '');
                if (!selector) {
                    el.setAttribute('data-jh-id', 'jh_field_' + idx);
                    selector = '[data-jh-id="jh_field_' + idx + '"]';
                }

                let options = [];
                if (el.tagName.toLowerCase() === 'select') {
                    options = Array.from(el.options).map(o => o.text.trim()).filter(Boolean);
                }

                results.push({
                    selector: selector,
                    id: el.id || '',
                    name: el.name || '',
                    tag: el.tagName.toLowerCase(),
                    type: (el.getAttribute('type') || '').toLowerCase(),
                    label: label.trim().replace(/\\s+/g, ' '),
                    value: val.trim(),
                    required: req,
                    is_react_select: isReactSelect,
                    options: options
                });
            });
            return results;
        }''')

    def _fill_selector(self, page, selector: str, value: str):
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.scroll_into_view_if_needed(timeout=1500)
                loc.click(timeout=1500)
                loc.fill(value, timeout=1500)
        except Exception:
            try:
                # Fallback directly via evaluate
                page.eval_on_selector(selector, '(el, val) => { el.value = val; el.dispatchEvent(new Event("input", {bubbles: true})); el.dispatchEvent(new Event("change", {bubbles: true})); }', value)
            except Exception:
                pass

    def _select_option(self, page, selector: str, option_text: str):
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.select_option(label=option_text, timeout=1500)
        except Exception:
            pass

    def _get_react_select_options(self, page, selector: str) -> List[str]:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                parent = loc.locator('..')
                parent.click(timeout=1500)
                page.wait_for_timeout(300)
                opts = page.evaluate('''() => Array.from(document.querySelectorAll('[class*="option"]')).map(o => o.innerText.trim()).filter(Boolean)''')
                return opts
        except Exception:
            pass
        return []

    def _click_react_select_option(self, page, selector: str, option_text: str):
        try:
            opt_loc = page.locator(f'[class*="option"]:has-text("{option_text}")').first
            if opt_loc.count() > 0 and opt_loc.is_visible():
                opt_loc.click(timeout=1500)
                page.wait_for_timeout(300)
            else:
                loc = page.locator(selector).first
                loc.fill(option_text, timeout=1500)
                loc.press("Enter", timeout=1500)
                page.wait_for_timeout(300)
        except Exception:
            pass
