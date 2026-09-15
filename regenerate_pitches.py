import sqlite3
import os
from generator.pitch_builder import generate_pitch
from tracker.db import save_pitch

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Clear existing pitches
cur.execute("DELETE FROM pitches")
conn.commit()

# Fetch all vacancies
cur.execute("SELECT * FROM vacancies")
vacs = [dict(r) for r in cur.fetchall()]

for vac in vacs:
    pitches = generate_pitch(vac, use_ai=False)
    lang = pitches["language"]
    save_pitch(vac["id"], "short_dm", lang, pitches["short_dm"])
    save_pitch(vac["id"], "cover_letter", lang, pitches["cover_letter"])
    save_pitch(vac["id"], "tailored_cv", lang, pitches["tailored_cv"])
    print(f"✅ Успешно сгенерировано для {vac['company']}")

conn.close()
print("Все питчи успешно пересобраны!")
