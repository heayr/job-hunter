import re
import json
import urllib.request
from typing import List, Dict, Any
from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class SuperJobScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "superjob"
        self.url = "https://www.superjob.ru/vacancy/search/?keywords=frontend"

    def parse_html(self, html_content: str) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []

        # 1. Extract exact URLs from application/ld+json
        url_map = {}
        ld_matches = re.findall(r'<script[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>', html_content, re.DOTALL)
        for ld_text in ld_matches:
            try:
                ld_obj = json.loads(ld_text)
                if isinstance(ld_obj, dict):
                    if ld_obj.get('@type') == 'ItemList':
                        for item in ld_obj.get('itemListElement', []):
                            u = item.get('url', '')
                            id_m = re.search(r'-(\d+)\.html', u)
                            if id_m:
                                url_map[id_m.group(1)] = u
                    elif ld_obj.get('@type') == 'JobPosting':
                        # Direct JobPosting fallback
                        t = ld_obj.get('title', '').strip()
                        comp = (ld_obj.get('hiringOrganization') or {}).get('name', 'SuperJob')
                        u = ld_obj.get('url', '')
                        vid_m = re.search(r'-(\d+)\.html', u)
                        vid = vid_m.group(1) if vid_m else str(abs(hash(u or t)))
                        sal_obj = ld_obj.get('baseSalary') or {}
                        val_obj = sal_obj.get('value') or {}
                        min_v = val_obj.get('minValue') if isinstance(val_obj, dict) else None
                        max_v = val_obj.get('maxValue') if isinstance(val_obj, dict) else None
                        salary = "По договорённости"
                        if min_v and max_v:
                            salary = f"{min_v:,} – {max_v:,} ₽".replace(",", " ")
                        elif min_v:
                            salary = f"от {min_v:,} ₽".replace(",", " ")

                        vacancies.append({
                            "id": f"superjob:{vid}",
                            "source": "superjob",
                            "title": t,
                            "company": comp,
                            "url": u,
                            "salary": salary,
                            "location": "РФ",
                            "is_remote": 0,
                            "description": ld_obj.get('description', ''),
                            "skills": "React, TypeScript, Frontend",
                            "language": "ru",
                            "contact_name": "",
                            "contact_handle": u,
                            "contact_type": "portal"
                        })
            except Exception:
                pass

        # 2. Extract structured entities from window.APP_STATE
        pos = html_content.find('window.APP_STATE=')
        if pos != -1:
            end_pos = html_content.find('</script>', pos)
            raw_json = html_content[pos + len('window.APP_STATE='):end_pos].rstrip(';')
            try:
                state_data = json.loads(raw_json)
                entities = state_data.get('entities', {})

                v_mains = entities.get('vacancyMainInfo', {})
                v_comps = entities.get('vacancyCompanyInfo', {})
                v_details = entities.get('vacancyDetailInfo', {})
                snippets = entities.get('searchSnippetSection', {})

                for vid, main_info in v_mains.items():
                    attrs = main_info.get('attributes', {})
                    title = attrs.get('profession', '').strip()
                    if not title:
                        continue

                    company_attrs = v_comps.get(vid, {}).get('attributes', {})
                    company = company_attrs.get('name', 'Работодатель на SuperJob').strip()

                    detail_attrs = v_details.get(vid, {}).get('attributes', {})
                    is_remote = bool(detail_attrs.get('isRemoteWork', False))

                    # Combine snippet texts for description
                    desc_parts = []
                    resp_snip = snippets.get(f"{vid}_responsibilities", {}).get('attributes', {}).get('text')
                    if resp_snip:
                        desc_parts.append(resp_snip)
                    req_snip = snippets.get(f"{vid}_requirements", {}).get('attributes', {}).get('text')
                    if req_snip:
                        desc_parts.append(req_snip)

                    description = "\n".join(desc_parts) if desc_parts else f"Вакансия {title} в компании {company}."
                    full_url = url_map.get(str(vid), f"https://www.superjob.ru/vakansii/{vid}.html")
                    contacts = extract_contacts(description)

                    pub_date = attrs.get('date_published') or detail_attrs.get('datePublished')
                    if isinstance(pub_date, (int, float)):
                        from datetime import datetime
                        pub_date = datetime.fromtimestamp(pub_date).strftime('%Y-%m-%d %H:%M:%S')

                    vacancies.append({
                        "id": f"superjob:{vid}",
                        "source": "superjob",
                        "title": title,
                        "company": company,
                        "url": full_url,
                        "salary": "По договорённости",
                        "location": "Удаленно" if is_remote else "РФ",
                        "is_remote": 1 if is_remote else 0,
                        "description": description,
                        "skills": "React, JavaScript, TypeScript, Frontend",
                        "language": "ru",
                        "contact_name": contacts.get("contact_name") or "",
                        "contact_handle": contacts.get("primary_handle") or full_url,
                        "contact_type": contacts.get("primary_type") or "portal",
                        "published_at": pub_date
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
            print(f"  ✗ SuperJobScraper error: {e}")
            return []
