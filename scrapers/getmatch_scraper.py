import json
import re
import urllib.request
import urllib.parse
from typing import List, Dict, Any

from scrapers.base import BaseScraper


class GetMatchScraper(BaseScraper):
    """
    Scrapes high-quality Russian and international tech vacancies from GetMatch (getmatch.ru).
    Focuses on Frontend, React, Fullstack, and TypeScript positions.
    """

    def __init__(self):
        super().__init__()
        self.name = "getmatch"
        self.queries = ["Frontend", "React", "Fullstack"]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        seen_ids = set()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        for query in self.queries:
            page = 1
            max_pages = 2
            while page <= max_pages:
                encoded_query = urllib.parse.quote(query)
                url = f"https://getmatch.ru/api/offers?p={page}&sa=150000&sp=development&text={encoded_query}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                    offers = data.get('offers', [])
                    if not offers:
                        break

                    for offer in offers:
                        raw_id = str(offer.get('id', ''))
                        if not raw_id:
                            continue
                        vac_id = f"getmatch:{raw_id}"
                        if vac_id in seen_ids:
                            continue
                        seen_ids.add(vac_id)

                        title = (offer.get('position') or 'Software Engineer').strip()
                        comp_info = offer.get('company') or {}
                        company = (comp_info.get('name') if isinstance(comp_info, dict) else str(comp_info)) or 'GetMatch Partner'

                        # Salary parsing
                        sal_from = offer.get('salary_display_from')
                        sal_to = offer.get('salary_display_to')
                        curr = offer.get('salary_currency') or 'RUR'
                        if curr.upper() == 'RUR':
                            curr = '₽'
                        elif curr.upper() == 'USD':
                            curr = '$'

                        if sal_from and sal_to:
                            salary = f"{sal_from} - {sal_to} {curr}"
                        elif sal_from:
                            salary = f"от {sal_from} {curr}"
                        elif sal_to:
                            salary = f"до {sal_to} {curr}"
                        else:
                            salary = offer.get('salary_description') or 'Не указана'

                        # Skills
                        skills_objs = offer.get('skills_objects') or []
                        skills = [s.get('name') for s in skills_objs if isinstance(s, dict) and s.get('name')]
                        skills_str = ", ".join(skills) if skills else query

                        # Location & Remote
                        loc_items = offer.get('location_items') or []
                        loc_names = [l.get('name') for l in loc_items if isinstance(l, dict) and l.get('name')]
                        loc_req = str(offer.get('location_requirements') or '')
                        is_remote = any(
                            'remote' in str(l).lower() or 'удален' in str(l).lower()
                            for l in loc_names
                        ) or 'remote' in loc_req.lower() or 'удален' in loc_req.lower()

                        location = ", ".join(loc_names) if loc_names else ("Remote" if is_remote else "РФ / СНГ")

                        # Description
                        raw_desc = offer.get('offer_description') or offer.get('description_html') or ''
                        clean_desc = re.sub(r'<[^>]+>', ' ', raw_desc).strip()
                        full_desc = f"{title} в {company}.\n\nСтек: {skills_str}\nЛокация: {location}\nЗарплата: {salary}\n\n{clean_desc[:3500]}"

                        rel_url = offer.get('url') or f"/vacancies/{raw_id}"
                        full_url = f"https://getmatch.ru{rel_url}" if rel_url.startswith('/') else rel_url

                        lang = offer.get('language') or 'ru'

                        vacancies.append({
                            "id": vac_id,
                            "source": "getmatch",
                            "title": title,
                            "company": company,
                            "url": full_url,
                            "salary": salary,
                            "location": location,
                            "is_remote": 1 if is_remote else 0,
                            "description": full_desc,
                            "skills": skills_str,
                            "language": lang,
                            "contact_name": "",
                            "contact_handle": full_url,
                            "contact_type": "portal"
                        })

                    page += 1
                except Exception as e:
                    print(f"  ✗ GetMatchScraper error for '{query}' (page {page}): {e}")
                    break

        return vacancies
