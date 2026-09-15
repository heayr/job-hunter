import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import xml.etree.ElementTree as ET
import re
import html
import hashlib
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class CryptoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "crypto"
        self.feed_url = "https://cryptojobslist.com/rss"

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }

        try:
            req = urllib.request.Request(self.feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                root = ET.fromstring(resp.read())

            for item in root.findall('./channel/item'):
                raw_title = item.findtext('title') or ""
                link = item.findtext('link') or ""
                raw_desc = item.findtext('description') or ""

                if not raw_title or not link:
                    continue

                company = "Web3 / Crypto Company"
                title = raw_title.strip()

                if " at " in raw_title:
                    parts = raw_title.rsplit(" at ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif " | " in raw_title:
                    parts = raw_title.rsplit(" | ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif " - " in raw_title:
                    parts = raw_title.split(" - ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()

                clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc)
                clean_desc = html.unescape(clean_desc).strip()

                salary_m = re.search(r'(\$\d+[\d,]*\s*[-–—]\s*\$\d+[\d,]*|\$\d+[\d,]*\s*[\+/yr/year/k]*)', clean_desc, re.I)
                salary = salary_m.group(0).strip() if salary_m else "Не указана"

                # Skills extraction
                skill_keywords = ["React", "Next.js", "TypeScript", "JavaScript", "Fullstack", "Node.js", "Tailwind", "Web3", "GraphQL", "Docker"]
                found_skills = [sk for sk in skill_keywords if re.search(rf'\b{re.escape(sk)}\b', f"{title} {clean_desc}", re.I)]
                skills_str = ", ".join(found_skills) if found_skills else "React, TypeScript, Frontend"

                job_hash = hashlib.md5(link.encode('utf-8')).hexdigest()[:10]
                contacts = extract_contacts(clean_desc)

                vacancies.append({
                    "id": f"crypto:{job_hash}",
                    "source": "crypto",
                    "title": title,
                    "company": company,
                    "url": link,
                    "salary": salary,
                    "location": "Worldwide Remote",
                    "is_remote": 1,
                    "description": clean_desc[:3000],
                    "skills": skills_str,
                    "language": "en",
                    "contact_name": contacts.get("contact_name") or "",
                    "contact_handle": contacts.get("primary_handle") or link,
                    "contact_type": contacts.get("primary_type") or "portal"
                })

        except Exception as e:
            print(f"  ✗ CryptoScraper error: {e}")

        return vacancies

if __name__ == "__main__":
    s = CryptoScraper()
    jobs = s.scrape()
    print(f"CryptoScraper got {len(jobs)} vacancies.")
    if jobs:
        print("Sample:", jobs[0]["title"], "@", jobs[0]["company"])
