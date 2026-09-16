import sys
import os
import sqlite3
import hashlib
import json

sys.path.insert(0, os.path.dirname(__file__))

from scrapers.telegram_scraper import TelegramScraper
from scrapers.habr_scraper import HabrScraper
from scrapers.wwr_scraper import WWRScraper
from scrapers.hh_scraper import HHScraper
from scrapers.crypto_scraper import CryptoScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.superjob_scraper import SuperJobScraper
from scrapers.rabotaru_scraper import RabotaRuScraper
from scrapers.ats_scraper import ATSScraper
from scrapers.hackernews_scraper import HackerNewsScraper
from scrapers.jobicy_scraper import JobicyScraper
from tracker.db import init_db, save_vacancy
from generator.pitch_builder import generate_pitch
from filter.profile_filter import is_qualified_vacancy, detect_vacancy_grade


def run():
    print("🚀 Initializing database and job scrapers...")
    init_db()

    scrapers = [
        TelegramScraper(),
        ATSScraper(),
        HackerNewsScraper(),
        JobicyScraper(),
        HabrScraper(),
        WWRScraper(),
        CryptoScraper(),
        RemotiveScraper(),
        HHScraper(),
        SuperJobScraper(),
        RabotaRuScraper()
    ]

    all_vacs = []
    for s in scrapers:
        print(f"\n▶ Running scraper: {s.name}")
        try:
            vacs = s.scrape()
            print(f"  ✓ [{s.name}] Got {len(vacs)} raw vacancies")
            all_vacs.extend(vacs)
        except Exception as e:
            print(f"  ✗ Scraper {s.name} failed: {e}")

    print(f"\n📊 Total raw vacancies collected: {len(all_vacs)}")

    db_path = os.path.join(os.path.dirname(__file__), "jobs.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load active profile from config if set
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    active_profile_id = None
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                active_profile_id = json.load(cf).get("active_profile_id")
        except Exception:
            pass

    saved = 0
    skipped_filter = 0
    skipped_duplicate = 0

    try:
        for v in all_vacs:
            # ── Ensure required fields exist ──
            if not v.get('id'):
                src = v.get('source', 'job')
                key = v.get('url') or v.get('title') or 'unknown'
                v['id'] = f"{src}:{hashlib.md5(key.encode('utf-8')).hexdigest()[:10]}"

            # ── 1. Filter out candidate resumes, ads, and irrelevant roles ──
            qualified, reason = is_qualified_vacancy(
                title=v.get('title', ''),
                skills=v.get('skills', ''),
                description=v.get('description', ''),
                company=v.get('company', ''),
            )
            if not qualified:
                print(f"  SKIP (filter: {reason}): {v.get('title')}")
                skipped_filter += 1
                continue

            grade = detect_vacancy_grade(v.get('title', ''), v.get('description', ''))
            v['grade'] = grade

            vac_id = v['id']
            vac_url = v.get('url', '')

            # ── 2. Deduplication by ID or URL ──
            cur.execute("SELECT id FROM vacancies WHERE id = ? OR (url = ? AND url != '')", (vac_id, vac_url))
            if cur.fetchone():
                skipped_duplicate += 1
                continue

            # ── 3. Save vacancy to DB ──
            try:
                save_vacancy(v)
                pitch_data = generate_pitch(v, use_ai=False, profile_id=active_profile_id)
                lang = pitch_data.get('language', 'ru')
                score = pitch_data.get('score', 0)

                # Save generated pitches with correct vacancy_id string
                for p_type in ['short_dm', 'cover_letter', 'tailored_cv']:
                    cur.execute(
                        "INSERT INTO pitches (vacancy_id, pitch_type, language, content, status) VALUES (?, ?, ?, ?, 'DRAFT')",
                        (vac_id, p_type, lang, pitch_data.get(p_type, ''))
                    )

                # Update score, language, grade and ensure status is 'new'
                cur.execute("UPDATE vacancies SET score = ?, status = 'new', language = ?, grade = ? WHERE id = ?", (score, lang, grade, vac_id))
                conn.commit()

                saved += 1
                print(f"  ✓ Saved: [{v.get('source')}] [{grade}] {v.get('title')} @ {v.get('company')} (Score: {score})")
            except Exception as e:
                conn.rollback()
                print(f"  ✗ Error saving {v.get('title')}: {e}")

    finally:
        conn.close()

    print(f"\n✅ Sourcing Finished: Saved: {saved} | Filtered: {skipped_filter} | Duplicates: {skipped_duplicate}")

    # Automatically purge any closed vacancies from the feed
    try:
        from tracker.cleanup_closed import archive_closed_vacancies
        archive_closed_vacancies()
    except Exception as e:
        print(f"Warning: Closed vacancies cleanup error: {e}")


if __name__ == "__main__":
    run()
