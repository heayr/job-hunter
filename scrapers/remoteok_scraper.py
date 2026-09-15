import urllib.request
import urllib.error
import json
import hashlib
from typing import List, Dict, Any

from scrapers.base import BaseScraper


class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "remoteok"

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        tags_to_query = ["react", "frontend", "typescript"]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        seen_ids = set()

        for tag in tags_to_query:
            url = f"https://remoteok.com/api?tag={tag}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode('utf-8'))

                for job in data[1:]:  # First element is legal disclaimer/metadata
                    link = job.get("url") or job.get("apply_url") or ""
                    job_id = job.get("id")
                    if not job_id:
                        job_id = hashlib.md5(link.encode('utf-8')).hexdigest()[:10]

                    vac_id = f"remoteok:{job_id}"
                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)

                    sal_min = job.get('salary_min')
                    sal_max = job.get('salary_max')
                    if sal_min and sal_max:
                        salary_str = f"${sal_min:,} - ${sal_max:,}"
                    elif sal_min:
                        salary_str = f"from ${sal_min:,}"
                    else:
                        salary_str = "Не указана"

                    tags = job.get("tags", [])
                    skills_str = ", ".join(tags) if tags else "React, JavaScript"

                    vacancies.append({
                        "id": vac_id,
                        "source": "remoteok",
                        "title": job.get("position", "Frontend Engineer"),
                        "company": job.get("company", "Remote Company"),
                        "url": link,
                        "salary": salary_str,
                        "location": job.get("location", "Worldwide Remote"),
                        "is_remote": 1,
                        "language": "en",
                        "contact_name": "",
                        "contact_handle": job.get("apply_url") or link,
                        "contact_type": "portal",
                        "skills": skills_str,
                        "description": job.get("description", "")
                    })
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    print(f"  ℹ RemoteOK API is protected by Cloudflare bot management (HTTP 403).")
                else:
                    print(f"  ✗ RemoteOK HTTP error: {e}")
            except Exception as e:
                print(f"  ✗ RemoteOK error for tag '{tag}': {e}")

        return vacancies
