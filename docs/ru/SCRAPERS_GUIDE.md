# 🔌 Руководство по созданию парсеров

**[English](../SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[Русский](SCRAPERS_GUIDE.md)**

В этом руководстве объясняется, как устроен сбор вакансий в Job Hunter CRM, и как добавить свой собственный парсер за 5 минут.

---

## 📋 Контракт данных вакансии

Каждый модуль парсера или сканера должен возвращать список словарей Python следующего формата:

```python
{
    "title": "Senior Frontend Developer",           # Название позиции (строка, обязательно)
    "company": "Финтех Инновации",                  # Название компании (строка, обязательно)
    "url": "https://example.com/jobs/12345",         # Прямая ссылка на вакансию (строка, обязательно)
    "description": "Полный текст описания...",       # Текст описания вакансии (строка, обязательно)
    "market": "ru",                                 # 'ru' (РФ/СНГ) или 'en' (International Remote)
    "skills": "React, TypeScript, Next.js",         # Ключевые технологии через запятую (опционально)
    "salary": "250 000 - 350 000 руб.",             # Зарплатная вилка (опционально)
    "contact_type": "telegram",                     # 'telegram', 'email' или 'link' (опционально)
    "contact_handle": "@techlead_igor"              # Контакт для прямого отклика (опционально)
}
```

---

## 🛠 Добавление своего парсера за 3 шага

### Шаг 1: Создайте файл парсера
Создайте новый файл в `scrapers/my_portal_scraper.py`:

```python
import json
import urllib.request
from typing import List, Dict, Any

class MyPortalScraper:
    def __init__(self):
        self.api_url = "https://api.myportal.com/vacancies"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        results = []
        try:
            req = urllib.request.Request(
                self.api_url, 
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            for item in data.get("jobs", []):
                results.append({
                    "title": item.get("role_title", "Software Engineer"),
                    "company": item.get("company_name", "Tech Co"),
                    "url": item.get("apply_url"),
                    "description": item.get("details", ""),
                    "market": "ru",  # РФ/СНГ рынок
                    "skills": ", ".join(item.get("tags", []))
                })
        except Exception as e:
            print(f"Ошибка при парсинге MyPortal: {e}")
            
        return results
```

### Шаг 2: Зарегистрируйте парсер в `harvest.py`
Откройте `harvest.py` и добавьте запуск вашего сборщика в общий пайплайн:

```python
from scrapers.my_portal_scraper import MyPortalScraper

def run_harvest():
    # ... существующие сборщики ...
    print("Собираем вакансии с MyPortal...")
    my_jobs = MyPortalScraper().fetch_jobs()
    all_jobs.extend(my_jobs)
```

### Шаг 3: Запустите и проверьте
Запустите сбор:
```bash
python3 harvest.py
```
Свежесобранные вакансии будут автоматически проверены на дубликаты, пропущены через Anti-BS фильтр, оценены по соответствию стеку и сохранены в локальную базу `jobs.db`.
