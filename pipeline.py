import os
import sys
from typing import List, Dict, Any

from tracker.db import init_db, save_vacancy, save_pitch, get_pending_pitches, update_pitch_status, get_stats
from enricher.lead_finder import extract_contacts
from generator.pitch_builder import generate_pitch, extract_target_keywords
from filter.profile_filter import is_qualified_vacancy

class JobHunterPipeline:
    def __init__(self):
        init_db()

    def process_vacancies(self, vacancies: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingests a list of vacancy dicts, filters strictly for candidate's tech stack, 
        enriches contacts, generates personalized pitches and ATS tailored CVs, and saves to database.
        """
        added_vacancies = 0
        added_pitches = 0
        skipped = 0

        for vac in vacancies:
            # Strictly filter by title and stack
            ok, reason = is_qualified_vacancy(
                vac.get("title", ""),
                vac.get("skills", ""),
                vac.get("description", ""),
                vac.get("company", "")
            )
            if not ok:
                skipped += 1
                continue

            # Enrich contacts if not already present
            if not vac.get("contact_handle") or vac.get("contact_type") == "portal":
                enriched = extract_contacts(vac.get("description", "") + " " + vac.get("title", ""))
                if enriched.get("primary_handle"):
                    vac["contact_handle"] = enriched["primary_handle"]
                    vac["contact_type"] = enriched["primary_type"]
                if enriched.get("contact_name") and not vac.get("contact_name"):
                    vac["contact_name"] = enriched["contact_name"]

            # Save vacancy to database
            is_new = save_vacancy(vac)
            if is_new:
                added_vacancies += 1
                # Generate pitches & ATS tailored CV
                pitches = generate_pitch(vac)
                
                # Save Short DM pitch
                save_pitch(
                    vacancy_id=vac["id"],
                    pitch_type="short_dm",
                    language=pitches["language"],
                    content=pitches["short_dm"]
                )
                
                # Save Cover Letter pitch
                save_pitch(
                    vacancy_id=vac["id"],
                    pitch_type="cover_letter",
                    language=pitches["language"],
                    content=pitches["cover_letter"]
                )

                # Save Tailored ATS Resume
                if "tailored_cv" in pitches:
                    save_pitch(
                        vacancy_id=vac["id"],
                        pitch_type="tailored_cv",
                        language=pitches["language"],
                        content=pitches["tailored_cv"]
                    )
                    added_pitches += 3
                else:
                    added_pitches += 2

        return {
            "processed": len(vacancies),
            "added_vacancies": added_vacancies,
            "added_pitches": added_pitches,
            "skipped": skipped
        }

    def generate_review_html(self, output_path: str = None) -> str:
        """
        Renders a clean, interactive HTML dashboard showing all pending drafts,
        with ATS keyword matching badges, tailored CV tab, direct Telegram/LinkedIn click links,
        and copy-to-clipboard buttons.
        """
        if output_path is None:
            output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "review_queue.html")

        pending = get_pending_pitches()
        stats = get_stats()

        # Group by vacancy
        vac_map = {}
        for row in pending:
            vid = row["vacancy_id"]
            if vid not in vac_map:
                vac_map[vid] = {
                    "info": row,
                    "short_dm": None,
                    "cover_letter": None,
                    "tailored_cv": None
                }
            if row["pitch_type"] == "short_dm":
                vac_map[vid]["short_dm"] = row
            elif row["pitch_type"] == "cover_letter":
                vac_map[vid]["cover_letter"] = row
            elif row["pitch_type"] == "tailored_cv":
                vac_map[vid]["tailored_cv"] = row

        cards_html = []
        for vid, data in vac_map.items():
            info = data["info"]
            title = info["title"]
            company = info["company"]
            salary = info["salary"]
            location = info["location"]
            source = info["source"].upper()
            vac_url = info["url"]
            contact_handle = info["contact_handle"]
            contact_type = info["contact_type"]

            short_dm = data["short_dm"]["content"] if data["short_dm"] else ""
            short_dm_id = data["short_dm"]["pitch_id"] if data["short_dm"] else ""
            cover_letter = data["cover_letter"]["content"] if data["cover_letter"] else ""
            cover_letter_id = data["cover_letter"]["pitch_id"] if data["cover_letter"] else ""
            tailored_cv = data["tailored_cv"]["content"] if data["tailored_cv"] else ""
            tailored_cv_id = data["tailored_cv"]["pitch_id"] if data["tailored_cv"] else ""

            # Extract ATS target keywords for this vacancy
            kws = extract_target_keywords(title, info.get("skills", "") or "", info.get("description", "") or "")
            kw_badge_str = ", ".join(kws[:7])

            # Direct contact badge
            if contact_type == "telegram" and contact_handle.startswith("@"):
                tg_clean = contact_handle.lstrip("@")
                contact_badge = f'<a class="btn-contact btn-tg" href="https://t.me/{tg_clean}" target="_blank">✈️ Написать в Telegram: {contact_handle}</a>'
            elif contact_type == "email":
                contact_badge = f'<a class="btn-contact btn-email" href="mailto:{contact_handle}">✉️ Отправить Email: {contact_handle}</a>'
            else:
                contact_badge = f'<a class="btn-contact btn-portal" href="{vac_url}" target="_blank">🔗 Отклик на портале ({source})</a>'

            card = f"""
            <div class="vac-card" id="card-{vid}">
                <div class="card-header">
                    <div class="card-badges">
                        <span class="badge badge-source">{source}</span>
                        <span class="badge badge-salary">{salary}</span>
                        <span class="badge badge-loc">{location}</span>
                        <span class="badge badge-ats">🎯 ATS Ключи: {kw_badge_str}</span>
                    </div>
                    <h2 class="vac-title"><a href="{vac_url}" target="_blank">{title}</a></h2>
                    <div class="vac-company">🏢 {company}</div>
                </div>

                <div class="contact-section">
                    <strong>Прямой контакт:</strong> {contact_badge}
                </div>

                <div class="tabs">
                    <button class="tab-btn active" onclick="switchTab(this, 'dm-{vid}')">💬 Питч в ЛС (Telegram / LinkedIn)</button>
                    <button class="tab-btn" onclick="switchTab(this, 'cl-{vid}')">✉️ Сопроводительное письмо</button>
                    <button class="tab-btn" onclick="switchTab(this, 'cv-{vid}')">🎯 ATS-резюме под вакансию</button>
                </div>

                <div id="dm-{vid}" class="tab-pane active">
                    <textarea class="pitch-box" id="text-dm-{vid}">{short_dm}</textarea>
                    <div class="action-bar">
                        <button class="action-btn copy-btn" onclick="copyText('text-dm-{vid}')">📋 Скопировать питч</button>
                        <button class="action-btn approve-btn" onclick="markPitch({short_dm_id}, 'APPROVED')">✅ Одобрено</button>
                        <button class="action-btn sent-btn" onclick="markPitch({short_dm_id}, 'SENT')">🚀 Отправлено</button>
                    </div>
                </div>

                <div id="cl-{vid}" class="tab-pane">
                    <textarea class="pitch-box cl-box" id="text-cl-{vid}">{cover_letter}</textarea>
                    <div class="action-bar">
                        <button class="action-btn copy-btn" onclick="copyText('text-cl-{vid}')">📋 Скопировать письмо</button>
                        <button class="action-btn approve-btn" onclick="markPitch({cover_letter_id}, 'APPROVED')">✅ Одобрено</button>
                        <button class="action-btn sent-btn" onclick="markPitch({cover_letter_id}, 'SENT')">🚀 Отправлено</button>
                    </div>
                </div>

                <div id="cv-{vid}" class="tab-pane">
                    <textarea class="pitch-box cv-box" id="text-cv-{vid}">{tailored_cv}</textarea>
                    <div class="action-bar">
                        <button class="action-btn copy-btn" onclick="copyText('text-cv-{vid}')">📋 Скопировать ATS-резюме</button>
                        <button class="action-btn approve-btn" onclick="markPitch({tailored_cv_id}, 'APPROVED')">✅ Одобрено</button>
                        <button class="action-btn sent-btn" onclick="markPitch({tailored_cv_id}, 'SENT')">🚀 Отправлено</button>
                    </div>
                </div>
            </div>
            """
            cards_html.append(card)

        html_doc = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Очередь откликов и вакансий — Job Hunter</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
        .container {{ max-width: 1060px; margin: 0 auto; }}
        
        header {{ margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #334155; }}
        h1 {{ font-size: 24px; font-weight: 700; color: #38bdf8; margin-bottom: 6px; }}
        .stats-bar {{ display: flex; gap: 16px; font-size: 13px; color: #94a3b8; }}
        .stat-item strong {{ color: #f8fafc; }}

        .vac-card {{ background: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.2); }}
        .card-header {{ margin-bottom: 12px; }}
        .card-badges {{ display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; align-items: center; }}
        .badge {{ font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }}
        .badge-source {{ background: #3b82f6; color: #fff; }}
        .badge-salary {{ background: #10b981; color: #fff; }}
        .badge-loc {{ background: #475569; color: #cbd5e1; }}
        .badge-ats {{ background: #7c3aed; color: #fff; font-weight: 700; }}
        
        .vac-title {{ font-size: 18px; font-weight: 600; margin-bottom: 4px; }}
        .vac-title a {{ color: #f8fafc; text-decoration: none; }}
        .vac-title a:hover {{ color: #38bdf8; }}
        .vac-company {{ font-size: 13px; color: #94a3b8; }}

        .contact-section {{ background: #0f172a; padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; display: flex; align-items: center; gap: 12px; font-size: 13px; }}
        .btn-contact {{ display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; }}
        .btn-tg {{ background: #0284c7; color: white; }}
        .btn-tg:hover {{ background: #0369a1; }}
        .btn-email {{ background: #e11d48; color: white; }}
        .btn-portal {{ background: #475569; color: white; }}

        .tabs {{ display: flex; gap: 8px; border-bottom: 1px solid #334155; margin-bottom: 12px; }}
        .tab-btn {{ background: none; border: none; color: #94a3b8; font-size: 13px; font-weight: 500; padding: 8px 12px; cursor: pointer; border-bottom: 2px solid transparent; transition: 0.15s; }}
        .tab-btn:hover {{ color: #e2e8f0; }}
        .tab-btn.active {{ color: #38bdf8; border-bottom: 2px solid #38bdf8; font-weight: 600; }}
        
        .tab-pane {{ display: none; }}
        .tab-pane.active {{ display: block; }}

        .pitch-box {{ width: 100%; height: 110px; background: #090d16; border: 1px solid #334155; border-radius: 8px; padding: 12px; color: #e2e8f0; font-family: inherit; font-size: 13px; line-height: 1.5; resize: vertical; }}
        .cl-box {{ height: 180px; }}
        .cv-box {{ height: 260px; font-family: monospace; font-size: 12px; }}

        .action-bar {{ display: flex; gap: 10px; margin-top: 10px; }}
        .action-btn {{ padding: 7px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: 0.15s; }}
        .copy-btn {{ background: #334155; color: white; }}
        .copy-btn:hover {{ background: #475569; }}
        .approve-btn {{ background: #059669; color: white; }}
        .approve-btn:hover {{ background: #047857; }}
        .sent-btn {{ background: #2563eb; color: white; }}
        .sent-btn:hover {{ background: #1d4ed8; }}

        .toast {{ position: fixed; bottom: 20px; right: 20px; background: #10b981; color: white; padding: 10px 18px; border-radius: 8px; font-weight: 600; font-size: 13px; display: none; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Очередь поиска вакансий и ATS-аутрича</h1>
            <div class="stats-bar">
                <span class="stat-item">Всего в базе: <strong>{stats['total_vacancies']}</strong></span>
                <span class="stat-item">Ожидают проверки: <strong>{len(vac_map)}</strong> вакансий</span>
                <span class="stat-item">Отправлено: <strong>{stats['sent_pitches']}</strong></span>
            </div>
        </header>

        <main>
            {''.join(cards_html) if cards_html else '<p style="color:#94a3b8;text-align:center;padding:40px;">Нет новых вакансий в очереди. Запустите сканирование!</p>'}
        </main>
    </div>

    <div class="toast" id="toast">Скопировано в буфер обмена!</div>

    <script>
        function switchTab(btn, paneId) {{
            const card = btn.closest('.vac-card');
            card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            card.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            card.querySelector('#' + paneId).classList.add('active');
        }}

        function copyText(elemId) {{
            const el = document.getElementById(elemId);
            el.select();
            navigator.clipboard.writeText(el.value);
            const toast = document.getElementById('toast');
            toast.style.display = 'block';
            setTimeout(() => {{ toast.style.display = 'none'; }}, 2000);
        }}

        function markPitch(pitchId, status) {{
            if (!pitchId) return;
            fetch('/api/pitch/' + pitchId + '/status', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ status: status }})
            }}).catch(() => {{}});
            alert('Статус обновлен на: ' + status);
        }}
    </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)

        return output_path

if __name__ == "__main__":
    print("🚀 Запуск пайплайна генерации...")
    pipeline = JobHunterPipeline()
    
    # We load vacancies from DB that need pitches
    # Wait, the pipeline process_vacancies expects a list of dicts.
    # In reality, harvest_all puts them in DB. So we can just fetch from DB.
    import sqlite3
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "jobs.db"))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM vacancies")
    vacs = [dict(r) for r in cur.fetchall()]
    
    print(f"Обработка {len(vacs)} вакансий...")
    stats = pipeline.process_vacancies(vacs)
    print("Готово!", stats)
    
    # generate HTML
    pipeline.generate_review_html()
