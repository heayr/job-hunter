import urllib.request
import xml.etree.ElementTree as ET
import re
import html
import hashlib
from typing import List, Dict, Any

from scrapers.base import BaseScraper


class WWRScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "weworkremotely"
        self.feeds = [
            "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

        for feed_url in self.feeds:
            try:
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    root = ET.fromstring(resp.read())

                for item in root.findall('./channel/item'):
                    raw_title = item.findtext('title') or ""
                    link = item.findtext('link') or ""
                    raw_desc = item.findtext('description') or ""

                    # Usually title is formatted as "Company: Role"
                    if ":" in raw_title:
                        company, title = raw_title.split(":", 1)
                        company = company.strip()
                        title = title.strip()
                    else:
                        company = "Remote Company"
                        title = raw_title.strip()

                    clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc)
                    clean_desc = html.unescape(clean_desc).strip()

                    job_hash = hashlib.md5(link.encode('utf-8')).hexdigest()[:10]
                    vac_id = f"wwr:{job_hash}"

                    vacancies.append({
                        "id": vac_id,
                        "source": "weworkremotely",
                        "title": title,
                        "company": company,
                        "url": link,
                        "salary": "Не указана",
                        "location": "Worldwide Remote",
                        "is_remote": 1,
                        "description": clean_desc[:2500],
                        "skills": "React, TypeScript, Frontend",
                        "language": "en",
                        "contact_name": "",
                        "contact_handle": link,
                        "contact_type": "portal"
                    })
            except Exception as e:
                print(f"  ✗ WWRScraper error for {feed_url}: {e}")

        return vacancies
