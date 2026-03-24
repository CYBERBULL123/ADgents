"""
ADgents Core Agent
The Agent is the autonomous entity — combining persona, memory, skills, and LLM into a living entity.
It runs a ReAct (Reason + Act) loop to solve tasks autonomously.
"""
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Callable, Generator
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .persona import Persona, PERSONA_TEMPLATES
from .memory import AgentMemory
from .skills import SkillRegistry, SKILL_REGISTRY, SkillResult
from .llm import LLMRouter, LLM_ROUTER, LLMResponse


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    REFLECTING = "reflecting"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class ThoughtStep:
    """A single step in the agent's reasoning process."""
    step_type: str  # thought | action | observation | reflection
    content: str
    skill_used: Optional[str] = None
    skill_args: Optional[Dict] = None
    skill_result: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "step_type": self.step_type,
            "content": self.content,
            "skill_used": self.skill_used,
            "skill_args": self.skill_args,
            "skill_result": self.skill_result,
            "timestamp": self.timestamp
        }


@dataclass  
class AgentTask:
    """A task assigned to an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: str = "pending"  # pending | running | completed | failed
    steps: List[ThoughtStep] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: ThoughtStep):
        self.steps.append(step)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id, "description": self.description, "status": self.status,
            "steps": [s.to_dict() for s in self.steps], "result": self.result,
            "error": self.error, "started_at": self.started_at,
            "completed_at": self.completed_at, "metadata": self.metadata
        }


class Agent:
    """
    The core autonomous agent — a digital persona with memory, skills, and reasoning.
    Runs a ReAct loop: Reason → Act → Observe → Reflect → Remember
    """
    
    def __init__(
        self,
        persona: Persona = None,
        skill_registry: SkillRegistry = None,
        llm_router: LLMRouter = None,
        memory: AgentMemory = None,
        max_iterations: int = 10
    ):
        self.persona = persona or PERSONA_TEMPLATES["assistant"]
        self.skill_registry = skill_registry or SKILL_REGISTRY
        self.llm = llm_router or LLM_ROUTER
        self.memory = memory or AgentMemory(self.persona.id)
        self.max_iterations = max_iterations
        self.is_deep_agent = False  # LangChain deep agent flag
        
        self.status = AgentStatus.IDLE
        self.current_task: Optional[AgentTask] = None
        self._on_thought: Optional[Callable] = None  # callback for streaming thoughts
        
        # Initialize working memory with persona system prompt
        self._init_system_prompt()
    
    def _init_system_prompt(self):
        """Set the system prompt in working memory."""
        sys_prompt = self.persona.to_system_prompt()
        sys_prompt += "\n\n## Available Skills\n"
        
        available_skills = self.skill_registry.list()
        filtered = [s for s in available_skills if s.name in (self.persona.skills or [s.name for s in available_skills])]
        
        for skill in filtered:
            sys_prompt += f"- **{skill.name}**: {skill.description}\n"
        
        self.memory.working.add_message("system", sys_prompt)
    
    def on_thought(self, callback: Callable):
        """Register callback for streaming thought steps."""
        self._on_thought = callback
        return self
    
    def _emit_thought(self, step: ThoughtStep):
        """Emit a thought step to callback if registered."""
        if self._on_thought:
            self._on_thought(step)
    
    def think(self, user_input: str) -> str:
        """
        Simple single-turn response without autonomous tool use.
        Good for conversation.
        """
        self.status = AgentStatus.THINKING
        
        # Add memory context if relevant
        context = self.memory.get_relevant_context(user_input)
        if context:
            self.memory.working.add_message("system", f"[Relevant Memory]\n{context}")
        
        # Add user message
        self.memory.working.add_message("user", user_input)
        
        # Get LLM response
        messages = self.memory.working.get_llm_messages()
        response = self.llm.complete(messages, temperature=self.persona.creativity)
        
        # Store response and remember
        self.memory.working.add_message("assistant", response.content)
        self.memory.remember_interaction(user_input, response.content)
        
        self.status = AgentStatus.IDLE
        return response.content
    
    def run(self, task: str, max_iterations: int = None) -> AgentTask:
        """
        Run an autonomous task using the ReAct loop.
        The agent plans, executes skills, observes results, and reflects.
        """
        max_iter = max_iterations or self.max_iterations
        
        agent_task = AgentTask(description=task, started_at=datetime.utcnow().isoformat())
        self.current_task = agent_task
        agent_task.status = "running"
        
        # Build available tools for this agent
        skill_names = self.persona.skills if self.persona.skills else None
        tools = self.skill_registry.get_openai_tools(skill_names)
        
        # Initial planning
        self.status = AgentStatus.THINKING
        
        planning_prompt = f"""I need to complete this task:

