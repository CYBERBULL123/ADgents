# Project Documentation

Documentation for running and using the ADgents project.

## Running ADgents

**New to ADgents?** Start with the application:

1. [**Quickstart Guide**](quickstart.md) - Get running in 5 minutes
2. [**Studio Web UI**](studio.md) - Use the interactive interface
3. [**Use Cases**](use_cases.md) - Real-world examples

## How It Works

| Topic | Guide | Learn |
|-------|-------|-------|
| **Architecture** | [System Design](architecture.md) | How ADgents is built |
| **Crews** | [Crew Coordination](crew.md) | Multi-agent orchestration |
| **Deployment** | [Production Setup](deployment.md) | Deploy at scale |

## Guides

### For End Users

Want to use ADgents right away?

1. [Quickstart](quickstart.md) - Start the app and use the UI
2. [Studio Guide](studio.md) - Interactive agent management
3. [Use Cases](use_cases.md) - Practical examples

### For Developers

Want to extend or understand ADgents?

1. [Architecture](architecture.md) - System design overview
2. [Crew Coordination](crew.md) - Multi-agent patterns
3. [Deployment](deployment.md) - Run in production

### For DevOps

Deploy and manage ADgents:

1. [Deployment Guide](deployment.md) - Production setup
2. [Docker Configuration](deployment.md#docker) - Containerized deployment
3. [Monitoring & Scaling](deployment.md) - Production operations

## Quick Reference

### Start the Server

```bash
python start.py
```

Then open: **http://localhost:8000/studio**

### Using the CLI

```bash
# Chat with an agent
python cli.py chat researcher

# Run a task
python cli.py run analyst "Analyze this data"

# List agents
python cli.py agents
```

### Using Python

```python
from sdk.python.adgents import ADgents

sdk = ADgents()
agent = sdk.create_agent(template="researcher")
response = agent.chat("Your question")
```

See [Integration Guide](../packages/integration.md) for more examples.

## Runnable Project

This folder contains everything to run the ADgents application:

```
ADgents/
├── server.py              ← FastAPI backend
├── cli.py                 ← Command-line interface
├── start.py               ← Startup script
├── studio/                ← Web UI (HTML/JS)
├── core/                  ← Agent engine
├── sdk/                   ← Python SDK
└── docs/                  ← Documentation
```

## Common Questions

### Q: How do I start using ADgents?
A: Follow the [Quickstart](quickstart.md) guide (5 minutes)

### Q: What can agents do?
A: See [Use Cases](use_cases.md) for real-world examples

### Q: How does the system work?
A: Read [Architecture](architecture.md) overview

### Q: How do I deploy to production?
A: Follow [Deployment](deployment.md) guide

### Q: Can I integrate agents into my app?
A: Yes, see [Package Integration](../packages/README.md)

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│          ADgents Application                 │
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │         Studio Web UI                │   │
│  │  (Interactive agent management)     │   │
│  └─────────────────────────────────────┘   │
│           ↓                                 │
│  ┌─────────────────────────────────────┐   │
│  │      FastAPI REST Server            │   │
│  │  (/api, /studio routes)            │   │
│  └─────────────────────────────────────┘   │
│           ↓                                 │
│  ┌─────────────────────────────────────┐   │
│  │      ADgents Core Engine            │   │
│  │  • Agent system                    │   │
│  │  • ReAct loop                      │   │
│  │  • Memory management               │   │
│  │  • Skill execution                 │   │
│  └─────────────────────────────────────┘   │
│           ↓                                 │
│  ┌─────────────────────────────────────┐   │
│  │      LLM Providers                  │   │
│  │  (OpenAI, Gemini, Claude, Ollama)  │   │
│  └─────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

## Key Features

- 🤖 **Autonomous Agents** - Agents with personas, memory, and skills
- 🧠 **Multi-tier Memory** - Working, episodic, semantic memory
- 🛠️ **Built-in Skills** - Web search, code execution, file I/O, APIs
- 🤝 **Multi-Agent Crews** - Teams of specialized agents
- 🔌 **LLM Providers** - OpenAI, Gemini, Claude, Ollama
- 💻 **Web UI (Studio)** - Interactive agent management
- 🔌 **REST API** - Integrate agents anywhere
- 🐍 **Python SDK** - First-class Python support
- ⚡ **CLI Tool** - Command-line interface

## Deployment Options

| Option | Best For | Effort |
|--------|----------|--------|
| **Local (start.py)** | Development, testing | 5 min |
| **Docker** | Any environment | 10 min |
| **Docker Compose** | Full stack with monitoring | 15 min |
| **Kubernetes** | Large scale, production | Advanced |

See [Deployment](deployment.md) for details.

## Next Steps

**Run ADgents:**
1. Follow [Quickstart](quickstart.md)
2. Explore [Studio UI](studio.md)
3. Try [Use Cases](use_cases.md)

**Integrate with your app:**
1. See [Package Integration](../packages/README.md)
2. Follow [Integration Guide](../packages/integration.md)
3. Review [Examples](../../EXAMPLES.md)

**Deploy to production:**
1. Read [Deployment](deployment.md)
2. Configure for your infrastructure
3. Monitor with observability tools

**Go deeper:**
1. Understand [Architecture](architecture.md)
2. Learn about [Crews](crew.md)
3. Read [Use Cases](use_cases.md)
