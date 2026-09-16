import re
import html
import urllib.request
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class HabrScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "habr"
        self.queries = ["React", "Frontend"]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        seen_ids = set()

        for query in self.queries:
            url = f"https://career.habr.com/vacancies?sort=date&q={urllib.request.quote(query)}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html_content = resp.read().decode('utf-8', errors='ignore')

                cards = re.findall(r'<div class="vacancy-card__info">(.*?)</div>\s*</div>\s*<div class="vacancy-card__footer">', html_content, re.DOTALL)

                for card in cards:
                    title_match = re.search(r'<a class="vacancy-card__title-link"[^>]*href="(/vacancies/\d+)"[^>]*>(.*?)</a>', card, re.DOTALL)
                    if not title_match:
                        continue
                    url_path, raw_title = title_match.groups()
                    title = html.unescape(raw_title).strip()
                    vac_num = url_path.replace('/vacancies/', '').strip()
                    vac_id = f"habr:{vac_num}"

                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)

                    company_match = re.search(r'<a class="link-comp link-comp--appearance-dark"[^>]*>(.*?)</a>', card, re.DOTALL)
                    company = html.unescape(company_match.group(1)).strip() if company_match else "Компания на Habr"

                    salary_match = re.search(r'<div class="basic-salary">(.*?)</div>', card, re.DOTALL)
                    salary = html.unescape(salary_match.group(1)).strip() if salary_match else "Не указана"

                    is_remote = bool(re.search(r'Можно удалённо|Удаленно|Remote', card, re.I))
                    location_match = re.search(r'<div class="chip-with-icon__text">(.*?)</div>', card, re.DOTALL)
                    location = html.unescape(location_match.group(1)).strip() if location_match else ("Удаленно" if is_remote else "РФ")

                    skills = re.findall(r'<div class="basic-chip__text">(.*?)</div>', card)
                    skills_str = ", ".join(html.unescape(s).strip() for s in skills) if skills else "React, TypeScript, Frontend"

                    full_url = f"https://career.habr.com{url_path}"
                    contacts = extract_contacts(card)

                    vacancies.append({
                        "id": vac_id,
                        "source": "habr",
                        "title": title,
                        "company": company,
                        "url": full_url,
                        "salary": salary,
                        "location": location,
                        "is_remote": 1 if is_remote else 0,
                        "description": f"Вакансия с Habr Career: {title} в {company}.\nСтек: {skills_str}.\nЛокация: {location}.\nЗарплата: {salary}.",
                        "skills": skills_str,
                        "language": "ru",
                        "contact_name": contacts.get("contact_name") or "",
                        "contact_handle": contacts.get("primary_handle") or full_url,
                        "contact_type": contacts.get("primary_type") or "portal"
                    })

            except Exception as e:
                print(f"  ✗ HabrScraper error for query '{query}': {e}")

        return vacancies
