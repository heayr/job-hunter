import re
from typing import Dict, Any, List, Optional


def verify_application_form(
    elements: List[Dict[str, Any]],
    classified_elements: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Automated Verification Engine for job applications.
    Inspects all DOM interactive elements prior to requesting human approval.
    Guarantees:
    - Zero missing required fields
    - Valid email, phone, and URL formats
    - File upload confirmation when required
    - Detection of validation errors and CAPTCHA
    """
    if not isinstance(elements, list):
        elements = []

    missing_required = []
    validation_errors = []
    dom_errors = []
    has_captcha = False
    fields_checked = 0

    # Build quick lookup for classification if provided
    classified_map = {}
    if classified_elements:
        for c in classified_elements:
            eid = c.get("element_id")
            if eid:
                classified_map[eid] = c

    for el in elements:
        tag = el.get("tag", "").lower()
        input_type = el.get("type", "").lower()
        elem_id = el.get("element_id") or el.get("elem_id") or el.get("id") or ""
        label = (el.get("label") or el.get("name") or el.get("placeholder") or "").strip()
        value = str(el.get("current_value") if el.get("current_value") is not None else el.get("value") or "").strip()
        checked = el.get("checked", False)
        is_required = el.get("required", False)
        error = el.get("error") or el.get("validation_message") or el.get("validation_error")
        aria_invalid = el.get("aria-invalid") in (True, "true")

        # Skip hidden inputs or submit/button tags for value completeness
        if input_type in ("hidden", "submit", "button", "reset") or tag == "button":
            continue

        fields_checked += 1

        # Check for CAPTCHA
        lower_sig = f"{label} {elem_id} {input_type}".lower()
        if el.get("has_captcha") or any(cap in lower_sig for cap in ["recaptcha", "hcaptcha", "turnstile", "cf-turnstile", "капча", "captcha"]):
            has_captcha = True

        # Check DOM-level errors
        if error or aria_invalid:
            dom_errors.append({
                "element_id": elem_id,
                "label": label,
                "error": str(error or "Field marked as invalid by browser/DOM")
            })

        # Check requirement heuristics (explicit required or asterisk in label)
        required_by_label = bool(re.search(r'[\*]|обязательн|required', label, re.I))
        effective_required = is_required or required_by_label

        if input_type in ("checkbox", "radio"):
            if effective_required and not checked:
                # If it's a consent or required checkbox
                missing_required.append({
                    "element_id": elem_id,
                    "label": label,
                    "type": input_type,
                    "reason": "Required checkbox is not checked"
                })
        elif input_type == "file":
            # For file upload, check files_count, attached_files, has_file, or value
            has_file = (
                el.get("has_file", False)
                or el.get("files_count", 0) > 0
                or bool(el.get("attached_files"))
                or bool(value)
            )
            if effective_required and not has_file:
                missing_required.append({
                    "element_id": elem_id,
                    "label": label,
                    "type": "file",
                    "reason": "Required resume/CV attachment is missing"
                })
        else:
            # Text, email, tel, textarea, select
            if effective_required and not value:
                missing_required.append({
                    "element_id": elem_id,
                    "label": label,
                    "type": input_type or tag,
                    "reason": "Required field is empty"
                })

        # Format Validations for populated fields
        if value:
            # Email validation
            if input_type == "email" or re.search(r'\b(?:email|e-mail|почта)\b', label, re.I):
                if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
                    validation_errors.append({
                        "element_id": elem_id,
                        "label": label,
                        "value": value,
                        "reason": f"Invalid email format: '{value}'"
                    })

            # Phone validation
            elif input_type == "tel" or re.search(r'\b(?:phone|tel|телефон)\b', label, re.I):
                digits = re.sub(r'\D', '', value)
                if len(digits) < 7 or len(digits) > 15:
                    validation_errors.append({
                        "element_id": elem_id,
                        "label": label,
                        "value": value,
                        "reason": f"Invalid phone number length (found {len(digits)} digits, expected 7-15)"
                    })

            # Web URL validation
            elif input_type == "url" or re.search(r'\b(?:portfolio|github|linkedin|сайт|портфолио)\b', label, re.I):
                if not (value.startswith("http://") or value.startswith("https://") or value.startswith("@")):
                    validation_errors.append({
                        "element_id": elem_id,
                        "label": label,
                        "value": value,
                        "reason": f"Invalid URL (must start with http:// or https://): '{value}'"
                    })

    # Anti-BS Rule: If no interactive fields were found/checked, form cannot be considered valid or verified
    if fields_checked == 0:
        return {
            "is_valid": False,
            "can_submit": False,
            "has_captcha": has_captcha,
            "total_fields_checked": 0,
            "missing_required": [{"reason": "Форма или поля ввода не обнаружены на странице"}],
            "validation_errors": [],
            "dom_errors": dom_errors,
            "summary": "Поля формы отклика не обнаружены на странице браузера. Проверьте адрес или откройте форму вручную."
        }

    is_valid = (len(missing_required) == 0 and len(validation_errors) == 0 and len(dom_errors) == 0)
    can_submit = is_valid and not has_captcha

    summary_parts = []
    if is_valid:
        summary_parts.append(f"All {fields_checked} interactive fields verified successfully.")
    else:
        if missing_required:
            summary_parts.append(f"{len(missing_required)} required fields are missing.")
        if validation_errors:
            summary_parts.append(f"{len(validation_errors)} fields failed format validation.")
        if dom_errors:
            summary_parts.append(f"{len(dom_errors)} fields have DOM error flags.")

    if has_captcha:
        summary_parts.append("CAPTCHA detected; human intervention required.")

    return {
        "is_valid": is_valid,
        "can_submit": can_submit,
        "has_captcha": has_captcha,
        "total_fields_checked": fields_checked,
        "missing_required": missing_required,
        "validation_errors": validation_errors,
        "dom_errors": dom_errors,
        "summary": " ".join(summary_parts)
    }
