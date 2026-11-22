"""Persistent registry for remote A2A Agent Cards."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path(__file__).parent.parent / "data" / "db" / "agent_network.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _decode(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    result = dict(row)
    result["card"] = json.loads(result.pop("card_json"))
    return result


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS remote_agents (
                id TEXT PRIMARY KEY,
                card_url TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                card_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_remote_agent(card_url: str, card: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id, created_at FROM remote_agents WHERE card_url = ?", (card_url,)
        ).fetchone()
        agent_id = existing["id"] if existing else str(uuid.uuid4())
        created_at = existing["created_at"] if existing else now
        conn.execute("""
            INSERT INTO remote_agents (id, card_url, name, description, card_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(card_url) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                card_json = excluded.card_json,
                updated_at = excluded.updated_at
        """, (
            agent_id,
            card_url,
            card["name"],
            card["description"],
            json.dumps(card),
            created_at,
            now,
        ))
        conn.commit()
    return get_remote_agent(agent_id)


def get_remote_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM remote_agents WHERE id = ?", (agent_id,)).fetchone()
    return _decode(row)


def list_remote_agents() -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM remote_agents ORDER BY name COLLATE NOCASE").fetchall()
    return [_decode(row) for row in rows]


def delete_remote_agent(agent_id: str) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM remote_agents WHERE id = ?", (agent_id,))
        conn.commit()
    return cursor.rowcount > 0


init_db()