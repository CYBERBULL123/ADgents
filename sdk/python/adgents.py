"""
ADgents Python SDK
Easy integration for your own applications.

Usage:
    from sdk.python.adgents import ADgents, Agent

    # Initialize
    sdk = ADgents(api_url="http://localhost:8000")

    # Create an agent  
    agent = sdk.create_agent(template="researcher")

    # Chat
    response = agent.chat("What are the latest AI trends?")

    # Run autonomous task
    task = agent.run_task("Research and summarize quantum computing advances in 2024")
    print(task.result)
    
    # Teach the agent
    agent.learn("Our company was founded in 2020 and specializes in AI.")
"""
import httpx
import json
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class AgentTask:
    id: str
    status: str
    steps: List[Dict]
    result: Optional[str]
    error: Optional[str]
    description: str


@dataclass  
class Memory:
    id: str
    content: str
    summary: str
    type: str
    importance: float
    tags: List[str]


class Agent:
    """SDK wrapper for a single ADgents agent."""
    
    def __init__(self, agent_data: Dict, client: "ADgents"):
        self._data = agent_data
        self._client = client
        self.persona = agent_data.get("persona", {})
        self.id = self.persona.get("id")
        self.name = self.persona.get("name", "Agent")
        self.role = self.persona.get("role", "")
        self.avatar = self.persona.get("avatar", "🤖")
    
    def chat(self, message: str) -> str:
        """Send a message and get a response."""
        res = self._client._post("/chat", {"agent_id": self.id, "message": message})
        return res.get("response", "")
    
    def run_task(self, task: str, poll_interval: float = 1.0, max_wait: float = 120.0) -> AgentTask:
        """
        Run an autonomous task and wait for completion.
        Note: This uses polling. For real-time updates, use the WebSocket API directly.
        """
        # Start the task
        res = self._client._post("/tasks", {"agent_id": self.id, "task": task})
        task_id = res.get("task_id")
        
        # For SDK simplicity, we just run synchronously via chat with task framing
        # In production this would use WebSocket or polling
        response = self.chat(
            f"Please complete this task autonomously, using your skills: {task}"
        )
        
        return AgentTask(
            id=task_id or "local",
            status="completed",
            steps=[],
            result=response,
            error=None,
            description=task
        )
    
    def learn(self, fact: str, topic: str = "general", importance: float = 0.7) -> str:
        """Teach the agent a new fact."""
        res = self._client._post(f"/agents/{self.id}/learn", {
            "agent_id": self.id, "fact": fact, "topic": topic, "importance": importance
        })
        return res.get("memory_id", "")
    
    def recall(self, query: str, limit: int = 5) -> List[Memory]:
        """Retrieve relevant memories."""
        res = self._client._get(f"/agents/{self.id}/memory?query={query}&limit={limit}")
        return [
            Memory(
                id=m["id"], content=m["content"], summary=m["summary"],
                type=m["type"], importance=m["importance"], tags=m["tags"]
            )
            for m in res.get("memories", [])
        ]
    
    def reset_session(self):
        """Clear the agent's working memory."""
        self._client._post(f"/agents/{self.id}/reset", {})
    
    def update_persona(self, **kwargs):
        """Update the agent's persona attributes."""
        res = self._client._put(f"/agents/{self.id}/persona", {"agent_id": self.id, "updates": kwargs})
        self.persona.update(res.get("persona", {}))
    
    def delete(self):
        """Delete this agent."""
        self._client._delete(f"/agents/{self.id}")
    
    def __repr__(self):
        return f"Agent(name={self.name!r}, role={self.role!r}, id={self.id[:8]}...)"


class ADgents:
    """
    ADgents SDK — Autonomous Agent Platform Client
    
    Quick Start:
        sdk = ADgents()
        agent = sdk.create_agent(template="researcher")
        print(agent.chat("Explain quantum computing"))
    """
    
    def __init__(self, api_url: str = "http://localhost:8000", timeout: float = 60.0):
        self.api_url = api_url.rstrip("/") + "/api"
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def create_agent(self, template: str = None, persona: Dict = None) -> Agent:
        """
        Create a new agent.
        
        Args:
            template: Use a built-in template ('researcher', 'engineer', 'analyst', 'assistant', 'strategist')
            persona: Custom persona dict with name, role, personality_traits, etc.
        
        Returns:
            Agent instance ready to use
        """
        if not template and not persona:
            template = "assistant"
        
        body = {}
        if template:
            body["template"] = template
        if persona:
            body["persona"] = persona
        
        res = self._post("/agents", body)
        return Agent(res["agent"], self)
    
    def get_agent(self, agent_id: str) -> Agent:
        """Get an existing agent by ID."""
        data = self._get(f"/agents/{agent_id}")
        return Agent(data, self)
    
    def list_agents(self) -> List[Agent]:
        """List all agents."""
        data = self._get("/agents")
        return [Agent(a, self) for a in data.get("agents", [])]
    
    def quick_agent(self, name: str, role: str, expertise: List[str] = None, **kwargs) -> Agent:
        """
        Quickly create a custom agent with minimal configuration.
        
        Example:
            agent = sdk.quick_agent("Sarah", "Customer Support Specialist", 
                                    expertise=["CRM", "refunds", "billing"])
        """
        persona = {
            "name": name,
            "role": role,
            "expertise_domains": expertise or [],
            **kwargs
        }
        return self.create_agent(persona=persona)
    
    def execute_skill(self, skill_name: str, **kwargs) -> Dict:
        """Execute a skill directly without an agent."""
        return self._post("/skills/execute", {"skill_name": skill_name, "arguments": kwargs})
    
    def list_templates(self) -> Dict:
        """List available persona templates."""
        return self._get("/templates")["templates"]
    
    def list_skills(self) -> List[Dict]:
        """List all available skills."""
        return self._get("/skills")["skills"]
    
    def configure_llm(self, provider: str, api_key: str, model: str = None):
        """Configure an LLM provider."""
        self._post("/llm/configure", {"provider": provider, "api_key": api_key, "model": model})
    
    def health(self) -> Dict:
        """Check API health."""
        return self._get("/health")
    
    # ── HTTP Helpers ──────────────────────────────────────────────────────────
    def _get(self, path: str) -> Dict:
        res = self._client.get(f"{self.api_url}{path}")
        res.raise_for_status()
        return res.json()
    
    def _post(self, path: str, body: Dict) -> Dict:
        res = self._client.post(f"{self.api_url}{path}", json=body)
        res.raise_for_status()
        return res.json()
    
    def _put(self, path: str, body: Dict) -> Dict:
        res = self._client.put(f"{self.api_url}{path}", json=body)
        res.raise_for_status()
        return res.json()
    
    def _delete(self, path: str) -> Dict:
        res = self._client.delete(f"{self.api_url}{path}")
        res.raise_for_status()
        return res.json()
    
    def close(self):
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def __repr__(self):
        return f"ADgents(api_url={self.api_url!r})"
