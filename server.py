"""
ADgents API Server
REST + WebSocket API for the agent platform.
"""
import json
import asyncio
import uuid
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent))

# Load .env — works with or without python-dotenv installed
def _load_env_file():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return
    except ImportError:
        pass
    # Fallback: parse .env manually
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

_load_env_file()

from core.agent import Agent, AgentFactory, AgentTask, ThoughtStep, AGENT_FACTORY
from core.persona import Persona, PERSONA_TEMPLATES
from core.skills import SKILL_REGISTRY, Skill
from core.llm import LLM_ROUTER
from core.memory import AgentMemory
from core.memory import AgentMemory
from core.agent_store import save_agent_persona, load_all_personas, delete_agent_persona
from core.task_db import save_task, list_tasks, get_task, delete_task, task_stats
from core.a2a_protocol import A2AProtocolManager, get_a2a_manager, A2AMessage
from core.mcp_server import MCPServer
from core.crew_manager import get_crew_manager


# ─── Logger Setup ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Suppress verbose Pydantic warnings ───────────────────────────────────────
import warnings
try:
    from pydantic import PydanticJsonSchemaWarning
    warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)
except ImportError:
    warnings.filterwarnings("ignore", message=".*non-serializable-default.*")

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    template: Optional[str] = None
    persona: Optional[Dict] = None
    is_deep_agent: Optional[bool] = False  # Enable LangChain advanced features

class ChatRequest(BaseModel):
    message: str
    agent_id: str

class TaskRequest(BaseModel):
    task: str
    agent_id: str
    max_iterations: Optional[int] = 10
    use_deep_agent: Optional[bool] = False  # Use Deep Agents SDK if True

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
    handler_code: str

class GenerateSkillRequest(BaseModel):
    description: str

class MCPConfigRequest(BaseModel):
    mode: Optional[str] = "stdio"
    port: Optional[int] = 8001

class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    role: str
    expertise: List[str] = []
    skills: List[str] = []
    instructions: str = ""
    model: str = "gemini-2.0-flash"

class CreateOrganizationRequest(BaseModel):
    name: str
    description: str = ""

class SendA2AMessageRequest(BaseModel):
    crew_id: str
    from_agent: str
    to_agent: str
    message_type: str
    content: Dict[str, Any]

class BroadcastA2AMessageRequest(BaseModel):
    crew_id: str
    from_agent: str
    message_type: str = "broadcast"
    content: Dict[str, Any]

class CreateCrewRequest(BaseModel):
    name: str
    description: str = ""
    organization: str = "default"
    members: List[Dict[str, Any]] = []
    communication_protocol: str = "a2a"


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

# Serve studio at root path
@app.get("/")
async def serve_studio():
    """Redirect root to studio."""
    return RedirectResponse(url="/studio/", status_code=302)

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


# ─── A2A Auto-Reply Engine ────────────────────────────────────────────────────

async def _agent_auto_reply(
    crew_id: str,
    receiver_id: str,
    sender_id: str,
    sender_name: str,
    receiver_name: str,
    message_text: str,
):
    """
    Background task: the receiving agent reads the message and replies autonomously
    using the built-in ReAct LLM agent (agent.think).
    """
    try:
        crew_mgr = get_crew_manager()

        receiver_agent = agents.get(receiver_id)
        if not receiver_agent:
            logger.info(f"[A2A] Agent {receiver_id} not in registry – skipping auto-reply")
            return

        context = f"[A2A Message from {sender_name}]: {message_text}"

        response_text = await asyncio.get_event_loop().run_in_executor(
            None, receiver_agent.think, context
        )

        if not response_text:
            return

        await crew_mgr.send_message_between_agents(
            crew_id=crew_id,
            from_agent=receiver_id,
            to_agent=sender_id,
            message={"text": response_text, "type": "text"},
            from_name=receiver_name,
            to_name=sender_name,
            message_type="response",
        )
        logger.info(f"[A2A] ✓ Auto-reply: {receiver_name} → {sender_name}")

    except Exception as e:
        logger.error(f"[A2A] Auto-reply error: {e}")


