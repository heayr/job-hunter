# 🔌 Scrapers & Harvester Guide

**[English](SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[Русский](ru/SCRAPERS_GUIDE.md)**

This guide details the 14 built-in job scrapers in Job Hunter CRM, explains the unified vacancy data contract, and walks through creating custom scrapers in under 5 minutes.

---

## 🌐 Built-in Scrapers Directory

Job Hunter includes 14 production scrapers across CIS and global remote tech markets:

| Scraper File | Target Platform | Market | Method / Protocol |
|---|---|---|---|
| `hh_scraper.py` | HeadHunter (HH.ru) | 🇷🇺 CIS / RU | Public REST API (`api.hh.ru/vacancies`) |
| `habr_scraper.py` | Хабр Карьера | 🇷🇺 CIS / RU | HTML scraping with CSS selectors & pagination |
| `superjob_scraper.py` | SuperJob | 🇷🇺 CIS / RU | Public search HTML / API parsing |
| `rabotaru_scraper.py` | Работа.ру | 🇷🇺 CIS / RU | Web search API & JSON parsing |
| `setka_scraper.py` | Сетка (Setka.ru) | 🇷🇺 CIS / RU | Mobile/web API parsing |
| `getmatch_scraper.py` | GetMatch | 🇷🇺 CIS / RU | REST API (`getmatch.ru/api/offers`) |
| `telegram_scraper.py` | Telegram Channels & Userbot | 🇷🇺 CIS / RU | Telegram web preview + Telethon MTProto client |
| `remoteok_scraper.py` | RemoteOK | 🌍 Global EN | Public JSON API (`remoteok.com/api`) |
| `remotive_scraper.py` | Remotive | 🌍 Global EN | REST API (`remotive.com/api/remote-jobs`) |
| `wwr_scraper.py` | WeWorkRemotely | 🌍 Global EN | Category RSS Feeds |
| `crypto_scraper.py` | CryptoJobsList | 🌍 Global EN | Web scraping & JSON feed |
| `hackernews_scraper.py` | Hacker News ("Who's Hiring") | 🌍 Global EN | Algolia HN Search API & thread parsing |
| `jobicy_scraper.py` | Jobicy | 🌍 Global EN | Public Remote Jobs API |
| `ats_scraper.py` | Greenhouse, Lever, Ashby, Workable | 🌍 Global EN | Direct company career page ATS ingestion |

---

## 📋 The Vacancy Data Contract

Every scraper module must return a list of Python dictionaries adhering to this specification:

```python
{
    "title": "Senior Frontend Developer",           # Job title (string, required)
    "company": "Fintech Innovations",               # Company name (string, required)
    "url": "https://example.com/jobs/12345",         # Direct job link (string, required)
    "description": "Full job description text...",   # Plain text description (string, required)
    "market": "ru",                                 # 'ru' (Local/CIS) or 'en' (International Remote)
    "skills": "React, TypeScript, Next.js",         # Comma-separated tech keywords (optional)
    "salary": "250,000 - 350,000 RUB",              # Salary range string (optional)
    "contact_type": "telegram",                     # 'telegram', 'email', or 'link' (optional)
    "contact_handle": "@techlead_igor"              # Direct contact handle or email (optional)
}
```

---

## 🛠 Adding a Custom Scraper in 3 Steps

### Step 1: Create the Scraper Module
Create a new file in `scrapers/my_portal_scraper.py`:

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
                    "market": "en",  # 'ru' or 'en'
                    "skills": ", ".join(item.get("tags", []))
                })
        except Exception as e:
            print(f"Error scraping MyPortal: {e}")
            
        return results
```

### Step 2: Register in `harvest.py`
Open `harvest.py` and import your scraper into the pipeline:

```python
from scrapers.my_portal_scraper import MyPortalScraper

def run_harvest():
    # ... existing scrapers ...
    print("Collecting from MyPortal...")
    my_jobs = MyPortalScraper().fetch_jobs()
    all_jobs.extend(my_jobs)
```

### Step 3: Run & Verify
Test your scraper execution:
```bash
python3 harvest.py
```
The newly scraped jobs will be automatically deduplicated, run through the Anti-BS filter, scored against candidate personas, and saved to `jobs.db`.
