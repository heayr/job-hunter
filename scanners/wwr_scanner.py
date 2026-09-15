import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_wwr_rss(xml_content: str) -> List[Dict[str, Any]]:
    """
    Robust regex-based parser for We Work Remotely RSS feeds.
    Works even if XML is partially truncated or contains malformed entities.
    """
    vacancies = []
    
    items = re.findall(r'<item>(.*?)(?:</item>|$)', xml_content, re.DOTALL)
    for item in items:
        title_m = re.search(r'<title>(.*?)</title>', item)
        link_m = re.search(r'<link>(.*?)</link>', item)
        if not link_m:
            link_m = re.search(r'<guid[^>]*>(.*?)(?:</guid>|$)', item)
        desc_m = re.search(r'<description>(.*?)(?:</description>|$)', item, re.DOTALL)
        region_m = re.search(r'<region>(.*?)</region>', item)

        if not title_m:
            continue

        raw_title = html.unescape(title_m.group(1)).strip()
        link = link_m.group(1).strip() if link_m else ""
        desc = html.unescape(desc_m.group(1)).strip() if desc_m else ""
        # Clean HTML tags from description
        clean_desc = re.sub(r'<[^>]+>', ' ', desc)
        clean_desc = ' '.join(clean_desc.split())
        
        region = region_m.group(1).strip() if region_m else "Anywhere in the World"

        parts = raw_title.split(":", 1)
        company = parts[0].strip() if len(parts) > 1 else "Unknown"
        title = parts[1].strip() if len(parts) > 1 else raw_title

        vac_id = f"wwr:{link.split('/')[-1] if link else abs(hash(raw_title))}"
        contacts = extract_contacts(clean_desc)

        vacancies.append({
            "id": vac_id,
            "source": "wwr",
            "title": title,
            "company": company,
            "url": link,
            "salary": "USD Remote",
            "location": region,
            "is_remote": True,
            "description": clean_desc[:1500],
            "skills": "React, TypeScript, Frontend, Remote",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or link,
            "contact_type": contacts.get("primary_type") or "portal"
        })

    return vacancies
