import urllib.request
import urllib.error
import json
import re
from typing import List, Dict, Any

from scrapers.base import BaseScraper


class HHScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "hh.ru"

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        url = "https://api.hh.ru/vacancies?text=Frontend+OR+React+OR+Next.js&search_field=name&order_by=publication_time&period=14&per_page=20"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))

            for item in data.get('items', []):
                if item.get('archived'):
                    continue
                vac_id = f"hh:{item.get('id', '')}"
                desc_clean = ""

                # Fetch detailed description if possible
                try:
                    job_url = f"https://api.hh.ru/vacancies/{item['id']}"
                    job_req = urllib.request.Request(job_url, headers=headers)
                    with urllib.request.urlopen(job_req, timeout=5) as job_resp:
                        job_data = json.loads(job_resp.read().decode('utf-8'))
                        desc = job_data.get('description', '')
                        desc_clean = re.sub(r'<[^>]+>', ' ', desc).strip()
                        key_skills = [sk['name'] for sk in job_data.get('key_skills', [])]
                        skills_str = ", ".join(key_skills) if key_skills else "React, TypeScript, Frontend"
                except Exception:
                    skills_str = "React, TypeScript, Frontend"

                salary_str = "Не указана"
                if item.get('salary'):
                    sal = item['salary']
                    fr = sal.get('from')
                    to = sal.get('to')
                    curr = sal.get('currency', 'RUR')
                    if fr and to:
                        salary_str = f"{fr} - {to} {curr}"
                    elif fr:
                        salary_str = f"от {fr} {curr}"
                    elif to:
                        salary_str = f"до {to} {curr}"

                loc = item.get("area", {}).get("name", "РФ / Remote")
                is_remote = bool(re.search(r'удален|remote', (item.get("schedule", {}).get("name", "") + " " + desc_clean), re.I))

                vacancies.append({
                    "id": vac_id,
                    "source": "hh.ru",
                    "title": item.get("name", "Frontend Developer"),
                    "company": item.get("employer", {}).get("name", "Компания на HH"),
                    "url": item.get("alternate_url", f"https://hh.ru/vacancy/{item.get('id')}"),
                    "salary": salary_str,
                    "location": loc,
                    "is_remote": 1 if is_remote else 0,
                    "contact_name": "",
                    "contact_handle": item.get("alternate_url", ""),
                    "contact_type": "portal",
                    "skills": skills_str,
                    "description": desc_clean or item.get("name", ""),
                    "published_at": item.get("published_at")
                })
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"  ℹ hh.ru API policy requires OAuth authorization or blocks automated requests (HTTP 403).")
            else:
                print(f"  ✗ HHScraper HTTP error: {e}")
        except Exception as e:
            print(f"  ✗ HHScraper error: {e}")

        return vacancies
