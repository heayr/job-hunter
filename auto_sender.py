import sqlite3
import asyncio
import os
import sys

# We will use pyrogram or telethon. Let's use Telethon.
try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PeerFloodError
    from telethon.tl.types import InputPeerUser
except ImportError:
    os.system(f"{sys.executable} -m pip install telethon")
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PeerFloodError
    from telethon.tl.types import InputPeerUser

# Ask user to get these from my.telegram.org
API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

async def send_all():
    if not API_ID or not API_HASH:
        print("ОШИБКА: Не заданы TG_API_ID и TG_API_HASH.")
        print("Получи их на https://my.telegram.org/ и запусти:")
        print("export TG_API_ID='твой_id'")
        print("export TG_API_HASH='твой_hash'")
        print("python3 auto_sender.py")
        return

    client = TelegramClient('tg_session', API_ID, API_HASH)
    await client.start()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Get approved or pending pitches with telegram contacts
    cur.execute('''
        SELECT p.id, p.vacancy_id, v.title, v.company, v.contact_handle, p.content
        FROM pitches p
        JOIN vacancies v ON p.vacancy_id = v.id
        WHERE p.pitch_type = 'short_dm'
        AND v.contact_type = 'telegram' AND v.contact_handle IS NOT NULL
        AND (v.status IN ('approved', 'inbox', 'new') OR p.status IN ('APPROVED', 'DRAFT'))
    ''')
    targets = cur.fetchall()

    if not targets:
        print("Нет готовых сообщений для отправки в Telegram (или нет контактов).")
        return

    print(f"Найдено {len(targets)} контактов для рассылки в Telegram.")
    
    for pitch_id, vac_id, title, company, handle, text in targets:
        handle = handle.replace('@', '').strip()
        print(f"Отправляем {handle} (Вакансия: {title} в {company})...")
        try:
            # send message
            await client.send_message(handle, text)
            print(" ✅ Успешно отправлено!")
            # mark as sent in DB
            cur.execute("UPDATE pitches SET status = 'SENT' WHERE id = ?", (pitch_id,))
            conn.commit()
            
            # Anti-spam delay
            await asyncio.sleep(5)
            
        except PeerFloodError:
            print(" ❌ Ошибка: Сработал спам-фильтр Telegram (PeerFloodError). Ждем 1 час.")
            break
        except Exception as e:
            print(f" ❌ Ошибка отправки: {e}")

    print("Рассылка завершена!")

if __name__ == '__main__':
    asyncio.run(send_all())
