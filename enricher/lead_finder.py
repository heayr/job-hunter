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
        r'(?:t\.me/)(?!s/)([a-zA-Z0-9_]{4,32})',
        r'(?:пишите?\s+в\s+(?:телеграм|тг|tg))\s*[@]?([a-zA-Z0-9_]{4,32})',
        r'(?:контакт| hr| рекрутер| тимлид| lead| cto)[:\s]+[@]?([a-zA-Z0-9_]{4,32})'
    ]
    # Known channel names, bots, and non-personal handles to ignore
    ignored_channels = {
        'telegram', 'channel', 'bot', 'react_jobs', 'frontend_jobs', 'devjobs',
        'habr_career', 'type', 'context', 'id', 'vocab', 'job_react', 'forfrontend',
        'normrabota', 'javascript_jobs_feed', 'remote_it_jobs', 'getitrussia',
        'job_hunter', 'react_channels', 'frontend_channels', 'hh_ru', 'headhunter',
        'superjob', 'rabota', 'linkedin', 'github', 'gitlab', 'stackoverflow',
        'medium', 'devto', 'habr', 'vc', 'career', 'jobs', 'hiring', 'remote',
        'startup', 'vacancy', 'job', 'work', 'resume', 'cv', 'apply',
        's', 'p', 'join', 'chat', 'group', 'public', 'news', 'blog',
        'instagram', 'twitter', 'facebook', 'youtube', 'tiktok', 'reddit',
        'google', 'apple', 'microsoft', 'amazon', 'meta', 'openai',
    }
    for pattern in tg_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            handle = match.group(1).strip().rstrip('.,;:!?')
            if handle.lower() not in ignored_channels and len(handle) >= 4:
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


def clean_company_name(raw_name: str, title: str = "", description: str = "") -> str:
    """
    Cleans legal noise, prefixes and quotes from company name.
    Extracts real brand if raw_name is a generic portal placeholder.
    """
    if not raw_name:
        raw_name = ""

    name = raw_name.strip()

    # 1. If placeholder like 'Компания на Habr', 'Работодатель на SuperJob', 'Unknown Company'
    is_placeholder = bool(re.search(r'компания|работодатель|unknown|remote company|не указана', name, re.IGNORECASE))

    if is_placeholder and title:
        title_patterns = [
            r'[\|\@]\s*([A-Za-zА-Яа-я0-9\-\.\s]{2,30})$',
            r'\b(?:в|at|for|для)\s+([A-Za-zА-Яа-я0-9\-\.\s]{2,30})$',
            r'\b(?:в|at|for|для)\s+([А-ЯA-Z][a-zA-Zа-яА-Я0-9\-_]+)'
        ]
        for pat in title_patterns:
            m = re.search(pat, title)
            if m:
                extracted = m.group(1).strip()
                if len(extracted) >= 2 and not re.search(r'команда|проект|отдел', extracted, re.IGNORECASE):
                    name = extracted
                    break

    # 2. Clean legal prefixes/suffixes: ООО, ПАО, ЗАО, АО, ИП, LLC, Ltd, Inc, GmbH
    name = re.sub(r'[\"\'«»„“”]', '', name)
    legal_patterns = [
        r'\b(?:ооо|пао|зао|нао|ао|ип)\b',
        r'\b(?:llc|ltd|inc|corp|corporation|gmbh|co\.)\b',
        r'\((?:пао|ооо|зао|ао|ип)\)',
    ]
    for lp in legal_patterns:
        name = re.sub(lp, '', name, flags=re.IGNORECASE)

    name = re.sub(r'\(\s*\)|\[\s*\]', '', name)
    name = re.sub(r'\s+', ' ', name).strip(' -.,/|')
    return name if name else (raw_name.strip() or "Компания")


def generate_direct_sourcing_links(company: str, title: str = "", lang: str = "ru") -> Dict[str, str]:
    """
    Generates targeted direct sourcing and OSINT search URLs for reaching
    company career pages (ATS) and hiring leads directly without aggregators.
    """
    import urllib.parse
    clean_comp = clean_company_name(company, title)
    clean_role = re.sub(r'[\|\(\)\/].*$', '', title).strip() or "Frontend"
    is_en = lang == "en"

    # 1. Direct ATS / Careers
    ats_query = f'"{clean_comp}" (site:greenhouse.io OR site:lever.co OR site:ashbyhq.com OR site:workable.com OR inurl:careers OR inurl:jobs) "{clean_role}"'
    ats_url = f"https://www.google.com/search?q={urllib.parse.quote(ats_query)}"

    # 2. Setka (Russian professional tech network by hh.ru)
    setka_query = f'site:setka.ru "{clean_comp}" (HR OR рекрутер OR CTO OR тимлид OR frontend)'
    setka_url = f"https://www.google.com/search?q={urllib.parse.quote(setka_query)}"

    # 3. HR / Recruiter search
    if is_en:
        hr_query = f'site:linkedin.com/in "{clean_comp}" ("Technical Recruiter" OR "Talent Acquisition" OR "Recruiter" OR "Head of HR")'
    else:
        hr_query = f'(site:linkedin.com/in OR site:t.me OR site:habr.com/ru/users OR site:setka.ru) "{clean_comp}" (рекрутер OR HR OR "talent acquisition" OR "найм")'
    hr_url = f"https://www.google.com/search?q={urllib.parse.quote(hr_query)}"

    # 4. CTO / Tech Lead search
    if is_en:
        cto_query = f'site:linkedin.com/in "{clean_comp}" ("CTO" OR "Engineering Manager" OR "Head of Engineering" OR "Tech Lead" OR "VP of Engineering")'
    else:
        cto_query = f'(site:linkedin.com/in OR site:habr.com/ru/users OR site:setka.ru) "{clean_comp}" (CTO OR "Engineering Manager" OR "Tech Lead" OR "Тимлид Frontend" OR "Руководитель разработки")'
    cto_url = f"https://www.google.com/search?q={urllib.parse.quote(cto_query)}"

    # 5. Corporate email search
    email_query = f'"{clean_comp}" ("careers@" OR "jobs@" OR "hr@" OR email) hiring'
    email_url = f"https://www.google.com/search?q={urllib.parse.quote(email_query)}"

    return {
        "clean_company": clean_comp,
        "direct_ats": ats_url,
        "setka": setka_url,
        "hr": hr_url,
        "cto": cto_url,
        "email": email_url
    }


if __name__ == "__main__":
    sample = "По всем вопросам пишите тимлиду Игорю в телеграм: @techlead_igor или на почту hr@fintech.io"
    print(extract_contacts(sample))
    print(clean_company_name("Банк ВТБ (ПАО)"))
    print(clean_company_name("ООО «Яндекс Крауд»"))
    print(clean_company_name("Компания на Habr", title="Frontend Developer | Sber"))

