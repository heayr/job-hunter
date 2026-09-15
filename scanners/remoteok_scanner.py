import json
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_remoteok_json(json_content: str) -> List[Dict[str, Any]]:
    vacancies = []
    try:
        data = json.loads(json_content)
        # RemoteOK API returns a legal disclaimer as the first element, skip it if needed
        for item in data:
            if "legal" in item:
                continue
            
            title = item.get("position", "")
            company = item.get("company", "")
            description = item.get("description", "")
            url = item.get("url", "")
            location = item.get("location", "Worldwide / Remote")
            salary = f"{item.get('salary_min', '')} - {item.get('salary_max', '')} USD".strip(" - USD")
            if not salary:
                salary = "Not specified"
            else:
                salary = "$" + salary

            tags = item.get("tags", [])
            skills = ", ".join(tags)

            contacts = extract_contacts(description)
            
            vacancies.append({
                "id": f"rok:{item.get('id', url)}",
                "source": "remote_ok",
                "title": title,
                "company": company,
                "url": url,
                "salary": salary,
                "location": location,
                "is_remote": True,
                "description": description[:1500],
                "skills": skills,
                "contact_name": contacts.get("contact_name", ""),
                "contact_handle": contacts.get("primary_handle", url),
                "contact_type": contacts.get("primary_type", "portal")
            })
    except Exception as e:
        pass
    
    return vacancies
