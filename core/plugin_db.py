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
    """Disable plugin DB initialization. Integrations removed in this deployment."""
    # Intentionally no-op to disable plugin DB and integrations.
    return None

def get_plugin(plugin_id: str) -> Optional[Dict[str, Any]]:
    # Integrations disabled — always return None
    return None

def list_plugins() -> List[Dict[str, Any]]:
    # No plugins available
    return []

def connect_plugin(plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    # Integrations disabled — return a disconnected stub
    return {"plugin_id": plugin_id, "status": "disconnected", "config": {}}

def disconnect_plugin(plugin_id: str) -> Dict[str, Any]:
    # Integrations disabled — return a disconnected stub
    return {"plugin_id": plugin_id, "status": "disconnected", "config": {}}

def get_plugin_context_string() -> str:
    # Integrations removed — return empty context
    return ""

# Auto init
init_plugin_db()