# ─── Deep Agent Execution ─────────────────────────────────────────────────────
def _run_deep_agent(agent: Agent, task: str, max_iterations: int, on_thought_callback: callable) -> AgentTask:
    """
    Execute an agent using the Deep Agents SDK (specialized LangChain-based agent framework).
    Deep Agents provide: planning, file system management, subagents, long-term memory.
    
    Args:
        agent: ADgents Agent instance with is_deep_agent=True
        task: The task to execute
        max_iterations: Max iterations for the agent
        on_thought_callback: Callback function to report thought steps
    
    Returns:
        AgentTask with results
    """
    started_at = datetime.utcnow().isoformat()
    
    try:
        # Try to import deepagents
        try:
            from deepagents import create_deep_agent
        except ImportError:
            # Fallback: if deepagents not installed, use standard agent.run()
            logger.warning("Deep Agents SDK not installed. Install with: pip install deepagents")
            logger.info(f"Falling back to standard ReAct loop for '{agent.persona.name}'")
            on_thought_callback(ThoughtStep(
                step_type="thought",
                content="⚠️ Deep Agents SDK not installed. Using standard ReAct. Run: pip install deepagents",
                timestamp=datetime.utcnow().isoformat()
            ))
            # Fallback to regular agent
            return agent.run(task, max_iterations)
        
        logger.info(f"🧠 Running Deep Agent '{agent.persona.name}' with task: {task[:100]}...")
        
        # Emit initial thought
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content="🧠 Deep Agent Mode - Planning, file management, and advanced reasoning enabled",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        # Get LLM model for Deep Agents - try to create a LangChain model
        langchain_model = None
        status = LLM_ROUTER.status()
        
        try:
            # Try to use configured providers
            if status.get("anthropic", {}).get("available"):
                from langchain_anthropic import ChatAnthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    langchain_model = ChatAnthropic(api_key=api_key, model="claude-3-5-sonnet-20241022")
                    logger.info("Using Anthropic/Claude for Deep Agent")
            elif status.get("openai", {}).get("available"):
                from langchain_openai import ChatOpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    langchain_model = ChatOpenAI(api_key=api_key, model="gpt-4o-mini")
                    logger.info("Using OpenAI/GPT-4o for Deep Agent")
            elif status.get("gemini", {}).get("available"):
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    langchain_model = ChatGoogleGenerativeAI(api_key=api_key, model="gemini-1.5-flash")
                    logger.info("Using Gemini for Deep Agent")
        except Exception as e:
            logger.warning(f"Failed to initialize LangChain model: {e}")
            langchain_model = None
        
        # If no model available, fallback to standard agent
        if not langchain_model:
            logger.warning("No LLM configured for Deep Agents. Falling back to standard ReAct")
            on_thought_callback(ThoughtStep(
                step_type="thought",
                content="⚠️ No LLM API key configured. Using standard ReAct. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY",
                timestamp=datetime.utcnow().isoformat()
            ))
            return agent.run(task, max_iterations)
        
        # Convert agent skills to deepagents-compatible LangChain tools
        from langchain_core.tools import StructuredTool
        import inspect
        
        tools = []
        for skill in agent.skill_registry.list():
            try:
                skill_name = skill.name
                skill_desc = skill.description or "Execute skill"
                skill_handler = skill.handler
                skill_params = skill.parameters or {}
                
                logger.info(f"[Deep Agent Tool] Converting skill: {skill_name} with params: {list(skill_params.get('properties', {}).keys())}")
                
                # Get the actual function signature to determine parameters
                sig = inspect.signature(skill_handler)
                param_names = list(sig.parameters.keys())
                
                logger.info(f"[Deep Agent Tool] Handler signature for {skill_name}: {param_names}")
                
                # Create tool wrapper that properly maps parameters
                def make_skill_tool(handler, name, desc, params_info, sig):
                    # Build a dynamic function with proper type hints
                    param_names = list(sig.parameters.keys())
                    
                    if not param_names:
                        # No parameters - shouldn't happen but handle it
                        def no_param_tool() -> str:
                            try:
                                result = handler({})
                                logger.info(f"[Skill {name}] Success")
                                return str(result)
                            except Exception as e:
                                logger.error(f"[Skill {name}] Error: {e}", exc_info=True)
                                return f"Error: {str(e)}"
                        return no_param_tool, name, desc
                    
                    elif len(param_names) == 1:
                        # Single parameter - use first param name
                        param_name = param_names[0]
                        param_type = sig.parameters[param_name].annotation or str
                        
                        def single_param_tool(**kwargs) -> str:
                            try:
                                # Extract the value from kwargs using the actual parameter name
                                value = kwargs.get(param_name, kwargs.get('query', kwargs.get('text', '')))
                                result = handler({param_name: value})
                                logger.info(f"[Skill {name}] Success")
                                return str(result)
                            except Exception as e:
                                logger.error(f"[Skill {name}] Error: {e}", exc_info=True)
                                return f"Error: {str(e)}"
                        
                        # Set proper annotation
                        single_param_tool.__annotations__ = {param_name: param_type, 'return': str}
                        return single_param_tool, name, desc
                    
                    else:
                        # Multiple parameters - build dynamic function
                        def multi_param_tool(**kwargs) -> str:
                            try:
                                # Build args dict with actual parameter names
                                args = {}
                                for pname in param_names:
                                    if pname in kwargs:
                                        args[pname] = kwargs[pname]
                                    elif pname == 'text' and 'query' in kwargs:
                                        args[pname] = kwargs['query']
                                    elif pname == 'max_sentences' or pname == 'num_results':
                                        args[pname] = kwargs.get(pname, 5)  # Default values
                                
                                logger.info(f"[Skill {name}] Calling with args: {args}")
                                result = handler(args)
                                logger.info(f"[Skill {name}] Success")
                                return str(result)
                            except Exception as e:
                                logger.error(f"[Skill {name}] Error: {e}", exc_info=True)
                                return f"Error: {str(e)}"
                        
                        # Build annotations
                        annotations = {}
                        for pname in param_names:
                            ptype = sig.parameters[pname].annotation or str
                            annotations[pname] = ptype
                        annotations['return'] = str
                        multi_param_tool.__annotations__ = annotations
                        return multi_param_tool, name, desc
                
                tool_func, tool_name, tool_desc = make_skill_tool(skill_handler, skill_name, skill_desc, skill_params, sig)
                
                # Create LangChain StructuredTool
                tool = StructuredTool.from_function(
                    func=tool_func,
                    name=tool_name,
                    description=tool_desc
                )
                tools.append(tool)
                logger.info(f"[Deep Agent Tool] ✅ Created tool: {tool_name}")
                
            except Exception as e:
                logger.error(f"[Deep Agent Tool] ❌ Failed to convert skill {skill.name}: {e}", exc_info=True)
        
        logger.info(f"[Deep Agent] Total tools ready: {len(tools)}")
        
        # Create Deep Agent with system prompt from agent persona
        system_prompt = agent.persona.to_system_prompt()
        
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content="🔧 Setting up Deep Agent tools and reasoning framework...",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        deep_agent = create_deep_agent(
            model=langchain_model,
            tools=tools,
            system_prompt=system_prompt,
        )
        
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content="💭 Beginning advanced planning and reasoning...",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        # Run the deep agent
        logger.info(f"[Deep Agent] Invoking with task: {task[:100]}")
        result = deep_agent.invoke({
            "messages": [{"role": "user", "content": task}]
        })
        
        logger.info(f"[Deep Agent] Result type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        completed_at = datetime.utcnow().isoformat()
        
        # Extract result from the message history - handle LangChain message objects
        output = ""
        if isinstance(result, dict):
            messages_list = result.get("messages", [])
            # Find the last message with actual content (skip empty messages)
            for msg in reversed(messages_list):
                # Handle LangChain BaseMessage objects
                if hasattr(msg, 'content'):
                    content = msg.content
                    if content and isinstance(content, str) and content.strip():
                        output = content.strip()
                        break
                # Handle dict format
                elif isinstance(msg, dict):
                    content = msg.get('content', '')
                    if content and isinstance(content, str) and content.strip():
                        output = content.strip()
                        break
            
            # If still no output, try to get the entire result summary
            if not output:
                # Extract from tool calls or other parts
                if "output" in result:
                    output = str(result["output"])[:1000]
                else:
                    output = f"Deep Agent reasoning completed. Messages: {len(messages_list)} messages processed."
        else:
            output = str(result)[:500]
        
        # Stream intermediate results
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content=f"📊 Analyzing results...",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content=f"✨ Processing Deep Agent output...",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        on_thought_callback(ThoughtStep(
            step_type="reflection",
            content=f"✅ Deep Agent Complete: {output[:200]}",
            timestamp=datetime.utcnow().isoformat()
        ))
        
        # Check for files created in data/files directory
        files_created = []
        try:
            files_dir = Path(__file__).parent / "data" / "files"
            if files_dir.exists():
                for file_path in files_dir.rglob("*"):
                    if file_path.is_file():
                        # Get relative path for display
                        try:
                            rel_path = file_path.relative_to(Path(__file__).parent)
                            files_created.append(str(rel_path))
                            logger.info(f"[Deep Agent] Found created file: {rel_path}")
                        except ValueError:
                            pass
        except Exception as e:
            logger.warning(f"Failed to scan for created files: {e}")
        
        return AgentTask(
            id=str(uuid.uuid4()),
            description=task,
            result=output,
            error=None,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            steps=[
                ThoughtStep(
                    step_type="reflection",
                    content=f"Deep Agent Output:\n{output}",
                    timestamp=completed_at
                )
            ],
            metadata={"files_created": files_created} if files_created else {}
        )
    
    except Exception as e:
        logger.error(f"Deep agent execution error: {e}", exc_info=True)
        completed_at = datetime.utcnow().isoformat()
        
        on_thought_callback(ThoughtStep(
            step_type="thought",
            content=f"❌ Deep Agent Error: {str(e)}",
            timestamp=completed_at
        ))
        
        return AgentTask(
            id=str(uuid.uuid4()),
            description=task,
            result=None,
            error=str(e),
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            steps=[]
        )



# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    studio_index = studio_path / "index.html"
    if studio_index.exists():
        return FileResponse(str(studio_index))
    return {"name": "ADgents API", "version": "1.0.0", "studio": "/studio"}


@app.get("/api/health")
async def health():
    llm_status = LLM_ROUTER.status()
    available_llms = [name for name, info in llm_status.items() if info.get("available", False)]
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents": len(agents),
        "skills": len(SKILL_REGISTRY.list()),
        "llm_providers": available_llms,
        "llm_total": len(llm_status),
        "llm_details": llm_status,
        "database": "sqlite",
        "database_status": "ready"
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
    agent.is_deep_agent = req.is_deep_agent or False
    agents[agent.id] = agent
    
    # Save persona with deep agent flag
    persona_data = persona.to_dict()
    persona_data['is_deep_agent'] = agent.is_deep_agent
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


@app.put("/api/agents/{agent_id}/deep-agent")
async def toggle_deep_agent(agent_id: str, enable: bool = True):
    """Toggle deep agent mode (LangChain advanced features) for an agent."""
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    
    agent.is_deep_agent = enable
    save_agent_persona(agent.persona)
    
    status = "enabled" if enable else "disabled"
    return {
        "success": True,
        "agent": agent.to_dict(),
        "message": f"Deep agent mode {status} for '{agent.persona.name}'"
    }


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
        import time
        step_queue: asyncio.Queue = asyncio.Queue()
        
        # Track last thought time to throttle streaming
        last_thought_time = [time.time()]
        
        def on_thought(step: ThoughtStep):
            # Thread-safe: put step into async queue with minimal throttling
            # This allows thoughts to stream more smoothly
            try:
                loop.call_soon_threadsafe(step_queue.put_nowait, step.to_dict())
                # Small sleep to allow UI to catch up
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"Failed to queue thought: {e}")
        
        agent.on_thought(on_thought)
        
        # Run CPU-bound agent execution in a thread pool
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Check if we should use deep agent mode
        # Use deep agent if: (1) explicitly requested via use_deep_agent flag OR (2) agent has is_deep_agent=True
        use_deep = req.use_deep_agent or agent.is_deep_agent
        
        if use_deep:
            # Use Deep Agents SDK for advanced reasoning
            agent_future = loop.run_in_executor(
                executor, 
                _run_deep_agent, 
                agent, 
                req.task, 
                req.max_iterations,
                on_thought
            )
        else:
            # Use standard ReAct loop
            agent_future = loop.run_in_executor(executor, agent.run, req.task, req.max_iterations)
        
        # Drain the step queue while the agent is running, streaming steps via WebSocket
        # Use shorter timeout to catch more frequent updates
        while not agent_future.done():
            try:
                step_dict = await asyncio.wait_for(step_queue.get(), timeout=0.05)
                await manager.send(req.agent_id, {
                    "type": "thought_step",
                    "task_id": task_id,
                    "step": step_dict
                })
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Queue drain error: {e}")
                break
        
        # Drain any remaining steps with more aggressive waiting
        max_retries = 100
        retry_count = 0
        while not step_queue.empty() and retry_count < max_retries:
            try:
                step_dict = step_queue.get_nowait()
                await manager.send(req.agent_id, {
                    "type": "thought_step",
                    "task_id": task_id,
                    "step": step_dict
                })
            except Exception:
                retry_count += 1
                await asyncio.sleep(0.01)
                continue
        
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


