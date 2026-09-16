import sqlite3
import asyncio
import os
import sys
import argparse

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PeerFloodError
except ImportError:
    os.system(f"{sys.executable} -m pip install telethon")
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PeerFloodError

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

async def send_single(vacancy_id: str):
    if not API_ID or not API_HASH:
        print("ОШИБКА: Не заданы TG_API_ID и TG_API_HASH.")
        sys.exit(1)

    # telethon session file will be created in the current dir
    client = TelegramClient('tg_session', API_ID, API_HASH)
    await client.start()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get the pitch and contact
    cur.execute('''
        SELECT p.id, v.title, v.company, v.contact_handle, p.content
        FROM pitches p
        JOIN vacancies v ON p.vacancy_id = v.id
        WHERE p.vacancy_id = ? AND p.pitch_type = 'short_dm'
    ''', (vacancy_id,))
    target = cur.fetchone()

    if not target:
        print(f"ОШИБКА: Не найден short_dm pitch для вакансии {vacancy_id}")
        await client.disconnect()
        sys.exit(1)

    pitch_id, title, company, handle, text = target
    
    if not handle:
        print(f"ОШИБКА: Нет contact_handle для вакансии {vacancy_id}")
        await client.disconnect()
        sys.exit(1)

    handle = handle.replace('@', '').strip()
    
    # Check if a PDF resume exists in a configured location (Optional, could just send text for now)
    # pdf_path = os.getenv("RESUME_PDF_PATH")
    
    print(f"Отправляем {handle} (Вакансия: {title} в {company})...")
    try:
        await client.send_message(handle, text)
        print(" ✅ Успешно отправлено!")
        
        # Mark as sent in DB
        cur.execute("UPDATE vacancies SET status = 'sent' WHERE id = ?", (vacancy_id,))
        cur.execute("UPDATE pitches SET status = 'SENT' WHERE id = ?", (pitch_id,))
        conn.commit()
    except Exception as e:
        print(f" ❌ Ошибка отправки: {e}")
        sys.exit(1)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True, help="Vacancy ID to send DM for")
    args = parser.parse_args()
    
    asyncio.run(send_single(args.id))
