"""
ADgents ADK (Agent Development Kit) Adapter
Wraps any ADgents Agent in a Google ADK-compatible interface.
Lets you run ADgents agents inside Google's Agent runner.

Usage:
    from core.adk_adapter import ADKAgent
    from core.agent import AGENT_FACTORY

    agent = AGENT_FACTORY.create_from_template("researcher")
    adk_agent = ADKAgent(agent)

    # Use in an ADK pipeline
    response = adk_agent.generate_content("Research AI trends in 2025")
"""
from typing import Any, Dict, List, Optional


class ADKMessage:
    """Minimal ADK-compatible message object."""

    def __init__(self, text: str, role: str = "model"):
        self.text = text
        self.role = role
        self.parts = [{"text": text}]

    def __repr__(self):
        return f"ADKMessage(role={self.role!r}, text={self.text[:60]!r}...)"


class ADKAgent:
    """
    Wraps an ADgents Agent to expose a Google ADK-compatible interface.
    This lets you plug any ADgents agent into ADK pipelines, runners,
    or evaluation harnesses.

    ADK-compatible methods exposed:
    - generate_content(prompt) → ADKMessage
    - run_async(prompt) → ADKMessage
    - name / description properties
    """

    def __init__(self, agent):
        """
        Args:
            agent: An ADgents `Agent` instance.
        """
        self._agent = agent

    # ── ADK identity properties ──────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._agent.persona.name

    @property
    def description(self) -> str:
        return f"{self._agent.persona.role}. {self._agent.persona.backstory[:200]}"

    @property
    def model(self) -> str:
        """Return the active LLM provider name."""
        providers = self._agent.llm.available_providers()
        return providers[0] if providers else "mock"

    # ── ADK content generation interface ────────────────────────────────────

    def generate_content(self, prompt: str, **kwargs) -> ADKMessage:
        """
        Synchronous ADK-compatible generation.
        Maps to ADgents think() for conversation-style prompts,
        or run() for task-style prompts (detected by keywords).
        """
        task_keywords = ["research", "analyse", "find", "write", "build", "create",
                         "search", "calculate", "generate", "summarise", "extract"]
        is_task = any(kw in prompt.lower() for kw in task_keywords)

        if is_task:
            result = self._agent.run(prompt)
            text = result.result or result.error or "(no output)"
        else:
            text = self._agent.think(prompt)

        return ADKMessage(text=text, role="model")

    async def run_async(self, prompt: str, **kwargs) -> ADKMessage:
        """Async ADK-compatible generation (runs sync in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.generate_content, prompt)
        return result

    # ── ADK tool declaration ─────────────────────────────────────────────────

    def as_tool(self) -> Dict:
        """
        Returns an OpenAI / ADK compatible tool definition so other agents
        can delegate to this agent as a tool.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name.lower().replace(" ", "_"),
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": f"The task or question for {self.name}"
                        }
                    },
                    "required": ["task"]
                }
            }
        }

    # ── ADK evaluation helpers ───────────────────────────────────────────────

    def get_metadata(self) -> Dict:
        return {
            "name": self.name,
            "role": self._agent.persona.role,
            "avatar": self._agent.persona.avatar,
            "autonomy_level": self._agent.persona.autonomy_level,
            "expertise": self._agent.persona.expertise_domains,
            "skills": self._agent.persona.skills,
            "llm_providers": self._agent.llm.available_providers(),
        }

    def __repr__(self):
        return f"ADKAgent(name={self.name!r}, role={self._agent.persona.role!r})"


def wrap_crew_as_adk_agent(crew) -> "ADKCrewAgent":
    """Convenience function to wrap an entire Crew as a single ADK agent."""
    return ADKCrewAgent(crew)


class ADKCrewAgent:
    """Wraps a Crew as a single ADK-compatible agent interface."""

    def __init__(self, crew):
        self._crew = crew

    @property
    def name(self) -> str:
        return self._crew.name

    @property
    def description(self) -> str:
        members = ", ".join(a.persona.name for a in self._crew.agents)
        return f"A crew of specialist agents: {members}. Collaboratively solves complex tasks."

    def generate_content(self, prompt: str, **kwargs) -> ADKMessage:
        run = self._crew.run(prompt)
        text = run.final_answer or run.error or "(no output)"
        return ADKMessage(text=text, role="model")

    async def run_async(self, prompt: str, **kwargs) -> ADKMessage:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_content, prompt)

    def __repr__(self):
        return f"ADKCrewAgent(name={self.name!r}, agents={len(self._crew.agents)})"