@app.get("/api/files/download")
async def download_file(path: str):
    """Download a file from the data/files directory."""
    # Security: ensure the path is within data/files/
    files_dir = Path(__file__).parent / "data" / "files"
    
    # Normalize the path to prevent directory traversal attacks
    requested_path = Path(path)
    if requested_path.is_absolute():
        # If absolute path is provided, make it relative to project root
        try:
            requested_path = requested_path.relative_to(Path(__file__).parent)
        except ValueError:
            raise HTTPException(400, "Invalid file path")
    
    # Construct full file path
    file_path = Path(__file__).parent / requested_path
    
    # Security check: ensure resolved path is within allowed directories
    try:
        file_path = file_path.resolve()
        allowed_dirs = [
            (Path(__file__).parent / "data" / "files").resolve(),
            (Path(__file__).parent / "data").resolve(),
        ]
        if not any(str(file_path).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs):
            raise HTTPException(403, "Access denied")
    except Exception:
        raise HTTPException(400, "Invalid file path")
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"File not found: {path}")
    
    # Return the file
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type='application/octet-stream'
    )


@app.get("/api/files/list")
async def list_files():
    """List all files in the data/files directory."""
    files_dir = Path(__file__).parent / "data" / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    
    files_list = []
    for file_path in files_dir.rglob("*"):
        if file_path.is_file():
            # Get file stats
            stat = file_path.stat()
            relative_path = file_path.relative_to(Path(__file__).parent)
            
            files_list.append({
                "name": file_path.name,
                "path": str(relative_path).replace("\\", "/"),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": file_path.suffix.lower()
            })
    
    # Sort by modified time (newest first)
    files_list.sort(key=lambda x: x["modified"], reverse=True)
    
    return {
        "files": files_list,
        "count": len(files_list),
        "total_size": sum(f["size"] for f in files_list)
    }


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


