import re
import html
from typing import List, Dict, Any
from enricher.lead_finder import extract_contacts

def parse_telegram_html(html_content: str, channel_name: str = "telegram") -> List[Dict[str, Any]]:
    """
    Parses Telegram channel web view (t.me/s/<channel>) into vacancy dicts.
    """
    vacancies = []
    
    # Robust pattern for Telegram web view message containers
    message_blocks = re.findall(
        r'<div class="[^"]*tgme_widget_message\b[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)(?=<div class="[^"]*tgme_widget_message\b|\Z)',
        html_content,
        re.DOTALL
    )
    
    for post_id, block_html in message_blocks:
        t_match = re.search(r'<div class="tgme_widget_message_text[^\"]*"[^>]*>(.*?)</div>', block_html, re.DOTALL)
        if not t_match:
            continue
        msg_html = t_match.group(1)

        # Convert HTML breaks to newlines
        text = re.sub(r'<br\s*/?>', '\n', msg_html)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text).strip()

        # Check if it looks like a vacancy
        is_vacancy = any(k in text.lower() for k in ["вакансия", "ищем", "hiring", "developer", "разработчик", "frontend", "react", "fullstack", "зарплата", "вилка", "отклик"])
        if not is_vacancy or len(text) < 60:
            continue

        # Extract company and title by skipping hashtag lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content_lines = [l for l in lines if not all(w.startswith('#') for w in l.split())]

        company_match = re.search(r'(?:компания|продукт|проект|в компанию|startup|company)[:\s]+([^\n.,;]+)', text, re.I)
        if company_match:
            company = company_match.group(1).strip()
            title = content_lines[0][:80].strip("# \t*•-") if content_lines else "Frontend Developer"
        elif len(content_lines) >= 2:
            company = content_lines[0][:60].strip("# \t*•-")
            title = content_lines[1][:80].strip("# \t*•-")
        else:
            company = f"Компания из @{channel_name}"
            title = content_lines[0][:80].strip("# \t*•-") if content_lines else "Frontend Developer"

        if not any(k in title.lower() for k in ["developer", "разработчик", "frontend", "react", "engineer", "fullstack"]):
            title = f"Frontend Developer ({title[:40]})"

        # Extract salary
        salary_match = re.search(r'(\d+[\d\s]*[—\-–]\s*\d+[\d\s]*\s*(?:₽|руб|USD|\$|EUR|€)|от\s+\d+[\d\s]*\s*(?:₽|руб|USD|\$)|до\s+\d+[\d\s]*\s*(?:₽|руб|USD|\$))', text, re.I)
        salary = salary_match.group(0).strip() if salary_match else "Не указана"

        is_remote = bool(re.search(r'удален|remote|удалёнка|любая локация', text, re.I))
        contacts = extract_contacts(text)
        post_url = f"https://t.me/{post_id}"

        vacancies.append({
            "id": f"tg:{post_id.replace('/', '_')}",
            "source": f"tg_{channel_name}",
            "title": title,
            "company": company,
            "url": post_url,
            "salary": salary,
            "location": "Удаленно" if is_remote else "РФ / Remote",
            "is_remote": is_remote,
            "description": text[:1500],
            "skills": "React, TypeScript, JavaScript",
            "contact_name": contacts.get("contact_name") or "",
            "contact_handle": contacts.get("primary_handle") or f"https://t.me/{post_id}",
            "contact_type": contacts.get("primary_type") or "telegram"
        })

    return vacancies
