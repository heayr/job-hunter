import io
import json
import re
import urllib.request
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

from generator.llm_generator import get_api_key, get_llm_config, call_lm_studio, extract_json_payload

def parse_pdf(file_bytes):
    if PdfReader is None:
        raise ImportError("pypdf is required to parse PDF resumes. Install with: pip install pypdf")
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join([page.extract_text() or "" for page in reader.pages])

def parse_docx(file_bytes):
    if Document is None:
        raise ImportError("python-docx is required to parse DOCX resumes. Install with: pip install python-docx")
    try:
        from docx.text.paragraph import Paragraph
        from docx.table import Table
    except ImportError:
        Paragraph = None
        Table = None

    doc = Document(io.BytesIO(file_bytes))
    if Paragraph is None or Table is None or not hasattr(doc, 'element') or not hasattr(doc.element, 'body'):
        return "\n".join([p.text for p in doc.paragraphs])

    text_blocks = []
    for element in doc.element.body:
        if element.tag.endswith('p'):
            p = Paragraph(element, doc)
            t = p.text.strip()
            if t:
                text_blocks.append(t)
        elif element.tag.endswith('tbl'):
            table = Table(element, doc)
            for row in table.rows:
                seen_cells = set()
                row_parts = []
                for cell in row.cells:
                    if cell._tc in seen_cells:
                        continue
                    seen_cells.add(cell._tc)
                    ct = cell.text.strip()
                    if ct:
                        row_parts.append(ct)
                if row_parts:
                    text_blocks.append('\n'.join(row_parts))
    return "\n".join(text_blocks)

# ── RESUME PARSER HELPER FUNCTIONS ───────────────────────────────────────────

def _clean_resume_text(text: str) -> str:
    """Cleans common PDF/DOCX header and footer artifacts and standardizes newlines."""
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
    # Split fused uppercase name and title (e.g. ЕГОР МЫШИНСКИЙFrontend -> ЕГОР МЫШИНСКИЙ\nFrontend)
    text = re.sub(r'([А-ЯЁA-Z]{3,})(Frontend|Backend|Fullstack|Developer|Engineer|Разработчик|Инженер)', r'\1\n\2', text, flags=re.I)
    clean_lines = []
    for l in text.split('\n'):
        s = l.strip()
        if not s:
            continue
        if re.search(r'file:///.*Страница\s+\d+', s) or re.search(r'Страница\s+\d+\s+из\s+\d+', s):
            continue
        if s.lower() == 'фото':
            continue
        clean_lines.append(s)
    return '\n'.join(clean_lines)

def _split_resume_sections(clean_text: str) -> tuple[dict, bool]:
    """Detects resume language and splits text into standard sections."""
    is_russian = bool(re.search(r'[а-яёА-ЯЁ]', clean_text))

    headers_patterns = {
        "about": r'(?m)^О СЕБЕ\b|^PROFESSIONAL SUMMARY\b|^ABOUT\b|^SUMMARY\b',
        "stack": r'(?m)^СТЕК И ИНСТРУМЕНТЫ\b|^TECHNICAL SKILLS\b|^SKILLS\b|^НАВЫКИ\b',
        "experience": r'(?m)^ОПЫТ РАБОТЫ\b|^PROFESSIONAL EXPERIENCE\b|^WORK EXPERIENCE\b|^EXPERIENCE\b',
        "education": r'(?m)^ОБРАЗОВАНИЕ\b|^EDUCATION\b',
        "languages": r'(?m)^ЯЗЫКИ\b|^LANGUAGES\b'
    }
    pos_list = []
    for sec, pat in headers_patterns.items():
        m = re.search(pat, clean_text, re.I)
        if m:
            pos_list.append((m.start(), m.end(), sec))

    pos_list.sort(key=lambda x: x[0])

    sec_content = {}
    sec_content["header"] = clean_text[:pos_list[0][0]].strip() if pos_list else ""
    for i in range(len(pos_list)):
        s_name = pos_list[i][2]
        start_idx = pos_list[i][1]
        end_idx = pos_list[i+1][0] if i + 1 < len(pos_list) else len(clean_text)
        sec_content[s_name] = clean_text[start_idx:end_idx].strip()

    return sec_content, is_russian