@app.get("/api/llm/configured")
async def get_configured_providers():
    """Get which providers are configured in environment variables."""
    import os
    configured = {}
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        configured["openai"] = {
            "available": True,
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "from_env": True
        }
    
    # Check Gemini
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        configured["gemini"] = {
            "available": True,
            "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            "from_env": True
        }
    
    # Check Claude
    if os.getenv("ANTHROPIC_API_KEY"):
        configured["claude"] = {
            "available": True,
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            "from_env": True
        }
    
    # Ollama doesn't need API key
    configured["ollama"] = {
        "available": True,
        "model": os.getenv("OLLAMA_MODEL", "llama2"),
        "note": "Local - no API key needed",
        "from_env": bool(os.getenv("OLLAMA_MODEL"))
    }
    
    return {"success": True, "configured": configured}


@app.post("/api/llm/configure")
async def configure_llm(config: Dict[str, Any]):
    """Configure LLM providers.
    
    If api_key is not provided, will use the key from environment variables (.env).
    """
    provider = config.get("provider")
    api_key = config.get("api_key")  # Can be None - will use .env if not provided
    model = config.get("model")
    
    if not provider:
        raise HTTPException(400, "Provider name required")
    
    import os
    
    # Only override environment variable if new key is provided
    if api_key:
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key

        elif provider == "claude":
            os.environ["ANTHROPIC_API_KEY"] = api_key
    
    # Reinitialize the router with the selected model
    # API key defaults to None, which means providers will use environment variables
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


