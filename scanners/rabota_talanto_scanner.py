import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_rabota_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses Rabota.ru / generic portal vacancy list HTML.
    """
    vacancies = []
    
    # Generic vacancy cards parser
    items = re.findall(r'<a[^>]*href=\"(/(?:vacancy|vacancies)/[^\"]+)\"[^>]*>(.*?)</a>', html_content)
    seen = set()

    for path, raw_title in items:
        clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
        if not clean_title or len(clean_title) < 5 or clean_title in seen:
            continue
        seen.add(clean_title)

        is_relevant = any(k in clean_title.lower() for k in ["frontend", "react", "next", "fullstack", "разработчик", "developer", "javascript"])
        if not is_relevant:
            continue

        full_url = f"https://www.rabota.ru{path}" if path.startswith('/') else path
        vac_id = f"rabota:{path.split('/')[-1]}"

        contacts = extract_contacts(clean_title)

        vacancies.append({
            "id": vac_id,
            "source": "rabota_ru",
            "title": clean_title,
            "company": "Работодатель на Rabota.ru",
            "url": full_url,
            "salary": "По договорённости",
            "location": "РФ / Remote",
            "is_remote": True,
            "description": f"Вакансия {clean_title}",
            "skills": "React, JavaScript, Web",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": full_url,
            "contact_type": "portal"
        })

    return vacancies

def parse_talanto_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses Talanto listings or talent cards.
    """
    vacancies = []
    # Looks for job listings / project blocks
    matches = re.findall(r'<div[^>]*class=\"[^\"]*(?:job|vacancy|project|card)[^\"]*\"[^>]*>(.*?)</div>', html_content, re.DOTALL)
    
    for block in matches:
        title_m = re.search(r'<h[1-4][^>]*>(.*?)</h[1-4]>', block)
        if not title_m:
            continue
        title = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(1))).strip()
        if not any(k in title.lower() for k in ["frontend", "react", "next", "fullstack", "разработчик", "developer"]):
            continue

        link_m = re.search(r'<a[^>]*href=\"([^\"]+)\"', block)
        link = link_m.group(1) if link_m else "https://talanto.ru"
        contacts = extract_contacts(block)

        vacancies.append({
            "id": f"talanto:{abs(hash(title))}",
            "source": "talanto",
            "title": title,
            "company": "Talanto Partner",
            "url": link,
            "salary": "По договорённости",
            "location": "Remote",
            "is_remote": True,
            "description": re.sub(r'<[^>]+>', ' ', block)[:1000],
            "skills": "React, TypeScript, Frontend",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or link,
            "contact_type": contacts.get("primary_type") or "portal"
        })

    return vacancies
