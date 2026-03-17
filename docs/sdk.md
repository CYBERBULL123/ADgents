# Python SDK

Embed ADgents dynamically into any application via our `ADgents` standard client setup found under `sdk/python/adgents.py`.

## Installation

Ensure you have ADgents cloned and added to the absolute path of your local Python runtime.

## Instantiating

```python
from sdk.python.adgents import ADgents

# The system uses environment variables for standard routing
sdk = ADgents()
```

## Basic Workflows
`ADgents.create_agent` takes either a configured dict payload of a custom persona or one of our 5 out-of-the-box template labels.

```python
researcher = sdk.create_agent(template="researcher")

# Straightforward conversational loop (with memory context):
response = researcher.chat("What are the latest AI trends this quarter?")
print(response)

# Enforce semantic memory rules explicitly:
researcher.learn("Anthropic launched Claude 3.5 Sonnet recently and it's our target.")
```

## Task Execution & Polling
You can run an automated multi-step block natively in your threads. The result holds the execution summary along with full trace steps.
```python
task_result = researcher.run_task("Investigate Sonnet's context windows compared to Gemini 1.5.")

print(f"Task status: {task_result.status}")
print(f"Task outcome: {task_result.result}")

# Review the intermediate thoughts of the agent:
for thought in task_result.steps:
    print(thought)
```

## Integrating into Langchain / CrewAI
Given that each Agent object maintains its own self-enclosed ReAct pipeline, you may easily abstract it as a standard standard worker within standard Langchain flows, provided you bridge the `run_task` output into the parent orchestrator chain.