STATIC_MODELS = {
    'openai': {
        'provider': 'OpenAI', 'icon': '🔴',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
        'env_key': 'OPENAI_API_KEY'
    },
    'gemini': {
        'provider': 'Google Gemini', 'icon': '🔵',
        'models': ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro'],
        'env_key': 'GEMINI_API_KEY'
    },
    'claude': {
        'provider': 'Anthropic Claude', 'icon': '✨',
        'models': ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
        'env_key': 'ANTHROPIC_API_KEY'
    },
}

@app.get("/api/llm/models")
async def get_all_available_models():
    """Get all available models for all providers.
    Shows which providers are configured based on environment variables.
    Models are listed for ALL providers, but marked as configured/unconfigured."""
    providers = {}
    
    for key, info in STATIC_MODELS.items():
        env_val = os.getenv(info['env_key'], '').strip()
        is_configured = bool(env_val and env_val not in ('', 'your-anthropic-key-here', 'your-google-cloud-api-key-here'))
        
        providers[key] = {
            'provider': info['provider'],
            'icon': info['icon'],
            'configured': is_configured,
            'models': info['models']
        }
    
    # Also check GOOGLE_API_KEY for gemini
    if os.getenv('GOOGLE_API_KEY', '').strip() and os.getenv('GOOGLE_API_KEY', '').strip() not in ('your-google-cloud-api-key-here',):
        providers['gemini']['configured'] = True
    
    return {
        "success": True,
        "providers": providers,
        "total_models": sum(len(v['models']) for v in providers.values()),
        "configured_count": sum(1 for v in providers.values() if v['configured'])
    }

