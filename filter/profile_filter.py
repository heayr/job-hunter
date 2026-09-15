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
    r'javascript',
    r'typescript',
    r'web[- ]?developer',
    r'веб-разработчик'
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

def is_qualified_vacancy(title: str, skills: str = "", description: str = "", company: str = "") -> Tuple[bool, str]:
    full_text = f"{title} {company} {skills} {description}".lower()
    
    # 0. Candidate resume exclusion (skip people posting their own CVs)
    resume_target = f"{title} {company} {description}".lower()
    if re.search(r'(?:#резюме|\bрезюме\b|\bcv\b|\bищу работу\b|open to work|looking for a job|готов к предложениям|\bкандидат\b|обо мне:\s|о себе:\s|обо мне\b|опыт работы:)', resume_target):
        return False, "Not a vacancy (Candidate Resume / CV)"

    # 1. Level exclusion: Senior/Lead/Founder level, never intern or junior
    if re.search(r'(?:стаж[её]р\w*|стажиров\w*|\bintern\b|\binternship\b|\bмладший\b|\bjunior\b|\bjr\.?\b)', full_text):
        return False, "Level: Junior/Intern"
        
    # 2. Check blacklist in title & company
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, f"{title} {company}".lower()):
            return False, f"Blacklist match: {pattern}"
            
    # 3. Check positive match in title
    for pattern in POSITIVE_ROLE_PATTERNS:
        if re.search(pattern, title.lower()):
            return True, f"Matched role: {pattern}"
            
    return False, "No positive frontend/fullstack/product engineer keyword in title"
