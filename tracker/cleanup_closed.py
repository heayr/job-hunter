import sqlite3
import urllib.request
import urllib.error
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.db")

CLOSED_PHRASES = [
    'вакансия закрыта',
    'вакансия в архиве',
    'архивная вакансия',
    'была перемещена в архив',
    'перемещена в архив',
    'снята с публикации',
    'вакансия снята',
    'больше не доступна',
    'position is closed',
    'this job has expired',
    'this job is no longer available',
    'job posting has expired',
    'job closed',
    'application closed'
]


def check_url_active(row: dict, timeout: int = 4) -> tuple[str, bool, str]:
    """
    Returns (vacancy_id, is_active, reason).
    """
    vac_id = row['id']
    url = row['url']
    source = row.get('source', '')

    if not url or not url.startswith('http'):
        return vac_id, True, "No HTTP URL"

    # Telegram links shouldn't be parsed with simple GET
    if 't.me/' in url:
        return vac_id, True, "Telegram post"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode('utf-8', errors='ignore').lower()

            # Geekjob closed badge
            if 'geekjob.ru' in url and ('вакансия закрыта' in content or 'закрыта</span>' in content):
                return vac_id, False, "GeekJob: Вакансия закрыта"

            # Habr closed badge
            if 'career.habr.com' in url and ('вакансия в архиве' in content or 'вакансия закрыта' in content):
                return vac_id, False, "Habr: Вакансия в архиве"

            # SuperJob archive badge
            if 'superjob.ru' in url and ('вакансия в архиве' in content or 'снята с публикации' in content):
                return vac_id, False, "SuperJob: Вакансия в архиве"

            for phrase in CLOSED_PHRASES:
                if phrase in content:
                    return vac_id, False, f"Matched closed phrase: '{phrase}'"

            return vac_id, True, "OK"
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return vac_id, False, f"HTTP {e.code}"
        return vac_id, True, f"HTTP {e.code}"
    except Exception as e:
        return vac_id, True, f"Error: {e}"


def archive_closed_vacancies(limit: int = 300) -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, source, title, url FROM vacancies
        WHERE status != 'archive'
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]

    print(f"🔍 Checking {len(rows)} vacancies in parallel...")
    to_archive = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(check_url_active, r): r for r in rows}
        for f in as_completed(futures):
            row = futures[f]
            try:
                vac_id, is_active, reason = f.result()
                if not is_active:
                    to_archive.append((vac_id, row['source'], row['title'], reason))
                    print(f"  ❌ [{row['source']}] {row['title']} -> {reason}")
            except Exception as e:
                pass

    for vac_id, source, title, reason in to_archive:
        cur.execute("UPDATE vacancies SET status = 'archive' WHERE id = ?", (vac_id,))

    conn.commit()
    conn.close()
    print(f"\n✨ Finished. Total closed vacancies archived: {len(to_archive)}")
    return len(to_archive)


if __name__ == '__main__':
    archive_closed_vacancies()
