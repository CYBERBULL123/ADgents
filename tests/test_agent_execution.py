import threading
import time
from concurrent.futures import ThreadPoolExecutor

from core.agent import Agent


def test_think_calls_for_one_agent_are_serialized():
    agent = Agent.__new__(Agent)
    agent._execution_lock = threading.RLock()
    active_calls = 0
    maximum_active_calls = 0
    state_lock = threading.Lock()

    def fake_think(user_input):
        nonlocal active_calls, maximum_active_calls
        with state_lock:
            active_calls += 1
            maximum_active_calls = max(maximum_active_calls, active_calls)
        time.sleep(0.03)
        with state_lock:
            active_calls -= 1
        return user_input

    agent._think = fake_think
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(agent.think, ["first", "second"]))

    assert results == ["first", "second"]
    assert maximum_active_calls == 1


def test_run_uses_and_restores_per_run_thought_callback():
    agent = Agent.__new__(Agent)
    agent._execution_lock = threading.RLock()
    previous_callback = lambda step: None
    task_callback = lambda step: None
    observed_callbacks = []
    agent._on_thought = previous_callback

    def fake_run(task, max_iterations, pod_id):
        observed_callbacks.append(agent._on_thought)
        return task

    agent._run = fake_run
    result = agent.run("test", on_thought=task_callback)

    assert result == "test"
    assert observed_callbacks == [task_callback]
    assert agent._on_thought is previous_callback