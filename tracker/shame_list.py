import os
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.db")
SHAME_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SHAME_LIST.md")

def generate_shame_list_markdown() -> str:
    """Queries all blacklisted vacancies from SQLite and formats a clean Markdown registry."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, company, url, source, salary, location,
               blacklist_reason, blacklisted_at, created_at, description
        FROM vacancies
        WHERE status = 'blacklist'
        ORDER BY blacklisted_at DESC, id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = []
    md.append("# 💩 Доска позора недобросовестных работодателей (Blacklist)\n")
    md.append("> **Цель реестра:** Публичная фиксация компаний и вакансий, нарушающих трудовое законодательство (ст. 15 ТК РФ — принуждение к оформлению через ИП/Самозанятость вместо штатного трудового договора), практикующих неоплачиваемые объемные тестовые задания до первого технического скрининга или вводящих кандидатов в заблуждение по условиям труда.\n")
    md.append(f"**Статистика:** Всего зафиксировано нарушителей: **{total}**  ")
    md.append(f"**Последнее обновление:** `{now_str}`\n")
    md.append("---\n")

    if total == 0:
        md.append("*(На данный момент список пуст. Все проверенные вакансии соответствуют нормам или еще находятся на рассмотрении.)*\n")
        return "".join(md)

    md.append("## 📋 Сводный реестр нарушений\n")
    md.append("| Компания | Вакансия | Источник | Зафиксированное нарушение | Дата | Ссылка |")
    md.append("| :--- | :--- | :--- | :--- | :---: | :---: |")

    for r in rows:
        comp = (r['company'] or 'Не указана').replace('|', '-')
        title = (r['title'] or 'Без названия').replace('|', '-')
        src = (r['source'] or 'direct').replace('|', '-')
        reason = (r['blacklist_reason'] or 'Токсичные условия / Нарушение ТК РФ').replace('|', '-')
        b_date = (r['blacklisted_at'] or r['created_at'] or '')[:10]
        url = r['url']
        link_md = f"[Открыть]({url})" if url else "—"

        md.append(f"| **{comp}** | {title} | `{src}` | 🛑 {reason} | {b_date} | {link_md} |")

    md.append("\n---\n")
    md.append("## 🔎 Подробные детали по нарушениям\n")

    for idx, r in enumerate(rows, 1):
        comp = r['company'] or 'Не указана'
        title = r['title'] or 'Без названия'
        reason = r['blacklist_reason'] or 'Токсичные условия / Нарушение ТК РФ'
        b_time = r['blacklisted_at'] or r['created_at'] or 'Не указано'
        url = r['url'] or 'Нет прямой ссылки'
        desc = (r['description'] or '').strip()
        short_desc = desc[:300] + '...' if len(desc) > 300 else desc

        md.append(f"### {idx}. {comp} — {title}")
        md.append(f"- **Причина внесения:** 🛑 **{reason}**")
        md.append(f"- **Дата фиксации:** `{b_time}`")
        md.append(f"- **Источник / Площадка:** `{r['source']}`")
        md.append(f"- **Ссылка на вакансию:** {url}")
        if short_desc:
            md.append(f"- **Фрагмент описания:**\n> {short_desc}\n")
        md.append("")

    md.append("---\n")
    md.append("*Реестр сформирован автоматически системой Job Hunter CRM.*")

    return "\n".join(md)

def update_shame_list_file() -> str:
    """Regenerates the SHAME_LIST.md file in project root."""
    content = generate_shame_list_markdown()
    with open(SHAME_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    return content
