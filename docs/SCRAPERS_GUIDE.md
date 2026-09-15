# 🔌 Scrapers & Harvester Guide

**[English](SCRAPERS_GUIDE.md)** &nbsp;•&nbsp; **[Русский](ru/SCRAPERS_GUIDE.md)**

This guide explains how Job Hunter CRM ingests job postings and how you can add a custom scraper in under 5 minutes.

---

## 📋 The Vacancy Data Contract

Every scraper or scanner module must return a list of Python dictionaries adhering to this specification:

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
    "contact_handle": "@techlead_igor"              # Username or email for direct outreach (optional)
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
                    "market": "en",  # Mark as international remote
                    "skills": ", ".join(item.get("tags", []))
                })
        except Exception as e:
            print(f"Error scraping MyPortal: {e}")
            
        return results
```

### Step 2: Register in `harvest.py`
Open `harvest.py` and add your scraper to the active pipeline:

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
The newly scraped jobs will be automatically deduplicated, run through the Anti-BS filter, scored, and stored in `jobs.db`.
