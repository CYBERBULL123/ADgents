"""
ADgents Task Database
Persists all autonomous task runs so they can be reviewed later.
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_DIR = Path(__file__).parent.parent / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DB = DB_DIR / "tasks.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(TASKS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table if it does not exist yet."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                agent_id    TEXT NOT NULL,
                agent_name  TEXT NOT NULL,
                agent_avatar TEXT NOT NULL DEFAULT '🤖',
                task_text   TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'running',
                result      TEXT,
                error       TEXT,
                steps       TEXT,       -- JSON array
                started_at  TEXT NOT NULL,
                completed_at TEXT,
                duration_s  REAL,
                max_iterations INTEGER DEFAULT 10
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_started ON tasks(started_at DESC)")
        conn.commit()


def save_task(
    task_id: str,
    agent_id: str,
    agent_name: str,
    agent_avatar: str,
    task_text: str,
    status: str,
    result: Optional[str],
    error: Optional[str],
    steps: List[Dict],
    started_at: str,
    completed_at: Optional[str],
    max_iterations: int = 10,
):
    """Insert or replace a completed task record."""
    duration = None
    if started_at and completed_at:
        try:
            fmt = "%Y-%m-%dT%H:%M:%S.%f"
            s = datetime.strptime(started_at[:26], fmt)
            e = datetime.strptime(completed_at[:26], fmt)
            duration = (e - s).total_seconds()
        except Exception:
            pass

    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO tasks
              (id, agent_id, agent_name, agent_avatar, task_text, status,
               result, error, steps, started_at, completed_at, duration_s, max_iterations)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            task_id, agent_id, agent_name, agent_avatar, task_text, status,
            result, error,
            json.dumps(steps or []),
            started_at, completed_at, duration,
            max_iterations,
        ))
        conn.commit()


def list_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
) -> List[Dict]:
    """Return a list of task records, newest first."""
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if agent_id:
        query += " AND agent_id = ?"
        params.append(agent_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (task_text LIKE ? OR result LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    with _get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d["steps"] = json.loads(d.get("steps") or "[]")
        result.append(d)
    return result


def get_task(task_id: str) -> Optional[Dict]:
    """Fetch a single task by ID."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["steps"] = json.loads(d.get("steps") or "[]")
    return d


def delete_task(task_id: str) -> bool:
    """Delete a task. Returns True if a row was removed."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    return cur.rowcount > 0


def task_stats() -> Dict[str, Any]:
    """Return aggregate statistics."""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='failed'").fetchone()[0]
        avg_dur = conn.execute(
            "SELECT AVG(duration_s) FROM tasks WHERE duration_s IS NOT NULL"
        ).fetchone()[0]
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "avg_duration_s": round(avg_dur or 0, 1),
    }


# Initialise on import
init_db()
