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


class JobicyScraper(BaseScraper):
    """
    Scraper for Jobicy Remote Jobs API (v2).
    Provides free, unpaywalled remote developer listings.
    """
    def __init__(self):
        super().__init__()
        self.name = "jobicy"
        self.tags = ["react", "frontend", "fullstack", "javascript"]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        seen_ids = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        for tag in self.tags:
            url = f"https://jobicy.com/api/v2/remote-jobs?count=30&tag={tag}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                jobs = data.get("jobs", [])
                for j in jobs:
                    job_id = j.get("id")
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    title = (j.get("jobTitle") or "").strip()
                    company = (j.get("companyName") or "Tech Company").strip()
                    link = (j.get("url") or "").strip()
                    if not title or not link:
                        continue

                    raw_desc = j.get("jobDescription") or j.get("jobExcerpt") or ""
                    clean_desc = html.unescape(re.sub(r"<[^>]+>", " ", raw_desc))
                    clean_desc = re.sub(r"[ \t]+", " ", clean_desc).strip()

                    geo = j.get("jobGeo") or "Anywhere"
                    level = j.get("jobLevel") or ""
                    salary = j.get("annualSalaryMin")
                    if salary:
                        salary_str = f"${salary:,} - ${j.get('annualSalaryMax', salary):,}"
                    else:
                        salary_str = "По договоренности"

                    contacts = extract_contacts(clean_desc)

                    vacancies.append({
                        "id": f"jobicy:{job_id}",
                        "source": "jobicy",
                        "title": title,
                        "company": company,
                        "url": link,
                        "salary": salary_str,
                        "location": f"Remote ({geo})",
                        "is_remote": 1,
                        "description": clean_desc[:3000],
                        "skills": f"{tag.capitalize()}, TypeScript, Web Development",
                        "language": "en",
                        "contact_name": contacts.get("contact_name") or f"{company} Hiring Team",
                        "contact_handle": contacts.get("primary_handle") or link,
                        "contact_type": contacts.get("primary_type") or "portal"
                    })

            except Exception as e:
                print(f"  ✗ JobicyScraper tag={tag} error: {e}")

        return vacancies


if __name__ == "__main__":
    s = JobicyScraper()
    jobs = s.scrape()
    print(f"JobicyScraper got {len(jobs)} vacancies.")
    if jobs:
        for j in jobs[:5]:
            print(f"  ✓ [{j['company']}] {j['title']} | {j['location']} | {j['salary']}")
