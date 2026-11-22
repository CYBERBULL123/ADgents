import threading

from core import trace_db
from core.agent import Agent, AgentStatus
from core.persona import Persona
from core.sre_supervisor import SRE_SUPERVISOR


class EmptySkillRegistry:
    def list(self, category=None):
        return []

    def get_openai_tools(self, skill_names=None):
        return []


class EmptyWorkingMemory:
    def add_message(self, *args, **kwargs):
        pass

    def get_llm_messages(self):
        return []


class EmptyMemory:
    def __init__(self):
        self.working = EmptyWorkingMemory()

    def get_relevant_context(self, query):
        return ""


class FailingLLM:
    def complete(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


def test_sre_prompt_retry_consumes_max_iteration(monkeypatch):
    for name in ("create_pod", "create_trace", "create_span", "update_span", "update_pod", "update_trace"):
        monkeypatch.setattr(trace_db, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(trace_db, "get_pod", lambda pod_id: None)

    diagnoses = []

    def keep_applying_corrections(*args, **kwargs):
        diagnoses.append(True)
        return {"applied": True, "patch_type": "memory_append", "diagnosis": "Retry safely."}

    monkeypatch.setattr(SRE_SUPERVISOR, "diagnose_and_heal", keep_applying_corrections)

    agent = Agent.__new__(Agent)
    agent.persona = Persona(id="retry-test", name="Retry Test", skills=[], agent_skills=[])
    agent.skill_registry = EmptySkillRegistry()
    agent.llm = FailingLLM()
    agent.memory = EmptyMemory()
    agent.max_iterations = 2
    agent.pod_id = None
    agent.trace_id = None
    agent.status = AgentStatus.IDLE
    agent.current_task = None
    agent._on_thought = None
    agent._execution_lock = threading.RLock()

    task = agent.run("test retry bound", max_iterations=2)

    assert task.status == "failed"
    assert len(diagnoses) == 2