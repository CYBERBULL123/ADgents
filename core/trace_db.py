"""
ADgents Agent OS Database (Kernel DB)
Manages the state of Agent Pods, Hierarchical Traces & Spans, and SRE Healing logs.
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


def init_db():
    """Initialize Agent OS databases."""
    with _get_conn() as conn:
        # 1. Agent Pods Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pods (
                id           TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'running', -- running | healing | suspended | completed | failed
                agent_id     TEXT NOT NULL,
                task_text    TEXT NOT NULL,
                tokens_used  INTEGER DEFAULT 0,
                cost         REAL DEFAULT 0.0,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
        """)
        
        # 2. Traces Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id           TEXT PRIMARY KEY,
                pod_id       TEXT,
                name         TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'running', -- running | completed | failed
                started_at   TEXT NOT NULL,
                completed_at TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_cost   REAL DEFAULT 0.0,
                FOREIGN KEY(pod_id) REFERENCES pods(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Spans Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                id             TEXT PRIMARY KEY,
                trace_id       TEXT NOT NULL,
                parent_span_id TEXT,
                name           TEXT NOT NULL,
                span_type      TEXT NOT NULL, -- thought | action | observation | reflection | llm | SRE_diagnosis | SRE_patch
                input          TEXT,          -- JSON or string
                output         TEXT,          -- JSON or string
                status         TEXT NOT NULL DEFAULT 'pending', -- pending | success | error
                started_at     TEXT NOT NULL,
                completed_at   TEXT,
                tokens_input   INTEGER DEFAULT 0,
                tokens_output  INTEGER DEFAULT 0,
                cost           REAL DEFAULT 0.0,
                error          TEXT,
                FOREIGN KEY(trace_id) REFERENCES traces(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_span_id) REFERENCES spans(id) ON DELETE SET NULL
            )
        """)
        
        # 4. Healing Interventions Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS healing_interventions (
                id             TEXT PRIMARY KEY,
                pod_id         TEXT NOT NULL,
                span_id        TEXT NOT NULL,
                error_message  TEXT NOT NULL,
                diagnosis      TEXT,
                patch_type     TEXT, -- memory_append | param_override | state_reset
                patch_content  TEXT,
                created_at     TEXT NOT NULL,
                FOREIGN KEY(pod_id) REFERENCES pods(id) ON DELETE CASCADE,
                FOREIGN KEY(span_id) REFERENCES spans(id) ON DELETE CASCADE
            )
        """)
        
        # Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pods_status ON pods(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_pod ON traces(pod_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_spans_parent ON spans(parent_span_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_healing_pod ON healing_interventions(pod_id)")
        conn.commit()


# --- Pod Operations ---

def create_pod(pod_id: str, name: str, agent_id: str, task_text: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO pods (id, name, status, agent_id, task_text, tokens_used, cost, created_at, updated_at)
            VALUES (?, ?, 'running', ?, ?, 0, 0.0, ?, ?)
        """, (pod_id, name, agent_id, task_text, now, now))
        conn.commit()
    return get_pod(pod_id)


def update_pod(pod_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return get_pod(pod_id)
    
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [pod_id]
    
    with _get_conn() as conn:
        conn.execute(f"UPDATE pods SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_pod(pod_id)


def get_pod(pod_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM pods WHERE id = ?", (pod_id,)).fetchone()
    return dict(row) if row else None


def list_pods(status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM pods"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    
    with _get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Trace Operations ---

def create_trace(trace_id: str, pod_id: Optional[str], name: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO traces (id, pod_id, name, status, started_at, total_tokens, total_cost)
            VALUES (?, ?, ?, 'running', ?, 0, 0.0)
        """, (trace_id, pod_id, name, now))
        conn.commit()
    return get_trace(trace_id)


def update_trace(trace_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return get_trace(trace_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [trace_id]
    
    with _get_conn() as conn:
        conn.execute(f"UPDATE traces SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_trace(trace_id)


def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
    return dict(row) if row else None


def list_traces(pod_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    query = "SELECT * FROM traces"
    params = []
    if pod_id:
        query += " WHERE pod_id = ?"
        params.append(pod_id)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    
    with _get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Span Operations ---

def create_span(
    span_id: str,
    trace_id: str,
    name: str,
    span_type: str,
    parent_span_id: Optional[str] = None,
    input_data: Optional[Any] = None
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    inp_str = json.dumps(input_data) if input_data is not None else None
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO spans (id, trace_id, parent_span_id, name, span_type, input, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (span_id, trace_id, parent_span_id, name, span_type, inp_str, now))
        conn.commit()
    return get_span(span_id)


def update_span(span_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return get_span(span_id)
    
    if "output" in kwargs and kwargs["output"] is not None and not isinstance(kwargs["output"], str):
        kwargs["output"] = json.dumps(kwargs["output"])
    if "input" in kwargs and kwargs["input"] is not None and not isinstance(kwargs["input"], str):
        kwargs["input"] = json.dumps(kwargs["input"])
        
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [span_id]
    
    with _get_conn() as conn:
        conn.execute(f"UPDATE spans SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_span(span_id)


def get_span(span_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM spans WHERE id = ?", (span_id,)).fetchone()
    return dict(row) if row else None


def get_trace_spans(trace_id: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM spans 
            WHERE trace_id = ? 
            ORDER BY started_at ASC
        """, (trace_id,)).fetchall()
    return [dict(r) for r in rows]


# --- Healing Intervention Operations ---

def create_healing_intervention(
    intervention_id: str,
    pod_id: str,
    span_id: str,
    error_message: str,
    diagnosis: Optional[str] = None,
    patch_type: Optional[str] = None,
    patch_content: Optional[str] = None
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO healing_interventions (id, pod_id, span_id, error_message, diagnosis, patch_type, patch_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (intervention_id, pod_id, span_id, error_message, diagnosis, patch_type, patch_content, now))
        conn.commit()
    
    # Fetch the saved intervention
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM healing_interventions WHERE id = ?", (intervention_id,)).fetchone()
    return dict(row)


def list_healing_interventions(pod_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM healing_interventions"
    params = []
    if pod_id:
        query += " WHERE pod_id = ?"
        params.append(pod_id)
    query += " ORDER BY created_at DESC"
    
    with _get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# Initialize on load
init_db()
