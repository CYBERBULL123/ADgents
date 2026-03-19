"""
ADgents API Server
REST + WebSocket API for the agent platform.
"""
import json
import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.agent import Agent, AgentFactory, AgentTask, ThoughtStep, AGENT_FACTORY
from core.persona import Persona, PERSONA_TEMPLATES
from core.skills import SKILL_REGISTRY, Skill
from core.llm import LLM_ROUTER
from core.memory import AgentMemory
from core.agent_store import save_agent_persona, load_all_personas, delete_agent_persona
from core.task_db import save_task, list_tasks, get_task, delete_task, task_stats
from core.crew import Crew
from core.crew_manager import CrewManager, get_crew_manager, AgentTemplate, CrewConfig
from core.a2a_protocol import A2AProtocolManager, get_a2a_manager, A2AMessage
from core.mcp_server import MCPServer

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    template: Optional[str] = None
    persona: Optional[Dict] = None

class ChatRequest(BaseModel):
    message: str
    agent_id: str

class TaskRequest(BaseModel):
    task: str
    agent_id: str
    max_iterations: Optional[int] = 10

class CrewRunRequest(BaseModel):
    task: str
    agent_ids: List[str]

class LearnRequest(BaseModel):
    agent_id: str
    fact: str
    topic: str = "general"
    importance: float = 0.7

class UpdatePersonaRequest(BaseModel):
    agent_id: str
    updates: Dict[str, Any]

class SkillExecuteRequest(BaseModel):
    skill_name: str
    arguments: Dict[str, Any] = {}

class RegisterSkillRequest(BaseModel):
    name: str
    description: str
    category: str = "custom"
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}
    handler_code: str  # Python code defining a 'handler' function

class GenerateSkillRequest(BaseModel):
    description: str

class MCPConfigRequest(BaseModel):
    mode: Optional[str] = "stdio"
    port: Optional[int] = 8001

# ─── Crew Management Models ───────────────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    role: str
    expertise: List[str] = []
    skills: List[str] = []
    instructions: str = ""
    model: str = "gemini-2.0-flash"

class CreateCrewRequest(BaseModel):
    name: str
    description: str = ""
    organization: str = "default"
    members: Optional[List[Dict]] = None
    communication_protocol: str = "a2a"

class AddCrewMemberRequest(BaseModel):
    crew_id: str
    agent_id: str
    agent_name: str
    role: str = "contributor"

class UpdateMemberStatusRequest(BaseModel):
    crew_id: str
    agent_id: str
    status: str
    current_task: Optional[str] = None

class SendA2AMessageRequest(BaseModel):
    crew_id: str
    from_agent: str
    to_agent: str
    message_type: str
    content: Dict[str, Any]

class BroadcastA2AMessageRequest(BaseModel):
    crew_id: str
    from_agent: str
    message_type: str
    content: Dict[str, Any]

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ADgents API",
    description="Autonomous AI Agent Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (Web Studio)
studio_path = Path(__file__).parent / "studio"
if studio_path.exists():
    app.mount("/studio", StaticFiles(directory=str(studio_path), html=True), name="studio")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, ws: WebSocket, agent_id: str):
        await ws.accept()
        if agent_id not in self.connections:
            self.connections[agent_id] = []
        self.connections[agent_id].append(ws)
    
    async def disconnect(self, ws: WebSocket, agent_id: str):
        if agent_id in self.connections:
            self.connections[agent_id].remove(ws)
    
    async def send(self, agent_id: str, data: Dict):
        if agent_id in self.connections:
            dead = []
            for ws in self.connections[agent_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections[agent_id].remove(ws)
    
    async def broadcast(self, data: Dict):
        for agent_id in list(self.connections.keys()):
            await self.send(agent_id, data)

manager = ConnectionManager()

# Agent registry - load saved agents on boot
agents: Dict[str, Agent] = {}
for _p in load_all_personas():
    agents[_p.id] = Agent(persona=_p)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    studio_index = studio_path / "index.html"
    if studio_index.exists():
        return FileResponse(str(studio_index))
    return {"name": "ADgents API", "version": "1.0.0", "studio": "/studio"}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": len(agents),
        "llm_providers": LLM_ROUTER.available_providers(),
        "skills": len(SKILL_REGISTRY.list())
    }


