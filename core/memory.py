"""
ADgents Memory System
Agents have layered memory just like humans:
- Working Memory: current session context
- Episodic Memory: past experiences (persisted)
- Semantic Memory: facts & knowledge
"""
import json
import sqlite3
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class MemoryEntry:
    """A single memory unit."""
    id: str
    agent_id: str
    memory_type: str  # episodic | semantic | procedural
    content: str
    summary: str
    importance: float  # 0.0 - 1.0
    tags: List[str]
    created_at: str
    last_accessed: str
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """
    Short-term, in-session memory. Holds the current conversation 
    and task context. Automatically trims to stay within token limits.
    """
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._messages: List[Dict] = []
        self._context: Dict[str, Any] = {}  # key-value scratchpad
    
    def add_message(self, role: str, content: str, metadata: Dict = None, tool_calls: list = None):
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        if tool_calls:
            entry["tool_calls"] = tool_calls  # stored for OpenAI format
        self._messages.append(entry)
        
        # Trim to max, keeping system messages
        if len(self._messages) > self.max_messages:
            # Keep first (system) and last N messages
            system_msgs = [m for m in self._messages if m["role"] == "system"]
            non_system = [m for m in self._messages if m["role"] != "system"]
            keep = non_system[-(self.max_messages - len(system_msgs)):]
            self._messages = system_msgs + keep
    
    def get_messages(self, roles: List[str] = None) -> List[Dict]:
        if roles:
            return [m for m in self._messages if m["role"] in roles]
        return list(self._messages)
    
    def get_llm_messages(self) -> List[Dict]:
        """Format for LLM API calls. Includes tool results so the LLM can synthesize them.
        Produces OpenAI-compatible format: assistant messages include tool_calls when present.
        """
        result = []
        for m in self._messages:
            if m["role"] not in ("system", "user", "assistant", "tool"):
                continue
            entry: Dict = {"role": m["role"], "content": m["content"] or ""}
            if m["role"] == "assistant" and m.get("tool_calls"):
                # OpenAI requires tool_calls on the assistant turn that preceded tool results
                entry["tool_calls"] = m["tool_calls"]
                # OpenAI expects content=None (not "") when there is no text alongside tool calls
                if not m["content"]:
                    entry["content"] = None
            if m["role"] == "tool":
                tool_call_id = m.get("metadata", {}).get("tool_call_id")
                if tool_call_id:
                    entry["tool_call_id"] = tool_call_id
            result.append(entry)
        return result
    
    def set_context(self, key: str, value: Any):
        self._context[key] = value
    
    def get_context(self, key: str, default=None) -> Any:
        return self._context.get(key, default)
    
    def clear(self):
        self._messages = []
        self._context = {}
    
    def summarize(self) -> str:
        """Simple summary of working memory state."""
        n = len(self._messages)
        roles = [m["role"] for m in self._messages]
        return f"Working memory: {n} messages ({roles.count('user')} user, {roles.count('assistant')} assistant)"
    
    def to_dict(self) -> Dict:
        return {"messages": self._messages, "context": self._context}


