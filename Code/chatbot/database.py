"""
database.py
SQLite storage for leads and chat logs.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "chatbot.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            intent TEXT DEFAULT '',
            operation TEXT DEFAULT '',
            property_type TEXT DEFAULT '',
            location TEXT DEFAULT '',
            bedrooms INTEGER DEFAULT 0,
            budget REAL DEFAULT 0,
            matched_refs TEXT DEFAULT '',
            summary TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chat_logs_chat_id ON chat_logs(chat_id);
        CREATE INDEX IF NOT EXISTS idx_leads_chat_id ON leads(chat_id);
    """)
    conn.close()


def save_lead(
    chat_id: str,
    name: str = "",
    email: str = "",
    phone: str = "",
    intent: str = "",
    operation: str = "",
    property_type: str = "",
    location: str = "",
    bedrooms: int = 0,
    budget: float = 0,
    matched_refs: str = "",
    summary: str = "",
) -> str:
    """Save a lead and return its ID."""
    lead_id = str(uuid.uuid4())
    conn = _get_conn()
    conn.execute(
        """INSERT INTO leads
           (id, chat_id, created_at, name, email, phone, intent, operation,
            property_type, location, bedrooms, budget, matched_refs, summary)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lead_id, chat_id, datetime.now().isoformat(), name, email, phone,
         intent, operation, property_type, location, bedrooms, budget,
         matched_refs, summary),
    )
    conn.commit()
    conn.close()
    return lead_id


def log_message(chat_id: str, role: str, content: str):
    """Append a message to the chat log."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO chat_logs (chat_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
        (chat_id, datetime.now().isoformat(), role, content),
    )
    conn.commit()
    conn.close()


def get_chat_history(chat_id: str) -> list[dict]:
    """Get all messages for a chat session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content FROM chat_logs WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_all_leads() -> list[dict]:
    """Get all leads, most recent first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM leads ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
