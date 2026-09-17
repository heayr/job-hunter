import re
import html
import urllib.request
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from enricher.lead_finder import extract_contacts


class TelegramScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "telegram"
        self.channels = [
            "job_react",
            "forfrontend",
            "normrabota",
            "javascript_jobs_feed",
            "remote_it_jobs",
            "getitrussia",
            "devjobs"
        ]

    def scrape(self) -> List[Dict[str, Any]]:
        vacancies: List[Dict[str, Any]] = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        for channel in self.channels:
            url = f"https://t.me/s/{channel}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html_content = resp.read().decode('utf-8', errors='ignore')

                # Extract message blocks
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

                    text = re.sub(r'<br\s*/?>', '\n', msg_html)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = html.unescape(text).strip()

                    # Check minimum length and relevance
                    if len(text) < 50:
                        continue

                    # Skip candidate resumes / self-promotions
                    resume_patterns = r'(?:#резюме\b|#cv\b|\bищу работу\b|\bв поиске работы\b|\bв поисках работы\b|\bв поиске проекта\b|\bищу проект\b|\bищу команду\b|\bopen to work\b|\blooking for (?:a )?job\b|\blooking for (?:new )?opportunities\b|\bготов к предложениям\b|\bрассматриваю предложения\b|\bготов рассмотреть предложения\b|\bоткрыт к предложениям\b|\bобо мне:\b|\bо себе:\b|\bмой стек:\b|\bмои навыки:\b|\bобо мне\n|\bо себе\n|резюме\s*[:\-]|cv\s*[:\-])'
                    if re.search(resume_patterns, text, re.I):
                        continue

                    # Skip promotional / ads / webinars / events / meetups
                    ad_patterns = r'(?:\bвебинар\b|\bинтенсив\b|\bтестовый собес\b|\bпробное собеседование\b|\bонлайн-практикум\b|\bбесплатный практикум\b|\bпрямой эфир\b|\bподкаст\b|\bмитап\b|\bконференция\b|\bреклама\.\s*о рекламодателе\b|подарок для всех,\s*кто зарегается)'
                    if re.search(ad_patterns, text, re.I):
                        continue

                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    # Skip if first line indicates candidate resume or self-promotion
                    if lines and re.search(r'^(?:[^\w\s]*\s*)?(?:резюме|cv)\b', lines[0], re.I):
                        continue
                    # Filter out purely hashtag lines and salary/noise lines for title extraction
                    content_lines = [
                        l for l in lines 
                        if not all(w.startswith('#') for w in l.split()) 
                        and not re.search(r'^(?:вилка|зарплата|зп|оклад|salary|от\s+\d+|до\s+\d+|\d+[\d\s]*\s*(?:₽|руб|\$|eur))\b', l, re.I)
                    ]

                    company_match = re.search(r'(?:компания|продукт|проект|в компанию|startup|company)[:\s]+([^\n.,;]+)', text, re.I)
                    company = company_match.group(1).strip() if company_match else ""

                    # Find a line that looks like a title/role
                    role_line = None
                    for cl in content_lines:
                        if re.search(r'\b(?:frontend|фронтенд|react|next\.?js|full-?stack|фуллстек|developer|разработчик|engineer|инженер)\b', cl, re.I):
                            role_line = cl.strip("# \t*•-")
                            break

                    title = role_line or (content_lines[0][:80].strip("# \t*•-") if content_lines else "Frontend Developer")
                    if not company:
                        if len(content_lines) >= 2 and content_lines[0] != title:
                            company = content_lines[0][:60].strip("# \t*•-")
                        else:
                            company = f"TG: @{channel}"

                    salary_match = re.search(r'(\d+[\d\s]*[—\-–]\s*\d+[\d\s]*\s*(?:₽|руб|USD|\$|EUR|€)|от\s+\d+[\d\s]*\s*(?:₽|руб|USD|\$)|до\s+\d+[\d\s]*\s*(?:₽|руб|USD|\$))', text, re.I)
                    salary = salary_match.group(0).strip() if salary_match else "Не указана"

                    is_remote = bool(re.search(r'удален|remote|удалёнка|любая локация', text, re.I))
                    contacts = extract_contacts(text)
                    post_url = f"https://t.me/{post_id}"

                    # Only mark as "direct contact" if we found a REAL personal handle
                    # (not a channel name, not the post URL itself)
                    has_real_contact = bool(contacts.get("primary_handle"))
                    contact_handle = contacts.get("primary_handle") or ""
                    contact_type = contacts.get("primary_type") or "portal"

                    # Skills extraction from text
                    skill_keywords = ["React", "Next.js", "TypeScript", "JavaScript", "Vue", "Node.js", "Redux", "Tailwind", "CSS", "HTML"]
                    found_skills = [sk for sk in skill_keywords if re.search(rf'\b{re.escape(sk)}\b', text, re.I)]
                    skills_str = ", ".join(found_skills) if found_skills else "React, TypeScript, Frontend"

                    # Extract post timestamp if present
                    time_match = re.search(r'<time[^>]*datetime="([^"]+)"', block_html)
                    published_at = time_match.group(1).replace('T', ' ').split('+')[0] if time_match else None

                    vacancies.append({
                        "id": f"tg:{post_id.replace('/', '_')}",
                        "source": f"tg_{channel}",
                        "title": title,
                        "company": company,
                        "url": post_url,
                        "salary": salary,
                        "location": "Удаленно" if is_remote else "РФ / Remote",
                        "is_remote": 1 if is_remote else 0,
                        "description": text[:2500],
                        "skills": skills_str,
                        "language": "ru",
                        "contact_name": contacts.get("contact_name") or "",
                        "contact_handle": contact_handle,
                        "contact_type": contact_type,
                        "published_at": published_at
                    })

            except Exception as e:
                print(f"  ✗ TelegramScraper error on @{channel}: {e}")

        return vacancies
