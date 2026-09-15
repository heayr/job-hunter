import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_superjob_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses SuperJob vacancy search HTML content into structured vacancy dicts.
    """
    vacancies = []
    
    # Extract links and titles
    matches = re.findall(r'<a[^>]*href=\"(/vakansii/[^\"]+?-(\d+)\.html)\"[^>]*>(.*?)</a>', html_content)
    seen_ids = set()

    for url_path, vac_id_num, raw_title in matches:
        if vac_id_num in seen_ids:
            continue
        seen_ids.add(vac_id_num)

        title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
        if not title or len(title) < 4:
            continue

        # Filter for relevant Frontend / Fullstack / React
        is_relevant = any(k in title.lower() for k in ["frontend", "front-end", "фронтенд", "react", "next", "fullstack", "фуллстек", "javascript", "web", "разработчик", "developer"])
        if not is_relevant:
            continue

        full_url = f"https://russia.superjob.ru{url_path}"
        vac_id = f"superjob:{vac_id_num}"

        # Try finding company near this link
        pos = html_content.find(url_path)
        snippet = html_content[max(0, pos-200):pos+600] if pos != -1 else ""
        
        company_m = re.search(r'<a[^>]*href=\"/(?:clients|kompanii)/[^\"]+\"[^>]*>(.*?)</a>', snippet)
        company = html.unescape(re.sub(r'<[^>]+>', '', company_m.group(1))).strip() if company_m else "Работодатель на SuperJob"

        # Salary search in snippet
        salary_m = re.search(r'(\d+[\d\s]*[—\-–]\s*\d+[\d\s]*\s*(?:₽|руб|USD|\$)|от\s+\d+[\d\s]*\s*(?:₽|руб)|до\s+\d+[\d\s]*\s*(?:₽|руб)|По договорённости)', snippet)
        salary = salary_m.group(0).strip() if salary_m else "По договорённости"

        is_remote = bool(re.search(r'Удаленная|Удалённо|Remote', snippet, re.I))
        contacts = extract_contacts(snippet)

        vacancies.append({
            "id": vac_id,
            "source": "superjob",
            "title": title,
            "company": company,
            "url": full_url,
            "salary": salary,
            "location": "Удаленно" if is_remote else "Москва / РФ",
            "is_remote": is_remote,
            "description": f"Позиция {title} в компании {company}.",
            "skills": "React, JavaScript, TypeScript, Frontend",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or full_url,
            "contact_type": contacts.get("primary_type") or "portal"
        })

    return vacancies
