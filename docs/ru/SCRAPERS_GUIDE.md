# 🔌 Руководство по скраперам и сбору вакансий

**[English](../SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[Русский](SCRAPERS_GUIDE.md)**

В этом руководстве подробно описаны 14 встроенных сборщиков вакансий Job Hunter CRM, единый контракт данных и пошаговый процесс создания собственных парсеров за 5 минут.

---

## 🌐 Каталог встроенных сборщиков

Job Hunter включает 14 готовых модулей сбора для рынков РФ/СНГ и международного Remote:

| Файл скрапера | Целевая платформа | Рынок | Метод / Протокол |
|---|---|---|---|
| `hh_scraper.py` | HeadHunter (HH.ru) | 🇷🇺 РФ / СНГ | Публичный REST API (`api.hh.ru/vacancies`) |
| `habr_scraper.py` | Хабр Карьера | 🇷🇺 РФ / СНГ | HTML-скрапинг с CSS-селекторами и пагинацией |
| `superjob_scraper.py` | SuperJob | 🇷🇺 РФ / СНГ | Парсинг публичного поиска / API |
| `rabotaru_scraper.py` | Работа.ру | 🇷🇺 РФ / СНГ | Поисковый API и парсинг JSON |
| `setka_scraper.py` | Сетка (Setka.ru) | 🇷🇺 РФ / СНГ | Мобильный / веб-API платформы |
| `getmatch_scraper.py` | GetMatch | 🇷🇺 РФ / СНГ | REST API (`getmatch.ru/api/offers`) |
| `telegram_scraper.py` | Telegram-каналы и Userbot | 🇷🇺 РФ / СНГ | Веб-превью каналов + клиент Telethon MTProto |
| `remoteok_scraper.py` | RemoteOK | 🌍 Global EN | Публичный JSON API (`remoteok.com/api`) |
| `remotive_scraper.py` | Remotive | 🌍 Global EN | REST API (`remotive.com/api/remote-jobs`) |
| `wwr_scraper.py` | WeWorkRemotely | 🌍 Global EN | Тематические RSS-ленты |
| `crypto_scraper.py` | CryptoJobsList | 🌍 Global EN | Парсинг веб-страниц и JSON-фида |
| `hackernews_scraper.py` | Hacker News ("Who's Hiring") | 🌍 Global EN | Algolia HN Search API и парсинг веток обсуждений |
| `jobicy_scraper.py` | Jobicy | 🌍 Global EN | Публичный Remote Jobs API |
| `ats_scraper.py` | Greenhouse, Lever, Ashby, Workable | 🌍 Global EN | Прямой сбор с карьерных страниц компаний |

---

## 📋 Контракт данных вакансии

Каждый модуль парсера должен возвращать список словарей Python следующего формата:

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
    "contact_handle": "@techlead_igor"              # Прямой контакт (опционально)
}
```

---

## 🛠 Добавление своего парсера за 3 шага

### Шаг 1: Создайте файл парсера
Создайте новый файл `scrapers/my_portal_scraper.py`:

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
                    "market": "ru",  # 'ru' или 'en'
                    "skills": ", ".join(item.get("tags", []))
                })
        except Exception as e:
            print(f"Ошибка при парсинге MyPortal: {e}")
            
        return results
```

### Шаг 2: Зарегистрируйте парсер в `harvest.py`
Откройте `harvest.py` и добавьте вызов вашего сборщика в общий пайплайн:

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
Свежесобранные вакансии будут автоматически проверены на дубликаты, отфильтрованы через Anti-BS фильтр, сопоставлены с профилем кандидата и сохранены в базу `jobs.db`.