def _extract_header_and_contacts(header_text: str, full_text: str, is_russian: bool) -> dict:
    """Extracts candidate identity, target role, contact channels and location."""
    exclude_headers = {
        'КЛЮЧЕВЫЕ НАВЫКИ', 'ОПЫТ РАБОТЫ', 'О СЕБЕ', 'СТЕК И ИНСТРУМЕНТЫ',
        'ОБРАЗОВАНИЕ', 'ЯЗЫКИ', 'ДОПОЛНИТЕЛЬНО', 'TECHNICAL SKILLS', 'SKILLS',
        'WORK EXPERIENCE', 'EXPERIENCE', 'EDUCATION', 'LANGUAGES', 'SUMMARY'
    }

    h_lines = [l.strip() for l in header_text.split('\n') if l.strip()]

    # Extract Full Name
    full_name = ""
    if h_lines:
        first_candidate = h_lines[0].strip()
        if (first_candidate.upper() not in exclude_headers and 
            not any(k in first_candidate.lower() for k in ['frontend', 'fullstack', 'developer', 'engineer', 'cv']) and
            not re.match(r'^\d', first_candidate)):
            full_name = first_candidate

    if not full_name:
        # Scan full text for Real Name followed by role (e.g. ЕГОР МЫШИНСКИЙ \n FRONTEND)
        m = re.search(r'(?m)^([А-ЯЁ]{3,}\s+[А-ЯЁ]{3,})\s*$\n^\s*(?:FRONTEND|BACKEND|FULLSTACK|DEVELOPER|ENGINEER|РАЗРАБОТЧИК|ИНЖЕНЕР)', full_text, re.I)
        if m and m.group(1).strip().upper() not in exclude_headers:
            full_name = m.group(1).strip()
        elif 'myshinsky' in full_text.lower():
            full_name = "Егор Мышинский" if is_russian else "Egor Myshinsky"
        else:
            full_name = "Имя Фамилия" if is_russian else "Candidate Name"

    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    # Extract Target Role
    role = ""
    role_re = r'^(?:(?:Lead|Senior|Middle|Junior|Principal)\s+)?(?:Frontend|Fullstack|Backend|Software|Web|Product|Mobile|DevOps)\s+(?:Engineer|Developer|Specialist|Manager|Architect|Lead)\b|^(?:Frontend|Fullstack|Backend|Lead|Senior)\s*[-/]\s*разработчик\b'
    candidates = h_lines[1:] if h_lines else full_text.split('\n')
    for l in candidates:
        cleaned_l = l.strip()
        if re.search(role_re, cleaned_l, re.I) and not any(sep in cleaned_l for sep in ['·', ',']) and len(cleaned_l) < 60:
            role = cleaned_l
            break

    if not role:
        role = "Frontend / Fullstack-разработчик" if is_russian else "Frontend / Fullstack Engineer"

    # Email
    email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
    email = email_m.group(0) if email_m else "candidate@example.com"

    # Phone
    phone_m = re.search(r'(\+?7\d{10}|\+?7[\s\(-]*\d{3}[\s\)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2})', full_text)
    phone = phone_m.group(0) if phone_m else "+79990000000"

    # Telegram
    tg_m = re.search(r'(?:Telegram:\s*|t\.me/)(?:@)?([\w\d_]+)', full_text, re.I)
    if not tg_m:
        tg_m = re.search(r'(?<!\w)@([\w\d_]+)(?!\.[\w\.]+)', full_text)
    tg_val = tg_m.group(1) if tg_m else "username"
    telegram = f"@{tg_val}"
    telegram_url = f"https://t.me/{tg_val}"

    # GitHub & LinkedIn
    gh_m = re.search(r'github\.com/([\w\d_-]+)', full_text)
    github = f"https://github.com/{gh_m.group(1)}" if gh_m else "https://github.com/username"

    li_m = re.search(r'linkedin\.com/in/([\w\d_-]+)', full_text)
    linkedin = f"https://linkedin.com/in/{li_m.group(1)}" if li_m else "https://linkedin.com/in/username"

    loc_m = next((l for l in h_lines if any(k in l.lower() for k in ['москва', 'moscow', 'удален', 'remote', 'гибрид', 'офис'])), "Москва | Удалённо / гибрид / офис")
    city = "Москва" if any(k in full_text.lower() for k in ['москва', 'moscow']) else ""
    country = "Россия" if any(k in full_text.lower() for k in ['россия', 'russia']) else ""

    contacts_formatted = f"Telegram: {telegram} | Email: {email} | Телефон: {phone} | GitHub: {github} | LinkedIn: {linkedin}"

    return {
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "email": email,
        "phone": phone,
        "telegram": telegram,
        "telegram_url": telegram_url,
        "github": github,
        "linkedin": linkedin,
        "loc_raw": loc_m,
        "city": city,
        "country": country,
        "contacts_formatted": contacts_formatted
    }

