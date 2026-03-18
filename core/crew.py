"""
ADgents Crew System — Multi-Agent Collaboration
Agents collaborate on complex tasks, each contributing their specialisation.
An Orchestrator decomposes the master task and routes sub-tasks to the right agents.
"""
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CrewStatus(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    SYNTHESISING = "synthesising"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SubTask:
    """A sub-task assigned to a specific agent within a crew run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    description: str = ""
    reason: str = ""          # Why this agent was chosen
    status: str = "pending"   # pending | running | done | failed
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "agent_id": self.agent_id,
            "agent_name": self.agent_name, "description": self.description,
            "reason": self.reason, "status": self.status,
            "result": self.result, "error": self.error,
            "started_at": self.started_at, "completed_at": self.completed_at,
        }


@dataclass
class CrewRun:
    """A single collaborative run of a Crew."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    crew_id: str = ""
    task: str = ""
    status: str = "pending"
    sub_tasks: List[SubTask] = field(default_factory=list)
    plan: str = ""                 # Orchestrator's plan text
    final_answer: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "crew_id": self.crew_id, "task": self.task,
            "status": self.status, "plan": self.plan,
            "sub_tasks": [s.to_dict() for s in self.sub_tasks],
            "final_answer": self.final_answer, "error": self.error,
            "started_at": self.started_at, "completed_at": self.completed_at,
        }


