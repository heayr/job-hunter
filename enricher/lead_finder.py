import re
from typing import Dict, Any, Optional

def extract_contacts(text: str) -> Dict[str, Any]:
    """
    Extracts direct contacts (Telegram handles, emails, phones, names) from vacancy text.
    """
    contacts = {
        "telegram": None,
        "email": None,
        "phone": None,
        "contact_name": None,
        "contact_role": None
    }
    
    if not text:
        return contacts

    # 1. Telegram extraction
    tg_patterns = [
        r'(?:t\.me/|@)([a-zA-Z0-9_]{4,32})',
        r'телеграм[^\w]*[@]?([a-zA-Z0-9_]{4,32})',
        r'тг[^\w]*[@]?([a-zA-Z0-9_]{4,32})'
    ]
    for pattern in tg_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            handle = match.group(1)
            # Avoid channel names or common non-personal handles / json-ld keywords
            ignored = ['telegram', 'channel', 'bot', 'react_jobs', 'frontend_jobs', 'devjobs', 'habr_career', 'type', 'context', 'id', 'vocab']
            if handle.lower() not in ignored:
                contacts["telegram"] = f"@{handle}"
                break

    # 2. Email extraction
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)
    if email_match:
        contacts["email"] = email_match.group(1)

    # 3. Phone extraction (RU/international format)
    phone_match = re.search(r'(\+7|8)[\s\-(]?\d{3}[\s\-) ]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text)
    if phone_match:
        contacts["phone"] = phone_match.group(0)

    # 4. Contact Name / Role Heuristics
    name_patterns = [
        r'(?:контакт|писать|hr|рекрутер|тимлид|lead|cto)[:\s]+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)',
        r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*\(?(?:hr|рекрутер|тимлид|recruiter)\)?'
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate_name = match.group(1).strip()
            if len(candidate_name.split()) <= 2:
                contacts["contact_name"] = candidate_name
                break

    # Determine primary contact handle & type
    if contacts["telegram"]:
        contacts["primary_handle"] = contacts["telegram"]
        contacts["primary_type"] = "telegram"
    elif contacts["email"]:
        contacts["primary_handle"] = contacts["email"]
        contacts["primary_type"] = "email"
    else:
        contacts["primary_handle"] = ""
        contacts["primary_type"] = "portal"

    return contacts

if __name__ == "__main__":
    sample = "По всем вопросам пишите тимлиду Игорю в телеграм: @techlead_igor или на почту hr@fintech.io"
    print(extract_contacts(sample))