# ─── Agent Management ─────────────────────────────────────────────────────────

@app.post("/api/agents")
async def create_agent(req: CreateAgentRequest):
    """Create a new agent from a template or custom persona."""
    if req.template:
        if req.template not in PERSONA_TEMPLATES:
            raise HTTPException(400, f"Unknown template. Available: {list(PERSONA_TEMPLATES.keys())}")
        persona = PERSONA_TEMPLATES[req.template]
        persona = Persona.from_dict(persona.to_dict())
    elif req.persona:
        try:
            persona = Persona.from_dict(req.persona)
        except Exception as e:
            raise HTTPException(400, f"Invalid persona: {e}")
    else:
        raise HTTPException(400, "Provide either 'template' or 'persona'")
    
    agent = Agent(persona=persona)
    agents[agent.id] = agent
    save_agent_persona(persona)
    
    return {
        "success": True,
        "agent": agent.to_dict(),
        "message": f"Agent '{persona.name}' created successfully"
    }


@app.get("/api/agents")
async def list_agents():
    """List all active agents."""
    return {
        "success": True,
        "agents": [a.to_dict() for a in agents.values()],
        "count": len(agents)
    }


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get details of a specific agent."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return agent.to_dict()


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    if agent_id not in agents:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    agent = agents.pop(agent_id)
    delete_agent_persona(agent_id)
    return {"success": True, "message": f"Agent '{agent.name}' deleted"}


@app.put("/api/agents/{agent_id}/persona")
async def update_persona(agent_id: str, req: UpdatePersonaRequest):
    """Update an agent's persona."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    agent.update_persona(**req.updates)
    save_agent_persona(agent.persona)
    return {"success": True, "persona": agent.persona.to_dict()}


@app.post("/api/agents/{agent_id}/reset")
async def reset_agent(agent_id: str):
    """Reset agent's working memory."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    agent.reset_session()
    return {"success": True, "message": "Session reset"}


