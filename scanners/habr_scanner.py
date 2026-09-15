import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_habr_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses Habr Career vacancy search HTML content into structured vacancy dicts.
    """
    vacancies = []
    
    # Pattern to match vacancy cards
    # <div class="vacancy-card__info">...
    cards = re.findall(r'<div class="vacancy-card__info">(.*?)</div>\s*</div>\s*<div class="vacancy-card__footer">', html_content, re.DOTALL)
    
    for card in cards:
        # Title & URL
        title_match = re.search(r'<a class="vacancy-card__title-link"[^>]*href="(/vacancies/\d+)"[^>]*>(.*?)</a>', card, re.DOTALL)
        if not title_match:
            continue
        url_path, title = title_match.groups()
        title = html.unescape(title).strip()
        vac_id = f"habr:{url_path.replace('/vacancies/', '')}"
        url = f"https://career.habr.com{url_path}"

        # Company
        company_match = re.search(r'<a class="link-comp link-comp--appearance-dark"[^>]*>(.*?)</a>', card, re.DOTALL)
        company = html.unescape(company_match.group(1)).strip() if company_match else "Unknown"

        # Salary
        salary_match = re.search(r'<div class="basic-salary">(.*?)</div>', card, re.DOTALL)
        salary = html.unescape(salary_match.group(1)).strip() if salary_match else "Не указана"

        # Location & Remote
        is_remote = bool(re.search(r'Можно удалённо|Удаленно|Remote', card, re.I))
        location_match = re.search(r'<div class="chip-with-icon__text">(.*?)</div>', card, re.DOTALL)
        location = html.unescape(location_match.group(1)).strip() if location_match else ("Удаленно" if is_remote else "")

        # Skills
        skills = re.findall(r'<div class="basic-chip__text">(.*?)</div>', card)
        skills_str = ", ".join(html.unescape(s).strip() for s in skills)

        contacts = extract_contacts(card)

        vacancies.append({
            "id": vac_id,
            "source": "habr",
            "title": title,
            "company": company,
            "url": url,
            "salary": salary,
            "location": location,
            "is_remote": is_remote,
            "description": f"Стек: {skills_str}",
            "skills": skills_str,
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or url,
            "contact_type": contacts.get("primary_type") or "portal"
        })

    return vacancies