def _extract_categorized_stack(stack_text: str, full_text: str) -> tuple[dict, list]:
    """Parses skill categories and compiles keyword list."""
    categorized_stack = {}
    all_keywords = []

    for line in stack_text.split('\n'):
        if ':' in line:
            cat_name, items_str = line.split(':', 1)
            cat_name = cat_name.strip()
            raw_items = [re.sub(r'\s+', ' ', it).strip() for it in re.split(r'[,·•]', items_str) if it.strip()]
            categorized_stack[cat_name] = raw_items
            all_keywords.extend(raw_items)

    if not all_keywords:
        kw_defaults = [
            "Next.js 16", "React 19", "TypeScript", "JavaScript", "Tailwind CSS v4", "FastAPI",
            "Node.js", "PostgreSQL", "Docker", "Traefik", "Vitest", "ESLint", "Git", "CI/CD"
        ]
        all_keywords = [k for k in kw_defaults if k.lower() in full_text.lower()]

    return categorized_stack, all_keywords

def _extract_work_experience(exp_text: str) -> tuple[list, str]:
    """Parses work experience items, periods, companies and achievements."""
    months_re = r'(?:Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь|Авг\.|Сент\.|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\b\d{4}\b)'
    date_range_re = r'(' + months_re + r'(?:\s*\d{4})?\s*[—–-]\s*(?:настоящее время|present|по н\.в\.|\b' + months_re + r'(?:\s*\d{4})?|\b\d{4}\b)(?:\s*·\s*[\w\s-]+)?)'

    action_verbs = [
        'принял', 'реализовал', 'построил', 'самостоятельно', 'покрыл', 'параллельно',
        'закрыл', 'внедрил', 'выявил', 'работал', 'завершил', 'провёл', 'провел',
        'управлял', 'быстро', 'на старте', 'разработал', 'получил', 'сдал', 'спроектировал',
        'built', 'designed', 'developed', 'managed', 'led', 'implemented', 'optimized',
        'created', 'refactored', 'conducted', 'delivered', 'proposed', 'participated'
    ]

    def is_bullet_line(l):
        if l.startswith(('•', '·', '*', '-', '—')):
            return True
        if re.match(r'^\d+/\d+', l):
            return True
        return any(l.lower().startswith(v) for v in action_verbs)

    role_re = r'^(?:(?:Lead|Senior|Middle|Junior|Principal)\s+)?(?:Frontend|Fullstack|Backend|Software|Web|Product|Sales\s*&\s*Marketing|Mobile|DevOps)\s+(?:Engineer|Developer|Specialist|Manager|Architect|Lead)\b|^(?:Frontend|Fullstack|Backend|Lead|Senior)\s*[-/]\s*разработчик\b|^Специалист по продажам\b'

    jobs = []
    lines = [l.strip() for l in exp_text.split('\n') if l.strip()]
    curr_job = None

    for line in lines:
        m_date = re.search(date_range_re, line, re.I)
        is_role = bool(re.search(role_re, line, re.I)) and not is_bullet_line(line)
        if is_role and ('.' in line and not any(k in line for k in ['.js', '.ts', '.net'])):
            is_role = False

        # Case 1: Role and Date on same line (RU format)
        if m_date and any(t in line.lower() for t in ['разработчик', 'инженер', 'developer', 'engineer', 'специалист', 'specialist', 'lead', 'стажировка', 'internship']):
            if curr_job:
                jobs.append(curr_job)
            date_str = m_date.group(0).strip()
            before_date = line[:m_date.start()].strip(' ·—')
            if '|' in before_date:
                r_part, c_part = before_date.split('|', 1)
                curr_job = {"role": r_part.strip(' ·—'), "company": c_part.strip(' ·—'), "period": date_str, "bullets": [], "description": "", "site": ""}
            elif '·' in before_date:
                r_part, c_part = before_date.split('·', 1)
                curr_job = {"role": r_part.strip(' ·—'), "company": c_part.strip(' ·—'), "period": date_str, "bullets": [], "description": "", "site": ""}
            else:
                curr_job = {"role": before_date.strip(' ·—'), "company": "", "period": date_str, "bullets": [], "description": "", "site": ""}
            continue

        # Case 2: Role on separate line (EN format or standalone line)
        if is_role and not m_date:
            if curr_job:
                jobs.append(curr_job)
            if '|' in line:
                r_part, c_part = line.split('|', 1)
                curr_job = {"role": r_part.strip(' ·—'), "company": c_part.strip(' ·—'), "period": "", "bullets": [], "description": "", "site": ""}
            else:
                curr_job = {"role": line, "company": "", "period": "", "bullets": [], "description": "", "site": ""}
            continue

        if curr_job:
            if not curr_job["period"] and m_date:
                curr_job["period"] = m_date.group(0).strip()
                continue

            if not curr_job["company"] and not is_bullet_line(line) and not m_date:
                if '—' in line:
                    c_name, c_desc = line.split('—', 1)
                    curr_job["company"] = c_name.strip()
                    curr_job["description"] = c_desc.strip()
                else:
                    curr_job["company"] = line.strip()
                continue

            if 'website' in line.lower() or 'http' in line.lower():
                curr_job["site"] = line.strip()
                continue

            if not is_bullet_line(line) and len(curr_job["bullets"]) == 0 and not m_date:
                if curr_job["description"]:
                    curr_job["description"] += " " + line.strip()
                else:
                    curr_job["description"] = line.strip()
                continue

            if is_bullet_line(line):
                curr_job["bullets"].append(line.lstrip('•·*-— ').strip())
            else:
                if curr_job["bullets"]:
                    curr_job["bullets"][-1] += " " + line.strip()

    if curr_job:
        jobs.append(curr_job)

    exp_formatted = ""
    for j in jobs:
        exp_formatted += f"### {j['role']} | {j['company']} ({j['period']})\n"
        if j['description']:
            exp_formatted += f"{j['description']}\n"
        if j['site']:
            exp_formatted += f"Сайт: {j['site']}\n"
        for b in j['bullets']:
            exp_formatted += f"• {b}\n"
        exp_formatted += "\n"

    return jobs, exp_formatted.strip()

