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
    
    def run(self, task: str, max_iterations: int = None, pod_id: str = None) -> AgentTask:
        """
        Run an autonomous task using the ReAct loop with trace logging and self-healing.
        """
        import uuid
        from datetime import datetime
        from .trace_db import (
            create_pod, create_trace, create_span, update_span, update_pod, get_pod, update_trace
        )
        from .sre_supervisor import SRE_SUPERVISOR

        max_iter = max_iterations or self.max_iterations
        
        # 1. Initialize Pod and Trace
        self.pod_id = pod_id or self.pod_id or f"pod_{str(uuid.uuid4())[:8]}"
        self.trace_id = self.pod_id
        
        pod_entry = get_pod(self.pod_id)
        if not pod_entry:
            create_pod(self.pod_id, self.name, self.id, task)
        else:
            update_pod(self.pod_id, status="running", task_text=task)
            
        create_trace(self.trace_id, self.pod_id, f"Run: {task[:50]}")

        agent_task = AgentTask(id=self.trace_id, description=task, started_at=datetime.utcnow().isoformat())
        self.current_task = agent_task
        agent_task.status = "running"
        
        # Build available tools for this agent
        skill_names = list(self.persona.skills) if self.persona.skills else None
        if skill_names is not None:
            # Dynamically make all connected integrations tools available
            active_integration_skills = self.skill_registry.list(category="integration")
            for s in active_integration_skills:
                if s.name not in skill_names:
                    skill_names.append(s.name)
        
        tools = self.skill_registry.get_openai_tools(skill_names)
        
        # Initial planning
        self.status = AgentStatus.THINKING
        
        from .plugin_db import get_plugin_context_string
        plugin_context = get_plugin_context_string()
        
        planning_prompt = f"""I need to complete this task:
 
**Task**: {task}
 
I'll use my available tools to complete this task autonomously."""
        
        if plugin_context:
            planning_prompt = f"{plugin_context}\n\n{planning_prompt}"
            
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
        
        # Root run span
        root_span_id = f"span_{str(uuid.uuid4())[:8]}"
        create_span(root_span_id, self.trace_id, "Master Task Execution", "thought", input_data={"task": task})

        # ReAct Loop
        iteration = 0
        skill_call_counts: dict = {}   # skill_name -> call count this task
        seen_calls: set = set()        # (skill_name, args_hash) already executed
        
        total_tokens = 0
        total_cost = 0.0

        while iteration < max_iter:
            # Check Pod status for suspension or stop signal
            pod_state = get_pod(self.pod_id)
            if pod_state:
                status_val = pod_state.get("status")
                if status_val == "suspended":
                    # Loop and wait until resumed or stopped
                    self._emit_thought(ThoughtStep(step_type="thought", content=f"[Agent OS] Pod execution suspended. Pausing ReAct loop..."))
                    while True:
                        import time
                        time.sleep(1)
                        pod_check = get_pod(self.pod_id)
                        if not pod_check or pod_check.get("status") != "suspended":
                            break
                    
                    # Recheck status after resuming
                    pod_state = get_pod(self.pod_id)
                    if pod_state and pod_state.get("status") in ("stopped", "failed"):
                        self._emit_thought(ThoughtStep(step_type="thought", content=f"[Agent OS] Pod execution terminated by operator."))
                        update_pod(self.pod_id, status="failed")
                        update_trace(self.trace_id, status="failed", completed_at=datetime.utcnow().isoformat())
                        update_span(root_span_id, status="error", error="Execution terminated by operator", completed_at=datetime.utcnow().isoformat())
                        agent_task.status = "failed"
                        agent_task.error = "Execution terminated by operator"
                        agent_task.completed_at = datetime.utcnow().isoformat()
                        self.status = AgentStatus.ERROR
                        return agent_task
                    self._emit_thought(ThoughtStep(step_type="thought", content=f"[Agent OS] Resuming pod execution..."))
                
                elif status_val in ("stopped", "failed"):
                    self._emit_thought(ThoughtStep(step_type="thought", content=f"[Agent OS] Pod execution terminated by operator."))
                    update_pod(self.pod_id, status="failed")
                    update_trace(self.trace_id, status="failed", completed_at=datetime.utcnow().isoformat())
                    update_span(root_span_id, status="error", error="Execution terminated by operator", completed_at=datetime.utcnow().isoformat())
                    agent_task.status = "failed"
                    agent_task.error = "Execution terminated by operator"
                    agent_task.completed_at = datetime.utcnow().isoformat()
                    self.status = AgentStatus.ERROR
                    return agent_task

            iteration += 1
            self.status = AgentStatus.THINKING
            
            iter_span_id = f"span_{str(uuid.uuid4())[:8]}"
            create_span(iter_span_id, self.trace_id, f"Iteration {iteration}", "thought", parent_span_id=root_span_id)
            
            messages = self.memory.working.get_llm_messages()
            
            # Trace LLM request
            llm_span_id = f"span_{str(uuid.uuid4())[:8]}"
            create_span(llm_span_id, self.trace_id, f"LLM Completion Run {iteration}", "llm", parent_span_id=iter_span_id, input_data={"messages_count": len(messages)})
            
            try:
                response = self.llm.complete(
                    messages,
                    tools=tools if tools else None,
                    temperature=self.persona.creativity
                )
                
                # Update tokens and cost
                tokens_in = response.input_tokens or 0
                tokens_out = response.output_tokens or 0
                total_tokens += (tokens_in + tokens_out)
                
                # Simple cost calculation
                cost = (tokens_in * 0.00000015) + (tokens_out * 0.00000060)
                total_cost += cost
                
                update_span(
                    llm_span_id, 
                    status="success", 
                    output={"content": response.content, "tool_calls": response.tool_calls},
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    cost=cost,
                    completed_at=datetime.utcnow().isoformat()
                )
                
                # Update pod and trace with stats
                update_pod(self.pod_id, tokens_used=total_tokens, cost=total_cost)
                update_trace(self.trace_id, total_tokens=total_tokens, total_cost=total_cost)
                
            except Exception as e:
                error_msg = f"LLM Error: {type(e).__name__}: {str(e)}"
                update_span(llm_span_id, status="error", error=error_msg, completed_at=datetime.utcnow().isoformat())
                update_span(iter_span_id, status="error", error=error_msg, completed_at=datetime.utcnow().isoformat())
                
                # SRE Intercept for LLM failure
                self._emit_thought(ThoughtStep(step_type="thought", content=f"[SRE Kernel Intercept] LLM call failed. Triggering diagnosis..."))
                update_pod(self.pod_id, status="healing")
                heal_result = SRE_SUPERVISOR.diagnose_and_heal(self.pod_id, llm_span_id, error_msg, self)
                
                if heal_result["applied"] and heal_result["patch_type"] == "memory_append":
                    # SRE injected diagnosis instruction, try to loop again
                    iteration -= 1  # retry this iteration
                    continue
                
                # If SRE couldn't heal, fail task
                err_step = ThoughtStep(step_type="observation", content=error_msg)
                agent_task.add_step(err_step)
                self._emit_thought(err_step)
                agent_task.error = error_msg
                agent_task.status = "failed"
                agent_task.result = error_msg
                agent_task.completed_at = datetime.utcnow().isoformat()
                self.status = AgentStatus.ERROR
                update_pod(self.pod_id, status="failed")
                update_trace(self.trace_id, status="failed", completed_at=datetime.utcnow().isoformat())
                update_span(root_span_id, status="error", error=error_msg, completed_at=datetime.utcnow().isoformat())
                return agent_task
            
            # Process response and store
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
                if response.content:
                    thought_step = ThoughtStep(step_type="thought", content=response.content)
                    agent_task.add_step(thought_step)
                    self._emit_thought(thought_step)
            else:
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

                    tool_span_id = f"span_{str(uuid.uuid4())[:8]}"
                    create_span(
                        tool_span_id, self.trace_id, f"Skill Execute: {skill_name}", "action", 
                        parent_span_id=iter_span_id, input_data=skill_args
                    )

                    # Deduplication guard
                    import hashlib
                    args_key = hashlib.md5(
                        json.dumps(skill_args, sort_keys=True).encode()
                    ).hexdigest()
                    call_sig = (skill_name, args_key)

                    skill_call_counts[skill_name] = skill_call_counts.get(skill_name, 0) + 1

                    # Check for repetitiveness
                    if call_sig in seen_calls or skill_call_counts[skill_name] > 3:
                        dup_error = f"Loop Detected: Skill '{skill_name}' called repetitively or exceeded safe iteration counts."
                        update_span(tool_span_id, status="error", error=dup_error, completed_at=datetime.utcnow().isoformat())
                        
                        # Trigger SRE Self-Healing
                        self._emit_thought(ThoughtStep(step_type="thought", content=f"[SRE Kernel Intercept] Loop / high repetition detected on '{skill_name}'. Initiating healing..."))
                        update_pod(self.pod_id, status="healing")
                        heal_result = SRE_SUPERVISOR.diagnose_and_heal(self.pod_id, tool_span_id, dup_error, self)
                        
                        obs_content = f"[SRE Kernel Injected Correction]\n"
                        if heal_result["applied"]:
                            obs_content += f"Diagnosis: {heal_result['diagnosis']}\nInstruction: {heal_result['patch_content']}"
                        else:
                            obs_content += f"SRE could not heal this loop automatically. Please break the cycle."
                            
                        self.memory.working.add_message("user", obs_content)
                        obs_step = ThoughtStep(
                            step_type="observation",
                            content=obs_content,
                            skill_used=skill_name
                        )
                        agent_task.add_step(obs_step)
                        self._emit_thought(obs_step)
                        continue

                    seen_calls.add(call_sig)
                    
                    action_step = ThoughtStep(
                        step_type="action",
                        content=f"Using skill: {skill_name}",
                        skill_used=skill_name,
                        skill_args=skill_args
                    )
                    self._emit_thought(action_step)
                    
                    # Execute skill
                    result = self.skill_registry.execute(skill_name, **skill_args)
                    result_text = result.to_text()
                    
                    if not result.success:
                        # Intercept error and run SRE Self-Healing
                        update_span(tool_span_id, status="error", error=result.error, completed_at=datetime.utcnow().isoformat())
                        self._emit_thought(ThoughtStep(step_type="thought", content=f"[SRE Kernel Intercept] Skill '{skill_name}' execution failed. Running SRE diagnosis..."))
                        update_pod(self.pod_id, status="healing")
                        
                        heal_result = SRE_SUPERVISOR.diagnose_and_heal(self.pod_id, tool_span_id, result.error, self)
                        
                        # Handle parameter overrides
                        if heal_result["applied"] and heal_result["patch_type"] == "param_override":
                            try:
                                override_args = json.loads(heal_result["patch_content"])
                                self._emit_thought(ThoughtStep(step_type="thought", content=f"[SRE Kernel] Retrying '{skill_name}' with overridden parameters: {override_args}"))
                                retry_result = self.skill_registry.execute(skill_name, **override_args)
                                if retry_result.success:
                                    update_span(
                                        tool_span_id, status="success", output=retry_result.to_text(), 
                                        error=None, completed_at=datetime.utcnow().isoformat()
                                    )
                                    result = retry_result
                                    result_text = retry_result.to_text()
                                else:
                                    result_text = retry_result.to_text()
                            except Exception as parse_err:
                                result_text = f"SRE override failed: {parse_err}\nOriginal Error: {result.error}"
                        else:
                            # SRE memory correction applied. Adjust result text to feed back to the ReAct loop
                            result_text = (
                                f"❌ Skill Failed: {result.error}\n"
                                f"[SRE Kernel Diagnostic]: {heal_result['diagnosis']}\n"
                                f"[SRE Correction Injected]: {heal_result['patch_content']}"
                            )
                    else:
                        update_span(tool_span_id, status="success", output=result_text, completed_at=datetime.utcnow().isoformat())
                    
                    # Track files created
                    if skill_name == "file_write" and result.success:
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
                
                # Request synthesis
                if any(s.step_type == "action" for s in agent_task.steps[-len(response.tool_calls)*3:]):
                    self.memory.working.add_message(
                        "user",
                        "Based on the tool results above, please provide a clear, comprehensive "
                        "final answer to the original task. "
                        "Do NOT call any more tools unless the information is genuinely missing."
                    )
                
                update_span(iter_span_id, status="success", completed_at=datetime.utcnow().isoformat())
                continue
            
            else:
                # Task finished successfully
                self.status = AgentStatus.REFLECTING
                
                reflection = ThoughtStep(
                    step_type="reflection",
                    content="Task complete. Storing experience in memory."
                )
                agent_task.add_step(reflection)
                self._emit_thought(reflection)
                
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
                
                # Complete Pod, Trace, Spans
                update_pod(self.pod_id, status="completed")
                update_trace(self.trace_id, status="completed", completed_at=datetime.utcnow().isoformat())
                update_span(iter_span_id, status="success", completed_at=datetime.utcnow().isoformat())
                update_span(root_span_id, status="success", completed_at=datetime.utcnow().isoformat())
                return agent_task
        
        # Max iterations reached
        final_answer = "I was unable to complete the task within the maximum iteration limit."
        agent_task.status = "completed"
        agent_task.result = final_answer
        agent_task.completed_at = datetime.utcnow().isoformat()
        self.status = AgentStatus.IDLE
        
        update_pod(self.pod_id, status="completed")
        update_trace(self.trace_id, status="completed", completed_at=datetime.utcnow().isoformat())
        update_span(root_span_id, status="success", completed_at=datetime.utcnow().isoformat())
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
        # Count only skills assigned to this agent, not all available skills
        all_skills = self.skill_registry.list()
        assigned_skills = self.persona.skills or [s.name for s in all_skills]
        assigned_count = len([s.name for s in all_skills if s.name in assigned_skills])
        
        return {
            "name": self.name,
            "id": self.id,
            "role": self.persona.role,
            "status": self.status.value,
            "memory": self.memory.stats(),
            "skills": assigned_count,
            "llm_providers": self.llm.available_providers()
        }
    
    def to_dict(self) -> Dict:
        # Return only skills assigned to this agent, not all available skills
        all_skills = self.skill_registry.list()
        assigned_skills = self.persona.skills or [s.name for s in all_skills]
        assigned_skill_names = [s.name for s in all_skills if s.name in assigned_skills]
        
        return {
            "id": self.id,
            "name": self.name,
            "persona": self.persona.to_dict(),
            "status": self.status.value,
            "memory_stats": self.memory.stats(),
            "available_skills": assigned_skill_names
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
