import re
import html
import urllib.request
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class SetkaScraper(BaseScraper):
    """
    Scrapes tech hiring posts and vacancies from Setka (setka.ru — HH.ru's professional tech network).
    Extracts recruiter posts, candidate inquiries, tech stack, and direct Telegram/email contacts.
    """

    def __init__(self):
        super().__init__()
        self.name = "setka"
        # Known Setka tech & community feed IDs
        self.feed_ids = [
            "01a0b110-10a8-7662-974f-8f9040d4bb34",
            "018fa181-2e82-4af3-b3c4-ab7c19461ba3",
            "018fc120-247b-47e6-98d6-1b44b316a2ec",
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        seen_ids = set()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'HX-Request': 'true',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        # Filter keywords identifying real hiring announcements
        hiring_pattern = re.compile(
            r'(?:ищем|ваканси|hiring|looking for|frontend|react|fullstack|разработчик|developer|инженер|тимлид|team lead|remote|удаленка)',
            re.IGNORECASE
        )

        for feed_id in self.feed_ids:
            url = f"https://setka.ru/feed/posts?feed_id={feed_id}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    content = resp.read().decode('utf-8', errors='ignore')

                # Split content into post blocks
                blocks = content.split('data-feed-post-id="')
                for block in blocks[1:]:
                    post_id_match = re.match(r'^([a-zA-Z0-9_\-]+)"', block)
                    if not post_id_match:
                        continue
                    post_id = post_id_match.group(1)
                    vac_id = f"setka:{post_id}"
                    if vac_id in seen_ids:
                        continue

                    # Extract text content from paragraph tags
                    raw_paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
                    cleaned_paragraphs = [
                        html.unescape(re.sub(r'<[^>]+>', ' ', p)).strip()
                        for p in raw_paragraphs
                        if not p.startswith('analytics') and not 'pop_up_view' in p
                    ]
                    post_text = "\n".join([p for p in cleaned_paragraphs if len(p) > 20])

                    if not post_text or not hiring_pattern.search(post_text):
                        continue

                    seen_ids.add(vac_id)

                    # Extract title (first line or headline)
                    lines = [l.strip() for l in post_text.split('\n') if l.strip()]
                    title = lines[0][:100] if lines else "Frontend / Fullstack Engineer"
                    if len(title) > 80:
                        title = title[:77] + "..."

                    # Extract company name or author
                    author_match = re.search(r'data-user-name="([^"]+)"', block) or re.search(r'alt="([^"]+)"', block)
                    company = author_match.group(1).strip() if author_match else "Сетка / Tech Community"

                    full_url = f"https://setka.ru/posts/{post_id}"
                    contacts = extract_contacts(post_text)

                    is_remote = bool(re.search(r'удален|remote|удалённо', post_text, re.IGNORECASE))
                    salary_match = re.search(r'(\d+[\s\d]*\s*(?:₽|руб|usd|\$))', post_text, re.IGNORECASE)
                    salary = salary_match.group(1).strip() if salary_match else "Не указана"

                    vacancies.append({
                        "id": vac_id,
                        "source": "setka",
                        "title": title,
                        "company": company,
                        "url": full_url,
                        "salary": salary,
                        "location": "Remote / РФ" if is_remote else "Москва / РФ",
                        "is_remote": 1 if is_remote else 0,
                        "description": f"Пост/Вакансия из Сетки (setka.ru):\n\n{post_text[:3500]}",
                        "skills": "React, TypeScript, Frontend, Fullstack",
                        "language": "ru",
                        "contact_name": contacts.get("contact_name") or company,
                        "contact_handle": contacts.get("primary_handle") or full_url,
                        "contact_type": contacts.get("primary_type") or "portal"
                    })

            except Exception as e:
                print(f"  ✗ SetkaScraper error for feed '{feed_id}': {e}")

        return vacancies