class Crew:
    """
    A Crew is a named group of specialised agents that collaborate on tasks.
    
    Usage:
        crew = Crew("Research Crew", [researcher_agent, engineer_agent, analyst_agent])
        run = crew.run("Analyse the state of AI frameworks in 2025")
        print(run.final_answer)
    """

    def __init__(
        self,
        name: str,
        agents: list,           # List[Agent] — avoid circular import
        llm_router=None,
        max_sub_tasks: int = 6,
        on_update: Optional[Callable] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.agents = agents
        self.max_sub_tasks = max_sub_tasks
        self._on_update = on_update  # streaming callback
        self.status = CrewStatus.IDLE
        self.runs: List[CrewRun] = []

        # Use the LLM from the first agent if not provided
        if llm_router is None and agents:
            self.llm = agents[0].llm
        else:
            self.llm = llm_router

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _agent_roster(self) -> str:
        lines = []
        for agent in self.agents:
            skills = ", ".join(getattr(agent.persona, "skills", []) or [])
            domains = ", ".join(getattr(agent.persona, "expertise_domains", []) or [])
            lines.append(
                f"- **{agent.persona.name}** (ID: {agent.persona.id})\n"
                f"  Role: {agent.persona.role}\n"
                f"  Expertise: {domains or 'general'}\n"
                f"  Skills: {skills or 'no special tools'}"
            )
        return "\n".join(lines)

    def _emit(self, event: str, data: Any):
        if self._on_update:
            self._on_update(event, data)

    # ── Orchestrator — planning step ─────────────────────────────────────────

    def _plan(self, task: str) -> List[Dict]:
        """
        Ask the LLM to decompose the task into sub-tasks and assign each to
        the most appropriate agent. Returns a list of dicts:
            [{"agent_id": ..., "agent_name": ..., "description": ..., "reason": ...}, ...]
        """
        roster = self._agent_roster()
        planning_prompt = f"""You are an expert Orchestrator managing a crew of AI agents.

## Master Task
{task}

## Available Agents
{roster}

## Your Job
Decompose the master task into up to {self.max_sub_tasks} coherent sub-tasks.
For each sub-task, assign it to the most suitable agent from the crew.

Return ONLY valid JSON — an array of objects with exactly these keys:
- "agent_id": the agent's persona ID
- "agent_name": the agent's name
- "description": a clear self-contained sub-task description
- "reason": one sentence explaining why this agent is best for this sub-task

Important:
- Each sub-task must be completable independently.
- Spread work according to specialisation, don't assign everything to one agent.
- Keep descriptions specific enough for autonomous execution.
"""
        messages = [
            {"role": "system", "content": "You are an expert task orchestrator. Output only valid JSON arrays."},
            {"role": "user", "content": planning_prompt}
        ]

        try:
            response = self.llm.complete(messages, temperature=0.3)
            content = response.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            plan_data = json.loads(content.strip())
            if not isinstance(plan_data, list):
                raise ValueError("Expected a JSON array")
            return plan_data
        except Exception as e:
            # Fallback: assign all to first agent
            return [{
                "agent_id": self.agents[0].persona.id,
                "agent_name": self.agents[0].persona.name,
                "description": task,
                "reason": f"Orchestration planning failed ({e}). Falling back to single agent."
            }]

    # ── Orchestrator — synthesis step ────────────────────────────────────────

    def _synthesise(self, task: str, sub_tasks: List[SubTask]) -> str:
        """Ask the LLM to synthesise all sub-task results into a final answer."""
        results_text = ""
        for st in sub_tasks:
            results_text += f"\n### {st.agent_name} — {st.description}\n"
            if st.status == "done":
                results_text += st.result or "(no output)"
            else:
                results_text += f"⚠️ Failed: {st.error}"
            results_text += "\n"

        messages = [
            {"role": "system", "content": "You are a senior analyst synthesising work from a team of specialist AI agents."},
            {"role": "user", "content": (
                f"## Original Task\n{task}\n\n"
                f"## Team Results\n{results_text}\n\n"
                f"## Your Job\n"
                f"Synthesise all the above results into one clear, well-structured final answer. "
                f"Give credit to which agent contributed which insight. "
                f"Be comprehensive and directly address the original task."
            )}
        ]

        response = self.llm.complete(messages, temperature=0.5)
        return response.content

    # ── Public API ───────────────────────────────────────────────────────────

    def run(self, task: str) -> "CrewRun":
        """
        Execute a collaborative task across all crew agents.
        Returns a CrewRun with the final synthesised answer.
        """
        crew_run = CrewRun(
            crew_id=self.id,
            task=task,
            started_at=datetime.utcnow().isoformat()
        )
        self.runs.append(crew_run)
        self.status = CrewStatus.PLANNING
        crew_run.status = "planning"

        self._emit("status", {"phase": "planning", "message": "Orchestrator is decomposing the task..."})

        # Step 1: Plan
        try:
            plan_data = self._plan(task)
        except Exception as e:
            crew_run.status = "failed"
            crew_run.error = str(e)
            crew_run.completed_at = datetime.utcnow().isoformat()
            self.status = CrewStatus.FAILED
            return crew_run

        # Build sub-tasks
        agent_map = {a.persona.id: a for a in self.agents}
        sub_tasks = []
        for item in plan_data:
            st = SubTask(
                agent_id=item.get("agent_id", ""),
                agent_name=item.get("agent_name", ""),
                description=item.get("description", ""),
                reason=item.get("reason", ""),
            )
            sub_tasks.append(st)
            crew_run.sub_tasks.append(st)

        crew_run.plan = json.dumps(plan_data, indent=2)
        crew_run.status = "running"
        self.status = CrewStatus.RUNNING

        self._emit("plan", {"sub_tasks": [s.to_dict() for s in sub_tasks]})

        # Step 2: Execute each sub-task
        for st in sub_tasks:
            agent = agent_map.get(st.agent_id)
            if not agent:
                # Try by name fallback
                agent = next((a for a in self.agents if a.persona.name == st.agent_name), None)
            if not agent:
                # Last resort: first agent
                agent = self.agents[0]
                st.agent_id = agent.persona.id
                st.agent_name = agent.persona.name

            st.status = "running"
            st.started_at = datetime.utcnow().isoformat()
            self._emit("sub_task_start", st.to_dict())

            try:
                task_result = agent.run(st.description)
                st.result = task_result.result or ""
                st.status = "done" if task_result.status == "completed" else "failed"
                if task_result.status != "completed":
                    st.error = task_result.error
            except Exception as e:
                st.status = "failed"
                st.error = str(e)

            st.completed_at = datetime.utcnow().isoformat()
            self._emit("sub_task_done", st.to_dict())

        # Step 3: Synthesise
        self.status = CrewStatus.SYNTHESISING
        crew_run.status = "synthesising"
        self._emit("status", {"phase": "synthesising", "message": "Orchestrator is synthesising results..."})

        try:
            crew_run.final_answer = self._synthesise(task, sub_tasks)
            crew_run.status = "done"
            self.status = CrewStatus.DONE
        except Exception as e:
            crew_run.status = "failed"
            crew_run.error = f"Synthesis failed: {e}"
            self.status = CrewStatus.FAILED

        crew_run.completed_at = datetime.utcnow().isoformat()
        self._emit("done", crew_run.to_dict())
        return crew_run

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "agents": [
                {"id": a.persona.id, "name": a.persona.name, "role": a.persona.role, "avatar": a.persona.avatar}
                for a in self.agents
            ],
            "run_count": len(self.runs),
        }