@app.get("/api/llm/models/{provider}")
async def get_provider_models(provider: str):
    """Get models for a specific provider.
    Returns all models for the provider regardless of configuration status."""
    if provider not in STATIC_MODELS:
        return {"success": False, "error": f"Unknown provider: {provider}"}
    
    info = STATIC_MODELS[provider]
    env_val = os.getenv(info['env_key'], '').strip()
    is_configured = bool(env_val and env_val not in ('', 'your-anthropic-key-here', 'your-google-cloud-api-key-here'))
    
    # Check GOOGLE_API_KEY for gemini
    if provider == 'gemini' and os.getenv('GOOGLE_API_KEY', '').strip() and os.getenv('GOOGLE_API_KEY', '').strip() not in ('your-google-cloud-api-key-here',):
        is_configured = True
    
    return {
        "success": True,
        "provider": info['provider'],
        "models": info['models'],
        "configured": is_configured,
        "env_key": info['env_key']
    }

@app.get("/api/llm/env-status")  
async def get_llm_env_status():
    """Check what LLM providers are configured in environment variables.
    Returns a simple view of what's set (without exposing actual keys)."""
    return {
        "success": True,
        "providers": {
            "openai": {
                "configured": bool(os.getenv('OPENAI_API_KEY', '').strip()),
                "icon": "🔴"
            },
            "gemini": {
                "configured": bool(os.getenv('GEMINI_API_KEY', '').strip() or os.getenv('GOOGLE_API_KEY', '').strip()),
                "icon": "🔵"
            },
            "claude": {
                "configured": bool(os.getenv('ANTHROPIC_API_KEY', '').strip()),
                "icon": "✨"
            }
        }
    }


