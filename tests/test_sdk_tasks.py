from sdk.python.adgents import ADgents, Agent


class PollingClient:
    def __init__(self):
        self.started = []
        self.polls = 0

    def _post(self, path, body):
        self.started.append((path, body))
        return {"task_id": "task-123"}

    def _get(self, path):
        assert path == "/tasks/task-123"
        self.polls += 1
        if self.polls == 1:
            return {"status": "running"}
        return {
            "id": "task-123",
            "task_text": "do the work",
            "status": "completed",
            "steps": [{"step_type": "thought", "content": "done"}],
            "result": "Finished",
            "error": None,
        }


def test_run_task_polls_started_task_without_sending_duplicate_chat():
    client = PollingClient()
    agent = Agent({"persona": {"id": "agent-1", "name": "Test Agent"}}, client)

    result = agent.run_task("do the work", poll_interval=0)

    assert client.started == [("/tasks", {"agent_id": "agent-1", "task": "do the work"})]
    assert client.polls == 2
    assert result.id == "task-123"
    assert result.status == "completed"
    assert result.result == "Finished"
    assert result.steps[0]["content"] == "done"


def test_sdk_sends_configured_bearer_token():
    client = ADgents(api_token="sdk-token")

    assert client._client.headers["authorization"] == "Bearer sdk-token"
    client.close()