class EpisodicMemory:
    """
    Long-term memory of past experiences and interactions.
    Stored in SQLite with simple keyword search.
    """
    
    def __init__(self, agent_id: str, db_path: Path = None):
        self.agent_id = agent_id
        db_dir = DATA_DIR / "db"
        db_dir.mkdir(exist_ok=True)
        self.db_path = db_path or (db_dir / f"agent_{agent_id[:8]}.db")
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    importance REAL DEFAULT 0.5,
                    tags TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_id ON memories(agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            """)
            conn.commit()
    
    def _make_id(self, content: str) -> str:
        return hashlib.md5(f"{self.agent_id}{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()
    
    def store(self, content: str, summary: str = None, memory_type: str = "episodic", 
              importance: float = 0.5, tags: List[str] = None, metadata: Dict = None) -> str:
        mem_id = self._make_id(content)
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, agent_id, memory_type, content, summary, importance, tags, created_at, last_accessed, access_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                mem_id, self.agent_id, memory_type, content,
                summary or content[:200], importance,
                json.dumps(tags or []), now, now, json.dumps(metadata or {})
            ))
            conn.commit()
        return mem_id
    
    def recall(self, query: str, limit: int = 5, memory_type: str = None) -> List[MemoryEntry]:
        """Retrieve relevant memories using keyword search."""
        words = query.lower().split()
        
        with sqlite3.connect(self.db_path) as conn:
            # Simple LIKE-based search across content + summary
            conditions = ["agent_id = ?"]
            params = [self.agent_id]
            
            if memory_type:
                conditions.append("memory_type = ?")
                params.append(memory_type)
            
            # Add keyword conditions
            keyword_parts = []
            for word in words[:5]:  # limit to 5 keywords
                keyword_parts.append("(content LIKE ? OR summary LIKE ? OR tags LIKE ?)")
                params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])
            
            if keyword_parts:
                conditions.append(f"({' OR '.join(keyword_parts)})")
            
            where_clause = " AND ".join(conditions)
            
            rows = conn.execute(f"""
                SELECT * FROM memories 
                WHERE {where_clause}
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
            """, params + [limit]).fetchall()
            
            # Update access counts
            ids = [r[0] for r in rows]
            if ids:
                conn.execute(
                    f"UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id IN ({','.join('?'*len(ids))})",
                    [datetime.utcnow().isoformat()] + ids
                )
                conn.commit()
            
            return [self._row_to_entry(r) for r in rows]
    
    def get_recent(self, limit: int = 10, memory_type: str = None) -> List[MemoryEntry]:
        """Get most recent memories."""
        with sqlite3.connect(self.db_path) as conn:
            where = "agent_id = ?"
            params = [self.agent_id]
            if memory_type:
                where += " AND memory_type = ?"
                params.append(memory_type)
            
            rows = conn.execute(
                f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
    
    def delete(self, memory_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE id = ? AND agent_id = ?", 
                        [memory_id, self.agent_id])
            conn.commit()
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM memories WHERE agent_id = ?", 
                               [self.agent_id]).fetchone()[0]
    
    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE agent_id = ?", [self.agent_id])
            conn.commit()
    
    def _row_to_entry(self, row) -> MemoryEntry:
        return MemoryEntry(
            id=row[0], agent_id=row[1], memory_type=row[2],
            content=row[3], summary=row[4], importance=row[5],
            tags=json.loads(row[6]), created_at=row[7],
            last_accessed=row[8], access_count=row[9],
            metadata=json.loads(row[10])
        )


class KnowledgeBase:
    """
    Agent's semantic/declarative knowledge — facts, domain knowledge, documents.
    Stored and searchable as text entries.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._episodic = EpisodicMemory(agent_id)
    
    def learn(self, fact: str, topic: str = "general", importance: float = 0.7, source: str = None) -> str:
        """Add a fact or piece of knowledge."""
        return self._episodic.store(
            content=fact,
            summary=fact[:200],
            memory_type="semantic",
            importance=importance,
            tags=[topic],
            metadata={"source": source or "user"}
        )
    
    def recall(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Search knowledge base."""
        return self._episodic.recall(query, limit=limit, memory_type="semantic")
    
    def get_all_topics(self) -> List[str]:
        """Get all unique topics."""
        entries = self._episodic.get_recent(limit=1000, memory_type="semantic")
        topics = set()
        for e in entries:
            topics.update(e.tags)
        return sorted(topics)
    
    def learn_from_text(self, text: str, topic: str = "document", chunk_size: int = 500):
        """Break text into chunks and learn each one."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)
        
        for chunk in chunks:
            self.learn(chunk, topic=topic)
        
        return len(chunks)




class VectorMemory:
    """
    Fast semantic memory search using vector embeddings.
    - Uses FAISS if installed (GPU-accelerated, very fast)
    - Falls back to numpy cosine similarity (no extra deps)
    - Falls back to keyword search if neither available
    
    Embeddings are generated locally using a simple TF-IDF style approach
    when no embedding API is configured, or via sentence-transformers if installed.
    """
    
    def __init__(self, agent_id: str, dim: int = 128):
        self.agent_id = agent_id
        self.dim = dim
        self._vectors = []   # list of np.ndarray
        self._entries = []   # parallel list of MemoryEntry
        self._index = None   # FAISS index if available
        self._use_faiss = False
        self._use_numpy = False
        self._vocab: dict = {}
        self._idf: dict = {}
        
        try:
            import numpy as np
            self._np = np
            self._use_numpy = True
            try:
                import faiss
                self._faiss = faiss
                self._index = faiss.IndexFlatIP(self.dim)
                self._use_faiss = True
            except ImportError:
                pass
        except ImportError:
            self._np = None
    
    def _tokenize(self, text: str):
        import re
        return re.findall(r"[a-z]+", text.lower())
    
    def _embed(self, text: str):
        """TF-IDF style embedding into fixed-size vector."""
        if not self._use_numpy:
            return None
        np = self._np
        tokens = self._tokenize(text)
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in tokens:
            idx = hash(tok) % self.dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec
    
    def add(self, entry):
        """Add a MemoryEntry to the vector index."""
        if not self._use_numpy:
            return
        vec = self._embed(entry.content + " " + entry.summary)
        if vec is None:
            return
        self._entries.append(entry)
        self._vectors.append(vec)
        if self._use_faiss:
            import numpy as np
            self._index.add(np.array([vec]))
    
    def search(self, query: str, limit: int = 5):
        """Return top-k most similar MemoryEntries."""
        if not self._use_numpy or not self._entries:
            return []
        np = self._np
        q_vec = self._embed(query)
        if q_vec is None:
            return []
        
        if self._use_faiss and len(self._entries) > 0:
            k = min(limit, len(self._entries))
            scores, indices = self._index.search(np.array([q_vec]), k)
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if idx >= 0 and score > 0:
                    results.append(self._entries[idx])
            return results
        else:
            # numpy cosine similarity
            matrix = np.array(self._vectors)
            scores = matrix @ q_vec
            top_k = np.argsort(scores)[::-1][:limit]
            return [self._entries[i] for i in top_k if scores[i] > 0]
    
    def clear(self):
        self._vectors = []
        self._entries = []
        if self._use_faiss:
            import faiss
            self._index = faiss.IndexFlatIP(self.dim)
    
    @property
    def backend(self) -> str:
        if self._use_faiss:
            return "faiss"
        if self._use_numpy:
            return "numpy"
        return "disabled"

class AgentMemory:
    """Unified memory interface for an agent."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory(agent_id)
        self.knowledge = KnowledgeBase(agent_id)
        self.vector = VectorMemory(agent_id)
        # Pre-index existing memories
        self._preindex_memories()
    
    def _preindex_memories(self):
        """Load existing memories into vector index."""
        try:
            recent = self.episodic.get_recent(limit=200)
            for m in recent:
                self.vector.add(m)
        except Exception:
            pass
    
    def remember_interaction(self, user_input: str, agent_response: str, task: str = None):
        """Store an interaction as episodic memory."""
        content = f"User: {user_input}\nAgent: {agent_response}"
        summary = f"Interaction about: {(task or user_input)[:100]}"
        mem_id = self.episodic.store(
            content=content, summary=summary,
            memory_type="episodic", importance=0.5,
            tags=["interaction"],
            metadata={"task": task or ""}
        )
        # Also index in vector memory for fast semantic search
        from dataclasses import asdict
        try:
            entries = self.episodic.get_recent(limit=1)
            if entries:
                self.vector.add(entries[0])
        except Exception:
            pass
    
    def get_relevant_context(self, query: str) -> str:
        """Build context string from relevant memories. Uses vector search when available."""
        # Try vector search first (faster, semantic)
        try:
            vec_results = self.vector.search(query, limit=4)
            if vec_results:
                episodic = [m for m in vec_results if m.memory_type == "episodic"][:3]
                semantic  = [m for m in vec_results if m.memory_type == "semantic"][:3]
            else:
                raise ValueError("no vector results")
        except Exception:
            episodic = self.episodic.recall(query, limit=3)
            semantic = self.knowledge.recall(query, limit=3)
        
        parts = []
        if episodic:
            parts.append("=== Relevant Past Experiences ===")
            for m in episodic:
                parts.append(f"• {m.summary}")
        
        if semantic:
            parts.append("\n=== Relevant Knowledge ===")
            for m in semantic:
                parts.append(f"• {m.content[:300]}")
        
        return "\n".join(parts) if parts else ""
    
    def stats(self) -> Dict[str, Any]:
        return {
            "working_memory_messages": len(self.working.get_messages()),
            "episodic_memories": self.episodic.count(),
            "knowledge_entries": len(self.knowledge.recall("", limit=9999)),
            "vector_backend": self.vector.backend,
            "vector_indexed": len(self.vector._entries)
        }