# ─── Docs ─────────────────────────────────────────────────────────────────────

@app.get("/api/docs/{doc_name}")
async def get_doc(doc_name: str):
    """Serve markdown documentation from packages or project folders."""
    docs_base = Path(__file__).parent / "docs"
    
    # Check if doc has section prefix (e.g., 'packages-installation')
    if '-' in doc_name:
        section, name = doc_name.split('-', 1)
        docs_path = docs_base / section / f"{name}.md"
    else:
        # Try packages first, then project, then root
        for location in [docs_base / "packages" / f"{doc_name}.md", 
                         docs_base / "project" / f"{doc_name}.md",
                         docs_base / f"{doc_name}.md"]:
            if location.exists() and location.is_file():
                docs_path = location
                break
        else:
            raise HTTPException(404, "Doc not found")
    
    if docs_path.exists() and docs_path.is_file():
        with open(docs_path, "r", encoding="utf-8") as f:
            return {"success": True, "content": f.read()}
    raise HTTPException(404, "Doc not found")

@app.get("/api/docs")
async def list_docs():
    """List available markdown docs from packages and project folders."""
    docs_base = Path(__file__).parent / "docs"
    docs = []
    
    # List docs from packages folder
    packages_path = docs_base / "packages"
    if packages_path.exists():
        for file in packages_path.glob("*.md"):
            if file.name != "README.md" and file.name != "LINKS.md":
                docs.append(f"packages-{file.stem}")
    
    # List docs from project folder
    project_path = docs_base / "project"
    if project_path.exists():
        for file in project_path.glob("*.md"):
            if file.name != "README.md":
                docs.append(f"project-{file.stem}")
    
    # List index and core docs from root
    for file in docs_base.glob("*.md"):
        if file.name == "index.md":
            docs.insert(0, "index")
        elif file.name not in ["README.md"]:
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
        # Get skills from registry
        tool_names = []
        
        if SKILL_REGISTRY and hasattr(SKILL_REGISTRY, '_skills'):
            try:
                # Use dictionary keys as skill names (this is the correct way)
                tool_names = list(SKILL_REGISTRY._skills.keys())
            except Exception as e:
                logger.warning(f"Failed to get skills from registry: {e}")
        
        # Get agents - extract names from agent objects
        agent_names = []
        if agents:
            try:
                agent_names = [a.persona.name for a in agents.values()]
            except Exception as e:
                logger.warning(f"Failed to get agent names: {e}")
        
        tools_count = len(tool_names)
        agents_count = len(agent_names)
        
        return {
            "success": True,
            "running": _mcp_server_running,
            "server_name": "adgents",
            "version": "1.0.0",
            "supported_protocols": ["stdio", "sse"],
            "available_tools": tools_count,
            "tool_names": tool_names,
            "available_agents": agents_count,
            "agent_names": agent_names,
            "config": _mcp_config,
            "capability": {
                "has_tools": tools_count > 0,
                "has_agents": agents_count > 0,
                "ready_for_connection": True
            }
        }
    except Exception as e:
        logger.error(f"Error in mcp_status: {e}")
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