**Task**: {task}

Let me think step by step about how to approach this:
1. What is the goal?
2. What information or resources do I need?
3. Which of my skills are relevant?
4. What's my action plan?

I'll use my available tools to complete this task autonomously."""
        
        context = self.memory.get_relevant_context(task)
        if context:
            planning_prompt = f"[Relevant Memory]\n{context}\n\n{planning_prompt}"
        
        self.memory.working.add_message("user", f"Please complete this task autonomously: {task}")
        
        thought_step = ThoughtStep(
            step_type="thought",
            content=f"Starting task: {task}"
        )
        agent_task.add_step(thought_step)
        self._emit_thought(thought_step)
        
        # ReAct Loop
        iteration = 0
        skill_call_counts: dict = {}   # skill_name -> call count this task
        seen_calls: set = set()        # (skill_name, args_hash) already executed
        while iteration < max_iter:
            iteration += 1
            self.status = AgentStatus.THINKING
            
            messages = self.memory.working.get_llm_messages()
            
            try:
                response = self.llm.complete(
                    messages,
                    tools=tools if tools else None,
                    temperature=self.persona.creativity
                )
            except Exception as e:
                error_msg = f"LLM Error: {type(e).__name__}: {str(e)}"
                err_step = ThoughtStep(
                    step_type="observation",
                    content=error_msg
                )
                agent_task.add_step(err_step)
                self._emit_thought(err_step)
                agent_task.error = error_msg
                agent_task.status = "failed"
                agent_task.result = error_msg
                agent_task.completed_at = datetime.utcnow().isoformat()
                self.status = AgentStatus.ERROR
                return agent_task
            
            # Add assistant response to working memory.
            # When there are tool calls, we MUST store the assistant message with the
            # tool_calls array so OpenAI sees a valid: assistant(tool_calls) → tool → ...
            if response.has_tool_calls():
                openai_tool_calls = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"])
                        }
                    }
                    for tc in response.tool_calls
                ]
                self.memory.working.add_message(
                    "assistant",
                    response.content or "",
                    tool_calls=openai_tool_calls
                )
                # Emit any accompanying thought text
                if response.content:
                    thought_step = ThoughtStep(step_type="thought", content=response.content)
                    agent_task.add_step(thought_step)
                    self._emit_thought(thought_step)
            else:
                # No tool calls — store content normally
                if response.content:
                    self.memory.working.add_message("assistant", response.content)
                    thought_step = ThoughtStep(step_type="thought", content=response.content)
                    agent_task.add_step(thought_step)
                    self._emit_thought(thought_step)
            
            # Check for tool calls
            if response.has_tool_calls():
                self.status = AgentStatus.ACTING
                
                for tool_call in response.tool_calls:
                    skill_name = tool_call["name"]
                    skill_args = tool_call["arguments"]

                    # ── Deduplication guard ──────────────────────────────────
                    import hashlib, json as _json
                    args_key = hashlib.md5(
                        _json.dumps(skill_args, sort_keys=True).encode()
                    ).hexdigest()
                    call_sig = (skill_name, args_key)

                    skill_call_counts[skill_name] = skill_call_counts.get(skill_name, 0) + 1

                    if call_sig in seen_calls:
                        # Duplicate call — inject a fake observation and skip
                        dup_msg = (
                            f"[Already executed '{skill_name}' with these exact arguments. "
                            f"Use the previous result shown above to write your final answer.]"
                        )
                        self.memory.working.add_message("user", dup_msg)
                        obs_step = ThoughtStep(
                            step_type="observation",
                            content=dup_msg,
                            skill_used=skill_name
                        )
                        agent_task.add_step(obs_step)
                        self._emit_thought(obs_step)
                        continue

                    if skill_call_counts[skill_name] > 3:
                        # Too many calls to the same skill — halt it
                        limit_msg = (
                            f"['{skill_name}' has been called {skill_call_counts[skill_name]} times. "
                            f"No more calls to this skill are allowed. Synthesize from existing results.]"
                        )
                        self.memory.working.add_message("user", limit_msg)
                        obs_step = ThoughtStep(
                            step_type="observation",
                            content=limit_msg,
                            skill_used=skill_name
                        )
                        agent_task.add_step(obs_step)
                        self._emit_thought(obs_step)
                        continue

                    seen_calls.add(call_sig)
                    # ── End deduplication guard ──────────────────────────────
                    
                    action_step = ThoughtStep(
                        step_type="action",
                        content=f"Using skill: {skill_name}",
                        skill_used=skill_name,
                        skill_args=skill_args
                    )
                    self._emit_thought(action_step)
                    
                    # Execute skill
                    result: SkillResult = self.skill_registry.execute(skill_name, **skill_args)
                    result_text = result.to_text()
                    
                    # Track files created during task execution
                    if skill_name == "file_write" and result.success:
                        # Extract file path from the result message
                        # Message format: "✅ Successfully wrote X characters to path/to/file"
                        import re
                        match = re.search(r'wrote \d+ characters to (.+)$', str(result.output))
                        if match:
                            file_path = match.group(1).strip()
                            if "files_created" not in agent_task.metadata:
                                agent_task.metadata["files_created"] = []
                            agent_task.metadata["files_created"].append(file_path)
                    
                    action_step.skill_result = result_text
                    agent_task.add_step(action_step)
                    
                    obs_step = ThoughtStep(
                        step_type="observation",
                        content=result_text,
                        skill_used=skill_name
                    )
                    agent_task.add_step(obs_step)
                    self._emit_thought(obs_step)
                    
                    # Add tool result back to conversation
                    self.memory.working.add_message(
                        "tool",  
                        json.dumps({"tool": skill_name, "result": result_text}),
                        metadata={"tool_call_id": tool_call.get("id")}
                    )
                
                # After executing ALL tool calls in this turn, ask the agent
                # to synthesize — but ONLY if at least one tool actually ran.
                if any(s.step_type == "action" for s in agent_task.steps[-len(response.tool_calls)*3:]):
                    self.memory.working.add_message(
                        "user",
                        "Based on the tool results above, please provide a clear, comprehensive "
                        "final answer to the original task. "
                        "Do NOT call any more tools unless the information is genuinely missing."
                    )
                
                # Continue the loop to process tool results
                continue
            
            else:
                # No tool calls means the agent is done
                self.status = AgentStatus.REFLECTING
                
                # Reflection step
                reflection = ThoughtStep(
                    step_type="reflection",
                    content="Task complete. Storing experience in memory."
                )
                agent_task.add_step(reflection)
                self._emit_thought(reflection)
                
                # Store this experience in episodic memory
                self.memory.episodic.store(
                    content=f"Task: {task}\nOutcome: {response.content[:500]}",
                    summary=f"Completed task: {task[:100]}",
                    memory_type="episodic",
                    importance=0.7,
                    tags=["autonomous_task"]
                )
                
                agent_task.result = response.content
                agent_task.status = "completed"
                agent_task.completed_at = datetime.utcnow().isoformat()
                self.status = AgentStatus.IDLE
                return agent_task
        
        # Max iterations reached — try to compile a final answer from what was gathered
        # Collect all observation content seen so far
        observations = [
            step.content for step in agent_task.steps
            if step.step_type == "observation" and step.content
        ]
        if observations:
            # Ask the LLM to synthesize a final answer from all observations
            try:
                synth_messages = self.memory.working.get_llm_messages()
                synth_messages.append({
                    "role": "user",
                    "content": (
                        "You have now gathered enough information. "
                        "Please synthesize all the tool results above into a clear, well-formatted final answer. "
                        "Do NOT use any more tools."
                    )
                })
                synth_response = self.llm.complete(
                    synth_messages,
                    tools=None,  # No tools — force a text answer
                    temperature=self.persona.creativity
                )
                final_answer = synth_response.content
            except Exception:
                final_answer = "\n\n".join(observations[:5])
        else:
            final_answer = "I was unable to find sufficient information to complete this task."

        agent_task.status = "completed"
        agent_task.result = final_answer
        agent_task.completed_at = datetime.utcnow().isoformat()
        self.status = AgentStatus.IDLE
        return agent_task
    
    def learn(self, fact: str, topic: str = "user_provided", importance: float = 0.8):
        """Teach the agent a new fact or piece of knowledge."""
        return self.memory.knowledge.learn(fact, topic=topic, importance=importance)
    
    def remember(self, content: str, importance: float = 0.6, tags: List[str] = None):
        """Store something in episodic memory."""
        return self.memory.episodic.store(
            content=content, importance=importance, tags=tags or ["user_stored"]
        )
    
    def recall(self, query: str, limit: int = 5) -> List[str]:
        """Recall relevant memories."""
        memories = self.memory.episodic.recall(query, limit=limit)
        return [m.summary for m in memories]
    
    def update_persona(self, **kwargs):
        """Dynamically update the agent's persona."""
        self.persona.update(**kwargs)
        # Reinitialize system prompt
        self.memory.working.clear()
        self._init_system_prompt()
    
    def reset_session(self):
        """Clear working memory for a fresh conversation."""
        self.memory.working.clear()
        self._init_system_prompt()
        self.status = AgentStatus.IDLE
    
    @property
    def name(self) -> str:
        return self.persona.name
    
    @property
    def id(self) -> str:
        return self.persona.id
    
    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "role": self.persona.role,
            "status": self.status.value,
            "memory": self.memory.stats(),
            "skills": len(self.skill_registry.list()),
            "llm_providers": self.llm.available_providers()
        }
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "persona": self.persona.to_dict(),
            "status": self.status.value,
            "is_deep_agent": self.is_deep_agent,
            "memory_stats": self.memory.stats(),
            "available_skills": [s.name for s in self.skill_registry.list()]
        }


