import re
from typing import Dict, Any, List, Optional


class FieldCategory:
    CONTACT_FIRST_NAME = "CONTACT_FIRST_NAME"
    CONTACT_LAST_NAME = "CONTACT_LAST_NAME"
    CONTACT_FULL_NAME = "CONTACT_FULL_NAME"
    CONTACT_EMAIL = "CONTACT_EMAIL"
    CONTACT_PHONE = "CONTACT_PHONE"
    CONTACT_LOCATION = "CONTACT_LOCATION"
    CONTACT_LINKEDIN = "CONTACT_LINKEDIN"
    CONTACT_GITHUB = "CONTACT_GITHUB"
    CONTACT_PORTFOLIO = "CONTACT_PORTFOLIO"
    CONTACT_TELEGRAM = "CONTACT_TELEGRAM"
    RESUME_FILE = "RESUME_FILE"
    COVER_LETTER = "COVER_LETTER"
    SCREENING_SALARY = "SCREENING_SALARY"
    SCREENING_NOTICE = "SCREENING_NOTICE"
    SCREENING_AUTHORIZATION = "SCREENING_AUTHORIZATION"
    SCREENING_EXPERIENCE_YEARS = "SCREENING_EXPERIENCE_YEARS"
    SCREENING_ENGLISH = "SCREENING_ENGLISH"
    CUSTOM_TECHNICAL_QUESTION = "CUSTOM_TECHNICAL_QUESTION"
    APPLY_ENTRY_BUTTON = "APPLY_ENTRY_BUTTON"
    SUBMIT_BUTTON = "SUBMIT_BUTTON"
    NEXT_BUTTON = "NEXT_BUTTON"
    UNKNOWN = "UNKNOWN"