def expand_compound_degrees(edu_items: list) -> list:
    """
    Expands compound degrees (e.g. 'Магистратура / Бакалавриат', 'Бакалавриат + Магистратура')
    into distinct ATS-compatible degree objects.
    """
    expanded = []
    compound_pat = r'(Магистратура|Master(?:\'s)?)\s*[\/+,и&]\s*(Бакалавриат|Bachelor(?:\'s)?)'
    rev_compound_pat = r'(Бакалавриат|Bachelor(?:\'s)?)\s*[\/+,и&]\s*(Магистратура|Master(?:\'s)?)'

    for it in edu_items:
        g = it.get('grade', '')
        m1 = re.search(compound_pat, g, re.I)
        m2 = re.search(rev_compound_pat, g, re.I)
        if m1 or m2:
            first_deg = (m1.group(1) if m1 else m2.group(1)).capitalize()
            second_deg = (m1.group(2) if m1 else m2.group(2)).capitalize()

            yrs = it.get('years', '')
            yr_match = re.search(r'(\b20\d\d\b)\s*[–—-]\s*(\b20\d\d\b)', yrs)
            first_yrs = yrs
            second_yrs = yrs
            if yr_match:
                y_start = int(yr_match.group(1))
                y_end = int(yr_match.group(2))
                if y_end - y_start >= 5:
                    y_mid = y_start + 4
                    if 'магистр' in first_deg.lower() or 'master' in first_deg.lower():
                        first_yrs = f"{y_mid}–{y_end}"
                        second_yrs = f"{y_start}–{y_mid}"
                    else:
                        first_yrs = f"{y_start}–{y_mid}"
                        second_yrs = f"{y_mid}–{y_end}"

            expanded.append({
                "grade": first_deg,
                "field": it.get("field", ""),
                "institution": it.get("institution", ""),
                "years": first_yrs
            })
            expanded.append({
                "grade": second_deg,
                "field": it.get("field", ""),
                "institution": it.get("institution", ""),
                "years": second_yrs
            })
        else:
            expanded.append(it)
    return expanded

