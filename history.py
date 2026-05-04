import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent / "data" / "history.db"
_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
                _conn.row_factory = sqlite3.Row
                _conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id          TEXT PRIMARY KEY,
                        memory_id   TEXT NOT NULL,
                        user_id     TEXT NOT NULL,
                        old_memory  TEXT,
                        new_memory  TEXT,
                        event       TEXT NOT NULL,
                        created_at  TEXT NOT NULL
                    )
                """)
                _conn.commit()
    return _conn


def add_history(memory_id: str, user_id: str, old_memory: str | None, new_memory: str | None, event: str) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO history (id, memory_id, user_id, old_memory, new_memory, event, created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), memory_id, user_id, old_memory, new_memory, event,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_history(memory_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, memory_id, user_id, old_memory, new_memory, event, created_at FROM history WHERE memory_id=? ORDER BY created_at",
        (memory_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_history_by_user(user_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, memory_id, user_id, old_memory, new_memory, event, created_at FROM history WHERE user_id=? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]
