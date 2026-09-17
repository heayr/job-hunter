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
    if 'grade' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN grade TEXT DEFAULT 'Middle'")
    if 'published_at' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN published_at TEXT")
        cursor.execute("UPDATE vacancies SET published_at = created_at WHERE published_at IS NULL")
    if 'blacklist_reason' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN blacklist_reason TEXT")
    if 'blacklisted_at' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN blacklisted_at TIMESTAMP")
    if 'understanding_json' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN understanding_json TEXT")
    if 'application_thesis_json' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN application_thesis_json TEXT")
    if 'application_strategy_json' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN application_strategy_json TEXT")
    if 'ats_report_json' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN ats_report_json TEXT")
    if 'fsm_state' not in columns:
        cursor.execute("ALTER TABLE vacancies ADD COLUMN fsm_state TEXT DEFAULT 'DISCOVERED'")

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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        id TEXT PRIMARY KEY,
        lang TEXT NOT NULL DEFAULT 'ru',
        target_role TEXT NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_dossiers (
        domain_key TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vacancy_id TEXT NOT NULL,
        company TEXT NOT NULL,
        role_title TEXT NOT NULL,
        portal TEXT NOT NULL,
        mode TEXT NOT NULL, -- 'ASSIST' | 'SEMI_AUTO' | 'AUTO'
        fsm_state TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        response_status TEXT DEFAULT 'PENDING', -- 'PENDING' | 'INTERVIEW' | 'REJECTED' | 'OFFER'
        metadata_json TEXT,
        FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_run_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vacancy_id TEXT NOT NULL,
        step_name TEXT NOT NULL,
        status TEXT NOT NULL, -- 'SUCCESS' | 'WARNING' | 'FAILED'
        duration_ms INTEGER DEFAULT 0,
        details_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vacancy_id TEXT NOT NULL,
        url TEXT NOT NULL,
        company TEXT NOT NULL,
        role_title TEXT NOT NULL,
        portal TEXT NOT NULL,
        cover_letter TEXT,
        status TEXT DEFAULT 'PENDING', -- 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
        result_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def save_vacancy(vacancy: Dict[str, Any]) -> bool:
    """Saves a vacancy if it does not already exist. Returns True if inserted, False if existed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pub_at = vacancy.get("published_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR IGNORE INTO vacancies (
            id, source, title, company, url, salary, location,
            is_remote, description, skills, contact_name, contact_handle, contact_type, language, grade, published_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            vacancy.get("language", "ru"),
            vacancy.get("grade", "Middle"),
            pub_at
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

def sync_canonical_profiles_to_db(profiles: List[Dict[str, Any]]) -> None:
    """Syncs canonical candidate profiles into candidate_profiles SQLite table."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for p in profiles:
            p_id = p.get("id")
            if not p_id:
                continue
            lang = p.get("lang", "ru")
            identity = p.get("identity", {})
            name = identity.get("name") or p.get("name", "Candidate")
            target_role = identity.get("target_role") or p.get("role", "Engineer")
            is_active = 1 if p.get("is_active", True) else 0
            data_json = json.dumps(p, ensure_ascii=False)

            cursor.execute("""
            INSERT INTO candidate_profiles (id, lang, target_role, name, is_active, data_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                lang = excluded.lang,
                target_role = excluded.target_role,
                name = excluded.name,
                is_active = excluded.is_active,
                data_json = excluded.data_json,
                updated_at = CURRENT_TIMESTAMP
            """, (p_id, lang, target_role, name, is_active, data_json))
        conn.commit()
    finally:
        conn.close()

def get_candidate_profile_from_db(profile_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single canonical profile from SQLite by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT data_json FROM candidate_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if row and row["data_json"]:
            return json.loads(row["data_json"])
        return None
    finally:
        conn.close()

def save_job_understanding(vacancy_id: str, understanding: Dict[str, Any]) -> None:
    """Saves structured job understanding JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE vacancies SET understanding_json = ? WHERE id = ?
        """, (json.dumps(understanding, ensure_ascii=False), vacancy_id))
        conn.commit()
    finally:
        conn.close()

def get_job_understanding(vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves structured job understanding JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT understanding_json FROM vacancies WHERE id = ?", (vacancy_id,))
        row = cursor.fetchone()
        if row and row["understanding_json"]:
            return json.loads(row["understanding_json"])
        return None
    finally:
        conn.close()

def save_application_thesis(vacancy_id: str, thesis_data: Dict[str, Any]) -> None:
    """Saves structured application thesis JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE vacancies SET application_thesis_json = ? WHERE id = ?
        """, (json.dumps(thesis_data, ensure_ascii=False), vacancy_id))
        conn.commit()
    finally:
        conn.close()

def get_application_thesis(vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves structured application thesis JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT application_thesis_json FROM vacancies WHERE id = ?", (vacancy_id,))
        row = cursor.fetchone()
        if row and row["application_thesis_json"]:
            return json.loads(row["application_thesis_json"])
        return None
    finally:
        conn.close()

def save_company_dossier(domain_key: str, company_name: str, dossier: Dict[str, Any]) -> None:
    """Saves or updates a company dossier in SQLite with timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO company_dossiers (domain_key, company_name, data_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(domain_key) DO UPDATE SET
            company_name = excluded.company_name,
            data_json = excluded.data_json,
            updated_at = CURRENT_TIMESTAMP
        """, (domain_key.lower().strip(), company_name, json.dumps(dossier, ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()

def get_cached_company_dossier(domain_key: str, ttl_days: int = 7) -> Optional[Dict[str, Any]]:
    """Retrieves a cached company dossier from SQLite if within TTL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT data_json, updated_at FROM company_dossiers
        WHERE domain_key = ? AND (julianday('now') - julianday(updated_at)) <= ?
        """, (domain_key.lower().strip(), ttl_days))
        row = cursor.fetchone()
        if row and row["data_json"]:
            return json.loads(row["data_json"])
        return None
    finally:
        conn.close()

def save_application_strategy(vacancy_id: str, strategy_data: Dict[str, Any]) -> None:
    """Saves structured application strategy plan JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE vacancies SET application_strategy_json = ? WHERE id = ?
        """, (json.dumps(strategy_data, ensure_ascii=False), vacancy_id))
        conn.commit()
    finally:
        conn.close()

def get_application_strategy(vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves structured application strategy plan JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT application_strategy_json FROM vacancies WHERE id = ?", (vacancy_id,))
        row = cursor.fetchone()
        if row and row["application_strategy_json"]:
            return json.loads(row["application_strategy_json"])
        return None
    finally:
        conn.close()

def save_ats_report(vacancy_id: str, report_data: Dict[str, Any]) -> None:
    """Saves ATS report JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE vacancies SET ats_report_json = ? WHERE id = ?
        """, (json.dumps(report_data, ensure_ascii=False), vacancy_id))
        conn.commit()
    finally:
        conn.close()

def get_ats_report(vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves ATS report JSON for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ats_report_json FROM vacancies WHERE id = ?", (vacancy_id,))
        row = cursor.fetchone()
        if row and row["ats_report_json"]:
            return json.loads(row["ats_report_json"])
        return None
    finally:
        conn.close()

def update_vacancy_fsm_state(vacancy_id: str, state: str) -> None:
    """Updates the FSM state for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE vacancies SET fsm_state = ? WHERE id = ?", (state, vacancy_id))
        conn.commit()
    finally:
        conn.close()

def get_vacancy_fsm_state(vacancy_id: str) -> str:
    """Gets the current FSM state for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fsm_state FROM vacancies WHERE id = ?", (vacancy_id,))
        row = cursor.fetchone()
        if row and row["fsm_state"]:
            return row["fsm_state"]
        return "DISCOVERED"
    finally:
        conn.close()

def record_application_event(vacancy_id: str, company: str, role_title: str, portal: str, mode: str, fsm_state: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    """Records an application event into application_history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO application_history (vacancy_id, company, role_title, portal, mode, fsm_state, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy_id,
            company,
            role_title,
            portal,
            mode,
            fsm_state,
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        record_id = cursor.lastrowid
        conn.commit()
        return record_id
    finally:
        conn.close()

def get_application_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves list of recent application events."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT * FROM application_history ORDER BY applied_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def log_agent_run_step(vacancy_id: str, step_name: str, status: str, duration_ms: int = 0, details: Optional[Dict[str, Any]] = None) -> int:
    """Logs an agent execution step for observability timeline."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO agent_run_logs (vacancy_id, step_name, status, duration_ms, details_json)
        VALUES (?, ?, ?, ?, ?)
        """, (
            vacancy_id,
            step_name,
            status,
            duration_ms,
            json.dumps(details or {}, ensure_ascii=False)
        ))
        log_id = cursor.lastrowid
        conn.commit()
        return log_id
    finally:
        conn.close()

def get_agent_run_timeline(vacancy_id: str) -> List[Dict[str, Any]]:
    """Retrieves timeline of agent steps for a vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT * FROM agent_run_logs WHERE vacancy_id = ? ORDER BY created_at ASC
        """, (vacancy_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def create_agent_task(vacancy_id: str, url: str, company: str, role_title: str, portal: str, cover_letter: str = "") -> int:
    """Creates a new task in the agent execution queue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO agent_tasks (vacancy_id, url, company, role_title, portal, cover_letter, status)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        """, (vacancy_id, url, company, role_title, portal, cover_letter))
        task_id = cursor.lastrowid
        conn.commit()
        return task_id
    finally:
        conn.close()

def get_pending_agent_tasks(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves pending tasks for the browser extension agent worker."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT * FROM agent_tasks WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def update_agent_task_status(task_id: int, status: str, result_message: str = "") -> None:
    """Updates status and result message for an agent task."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE agent_tasks
        SET status = ?, result_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, result_message, task_id))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized at:", DB_PATH)