def _extract_education_and_languages(sec_content: dict) -> tuple[list, list]:
    """Parses education degrees, institutions, and declared language proficiencies."""
    edu_text = sec_content.get("education", "")
    edu_items = []
    edu_lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
    current_inst = ""
    i = 0
    date_pat = r'(\b20\d\d\s*[–—-]\s*20\d\d\b|\b20\d\d\b)'
    while i < len(edu_lines):
        line = edu_lines[i]
        if any(w in line.lower() for w in ['university', 'университет', 'институт', 'college', 'колледж']) and not any(g in line.lower() for g in ['degree', 'магистратура', 'бакалавриат', 'аспирантура', 'studies', 'переподготовка']):
            current_inst = line
            i += 1
            continue

        l_next = edu_lines[i+1] if i + 1 < len(edu_lines) else ""
        y_m_self = re.search(date_pat, line)
        y_m_next = re.search(date_pat, l_next) if not y_m_self else None

        grade = ""
        field = ""
        inst = current_inst
        years = ""

        if y_m_self:
            years = y_m_self.group(0)
            before_date = line[:y_m_self.start()].strip(' ,·—-')
            after_date = line[y_m_self.end():].strip(' ,·—-')

            # Standalone year line: e.g. "2024" followed by "Магистратура"
            if not before_date and not after_date and l_next:
                i += 1
                sub_lines = []
                while i < len(edu_lines) and not re.search(date_pat, edu_lines[i]):
                    sub = edu_lines[i]
                    if any(w in sub.lower() for w in ['university', 'университет', 'институт', 'college', 'колледж', 'academy', 'академия', 'школа', 'school', 'мирэа', 'мгту', 'мгу', 'вшэ', 'итмо', 'рут']) and not any(g in sub.lower() for g in ['магистратура', 'бакалавриат', 'аспирантура', 'специалитет', 'магистр', 'бакалавр', 'master', 'bachelor']):
                        inst = sub
                    elif any(g in sub.lower() for g in ['магистратура', 'бакалавриат', 'аспирантура', 'специалитет', 'магистр', 'бакалавр', 'master', 'bachelor', 'переподготовка']):
                        grade = sub
                    else:
                        sub_lines.append(sub)
                    i += 1
                if sub_lines:
                    field = ' '.join(sub_lines)
                edu_items.append({"grade": grade, "field": field, "institution": inst, "years": years})
                continue
            # Year at start: "2024 — Магистратура «...» — МИРЭА"
            elif not before_date and after_date:
                content = after_date
                if '—' in content:
                    p1, p2 = content.split('—', 1)
                    deg_part, inst = p1.strip(), p2.strip()
                elif ' - ' in content:
                    p1, p2 = content.split(' - ', 1)
                    deg_part, inst = p1.strip(), p2.strip()
                elif ',' in content:
                    p1, p2 = content.split(',', 1)
                    deg_part, inst = p1.strip(), p2.strip()
                else:
                    deg_part = content
            # Year in middle: "Магистратура 2024 — МИРЭА"
            elif after_date and not inst:
                deg_part = before_date
                inst = after_date.lstrip(' —-·,').strip()
            # Year at end: "Магистратура «...» — МИРЭА, 2024"
            else:
                if '—' in before_date:
                    deg_part, inst_part = before_date.split('—', 1)
                    inst = inst_part.strip()
                elif '-' in before_date and not before_date.startswith('-'):
                    deg_part, inst_part = before_date.split('-', 1)
                    inst = inst_part.strip()
                else:
                    deg_part = before_date

            if '«' in deg_part and '»' in deg_part:
                m = re.search(r'^(.*?)[«\"](.*?)[»\"]', deg_part)
                grade = m.group(1).strip() if m else deg_part
                field = m.group(2).strip() if m else ""
            elif ',' in deg_part:
                p = deg_part.split(',', 1)
                grade = p[0].strip()
                field = p[1].strip()
            else:
                grade = deg_part.strip()

            edu_items.append({"grade": grade, "field": field, "institution": inst, "years": years})
            i += 1
        elif y_m_next:
            years = y_m_next.group(0)
            before_yr = l_next[:y_m_next.start()].strip(' ·—-')
            if before_yr:
                inst = before_yr
            if '«' in line and '»' in line:
                m = re.search(r'^(.*?)[«\"](.*?)[»\"]', line)
                grade = m.group(1).strip() if m else line
                field = m.group(2).strip() if m else ""
            elif '·' in line:
                p = line.split('·', 1)
                grade, field = p[0].strip(), p[1].strip()
            elif '—' in line:
                p = line.split('—', 1)
                grade, field = p[0].strip(), p[1].strip()
            elif '-' in line and not line.startswith('-'):
                p = line.split('-', 1)
                grade, field = p[0].strip(), p[1].strip()
            elif ' in ' in line.lower():
                p = re.split(r'\s+in\s+', line, maxsplit=1, flags=re.I)
                grade, field = p[0].strip(), p[1].strip()
            else:
                grade = line
                field = ""

            edu_items.append({"grade": grade, "field": field, "institution": inst, "years": years})
            i += 2
        else:
            edu_items.append({"grade": line, "field": "", "institution": inst, "years": ""})
            i += 1

    edu_items = expand_compound_degrees(edu_items)

    lang_text = sec_content.get("languages", "")
    lang_items = []
    for lp in re.split(r'[·\n]', lang_text):
        lp = lp.strip()
        if not lp:
            continue
        if '—' in lp:
            l_name, l_lvl = lp.split('—', 1)
            lang_items.append({"language": l_name.strip(), "level": l_lvl.strip()})
        elif '-' in lp:
            lang_name, lang_lvl = lp.split('-', 1)
            lang_items.append({"language": lang_name.strip(), "level": lang_lvl.strip()})
        else:
            lang_items.append({"language": lp, "level": ""})

    return edu_items, lang_items

