"""
ADgents Plugin Database helper.
Manages SQLite storage for connected integration settings and tokens.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_DIR = Path(__file__).parent.parent / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
OS_DB = DB_DIR / "agent_os.db"

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(OS_DB))
    conn.row_factory = sqlite3.Row
    return conn

def init_plugin_db():
    """Create plugins table if not exists."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                plugin_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'disconnected', -- connected | disconnected
                config      TEXT,                                 -- JSON dictionary of parameters
                updated_at  TEXT NOT NULL
            )
        """)
        
        # Populate defaults if empty
        cursor = conn.execute("SELECT COUNT(*) FROM plugins")
        if cursor.fetchone()[0] == 0:
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO plugins (plugin_id, name, status, config, updated_at)
                VALUES ('github', 'GitHub Workspace', 'disconnected', '{}', ?)
            """, (now,))
            conn.execute("""
                INSERT INTO plugins (plugin_id, name, status, config, updated_at)
                VALUES ('slack', 'Slack Notifications', 'disconnected', '{}', ?)
            """, (now,))
            conn.execute("""
                INSERT INTO plugins (plugin_id, name, status, config, updated_at)
                VALUES ('email', 'Gmail / SMTP Alerting', 'disconnected', '{}', ?)
            """, (now,))
        conn.commit()

def get_plugin(plugin_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM plugins WHERE plugin_id = ?", (plugin_id,)).fetchone()
    if row:
        res = dict(row)
        try:
            res["config"] = json.loads(res["config"])
        except Exception:
            res["config"] = {}
        return res
    return None

def list_plugins() -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM plugins ORDER BY plugin_id ASC").fetchall()
    res_list = []
    for r in rows:
        d = dict(r)
        try:
            d["config"] = json.loads(d["config"])
        except Exception:
            d["config"] = {}
        res_list.append(d)
    return res_list

def connect_plugin(plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    config_str = json.dumps(config)
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO plugins (plugin_id, name, status, config, updated_at)
            VALUES (?, ?, 'connected', ?, ?)
            ON CONFLICT(plugin_id) DO UPDATE SET
                status = 'connected',
                config = excluded.config,
                updated_at = excluded.updated_at
        """, (plugin_id, plugin_id.capitalize(), config_str, now))
        conn.commit()
    return get_plugin(plugin_id)

def disconnect_plugin(plugin_id: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            UPDATE plugins
            SET status = 'disconnected', config = '{}', updated_at = ?
            WHERE plugin_id = ?
        """, (now, plugin_id))
        conn.commit()
    return get_plugin(plugin_id)

def get_plugin_context_string() -> str:
    """Compile description of connected integrations for the agent's context layer."""
    plugins = list_plugins()
    connected = [p for p in plugins if p["status"] == "connected"]
    if not connected:
        return ""
        
    lines = ["[Connected Integrations Context]"]
    for p in connected:
        cfg = p["config"]
        if p["plugin_id"] == "github":
            repo = cfg.get("repository", "Not Specified")
            lines.append(f"- GitHub workspace connected. Active Repo: '{repo}'. Available skills: github_search_repos, github_get_issue, github_create_pr, github_commit_changes.")
        elif p["plugin_id"] == "slack":
            channel = cfg.get("channel", "Not Specified")
            lines.append(f"- Slack alerts connected. Active Channel: '{channel}'. Available skills: slack_send_message, slack_read_channel.")
        elif p["plugin_id"] == "email":
            smtp = cfg.get("smtp_server", "smtp.gmail.com")
            email = cfg.get("sender_email", "agent@gmail.com")
            lines.append(f"- Email alerts connected. SMTP Client: '{smtp}' (Sender: '{email}'). Available skills: email_send, email_read_unread.")
    return "\n".join(lines)

# Auto init
init_plugin_db()