# ─── Organizations ────────────────────────────────────────────────────────────

@app.post("/api/organizations/create")
async def create_organization(req: CreateOrganizationRequest):
    """Create a new organization."""
    try:
        crew_mgr = get_crew_manager()
        org = crew_mgr.create_organization(req.name, req.description)
        return {
            "success": True,
            "organization": org,
            "message": f"Organization created: {req.name}"
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
async def send_a2a_message(req: SendA2AMessageRequest, background_tasks: BackgroundTasks):
    """Send a message between two agents via A2A protocol and trigger autonomous reply."""
    try:
        crew_mgr = get_crew_manager()

        crew = crew_mgr.get_crew(req.crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}

        agent_ids = {m.agent_id for m in crew.members}
        if req.from_agent not in agent_ids or req.to_agent not in agent_ids:
            return {"success": False, "error": "Agent not in crew"}

        # Resolve human-readable names
        from_member = next((m for m in crew.members if m.agent_id == req.from_agent), None)
        to_member = next((m for m in crew.members if m.agent_id == req.to_agent), None)
        from_name = from_member.agent_name if from_member else req.from_agent[:8]
        to_name = to_member.agent_name if to_member else req.to_agent[:8]

        result = await crew_mgr.send_message_between_agents(
            crew_id=req.crew_id,
            from_agent=req.from_agent,
            to_agent=req.to_agent,
            message=req.content,
            from_name=from_name,
            to_name=to_name,
            message_type=req.message_type,
        )

        # Trigger receiving agent to reply autonomously in background
        message_text = req.content.get("text", str(req.content)) if isinstance(req.content, dict) else str(req.content)
        background_tasks.add_task(
            _agent_auto_reply,
            req.crew_id, req.to_agent, req.from_agent,
            from_name, to_name, message_text,
        )

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/a2a/broadcast")
async def broadcast_a2a_message(req: BroadcastA2AMessageRequest, background_tasks: BackgroundTasks):
    """Broadcast a message to all agents in a crew and trigger autonomous replies."""
    try:
        crew_mgr = get_crew_manager()

        crew = crew_mgr.get_crew(req.crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}

        from_member = next((m for m in crew.members if m.agent_id == req.from_agent), None)
        from_name = from_member.agent_name if from_member else req.from_agent[:8]

        result = await crew_mgr.broadcast_to_crew(
            crew_id=req.crew_id,
            from_agent=req.from_agent,
            message=req.content,
        )

        # Each receiving agent replies autonomously
        message_text = req.content.get("text", str(req.content)) if isinstance(req.content, dict) else str(req.content)
        for member in crew.members:
            if member.agent_id != req.from_agent:
                background_tasks.add_task(
                    _agent_auto_reply,
                    req.crew_id, member.agent_id, req.from_agent,
                    from_name, member.agent_name, message_text,
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

# ─── Crew Management Endpoints ────────────────────────────────────────────────

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
async def list_crews():
    """List all crews."""
    try:
        crew_mgr = get_crew_manager()
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


@app.post("/api/crews/{crew_id}/members")
async def add_crew_member(crew_id: str, member_data: Dict[str, Any]):
    """Add a member to a crew."""
    try:
        crew_mgr = get_crew_manager()
        success = crew_mgr.add_member_to_crew(
            crew_id=crew_id,
            agent_id=member_data["agent_id"],
            agent_name=member_data["agent_name"],
            role=member_data.get("role", "contributor")
        )
        if not success:
            return {"success": False, "error": "Failed to add member"}
        return {"success": True, "message": "Member added to crew"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/crews/{crew_id}")
async def delete_crew(crew_id: str):
    """Delete a crew."""
    try:
        crew_mgr = get_crew_manager()
        success = crew_mgr.delete_crew(crew_id)
        if not success:
            return {"success": False, "error": "Crew not found"}
        return {"success": True, "message": "Crew deleted successfully"}
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