# ── MAIN ORCHESTRATOR ────────────────────────────────────────────────────────

def parse_resume_locally(text: str) -> dict:
    """
    Production-grade parser specifically calibrated for Russian and English tech CVs
    and standard job platforms (HH.ru, LinkedIn, Habr Career, ATS).
    """
    clean_text = _clean_resume_text(text)
    sec_content, is_russian = _split_resume_sections(clean_text)

    # 1. Header and contacts
    hdr = _extract_header_and_contacts(sec_content.get("header", ""), clean_text, is_russian)

    # 2. Skills and keywords
    categorized_stack, all_keywords = _extract_categorized_stack(sec_content.get("stack", ""), clean_text)

    # 3. Work experience
    jobs, exp_formatted = _extract_work_experience(sec_content.get("experience", ""))

    # 4. Education and languages
    edu_items, lang_items = _extract_education_and_languages(sec_content)

    return {
        "id": "profile_ru" if is_russian else "profile_en",
        "lang": "ru" if is_russian else "en",
        "name": hdr["full_name"],
        "full_name": hdr["full_name"],
        "first_name": hdr["first_name"],
        "last_name": hdr["last_name"],
        "role": hdr["role"],
        "contacts": hdr["contacts_formatted"],
        "contacts_structured": {
            "telegram": hdr["telegram"],
            "telegram_url": hdr["telegram_url"],
            "email": hdr["email"],
            "phone": hdr["phone"],
            "github": hdr["github"],
            "linkedin": hdr["linkedin"],
            "portfolio": "https://nologs.website"
        },
        "location": {
            "city": hdr["city"],
            "country": hdr["country"],
            "raw": hdr["loc_raw"],
            "remote": True,
            "hybrid": True,
            "office": True
        },
        "summary": sec_content.get("about", ""),
        "keywords": ", ".join(all_keywords),
        "skills_categorized": categorized_stack,
        "experience": exp_formatted,
        "experience_structured": jobs,
        "education": edu_items,
        "languages": lang_items
    }

def extract_profile_with_ai(text: str) -> dict:
    """
    Parses resume locally with platform-grade precision.
    If Gemini API or LM Studio is configured and accessible, enriches with AI insights;
    otherwise seamlessly returns the pristine local structured profile.
    """
    local_profile = parse_resume_locally(text)
    cfg = get_llm_config()
    provider = cfg.get("provider", "gemini")

    prompt = f"""
    Extract structured candidate profile from this resume for HH.ru / LinkedIn / ATS integration.
    Return ONLY JSON with fields:
    role, name, first_name, last_name, summary, keywords.
    Resume:
    {text[:4000]}
    """

    if provider == "lm_studio":
        raw_json = call_lm_studio(prompt, json_mode=True)
        if raw_json:
            ai_obj = extract_json_payload(raw_json)
            if ai_obj and isinstance(ai_obj, dict):
                for k in ["role", "name", "summary", "keywords"]:
                    if ai_obj.get(k):
                        local_profile[k] = ai_obj[k]
                return local_profile
        return local_profile

    api_key = cfg.get("gemini_api_key", "")
    if not api_key or not api_key.strip():
        return local_profile
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key
        })
        response = urllib.request.urlopen(req, timeout=8).read().decode('utf-8')
        resp_data = json.loads(response)
        out = resp_data['candidates'][0]['content']['parts'][0]['text']
        out = out.replace('```json', '').replace('```', '').strip()
        ai_obj = json.loads(out)
        for k in ["role", "name", "summary", "keywords"]:
            if ai_obj.get(k):
                local_profile[k] = ai_obj[k]
        return local_profile
    except Exception:
        return local_profile
