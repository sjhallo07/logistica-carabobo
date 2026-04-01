import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_PATH = "./data/events.db"

def _get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = _get_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        event_type TEXT,
        payload TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_event(user_id: Optional[str], event_type: str, payload: Dict[str, Any]):
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO events (user_id, event_type, payload, created_at) VALUES (?,?,?,?)",
                 (user_id, event_type, json.dumps(payload), now))
    conn.commit()
    conn.close()

def get_events(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_conn()
    cur = conn.execute("SELECT id, user_id, event_type, payload, created_at FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({"id": r[0], "user_id": r[1], "event_type": r[2], "payload": json.loads(r[3]), "created_at": r[4]})
    return out

# initialize on import
init_db()
