import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vacancies (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        url TEXT,
        salary TEXT,
        location TEXT,
        is_remote INTEGER DEFAULT 0,
        description TEXT,
        skills TEXT,
        contact_name TEXT,
        contact_handle TEXT,
        contact_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'new',
        score INTEGER DEFAULT 0,
        language TEXT DEFAULT 'ru'
    );
    """)

    # Migration for databases created before status/score/language were added
    cursor.execute("PRAGMA table_info(vacancies)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN status TEXT DEFAULT 'new'")
    if 'score' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN score INTEGER DEFAULT 0")
    if 'language' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN language TEXT DEFAULT 'ru'")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pitches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vacancy_id TEXT NOT NULL,
        pitch_type TEXT NOT NULL, -- 'short_dm' | 'cover_letter'
        language TEXT NOT NULL,   -- 'ru' | 'en'
        content TEXT NOT NULL,
        status TEXT DEFAULT 'DRAFT', -- 'DRAFT' | 'APPROVED' | 'SENT' | 'REJECTED'
        sent_at TIMESTAMP,
        notes TEXT,
        FOREIGN KEY(vacancy_id) REFERENCES vacancies(id)
    );
    """)
    conn.commit()
    conn.close()

def save_vacancy(vacancy: Dict[str, Any]) -> bool:
    """Saves a vacancy if it does not already exist. Returns True if inserted, False if existed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO vacancies 
        (id, source, title, company, url, salary, location, is_remote, description, skills, contact_name, contact_handle, contact_type, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy["id"],
            vacancy.get("source", "unknown"),
            vacancy["title"],
            vacancy.get("company", "Unknown"),
            vacancy.get("url", ""),
            vacancy.get("salary", "Не указана"),
            vacancy.get("location", ""),
            1 if vacancy.get("is_remote") else 0,
            vacancy.get("description", ""),
            vacancy.get("skills", ""),
            vacancy.get("contact_name", ""),
            vacancy.get("contact_handle", ""),
            vacancy.get("contact_type", ""),
            vacancy.get("language", "ru")
        ))
        inserted = cursor.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()

def save_pitch(vacancy_id: str, pitch_type: str, language: str, content: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO pitches (vacancy_id, pitch_type, language, content, status)
        VALUES (?, ?, ?, ?, 'DRAFT')
        """, (vacancy_id, pitch_type, language, content))
        pitch_id = cursor.lastrowid
        conn.commit()
        return pitch_id
    finally:
        conn.close()

def get_pending_pitches() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT p.id as pitch_id, p.pitch_type, p.language, p.content, p.status,
               v.id as vacancy_id, v.title, v.company, v.url, v.salary, v.location,
               v.skills, v.description,
               v.contact_name, v.contact_handle, v.contact_type, v.source
        FROM pitches p
        JOIN vacancies v ON p.vacancy_id = v.id
        WHERE p.status = 'DRAFT'
        ORDER BY p.id DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def update_pitch_status(pitch_id: int, status: str, notes: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if status == 'SENT':
            cursor.execute("""
            UPDATE pitches SET status = ?, sent_at = CURRENT_TIMESTAMP, notes = COALESCE(?, notes)
            WHERE id = ?
            """, (status, notes, pitch_id))
        else:
            cursor.execute("""
            UPDATE pitches SET status = ?, notes = COALESCE(?, notes)
            WHERE id = ?
            """, (status, notes, pitch_id))
        conn.commit()
    finally:
        conn.close()

def get_stats() -> Dict[str, int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM vacancies")
        total_vacancies = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pitches WHERE status = 'DRAFT'")
        draft_pitches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pitches WHERE status = 'APPROVED'")
        approved_pitches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pitches WHERE status = 'SENT'")
        sent_pitches = cursor.fetchone()[0]

        return {
            "total_vacancies": total_vacancies,
            "draft_pitches": draft_pitches,
            "approved_pitches": approved_pitches,
            "sent_pitches": sent_pitches
        }
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized at:", DB_PATH)
