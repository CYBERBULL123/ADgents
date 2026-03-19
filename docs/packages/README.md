# Package Integration Documentation

Everything you need to integrate ADgents as a Python package into your projects.

## Getting Started

**New to ADgents?** Start here:

1. [**Installation & Setup**](installation.md) - System requirements, multiple installation methods
2. [**Quick Integration**](integration.md) - Your first agent in 5 minutes
3. [**API Reference**](api_reference.md) - Complete Python SDK docs

## Core Concepts

| Concept | Guide | Purpose |
|---------|-------|---------|
| **Agents** | [API Reference](api_reference.md) | Individual AI agents with personas |
| **Skills** | [⭐ Custom Skills](skills.md) | Create and register custom capabilities |
| **Crews** | [Crew Management](crew_management.md) | Multi-agent teams for complex tasks |
| **Memory** | [Advanced Features](advanced.md) | Working, episodic, and semantic memory |
| **LLMs** | [Advanced Features](advanced.md) | Using different AI models |

## Integration Guides

### For Application Developers

Use ADgents to add AI capabilities to your app:

- [Integration Guide](integration.md) - Add agents to your codebase
- [Web Framework Integration](integration.md#web-framework-integration) - FastAPI, Flask examples
- [EXAMPLES.md](../../../EXAMPLES.md) - Real-world code examples

### For Data Scientists

Use ADgents for data analysis and processing:

- [Data Analysis Integration](integration.md#integration-with-data-processing) - Pandas + ADgents
- [Custom Skills](skills.md#data-processing-skills) - Create data processing skills
- [API Integration](skills.md#api-integration-skills) - Connect to data sources

### For DevOps/Platform Engineers

Deploy ADgents at scale:

- [Installation Methods](installation.md#installation-methods) - PyPI, Docker, source
- [Configuration](installation.md#configuration) - Environment setup
- [Production Deployment](../project/deployment.md) - Scale and monitor

## Documentation Structure

```
packages/
├── installation.md          ← Installation & setup
├── integration.md           ← Integration patterns
├── api_reference.md         ← Complete API docs
├── crew_management.md       ← Multi-agent teams
├── advanced.md             ← Advanced patterns
└── skills.md               ← Custom skills

project/
├── quickstart.md           ← 5-minute quickstart
├── studio.md              ← Web UI guide
├── deployment.md          ← Production deployment
├── use_cases.md           ← Real-world examples
├── architecture.md        ← System design
└── crew.md               ← Crew coordination
```

## Quick Reference

### Create Your First Agent

```python
from core.agent import Agent
from core.persona import Persona

agent = Agent(
    persona=Persona(
        name="Your Agent",
        role="Your Role",
        expertise_domains=["Domain1", "Domain2"]
    )
)

response = agent.chat("Your question here")
```

See [Integration Guide](integration.md) for more patterns.

### Create a Skill

```python
from core.skills import register_skill

@register_skill(
    name="my_skill",
    description="What it does",
    parameters={"param": "Description"}
)
def my_skill(param: str) -> str:
    return f"Result: {param}"
```

See [Skills Guide](skills.md) for complete documentation.

### Create a Multi-Agent Crew

```python
from core.crew_manager import CrewManager

crew_mgr = CrewManager()
crew = crew_mgr.create_crew(
    name="My Team",
    organization="dept",
    members=[...]
)
```

See [Crew Management](crew_management.md) for details.

## Common Tasks

### Task: "I want to add AI to my Flask app"
→ See [Web Framework Integration](integration.md#web-framework-integration)

### Task: "I need to create a custom skill"
→ See [Skills Guide](skills.md)

### Task: "I want agents working together"
→ See [Crew Management](crew_management.md)

### Task: "I need to handle memory/context"
→ See [Advanced Features](advanced.md#memory-systems)

### Task: "I want to understand all APIs"
→ See [API Reference](api_reference.md)

## Installation Quick Links

- [PyPI Installation](installation.md#1-installation-from-pypi-recommended)
- [Source Installation](installation.md#2-installation-from-source)
- [Docker Installation](installation.md#3-using-docker)
- [Configuration Guide](installation.md#configuration)

## Troubleshooting

Having issues?

- [General Troubleshooting](../../../TROUBLESHOOTING.md)
- [Installation Issues](../../../TROUBLESHOOTING.md#installation-issues)
- [API Key Issues](../../../TROUBLESHOOTING.md#api-key--configuration)
- [Agent Issues](../../../TROUBLESHOOTING.md#agent-issues)

## Need Help?

- 📝 [Examples](../../../EXAMPLES.md) - Real-world code examples
- 🤝 [Contributing](../../../CONTRIBUTING.md) - Join the community
- 🐛 [Report Issues](https://github.com/CYBERBULL123/ADgents/issues)
- 💬 [Discussions](https://github.com/CYBERBULL123/ADgents/discussions)

## What's Included?

**Package Features:**
- ✅ Agent system with personas
- ✅ Multi-tier memory (working, episodic, semantic)
- ✅ 10+ built-in skills
- ✅ Custom skill creation
- ✅ Multi-agent crews
- ✅ LLM provider routing
- ✅ REST API
- ✅ Python SDK
- ✅ Async/await support

**Supported Models:**
- OpenAI (GPT-4, GPT-4o)
- Google Gemini (Flash, Pro)
- Anthropic Claude (3.5 Sonnet)
- Ollama (Local models)

## Next Steps

**Start here:**
1. Read [Installation & Setup](installation.md)
2. Run [Quick Integration](integration.md)
3. Explore [Examples](../../../EXAMPLES.md)
4. Build your first integration!

**Go deeper:**
- [API Reference](api_reference.md) - Learn all APIs
- [Skills Guide](skills.md) - Create custom skills
- [Advanced Features](advanced.md) - Master advanced patterns

**Deploy to production:**
- [Production Deployment](../project/deployment.md)
- [Configuration Guide](installation.md#configuration)