def classify_form_element(element: Dict[str, Any], profile: Dict[str, Any], has_input_fields: bool = True) -> Dict[str, Any]:
    """
    Classifies a single interactive element semantically and maps it
    to a verified value from Master Experience.
    """
    tag = element.get("tag", "").lower()
    type_ = (element.get("type") or "").lower()
    label = (element.get("label") or "").lower()
    placeholder = (element.get("placeholder") or "").lower()
    btn_text = (element.get("button_text") or "").lower()
    combined_text = f"{label} {placeholder} {btn_text}".strip()

    ident = profile.get("identity", {})
    contacts = ident.get("contacts", {})
    screening = profile.get("screening_facts", {})

    category = FieldCategory.UNKNOWN
    recommended_value = None
    action = "ignore"

    # Buttons or interactive links
    if tag in ("button", "a") or element.get("is_submit"):
        if re.search(r'(?:submit|apply|send|отправить|подать|откликнуться|отклик|finish)', combined_text):
            if not has_input_fields:
                return {
                    "element_id": element.get("element_id"),
                    "category": FieldCategory.APPLY_ENTRY_BUTTON,
                    "action": "click",
                    "recommended_value": None,
                    "required": False,
                    "label": element.get("label") or element.get("button_text", "Откликнуться"),
                    "tag": tag,
                    "type": type_
                }
            return {
                "element_id": element.get("element_id"),
                "category": FieldCategory.SUBMIT_BUTTON,
                "action": "submit_gate",
                "recommended_value": None,
                "required": False,
                "label": element.get("label") or element.get("button_text", "Submit"),
                "tag": tag,
                "type": type_
            }
        elif re.search(r'(?:next|continue|далее|продолжить)', combined_text):
            return {
                "element_id": element.get("element_id"),
                "category": FieldCategory.NEXT_BUTTON,
                "action": "click",
                "recommended_value": None,
                "required": False,
                "label": element.get("label") or element.get("button_text", "Next"),
                "tag": tag,
                "type": type_
            }

    # File input
    if type_ == "file" or re.search(r'(?:resume|cv|curriculum vitae|резюме)', combined_text):
        return {
            "element_id": element.get("element_id"),
            "category": FieldCategory.RESUME_FILE,
            "action": "upload",
            "recommended_value": "COMPILED_CV_ARTIFACT"
        }

    # Standard Contacts
    if type_ == "email" or re.search(r'\b(?:e[- ]?mail|почта)\b', combined_text):
        category = FieldCategory.CONTACT_EMAIL
        recommended_value = contacts.get("email") or "candidate@example.com"
        action = "fill"

    elif type_ == "tel" or re.search(r'\b(?:phone|mobile|cell|телефон|тел)\b', combined_text):
        category = FieldCategory.CONTACT_PHONE
        recommended_value = contacts.get("phone") or "+79998291788"
        action = "fill"

    elif re.search(r'\b(?:first\s*name|given\s*name|имя)\b', combined_text) and not re.search(r'\b(?:last|фамилия)\b', combined_text):
        category = FieldCategory.CONTACT_FIRST_NAME
        recommended_value = ident.get("first_name") or ident.get("name", "").split()[0]
        action = "fill"

    elif re.search(r'\b(?:last\s*name|surname|family\s*name|фамилия)\b', combined_text):
        category = FieldCategory.CONTACT_LAST_NAME
        parts = ident.get("name", "").split()
        recommended_value = ident.get("last_name") or (" ".join(parts[1:]) if len(parts) > 1 else "")
        action = "fill"

    elif re.search(r'\b(?:full\s*name|your\s*name|applicant\s*name|фио)\b', combined_text):
        category = FieldCategory.CONTACT_FULL_NAME
        recommended_value = ident.get("name") or "Egor Myshinsky"
        action = "fill"

    elif "linkedin" in combined_text:
        category = FieldCategory.CONTACT_LINKEDIN
        recommended_value = contacts.get("linkedin") or "https://linkedin.com/in/potatochipasu"
        action = "fill"

    elif "github" in combined_text:
        category = FieldCategory.CONTACT_GITHUB
        recommended_value = contacts.get("github") or "https://github.com/heayr"
        action = "fill"

    elif re.search(r'\b(?:portfolio|website|web site|портфолио|веб-сайт)\b', combined_text):
        category = FieldCategory.CONTACT_PORTFOLIO
        recommended_value = contacts.get("portfolio") or "https://nologs.website"
        action = "fill"

    elif re.search(r'\b(?:telegram|телеграм|tg)\b', combined_text):
        category = FieldCategory.CONTACT_TELEGRAM
        recommended_value = contacts.get("telegram") or "@PotatoChipasu"
        action = "fill"

    elif re.search(r'\b(?:city|location|residence|город|локация|проживание)\b', combined_text) and not re.search(r'cover', combined_text):
        category = FieldCategory.CONTACT_LOCATION
        recommended_value = ident.get("location") or screening.get("location", "Москва / Ереван / Remote")
        action = "fill"

    # Screening Questions & Facts
    elif re.search(r'(?:salary|compensation|зарплат|ожидания по зп|ставка|rate)', combined_text):
        category = FieldCategory.SCREENING_SALARY
        sal_data = screening.get("salary", {})
        if "usd" in combined_text or "$" in combined_text:
            recommended_value = str(sal_data.get("target_usd", 5000))
        elif "rub" in combined_text or "руб" in combined_text or "₽" in combined_text:
            recommended_value = str(sal_data.get("target_rub", 400000))
        else:
            recommended_value = str(sal_data.get("target_rub", 400000))
        action = "fill"

    elif re.search(r'(?:notice\s*period|start\s*date|когда готовы приступить|срок выхода)', combined_text):
        category = FieldCategory.SCREENING_NOTICE
        recommended_value = screening.get("notice_period", "2 недели / 2 weeks")
        action = "fill"

    elif re.search(r'(?:authorized to work|legal authorization|право на работу|гражданство|citizenship|visa|work permit)', combined_text):
        category = FieldCategory.SCREENING_AUTHORIZATION
        if tag == "select" or type_ in ("radio", "checkbox"):
            # Usually Yes/No or option
            recommended_value = "Yes" if "authorized" in combined_text or "право" in combined_text else "No"
            action = "select" if tag == "select" else "fill"
        else:
            recommended_value = screening.get("work_authorization", "Гражданство РФ, самозанятость, ИП, B2B контракт")
            action = "fill"

    elif re.search(r'\b(?:years\s+of\s+experience|how\s+many\s+years|сколько\s+лет\s+опыта|общий\s+стаж)\b', combined_text) and tag != "textarea":
        category = FieldCategory.SCREENING_EXPERIENCE_YEARS
        if tag == "select":
            action = "select"
            recommended_value = "5+"
        else:
            recommended_value = str(screening.get("years_of_experience_num", 6))
            action = "fill"

    elif re.search(r'(?:english|уровень английского|language level)', combined_text):
        category = FieldCategory.SCREENING_ENGLISH
        recommended_value = screening.get("english_level", "C1 (Advanced)")
        action = "select" if tag == "select" else "fill"

    # Cover Letter / Open Message
    elif tag == "textarea" and re.search(r'(?:cover\s*letter|сопроводительн|tell us why|why do you want|about yourself|note to hiring)', combined_text):
        category = FieldCategory.COVER_LETTER
        action = "generate_cover_letter"
        recommended_value = "DYNAMIC_COVER_LETTER"

    # Custom Technical / Situation Questions
    elif tag == "textarea" or len(label) > 35:
        category = FieldCategory.CUSTOM_TECHNICAL_QUESTION
        action = "generate_answer"
        recommended_value = "DYNAMIC_EVIDENCE_ANSWER"

    else:
        category = FieldCategory.UNKNOWN
        if element.get("required"):
            action = "ask_user"
        else:
            action = "skip"

    return {
        "element_id": element.get("element_id"),
        "category": category,
        "action": action,
        "recommended_value": recommended_value,
        "required": element.get("required", False),
        "label": element.get("label", ""),
        "tag": tag,
        "type": type_
    }


def classify_form_elements(elements: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Classifies all interactive elements on the page."""
    # Check if any input/textarea/select/file fields are present
    has_input_fields = any(
        el.get("tag", "").lower() in ("input", "textarea", "select")
        and (el.get("type") or "").lower() not in ("hidden", "submit", "button")
        for el in elements
    )
    return [classify_form_element(el, profile, has_input_fields=has_input_fields) for el in elements]