class AgentFactory:
    """Factory for creating and managing agents."""
    
    def __init__(self, skill_registry: SkillRegistry = None, llm_router: LLMRouter = None):
        self.skill_registry = skill_registry or SKILL_REGISTRY
        self.llm_router = llm_router or LLM_ROUTER
        self._agents: Dict[str, Agent] = {}
    
    def create_from_template(self, template_name: str) -> Agent:
        """Create an agent from a built-in persona template."""
        if template_name not in PERSONA_TEMPLATES:
            raise ValueError(f"Unknown template '{template_name}'. Available: {list(PERSONA_TEMPLATES.keys())}")
        
        persona = PERSONA_TEMPLATES[template_name]
        # Clone to avoid sharing state
        persona = Persona.from_dict(persona.to_dict())
        
        agent = Agent(
            persona=persona,
            skill_registry=self.skill_registry,
            llm_router=self.llm_router
        )
        self._agents[agent.id] = agent
        return agent
    
    def create_from_persona(self, persona: Persona) -> Agent:
        """Create an agent from a custom persona."""
        agent = Agent(
            persona=persona,
            skill_registry=self.skill_registry,
            llm_router=self.llm_router
        )
        self._agents[agent.id] = agent
        return agent
    
    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)
    
    def list(self) -> List[Agent]:
        return list(self._agents.values())
    
    def delete(self, agent_id: str):
        if agent_id in self._agents:
            del self._agents[agent_id]


# Global factory
AGENT_FACTORY = AgentFactory()
