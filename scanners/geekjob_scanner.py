import json
import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_geekjob_json(json_content_or_str: Any) -> List[Dict[str, Any]]:
    """
    Parses GeekJob JSON API response (/json/find/vacancy?qs=...) into structured vacancy dicts.
    """
    vacancies = []
    
    if isinstance(json_content_or_str, str):
        # Clean markdown wrapper if present
        raw = json_content_or_str.strip()
        if "{" in raw:
            raw = raw[raw.find("{"):]
        try:
            data = json.loads(raw)
        except Exception:
            return vacancies
    else:
        data = json_content_or_str

    items = data.get("data", [])
    for item in items:
        vac_id_raw = item.get("id")
        if not vac_id_raw:
            continue
        
        position = item.get("position", "Frontend Developer")
        company_obj = item.get("company") or {}
        company = company_obj.get("name", "Unknown Company")
        salary = item.get("salary") or "По договорённости"
        
        job_format = item.get("jobFormat") or {}
        is_remote = bool(job_format.get("remote", False))
        
        city = item.get("city") or ""
        country = item.get("country") or ""
        loc_parts = [p for p in [country, city] if p]
        location = ", ".join(loc_parts) if loc_parts else ("Удаленно" if is_remote else "Москва / РФ")

        vac_url = f"https://geekjob.ru/vacancy/{vac_id_raw}"
        vac_id = f"geekjob:{vac_id_raw}"

        # Combine title and details for contact extraction
        contacts = extract_contacts(f"{position} {company} {location}")

        vacancies.append({
            "id": vac_id,
            "source": "geekjob",
            "title": position,
            "company": company,
            "url": vac_url,
            "salary": salary,
            "location": location,
            "is_remote": is_remote,
            "description": f"Позиция {position} в {company}. Формат: {location}, зарплата: {salary}.",
            "skills": "React, TypeScript, Frontend, Fullstack",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or vac_url,
            "contact_type": contacts.get("primary_type") or "portal"
        })

    return vacancies
