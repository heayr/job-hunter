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


class HackerNewsScraper(BaseScraper):
    """
    Scrapes the official Hacker News 'Ask HN: Who is hiring?' threads via Algolia search API.
    Extracts direct founder/CTO postings, direct emails, and company websites without middlemen.
    """
    def __init__(self):
        super().__init__()
        self.name = "hackernews"
        self.relevant_regex = re.compile(
            r'\b(frontend|front-end|fullstack|full-stack|react|typescript|javascript|software engineer|web developer|frontend engineer|ui engineer|full stack)\b',
            re.IGNORECASE
        )

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        try:
            # 1. Find the latest "Ask HN: Who is hiring?" thread
            search_url = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=1"
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                story_data = json.loads(resp.read().decode("utf-8"))
            
            hits = story_data.get("hits", [])
            if not hits:
                print("  [hackernews_scraper] No 'Who is hiring' thread found.")
                return vacancies

            latest_story = hits[0]
            story_id = latest_story.get("objectID")
            story_title = latest_story.get("title")
            print(f"  [hackernews_scraper] Latest thread: {story_title} (ID: {story_id})")

            # 2. Fetch top comments (job postings) from the story
            comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=100"
            req2 = urllib.request.Request(comments_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=12) as resp:
                comments_data = json.loads(resp.read().decode("utf-8"))

            comments = comments_data.get("hits", [])
            for c in comments:
                # Only process top-level job postings where parent_id is the story itself
                if str(c.get("parent_id")) != str(story_id):
                    continue

                raw_html = c.get("comment_text") or ""
                if not raw_html:
                    continue

                clean_text = html.unescape(re.sub(r"<[^>]+>", " ", raw_html))
                clean_text = re.sub(r"[ \t]+", " ", clean_text).strip()
                lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
                if not lines:
                    continue

                first_line = lines[0]
                parts = [p.strip() for p in first_line.split("|")]
                
                # Hacker News standard format: Company | Role | Location | ...
                if len(parts) >= 2:
                    company = re.sub(r"\s*\(.*?\)", "", parts[0]).strip()
                    title = parts[1].strip()
                    loc_part = parts[2].strip() if len(parts) > 2 else "Remote / US"
                else:
                    company = "Hacker News Startup"
                    title = first_line[:60]
                    loc_part = "Remote"

                # Check relevance
                full_search_text = f"{title} {first_line} {clean_text[:400]}"
                if not self.relevant_regex.search(full_search_text):
                    continue

                comment_id = c.get("objectID")
                hn_link = f"https://news.ycombinator.com/item?id={comment_id}"

                # Extract external links from raw HTML if present
                ext_links = re.findall(r'href=[\'"](https?://[^\'"]+)[\'"]', raw_html)
                ext_url = ""
                for link in ext_links:
                    if "ycombinator.com" not in link and "github.com/whoishiring" not in link:
                        ext_url = link
                        break

                target_url = ext_url if ext_url else hn_link

                is_remote = 1 if any(w in loc_part.lower() or w in clean_text[:300].lower() for w in ["remote", "anywhere", "worldwide"]) else 0
                contacts = extract_contacts(clean_text)

                contact_handle = contacts.get("primary_handle") or target_url
                contact_type = contacts.get("primary_type") or ("email" if "@" in contact_handle else "hn_comment")

                vacancies.append({
                    "id": f"hn:{comment_id}",
                    "source": "hackernews",
                    "title": title[:100],
                    "company": company[:80],
                    "url": target_url,
                    "salary": "По договоренности (HN Direct)",
                    "location": loc_part[:80],
                    "is_remote": is_remote,
                    "description": clean_text[:3000],
                    "skills": "React, TypeScript, Frontend, Fullstack",
                    "language": "en",
                    "contact_name": contacts.get("contact_name") or f"{company} Founder/CTO",
                    "contact_handle": contact_handle,
                    "contact_type": contact_type
                })

        except Exception as e:
            print(f"  ✗ HackerNewsScraper error: {e}")

        return vacancies


if __name__ == "__main__":
    s = HackerNewsScraper()
    jobs = s.scrape()
    print(f"HackerNewsScraper got {len(jobs)} vacancies.")
    if jobs:
        for j in jobs[:5]:
            print(f"  ✓ [{j['company']}] {j['title']} | Loc: {j['location']} | Contact: {j['contact_type']} -> {j['contact_handle']}")
