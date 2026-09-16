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


class ATSScraper(BaseScraper):
    """
    Direct ATS Scraper for open Greenhouse and Lever company boards.
    Fetches genuine vacancies directly from employer career APIs without middleman fees.
    """
    def __init__(self):
        super().__init__()
        self.name = "ats"
        
        # Curated tech companies with public ATS endpoints
        self.greenhouse_boards = [
            {"slug": "gitlab", "name": "GitLab"},
            {"slug": "canonical", "name": "Canonical"},
            {"slug": "cloudflare", "name": "Cloudflare"},
            {"slug": "figma", "name": "Figma"},
            {"slug": "stripe", "name": "Stripe"},
            {"slug": "elastic", "name": "Elastic"},
            {"slug": "reddit", "name": "Reddit"},
            {"slug": "pinterest", "name": "Pinterest"},
            {"slug": "consensys", "name": "ConsenSys"}
        ]
        
        self.lever_boards = [
            {"slug": "palantir", "name": "Palantir"},
            {"slug": "spotify", "name": "Spotify"}
        ]

        # Explicit regex for targeted Web / Frontend / Fullstack roles
        self.relevant_regex = re.compile(
            r'\b(frontend|front-end|fullstack|full-stack|react|vue|angular|typescript|javascript|web developer|ui engineer|ui developer|full stack)\b',
            re.IGNORECASE
        )
        # Software engineer only if paired with web/frontend/ui
        self.web_se_regex = re.compile(
            r'\bsoftware engineer\b.*?\b(web|frontend|front-end|ui|react|fullstack|full-stack)\b|\b(web|frontend|front-end|ui|react|fullstack|full-stack)\b.*?\bsoftware engineer\b',
            re.IGNORECASE
        )
        # Immediate exclusions for irrelevant / defense / low-level roles
        self.exclude_regex = re.compile(
            r'\b(defense|clearance|c\+\+|embedded|firmware|kernel|hardware|ios|android|mobile|devops|sre|infrastructure|sales|recruiter|hr|analyst|data scientist|machine learning)\b',
            re.IGNORECASE
        )

    def _is_relevant(self, title: str) -> bool:
        if self.exclude_regex.search(title):
            return False
        return bool(self.relevant_regex.search(title) or self.web_se_regex.search(title))

    def scrape_greenhouse(self, board: Dict[str, str]) -> List[Dict[str, Any]]:
        results = []
        slug = board["slug"]
        company = board["name"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            jobs = data.get("jobs", [])
            for job in jobs:
                title = (job.get("title") or "").strip()
                if not title or not self._is_relevant(title):
                    continue
                
                job_id = job.get("id")
                link = job.get("absolute_url") or f"https://job-boards.greenhouse.io/{slug}/jobs/{job_id}"
                
                loc_data = job.get("location") or {}
                location = loc_data.get("name") if isinstance(loc_data, dict) else str(loc_data)
                if not location:
                    location = "Remote / Global"
                
                is_remote = 1 if any(w in location.lower() for w in ["remote", "worldwide", "anywhere", "global"]) else 0
                
                depts = [d.get("name") for d in job.get("departments", []) if isinstance(d, dict) and d.get("name")]
                dept_str = f" | Dept: {', '.join(depts)}" if depts else ""
                desc = f"{title} at {company}. Direct application via official {company} ATS board (Greenhouse). Location: {location}{dept_str}. Apply directly without middlemen."

                results.append({
                    "id": f"ats:gh:{slug}:{job_id}",
                    "source": "ats_greenhouse",
                    "title": title,
                    "company": company,
                    "url": link,
                    "salary": "По договоренности (Direct ATS)",
                    "location": location,
                    "is_remote": is_remote,
                    "description": desc,
                    "skills": "React, TypeScript, Frontend, Software Engineering",
                    "language": "en",
                    "contact_name": f"{company} Talent Team",
                    "contact_handle": link,
                    "contact_type": "ats"
                })
        except Exception as e:
            print(f"  [ats_scraper] Greenhouse {slug} error: {e}")
            
        return results

    def scrape_lever(self, board: Dict[str, str]) -> List[Dict[str, Any]]:
        results = []
        slug = board["slug"]
        company = board["name"]
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                jobs = json.loads(resp.read().decode("utf-8"))
            
            for job in jobs:
                title = (job.get("text") or "").strip()
                if not title or not self._is_relevant(title):
                    continue
                
                job_id = job.get("id")
                link = job.get("applyUrl") or job.get("hostedUrl") or f"https://jobs.lever.co/{slug}/{job_id}"
                
                desc = job.get("descriptionPlain") or job.get("description") or ""
                clean_desc = re.sub(r"<[^>]+>", " ", desc)
                clean_desc = html.unescape(clean_desc)
                clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                if not clean_desc:
                    clean_desc = f"{title} at {company}. Direct application via official {company} Lever board."
                
                cats = job.get("categories") or {}
                location = cats.get("location") or "Remote"
                workplace_type = (job.get("workplaceType") or "").lower()
                
                is_remote = 1 if "remote" in workplace_type or "remote" in location.lower() else 0
                contacts = extract_contacts(clean_desc)
                
                results.append({
                    "id": f"ats:lever:{slug}:{job_id}",
                    "source": "ats_lever",
                    "title": title,
                    "company": company,
                    "url": link,
                    "salary": "По договоренности (Direct ATS)",
                    "location": location,
                    "is_remote": is_remote,
                    "description": clean_desc[:3000],
                    "skills": "React, TypeScript, Frontend, Software Engineering",
                    "language": "en",
                    "contact_name": contacts.get("contact_name") or f"{company} Talent Team",
                    "contact_handle": contacts.get("primary_handle") or link,
                    "contact_type": contacts.get("primary_type") or "ats"
                })
        except Exception as e:
            print(f"  [ats_scraper] Lever {slug} error: {e}")
            
        return results

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        
        for b in self.greenhouse_boards:
            vacs = self.scrape_greenhouse(b)
            vacancies.extend(vacs)
            
        for b in self.lever_boards:
            vacs = self.scrape_lever(b)
            vacancies.extend(vacs)
            
        return vacancies


if __name__ == "__main__":
    s = ATSScraper()
    jobs = s.scrape()
    print(f"ATSScraper got {len(jobs)} vacancies.")
    if jobs:
        for j in jobs[:5]:
            print(f"  ✓ [{j['company']}] {j['title']} | {j['location']} | {j['url']}")
