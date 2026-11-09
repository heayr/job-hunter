import sqlite3
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jobs.db")


def init_db(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auto_applies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                vacancy_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                url TEXT,
                resume_id TEXT,
                status TEXT NOT NULL,  -- 'applied', 'already_applied', 'limit_exceeded', 'test_required', 'error', 'skipped'
                message TEXT,
                applied_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, vacancy_id)
            )
        """)
        conn.commit()


def is_already_processed(platform: str, vacancy_id: str, db_path: str = DB_PATH) -> bool:
    """Checks if we have already attempted or applied to this vacancy."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM auto_applies WHERE platform = ? AND vacancy_id = ? AND status IN ('applied', 'already_applied')",
            (platform, str(vacancy_id))
        )
        return cur.fetchone() is not None


def record_apply_attempt(
    platform: str,
    vacancy_id: str,
    status: str,
    title: str = "",
    company: str = "",
    url: str = "",
    resume_id: str = "",
    message: str = "",
    db_path: str = DB_PATH
) -> None:
    """Records the apply result into local history."""
    init_db(db_path)
    today_str = date.today().isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO auto_applies (platform, vacancy_id, title, company, url, resume_id, status, message, applied_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform, vacancy_id) DO UPDATE SET
                status = excluded.status,
                message = excluded.message,
                applied_date = excluded.applied_date,
                created_at = CURRENT_TIMESTAMP
        """, (platform, str(vacancy_id), title, company, url, resume_id, status, message, today_str))
        conn.commit()


def get_daily_applied_count(platform: str, db_path: str = DB_PATH) -> int:
    """Returns number of successful applies sent today."""
    init_db(db_path)
    today_str = date.today().isoformat()
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM auto_applies WHERE platform = ? AND applied_date = ? AND status = 'applied'",
            (platform, today_str)
        )
        row = cur.fetchone()
        return row[0] if row else 0


def get_recent_applies(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Returns recent application logs."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT platform, vacancy_id, title, company, url, status, applied_date, created_at FROM auto_applies ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]
