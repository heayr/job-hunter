import re
import html
import json
import urllib.request
from typing import List, Dict, Any
from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class RabotaRuScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "rabota_ru"
        self.url = "https://www.rabota.ru/vacancy/?query=frontend"

    def parse_html(self, html_content: str) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        ld_matches = re.findall(r'<script[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>', html_content, re.DOTALL)
        for ld_text in ld_matches:
            try:
                data = json.loads(ld_text)
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    continue

                for item in data:
                    if not isinstance(item, dict) or item.get('@type') != 'JobPosting':
                        continue

                    title = html.unescape(item.get('title') or '').strip()
                    if not title:
                        continue

                    company_obj = item.get('hiringOrganization') or {}
                    company = company_obj.get('name') or 'Работодатель на Rabota.ru'

                    vac_url = item.get('url') or ''
                    vac_id_m = re.search(r'/vacancy/(\d+)', vac_url)
                    vac_id = f"rabota:{vac_id_m.group(1)}" if vac_id_m else f"rabota:{abs(hash(vac_url or title))}"

                    raw_desc = item.get('description') or ''
                    clean_desc = re.sub(r'<br\s*/?>', '\n', raw_desc)
                    clean_desc = re.sub(r'<[^>]+>', ' ', clean_desc)
                    clean_desc = html.unescape(clean_desc).strip()

                    # Salary formatting
                    salary = "По договорённости"
                    base_salary = item.get('baseSalary') or {}
                    min_v = base_salary.get('minValue')
                    max_v = base_salary.get('maxValue')
                    val_v = base_salary.get('value')
                    curr = base_salary.get('currency', 'RUB')
                    curr_sym = "₽" if curr in ("RUB", "RUR") else curr

                    if min_v and max_v:
                        salary = f"{min_v:,} – {max_v:,} {curr_sym}".replace(",", " ")
                    elif min_v:
                        salary = f"от {min_v:,} {curr_sym}".replace(",", " ")
                    elif max_v:
                        salary = f"до {max_v:,} {curr_sym}".replace(",", " ")
                    elif val_v:
                        if isinstance(val_v, dict):
                            val_v = val_v.get('value') or val_v.get('minValue')
                        if val_v:
                            salary = f"{int(val_v):,} {curr_sym}".replace(",", " ")

                    is_remote = bool(re.search(r'удален|remote|любой город', clean_desc, re.I))
                    contacts = extract_contacts(clean_desc)

                    # Extract skills
                    skill_keywords = ["React", "Next.js", "TypeScript", "JavaScript", "Vue", "Node.js", "Redux", "Tailwind", "CSS", "HTML"]
                    found_skills = [sk for sk in skill_keywords if re.search(rf'\b{re.escape(sk)}\b', clean_desc, re.I)]
                    skills_str = ", ".join(found_skills) if found_skills else "React, TypeScript, Frontend"

                    vacancies.append({
                        "id": vac_id,
                        "source": "rabotaru",
                        "title": title,
                        "company": company,
                        "url": vac_url,
                        "salary": salary,
                        "location": "Удаленно" if is_remote else "РФ",
                        "is_remote": 1 if is_remote else 0,
                        "description": clean_desc[:2500],
                        "skills": skills_str,
                        "language": "ru",
                        "contact_name": contacts.get("contact_name") or "",
                        "contact_handle": contacts.get("primary_handle") or vac_url,
                        "contact_type": contacts.get("primary_type") or "portal",
                        "published_at": item.get('datePosted')
                    })
            except Exception:
                pass
        return vacancies

    def scrape(self) -> List[Dict[str, Any]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        }

        try:
            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')
            return self.parse_html(html_content)
        except Exception as e:
            print(f"  ✗ RabotaRuScraper error: {e}")
            return []