# ─── Chat & Tasks ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Simple chat with an agent."""
    agent = agents.get(req.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{req.agent_id}' not found")
    
    response = agent.think(req.message)
    return {
        "response": response,
        "agent": agent.name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/tasks")
async def run_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """Start an autonomous task with real-time WebSocket streaming."""
    agent = agents.get(req.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{req.agent_id}' not found")
    
    task_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    
    async def run_and_broadcast():
        import concurrent.futures
        step_queue: asyncio.Queue = asyncio.Queue()
        
        def on_thought(step: ThoughtStep):
            # Thread-safe: put step into async queue
            loop.call_soon_threadsafe(step_queue.put_nowait, step.to_dict())
        
        agent.on_thought(on_thought)
        
        # Run CPU-bound agent.run() in a thread pool so it doesn't block the event loop
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        agent_future = loop.run_in_executor(executor, agent.run, req.task, req.max_iterations)
        
        # Drain the step queue while the agent is running, streaming steps via WebSocket
        while not agent_future.done():
            try:
                step_dict = await asyncio.wait_for(step_queue.get(), timeout=0.1)
                await manager.send(req.agent_id, {
                    "type": "thought_step",
                    "task_id": task_id,
                    "step": step_dict
                })
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
        
        # Drain any remaining steps
        while not step_queue.empty():
            try:
                step_dict = step_queue.get_nowait()
                await manager.send(req.agent_id, {
                    "type": "thought_step",
                    "task_id": task_id,
                    "step": step_dict
                })
            except Exception:
                break
        
        # Get the completed task
        try:
            task = await agent_future
            task_dict = task.to_dict()
            # ── Persist to DB ──────────────────────────────────────────────
            agent_obj = agents.get(req.agent_id)
            save_task(
                task_id=task_id,
                agent_id=req.agent_id,
                agent_name=agent_obj.name if agent_obj else req.agent_id,
                agent_avatar=agent_obj.persona.avatar if agent_obj else "🤖",
                task_text=req.task,
                status=task_dict.get("status", "completed"),
                result=task_dict.get("result"),
                error=task_dict.get("error"),
                steps=task_dict.get("steps", []),
                started_at=task_dict.get("started_at", datetime.utcnow().isoformat()),
                completed_at=task_dict.get("completed_at", datetime.utcnow().isoformat()),
                max_iterations=req.max_iterations,
            )
            await manager.send(req.agent_id, {
                "type": "task_complete",
                "task_id": task_id,
                "task": task_dict
            })
        except Exception as e:
            save_task(
                task_id=task_id, agent_id=req.agent_id,
                agent_name=agents.get(req.agent_id, agent).name,
                agent_avatar=agents.get(req.agent_id, agent).persona.avatar if agents.get(req.agent_id) else "🤖",
                task_text=req.task, status="failed",
                result=None, error=str(e), steps=[],
                started_at=datetime.utcnow().isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                max_iterations=req.max_iterations,
            )
            await manager.send(req.agent_id, {
                "type": "task_error",
                "task_id": task_id,
                "error": str(e)
            })
        finally:
            executor.shutdown(wait=False)
    
    background_tasks.add_task(run_and_broadcast)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"Task started for agent '{agent.name}'"
    }


# ─── Task History ─────────────────────────────────────────────────────────────

@app.get("/api/tasks")
async def get_task_history(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List persisted task history, newest first."""
    tasks = list_tasks(agent_id=agent_id, status=status, search=search, limit=limit, offset=offset)
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/api/tasks/stats")
async def get_task_stats():
    """Return aggregate task statistics."""
    return task_stats()


@app.get("/api/tasks/{task_id}")
async def get_single_task(task_id: str):
    """Get a single task by ID."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return task


@app.delete("/api/tasks/{task_id}")
async def remove_task(task_id: str):
    """Delete a task from history."""
    if not delete_task(task_id):
        raise HTTPException(404, f"Task '{task_id}' not found")
    return {"success": True}


# ─── Memory & Knowledge ───────────────────────────────────────────────────────

@app.get("/api/agents/{agent_id}/memory")
async def get_memory(agent_id: str, query: str = "", limit: int = 10):
    """Get agent's memories."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    if query:
        memories = agent.memory.episodic.recall(query, limit=limit)
    else:
        memories = agent.memory.episodic.get_recent(limit=limit)
    
    return {
        "memories": [
            {
                "id": m.id, "content": m.content, "summary": m.summary,
                "type": m.memory_type, "importance": m.importance,
                "tags": m.tags, "created_at": m.created_at
            }
            for m in memories
        ],
        "count": len(memories)
    }


@app.post("/api/agents/{agent_id}/learn")
async def teach_agent(agent_id: str, req: LearnRequest):
    """Teach an agent a new fact."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    mem_id = agent.learn(req.fact, topic=req.topic, importance=req.importance)
    return {"success": True, "memory_id": mem_id}


@app.delete("/api/agents/{agent_id}/memory/{memory_id}")
async def delete_memory(agent_id: str, memory_id: str):
    """Delete a specific memory."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    agent.memory.episodic.delete(memory_id)
    return {"success": True}


# ─── Skills ───────────────────────────────────────────────────────────────────

@app.get("/api/skills")
async def list_skills(category: str = None):
    """List all available skills."""
    skills = SKILL_REGISTRY.list(category=category)
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "parameters": s.parameters,
                "requires_confirmation": s.requires_confirmation,
                "is_custom": s.is_custom,
                "handler_code": s.handler_code if s.is_custom else ""
            }
            for s in skills
        ],
        "count": len(skills)
    }


@app.post("/api/skills/execute")
async def execute_skill(req: SkillExecuteRequest):
    """Execute a skill directly."""
    result = SKILL_REGISTRY.execute(req.skill_name, **req.arguments)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "execution_time": result.execution_time
    }


@app.post("/api/skills/register")
async def register_skill(req: RegisterSkillRequest):
    """Register a new custom skill from Python handler code."""
    if SKILL_REGISTRY.get(req.name) and not SKILL_REGISTRY.get(req.name).is_custom:
        raise HTTPException(400, f"Cannot override built-in skill '{req.name}'")
    try:
        skill = SKILL_REGISTRY.register_from_code(
            name=req.name,
            description=req.description,
            handler_code=req.handler_code,
            parameters=req.parameters,
            category=req.category
        )
        return {
            "success": True,
            "skill": {
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "is_custom": True
            },
            "message": f"Skill '{req.name}' registered successfully"
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/skills/{skill_name}")
async def delete_skill(skill_name: str):
    """Delete a custom skill."""
    skill = SKILL_REGISTRY.get(skill_name)
    if not skill:
        raise HTTPException(404, f"Skill '{skill_name}' not found")
    if not skill.is_custom:
        raise HTTPException(403, f"Cannot delete built-in skill '{skill_name}'")
    SKILL_REGISTRY.unregister(skill_name)
    return {"success": True, "message": f"Skill '{skill_name}' deleted"}


@app.post("/api/skills/generate")
async def generate_skill(req: GenerateSkillRequest):
    """Generate a custom skill from natural language using the active LLM."""
    prompt = f"""
You are an expert Python developer.
Generate a Python function named `handler` that accomplishes the following task:
{req.description}

Requirements:
- The function MUST be named `handler` and accept `**kwargs` or specific parameters.
- Return a dictionary with at least a 'success' boolean key and any resulting data.
- CRITICAL: You MUST ONLY use Python built-in standard libraries (e.g. `urllib.request`, `json`, `re`, `math`).
- STRICTLY FORBIDDEN to use third-party packages such as `requests`, `bs4`, `numpy`, or `pandas`. Use `urllib.request` instead of `requests`.
- Import any necessary standard libraries at the top of the file, above the function.
- DO NOT use markdown formatting (like ```python) around the code, output purely the python code.
Task: {req.description}
"""
    messages = [
        {"role": "system", "content": "You are a code generator. Output ONLY valid Python code, without any markdown blocks, explanations, or text."},
        {"role": "user", "content": prompt}
    ]
    
    response = LLM_ROUTER.complete(messages=messages, temperature=0.1)
    code = response.content.strip()
    
    import re
    # Extract python code if wrapped in markdown blocks
    match = re.search(r"```(?:python)?\s*(.*?)\s*```", code, re.DOTALL)
    if match:
        code = match.group(1)
        
    code = code.strip()
    return {
        "success": True,
        "code": code,
        "message": "Skill code generated. Please review and register."
    }


# ─── Templates ────────────────────────────────────────────────────────────────

@app.get("/api/templates")
async def list_templates():
    """List all persona templates."""
    return {
        "templates": {
            name: persona.to_dict()
            for name, persona in PERSONA_TEMPLATES.items()
        }
    }


# ─── LLM Config ──────────────────────────────────────────────────────────────

@app.get("/api/llm/status")
async def llm_status():
    """Get LLM provider status."""
    return LLM_ROUTER.status()


@app.post("/api/llm/configure")
async def configure_llm(config: Dict[str, Any]):
    """Configure LLM providers."""
    provider = config.get("provider")
    api_key = config.get("api_key")
    model = config.get("model")
    
    if not provider:
        raise HTTPException(400, "Provider name required")
    
    import os
    if api_key:
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "claude":
            os.environ["ANTHROPIC_API_KEY"] = api_key
    
    # Reinitialize the router
    from core.llm import OpenAIProvider, GeminiProvider, AnthropicProvider
    if provider == "openai":
        LLM_ROUTER.register(OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini"))
        LLM_ROUTER.set_default("openai")
    elif provider == "gemini":
        LLM_ROUTER.register(GeminiProvider(api_key=api_key, model=model or "gemini-1.5-flash"))
        LLM_ROUTER.set_default("gemini")
    elif provider == "claude":
        LLM_ROUTER.register(AnthropicProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022"))
        LLM_ROUTER.set_default("claude")
    
    return {"success": True, "status": LLM_ROUTER.status()}


# ─── Docs ─────────────────────────────────────────────────────────────────────

@app.get("/api/docs/{doc_name}")
async def get_doc(doc_name: str):
    """Serve markdown documentation."""
    docs_path = Path(__file__).parent / "docs" / f"{doc_name}.md"
    if docs_path.exists() and docs_path.is_file():
        with open(docs_path, "r", encoding="utf-8") as f:
            return {"success": True, "content": f.read()}
    raise HTTPException(404, "Doc not found")

@app.get("/api/docs")
async def list_docs():
    """List available markdown docs."""
    docs_path = Path(__file__).parent / "docs"
    docs = []
    if docs_path.exists():
        for file in docs_path.glob("*.md"):
            docs.append(file.stem)
    return {"success": True, "docs": docs}


# ─── MCP (Model Context Protocol) ─────────────────────────────────────────────

# Global MCP server state
_mcp_server_running = False
_mcp_config = {"mode": "stdio", "port": 8001}

@app.get("/api/mcp/status")
async def mcp_status():
    """Get MCP server status and available tools."""
    try:
        tools_count = len(SKILL_REGISTRY._skills) if SKILL_REGISTRY and hasattr(SKILL_REGISTRY, '_skills') else 0
        agents_count = len(agents) if agents else 0
        return {
            "success": True,
            "running": _mcp_server_running,
            "server_name": "adgents",
            "version": "1.0.0",
            "supported_protocols": ["stdio", "sse"],
            "available_tools": tools_count,
            "available_agents": agents_count,
            "config": _mcp_config,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "running": False}

@app.get("/api/mcp/tools")
async def mcp_list_tools():
    """List all skills available as MCP tools."""
    tools = []
    for skill_name, skill in SKILL_REGISTRY._skills.items():
        tools.append({
            "name": skill_name,
            "description": skill.description,
            "input_schema": skill.parameters
        })
    return {"success": True, "tools": tools}

@app.post("/api/mcp/configure")
async def mcp_configure(request: MCPConfigRequest):
    """Configure MCP server settings (e.g., stdio vs SSE mode)."""
    global _mcp_config
    _mcp_config = {
        "mode": request.mode or "stdio",
        "port": request.port or 8001,
    }
    return {
        "success": True,
        "message": "MCP configured successfully",
        "config": _mcp_config,
    }

@app.post("/api/mcp/start")
async def mcp_start():
    """Start the MCP server."""
    global _mcp_server_running
    try:
        _mcp_server_running = True
        return {
            "success": True,
            "message": "MCP server started",
            "running": True,
            "config": _mcp_config,
            "tools_count": len(SKILL_REGISTRY._skills) if SKILL_REGISTRY else 0,
            "agents_count": len(agents) if agents else 0,
        }
    except Exception as e:
        _mcp_server_running = False
        return {"success": False, "error": str(e), "message": "Failed to start MCP server"}

@app.post("/api/mcp/stop")
async def mcp_stop():
    """Stop the MCP server."""
    global _mcp_server_running
    try:
        _mcp_server_running = False
        return {
            "success": True,
            "message": "MCP server stopped",
            "running": False,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to stop MCP server"}



# ─── LangChain Integration ────────────────────────────────────────────────────

_langchain_agents = {}  # Store LangChain adapters

@app.post("/api/langchain/create-agent")
async def langchain_create_agent(request: CreateAgentRequest):
    """Create a LangChain-powered agent from an ADgents agent."""
    try:
        from core.langchain_integration import create_langchain_agent_from_adgent
        
        agent_id = request.name.lower().replace(" ", "_")
        agent = agents.get(agent_id)
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Create LangChain adapter with all available skills
        skills_list = list(SKILL_REGISTRY._skills.values()) if SKILL_REGISTRY else []
        langchain_agent = create_langchain_agent_from_adgent(agent, skills_list=skills_list)
        
        _langchain_agents[agent_id] = langchain_agent
        
        return {
            "success": True,
            "message": f"LangChain agent created for {agent_id}",
            "agent_id": agent_id,
            "tools_registered": len(skills_list),
            "type": "langchain_agent"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/langchain/run-agent")
async def langchain_run_agent(request: ChatRequest):
    """Run a LangChain agent."""
    try:
        agent_id = request.agent_id
        user_input = request.message
        
        if agent_id not in _langchain_agents:
            raise ValueError(f"LangChain agent {agent_id} not found. Create it first.")
        
        langchain_agent = _langchain_agents[agent_id]
        result = await langchain_agent.run_agent(user_input)
        
        return {
            "success": result.get("success", False),
            "response": result.get("output"),
            "memory": result.get("memory"),
            "error": result.get("error")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/langchain/agents")
async def langchain_list_agents():
    """List all LangChain agents."""
    agents_list = [
        {"agent_id": agent_id, "type": "langchain_agent"}
        for agent_id in _langchain_agents.keys()
    ]
    return {
        "success": True,
        "agents": agents_list,
        "total": len(agents_list)
    }




# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """Real-time WebSocket connection for agent updates."""
    await manager.connect(websocket, agent_id)
    
    await websocket.send_json({
        "type": "connected",
        "agent_id": agent_id,
        "message": f"Connected to agent {agent_id}"
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "chat":
                agent = agents.get(agent_id)
                if agent:
                    response = agent.think(data.get("message", ""))
                    await websocket.send_json({
                        "type": "chat_response",
                        "response": response,
                        "agent": agent.name,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await websocket.send_json({"type": "error", "message": "Agent not found"})
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, agent_id)


# ─── Multi-Agent Crew ─────────────────────────────────────────────────────────

@app.post("/api/crew/run")
async def run_crew(req: CrewRunRequest):
    """Run an autonomous task using a multi-agent Crew."""
    crew_agents = [agents[a_id] for a_id in req.agent_ids if a_id in agents]
    if len(crew_agents) < 2:
        raise HTTPException(400, "Crew requires at least 2 active agents")
    
    crew = Crew(name="Ad-hoc Crew", agents=crew_agents)
    
    # We will just run it in a thread executor
    loop = asyncio.get_event_loop()
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    try:
        run_obj = await loop.run_in_executor(executor, crew.run, req.task)
        return {"success": True, "run": run_obj.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Agent Templates ──────────────────────────────────────────────────────────

@app.post("/api/templates/create")
async def create_template(req: CreateTemplateRequest):
    """Create an agent template."""
    try:
        crew_mgr = get_crew_manager()
        template = crew_mgr.create_template(
            name=req.name,
            description=req.description,
            role=req.role,
            expertise=req.expertise,
            skills=req.skills,
            instructions=req.instructions,
            model=req.model
        )
        return {
            "success": True,
            "template": template.to_dict(),
            "message": f"Template created: {req.name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/templates")
async def list_templates():
    """List all agent templates."""
    try:
        crew_mgr = get_crew_manager()
        templates = crew_mgr.get_templates()
        return {
            "success": True,
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template."""
    try:
        crew_mgr = get_crew_manager()
        template = crew_mgr.get_template(template_id)
        if not template:
            raise HTTPException(404, "Template not found")
        return {
            "success": True,
            "template": template.to_dict()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template."""
    try:
        crew_mgr = get_crew_manager()
        if crew_mgr.delete_template(template_id):
            return {"success": True, "message": "Template deleted"}
        return {"success": False, "error": "Template not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Crew Management ──────────────────────────────────────────────────────────

@app.post("/api/crews/create")
async def create_crew(req: CreateCrewRequest):
    """Create a new crew."""
    try:
        crew_mgr = get_crew_manager()
        crew = crew_mgr.create_crew(
            name=req.name,
            description=req.description,
            organization=req.organization,
            members=req.members,
            communication_protocol=req.communication_protocol
        )
        return {
            "success": True,
            "crew": crew.to_dict(),
            "message": f"Crew created: {req.name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/crews")
async def list_crews(organization: Optional[str] = None):
    """List all crews (optionally filtered by organization)."""
    try:
        crew_mgr = get_crew_manager()
        if organization:
            crews = crew_mgr.get_crews_by_organization(organization)
        else:
            crews = crew_mgr.list_crews()
        
        return {
            "success": True,
            "crews": [c.to_dict() for c in crews],
            "count": len(crews)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/crews/{crew_id}")
async def get_crew(crew_id: str):
    """Get a specific crew."""
    try:
        crew_mgr = get_crew_manager()
        crew = crew_mgr.get_crew(crew_id)
        if not crew:
            raise HTTPException(404, "Crew not found")
        return {
            "success": True,
            "crew": crew.to_dict()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/crews/{crew_id}/add-member")
async def add_crew_member(crew_id: str, req: AddCrewMemberRequest):
    """Add an agent to a crew."""
    try:
        crew_mgr = get_crew_manager()
        success = crew_mgr.add_member_to_crew(
            crew_id=crew_id,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            role=req.role
        )
        if success:
            crew = crew_mgr.get_crew(crew_id)
            return {
                "success": True,
                "crew": crew.to_dict(),
                "message": f"Added {req.agent_name} to crew"
            }
        return {"success": False, "error": "Failed to add member"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/crews/{crew_id}/remove-member")
async def remove_crew_member(crew_id: str, agent_id: str):
    """Remove an agent from a crew."""
    try:
        crew_mgr = get_crew_manager()
        success = crew_mgr.remove_member_from_crew(crew_id, agent_id)
        if success:
            crew = crew_mgr.get_crew(crew_id)
            return {
                "success": True,
                "crew": crew.to_dict(),
                "message": "Member removed from crew"
            }
        return {"success": False, "error": "Member not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/crews/{crew_id}/update-member-status")
async def update_member_status(crew_id: str, req: UpdateMemberStatusRequest):
    """Update a crew member's status in real-time."""
    try:
        crew_mgr = get_crew_manager()
        success = crew_mgr.update_member_status(
            crew_id=crew_id,
            agent_id=req.agent_id,
            status=req.status,
            current_task=req.current_task
        )
        if success:
            return {
                "success": True,
                "message": f"Member status updated to: {req.status}"
            }
        return {"success": False, "error": "Member not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/crews/{crew_id}")
async def delete_crew(crew_id: str):
    """Delete a crew."""
    try:
        crew_mgr = get_crew_manager()
        if crew_mgr.delete_crew(crew_id):
            return {"success": True, "message": "Crew deleted"}
        return {"success": False, "error": "Crew not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/crews/{crew_id}/execute")
async def execute_crew_task(crew_id: str, req: TaskRequest):
    """Execute a task autonomously using a crew."""
    try:
        crew_mgr = get_crew_manager()
        crew = crew_mgr.get_crew(crew_id)
        
        if not crew:
            raise HTTPException(404, f"Crew {crew_id} not found")
        
        # Get crew members
        crew_agents = []
        for member in crew.get('members', []):
            agent_id = member.get('agent_id')
            if agent_id and agent_id in agents:
                crew_agents.append(agents[agent_id])
        
        if not crew_agents:
            raise ValueError("No valid agents in crew")
        
        # Execute task with primary agent (coordinator)
        primary_agent = crew_agents[0]
        
        # Add context about other team members
        team_context = f"\n\nYou are part of a crew with these team members:\n"
        for member in crew.get('members', []):
            team_context += f"- {member.get('agent_name', 'Agent')} (Role: {member.get('role', 'contributor')})\n"
        
        task_with_context = f"{req.task}{team_context}"
        
        # Run the task
        result = await primary_agent.run_task(task_with_context, max_iterations=req.max_iterations)
        
        return {
            "success": True,
            "crew_id": crew_id,
            "task": req.task,
            "agents_involved": len(crew_agents),
            "agent_names": [m.get('agent_name', 'Agent') for m in crew.get('members', [])],
            "output": result if isinstance(result, str) else str(result),
            "message": "Task executed autonomously"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to execute crew task"
        }


# ─── Organizations ────────────────────────────────────────────────────────────

@app.post("/api/organizations/create")
async def create_organization(name: str, description: str = ""):
    """Create a new organization."""
    try:
        crew_mgr = get_crew_manager()
        org = crew_mgr.create_organization(name, description)
        return {
            "success": True,
            "organization": org,
            "message": f"Organization created: {name}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/organizations")
async def list_organizations():
    """List all organizations."""
    try:
        crew_mgr = get_crew_manager()
        orgs = crew_mgr.list_organizations()
        return {
            "success": True,
            "organizations": orgs,
            "count": len(orgs)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/organizations/{org_id}")
async def get_organization(org_id: str):
    """Get organization details and statistics."""
    try:
        crew_mgr = get_crew_manager()
        org = crew_mgr.get_organization(org_id)
        if not org:
            raise HTTPException(404, "Organization not found")
        
        stats = crew_mgr.get_organization_stats(org_id)
        
        return {
            "success": True,
            "organization": org,
            "statistics": stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Agent-to-Agent (A2A) Protocol ────────────────────────────────────────────

@app.post("/api/a2a/send")
async def send_a2a_message(req: SendA2AMessageRequest):
    """Send a message between two agents via A2A protocol."""
    try:
        crew_mgr = get_crew_manager()
        a2a_mgr = get_a2a_manager()
        
        # Verify crew and agents exist
        crew = crew_mgr.get_crew(req.crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}
        
        agent_ids = {m.agent_id for m in crew.members}
        if req.from_agent not in agent_ids or req.to_agent not in agent_ids:
            return {"success": False, "error": "Agent not in crew"}
        
        # Create A2A message
        message = A2AMessage(
            sender_id=req.from_agent,
            receiver_id=req.to_agent,
            crew_id=req.crew_id,
            message_type=req.message_type,
            content=req.content
        )
        
        # Send via A2A protocol
        result = await crew_mgr.send_message_between_agents(
            crew_id=req.crew_id,
            from_agent=req.from_agent,
            to_agent=req.to_agent,
            message=req.content
        )
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/a2a/broadcast")
async def broadcast_a2a_message(req: BroadcastA2AMessageRequest):
    """Broadcast a message to all agents in a crew."""
    try:
        crew_mgr = get_crew_manager()
        
        # Verify crew exists
        crew = crew_mgr.get_crew(req.crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}
        
        # Broadcast message
        result = await crew_mgr.broadcast_to_crew(
            crew_id=req.crew_id,
            from_agent=req.from_agent,
            message=req.content
        )
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/a2a/communications/{crew_id}")
async def get_crew_communications(crew_id: str):
    """Get all communications in a crew."""
    try:
        crew_mgr = get_crew_manager()
        comms = crew_mgr.get_crew_communications(crew_id)
        return {
            "success": True,
            "communications": comms,
            "count": len(comms)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/a2a/communications/agent/{agent_id}")
async def get_agent_communications(agent_id: str):
    """Get all communications for a specific agent."""
    try:
        crew_mgr = get_crew_manager()
        comms = crew_mgr.get_agent_communications(agent_id)
        return {
            "success": True,
            "communications": comms,
            "count": len(comms)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ─── MCP Endpoint ─────────────────────────────────────────────────────────────

# Expose all currently running agents and global skills
mcp_server = MCPServer(skill_registry=SKILL_REGISTRY, agents=list(agents.values()))
app.include_router(mcp_server.get_fastapi_router(), prefix="/mcp")

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ADgents API Server...")
    print("📡 API: http://localhost:8000")
    print("🎨 Studio: http://localhost:8000/studio")
    print("📚 Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
