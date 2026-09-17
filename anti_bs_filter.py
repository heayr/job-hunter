import re

def analyze_vacancy_traps(description: str):
    description = description.lower()
    warnings = []
    
    # 1. B2B / ИП check
    if re.search(r'\b(только ип|оформление как ип|оформление по ип|статус ип|индивидуальный предприниматель|самозанятость|самозанятый|b2b contract)\b', description):
        warnings.append("⚠️ Только ИП/Самозанятость!")
        
    # 2. Test Assignment Check
    if re.search(r'\b(тестовое задание|тестового задания|сделать тестовое|выполнить тестовое)\b', description):
        warnings.append("🛠 В вакансии упоминается ТЕСТОВОЕ ЗАДАНИЕ.")
        
    # 3. Attention Check / Hidden Words Check
    if re.search(r'(начн(?:и|ите)\s*(сопроводительное|письмо|отклик).*?со\s*слов(?:а|ас)\b)', description) or \
       re.search(r'(кодов(?:е|й)\s*слов(?:о|а))', description) or \
       re.search(r'(укаж(?:и|ите)\s*в\s*(отклике|сопроводительном).*?слов(?:о|а)\b)', description) or \
       re.search(r'(если.*дочитал.*напиш(?:и|ите))', description):
        warnings.append("🕵️ ПРОВЕРКА НА ВНИМАТЕЛЬНОСТЬ! В тексте просят кодовое слово.")
        
    # 4. Strict Github Check
    if re.search(r'\b(github\s*профиль|ссылку\s*на\s*github|проверк(?:а|у)\s*через\s*github|покажите\s*код)\b', description):
        warnings.append("💻 Хотят видеть код/GitHub. Обязательно подсвети ссылку на репозиторий!")
        
    # 5. English level requirement
    if re.search(r'\b(advanced|fluent|c1|c2|свободный английский|свободное владение)\b', description):
        warnings.append("🇬🇧 Требуется свободный английский (C1/C2).")

    return warnings
