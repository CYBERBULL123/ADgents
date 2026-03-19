# Google ADK Integration Guide

This document explains how to use the Google ADK (Agent Development Kit) integration with ADgents.

## Overview

The Google ADK is a flexible framework for developing and deploying AI agents. ADgents now provides full integration with Google ADK, enabling:

- **LLM Agents** - Single agents powered by Gemini, Claude, or other models
- **Workflow Agents** - Sequential, Parallel, and Loop agents for complex workflows
- **Multi-Agent Systems** - Multiple coordinated agents working together
- **Tool Integration** - Register ADgents skills as ADK tools
- **Deployment** - Deploy to Vertex AI Agent Engine, Cloud Run, or GKE

## Installation

### 1. Install Google ADK

```bash
pip install google-adk
```

### 2. Set API Keys

Export your API key:

```bash
export GOOGLE_API_KEY="your_api_key_here"
```

Or set it in `.env`:

```
GOOGLE_API_KEY=your_api_key_here
```

## API Endpoints

### Create Agents

#### Create LLM Agent

```bash
POST /api/google-adk/create-agent
Content-Type: application/json

{
  "name": "Research Assistant"
}
```

Response:
```json
{
  "success": true,
  "agent_id": "research_assistant",
  "agent_info": {
    "name": "research_assistant",
    "model": "gemini-2.0-flash",
    "tools_count": 0,
    "status": "initialized"
  }
}
```

### Workflow Agents

#### Create Sequential Workflow

Agents execute in order, passing output to the next agent:

```bash
POST /api/google-adk/create-sequential-workflow
Content-Type: application/json

{
  "name": "research_pipeline",
  "agents": ["researcher", "analyst", "writer"]
}
```

#### Create Parallel Workflow

Agents execute simultaneously:

```bash
POST /api/google-adk/create-parallel-workflow
Content-Type: application/json

{
  "name": "multi_analysis",
  "agents": ["sentiment_analyzer", "topic_classifier", "summary_agent"]
}
```

#### Create Multi-Agent System

Coordinated agents with communication:

```bash
POST /api/google-adk/create-multi-agent-system
Content-Type: application/json

{
  "name": "research_team",
  "agents": ["planner", "researcher", "validator", "reporter"]
}
```

### Tool Registration

Register ADgents skills as ADK tools:

```bash
POST /api/google-adk/register-tool
Content-Type: application/json

{
  "agent_name": "research_assistant",
  "skill_name": "web_search"
}
```

### Running Agents

```bash
POST /api/google-adk/run-agent
Content-Type: application/json

{
  "agent_id": "research_assistant",
  "message": "What are the latest trends in AI?"
}
```

Response:
```json
{
  "success": true,
  "output": "Based on recent developments...",
  "model": "gemini-2.0-flash",
  "agent_name": "research_assistant"
}
```

### List Agents

```bash
GET /api/google-adk/agents
```

Response:
```json
{
  "success": true,
  "agents": [
    {
      "name": "research_assistant",
      "model": "gemini-2.0-flash",
      "tools_count": 3,
      "status": "initialized"
    }
  ],
  "total": 1
}
```

### Deployment Configuration

```bash
GET /api/google-adk/deployment-config
```

Response:
```json
{
  "success": true,
  "deployment_config": {
    "agents": [...],
    "deployment_ready": true,
    "supported_models": [
      "gemini-2.0-flash",
      "gemini-1.5-pro",
      "claude-3-opus",
      "claude-3-sonnet"
    ],
    "deployment_options": [
      "vertex_ai_agent_engine",
      "cloud_run",
      "gke",
      "local"
    ]
  }
}
```

## Python Code Examples

### Basic LLM Agent

```python
from core.google_adk_integration import ADKIntegration

# Initialize
adk = ADKIntegration()

# Create agent
agent = adk.create_llm_agent(
    name="chat_bot",
    description="A helpful chat assistant",
    model="gemini-2.0-flash"
)

# Run agent
import asyncio
result = asyncio.run(agent.run("Hello! What can you help me with?"))
print(result['output'])
```

### Agent with Tools

```python
# Create agent
agent = adk.create_llm_agent(
    name="search_agent",
    description="Search and analyze information"
)

# Register skills as tools
from core.skills import SKILL_REGISTRY

skill = SKILL_REGISTRY.get("web_search")
if skill:
    tool = adk.convert_adgent_skill_to_tool(skill)
    adk.register_tool("search_agent", tool)

# Run with tools available
result = asyncio.run(agent.run("Search for information about Python 3.12"))
```

### Sequential Workflow

```python
# Create agents
agent1 = adk.create_llm_agent(
    name="researcher",
    description="Researches topics"
)

agent2 = adk.create_llm_agent(
    name="summarizer", 
    description="Summarizes findings"
)

# Create workflow
workflow = adk.create_sequential_workflow(
    name="research_pipeline",
    agents_sequence=["researcher", "summarizer"]
)

print(workflow)
```

### Multi-Agent System

```python
# Create specialized agents
planner = adk.create_llm_agent("project_planner", "Plans projects")
executor = adk.create_llm_agent("task_executor", "Executes tasks")
reviewer = adk.create_llm_agent("code_reviewer", "Reviews code")

# Create system
system = adk.create_multi_agent_system(
    name="dev_team",
    agents={
        "planner": planner,
        "executor": executor,
        "reviewer": reviewer
    }
)

print(system)
```

## Model Support

ADK supports multiple models:

- **Google**: `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`
- **Anthropic**: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Others**: Vertex AI models, Ollama, vLLM, LiteLLM compatible models

## Deployment Options

### Vertex AI Agent Engine (Recommended)

```python
from core.google_adk_integration import VertexAIDeployment

deployer = VertexAIDeployment(
    project_id="your-project-id",
    region="us-central1"
)

agent = adk.get_agent("research_assistant")
result = deployer.deploy(agent)
print(result['endpoint'])
```

### Cloud Run

Agents can be containerized and deployed to Cloud Run:

```bash
docker build -t my-agent .
docker push gcr.io/my-project/my-agent
gcloud run deploy my-agent --image gcr.io/my-project/my-agent
```

### Local Development

Use the ADK CLI for local development:

```bash
adk create my_agent
adk run my_agent
adk web --port 8000
```

## Safety and Best Practices

1. **API Key Security**: Never commit API keys. Use environment variables or secret management.

2. **Tool Validation**: Ensure tools are safe before registering them.

3. **Rate Limiting**: Implement rate limiting for agent endpoints.

4. **Monitoring**: Monitor agent performance and costs.

5. **Error Handling**: Implement proper error handling for agent failures.

## Integration with ADgents Skills

All ADgents skills can be automatically converted to ADK tools:

```python
# Get all skills
all_tools = []
for skill in SKILL_REGISTRY.list():
    tool = adk.convert_adgent_skill_to_tool(skill)
    all_tools.append(tool)

# Register with agent
agent = adk.create_llm_agent("full_featured_agent", "Has all skills")
for tool in all_tools:
    adk.register_tool("full_featured_agent", tool)
```

## Reference

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Python ADK GitHub](https://github.com/google/adk-python)
- [Agent Development Kit](https://google.github.io/adk-docs/)
