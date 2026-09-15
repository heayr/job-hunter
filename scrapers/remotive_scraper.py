import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import json
import re
import html
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class RemotiveScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "remotive"
        self.url = "https://remotive.com/api/remote-jobs?category=software-dev"

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }

        try:
            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            jobs = data.get('jobs', [])
            for job in jobs:
                title = job.get('title', '').strip()
                company = job.get('company_name', 'Remote Company').strip()
                link = job.get('url', '')
                job_id = job.get('id') or hash(link)

                if not title or not link:
                    continue

                raw_desc = job.get('description', '')
                clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc)
                clean_desc = html.unescape(clean_desc).strip()

                loc = job.get('candidate_required_location') or "Worldwide Remote"
                salary = job.get('salary') or "Не указана"

                tags = job.get('tags', [])
                skills_str = ", ".join(tags) if tags else "React, TypeScript, Frontend"

                contacts = extract_contacts(clean_desc)

                vacancies.append({
                    "id": f"remotive:{job_id}",
                    "source": "remotive",
                    "title": title,
                    "company": company,
                    "url": link,
                    "salary": salary,
                    "location": f"Remote ({loc})",
                    "is_remote": 1,
                    "description": clean_desc[:3000],
                    "skills": skills_str,
                    "language": "en",
                    "contact_name": contacts.get("contact_name") or "",
                    "contact_handle": contacts.get("primary_handle") or link,
                    "contact_type": contacts.get("primary_type") or "portal"
                })

        except Exception as e:
            print(f"  ✗ RemotiveScraper error: {e}")

        return vacancies

if __name__ == "__main__":
    s = RemotiveScraper()
    jobs = s.scrape()
    print(f"RemotiveScraper got {len(jobs)} vacancies.")
    if jobs:
        print("Sample:", jobs[0]["title"], "@", jobs[0]["company"], "| loc:", jobs[0]["location"])
