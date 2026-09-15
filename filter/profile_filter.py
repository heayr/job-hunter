import re
from typing import Tuple

POSITIVE_ROLE_PATTERNS = [
    r'frontend',
    r'фронтенд',
    r'react',
    r'next\.?js',
    r'full-?stack',
    r'фуллстек',
    r'product engineer',
    r'ui (?:engineer|developer|разработчик)',
    r'пользовательских интерфейсов',
    r'(?:javascript|typescript).*(?:developer|engineer|разработчик|программист|lead|архитектор)',
    r'(?:developer|engineer|разработчик|программист|lead).*(?:javascript|typescript)',
    r'web[- ]?developer',
    r'веб-разработчик',
    r'software engineer',
    r'product engineering'
]

BLACKLIST_PATTERNS = [
    r'\bpython\b',
    r'\bпитон\b',
    r'\bjava(?!script)\b',
    r'\bgolang\b',
    r'\bgo developer\b',
    r'\brust\b',
    r'\.net\b',
    r'\bc#\b',
    r'\bc\+\+\b',
    r'\bphp\b',
    r'\bruby\b',
    r'\bqa\b',
    r'тестиров',
    r'\bdwh\b',
    r'\boracle\b',
    r'pl/sql',
    r'sql developer',
    r'\bdevops\b',
    r'\bsre\b',
    r'системный администратор',
    r'sysadmin',
    r'\bаналитик\b',
    r'\banalyst\b',
    r'data engineer',
    r'торговых стратегий',
    r'руководитель направления',
    r'рэа',
    r'hardware',
    r'конструктор',
    r'\bios\b',
    r'\bandroid\b',
    r'\bflutter\b',
    r'\bangular\b',
    r'(?:wordpress|вордпресс|bitrix|битрикс|joomla|1с|1c)'
]

def detect_vacancy_grade(title: str, description: str = "") -> str:
    """Classifies vacancy grade based on title and description."""
    combined = f"{title} {description}".lower()
    if re.search(r'\b(?:lead|тимлид|лид|principal|architect|архитектор|head\s+of)\b', combined):
        return "Lead"
    if re.search(r'\b(?:senior|сеньор|сениор|сеньёр|sr\.?|старший)\b', combined):
        return "Senior"
    if re.search(r'(?:стаж[её]р\w*|стажиров\w*|\bintern\b|\binternship\b)', combined):
        return "Intern"
    if re.search(r'(?:\bjunior\b|\bjr\.?\b|\bмладший\b)', combined):
        return "Junior"
    if re.search(r'\b(?:middle|миддл|мидл|mid)\b', combined):
        return "Middle"
    return "Middle"


def is_qualified_vacancy(title: str, skills: str = "", description: str = "", company: str = "") -> Tuple[bool, str]:
    full_text = f"{title} {company} {skills} {description}".lower()
    header_text = f"{title} {company}".lower()
    
    # 0. Candidate resume exclusion (skip people posting their own CVs / self-promotions)
    if re.search(r'(?:#резюме\b|#cv\b|\bрезюме\b|\bcv\b|\bсоискател\w*)', header_text):
        return False, "Not a vacancy (Candidate Resume / CV in header)"

    candidate_phrases = [
        r'#резюме\b',
        r'#cv\b',
        r'\bищу работу\b',
        r'\bв поиске работы\b',
        r'\bв поисках работы\b',
        r'\bв поиске проекта\b',
        r'\bищу проект\b',
        r'\bищу команду\b',
        r'\bopen to work\b',
        r'\blooking for (?:a )?job\b',
        r'\blooking for (?:new )?opportunities\b',
        r'\bготов к предложениям\b',
        r'\bрассматриваю предложения\b',
        r'\bготов рассмотреть предложения\b',
        r'\bоткрыт к предложениям\b',
        r'\bобо мне:\b',
        r'\bо себе:\b',
        r'\bмой стек:\b',
        r'\bмои навыки:\b',
        r'\bобо мне\n',
        r'\bо себе\n',
        r'резюме\s*[:\-]',
        r'cv\s*[:\-]',
    ]
    for cp in candidate_phrases:
        if re.search(cp, full_text):
            return False, f"Not a vacancy (Candidate Resume / CV: {cp})"

    # 0.1 Ads / Webinars / Events exclusion
    ad_phrases = [
        r'\bвебинар\b',
        r'\bинтенсив\b',
        r'\bтестовый собес\b',
        r'\bпробное собеседование\b',
        r'\bбесплатный практикум\b',
        r'\bонлайн-практикум\b',
        r'\bпрямой эфир\b',
        r'\bподкаст\b',
        r'\bконференция\b',
        r'\bмитап\b',
        r'\bреклама\.\s*о рекламодателе\b',
        r'подарок для всех,\s*кто зарегается',
    ]
    for ap in ad_phrases:
        if re.search(ap, full_text):
            return False, f"Not a vacancy (Ad/Event: {ap})"

    # 1. Check blacklist in title & company
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, f"{title} {company}".lower()):
            # Allow mixed fullstack/frontend vacancies with secondary backend technologies
            if re.search(r'\b(?:full-?stack|фуллстек|frontend|фронтенд)\b', title.lower()):
                continue
            return False, f"Blacklist match: {pattern}"

    # 2. Positive role check in title
    matched_role = None
    for pattern in POSITIVE_ROLE_PATTERNS:
        if re.search(pattern, title.lower()):
            matched_role = pattern
            break

    if not matched_role:
        return False, "No positive frontend/fullstack/product engineer keyword in title"

    return True, f"Matched role: {matched_role}"
