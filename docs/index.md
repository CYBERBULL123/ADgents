# ADgents Documentation

Welcome to the **ADgents Documentation**.

**[⭐ View the official repository on GitHub](https://github.com/CYBERBULL123/ADgents)**

ADgents is an advanced, lightweight python framework and application platform designed to help you run **autonomous AI agents**. Instead of building from scratch, you can instantiate agents out-of-the-box that have distinct personas, interactive memory, and useful backend skills.

## 🎯 Which Documentation Section Do You Need?

**Choose your path:**

- 📦 **[Package Integration](packages/README.md)** - I'm integrating ADgents into my Python project
- 🚀 **[Project Application](project/README.md)** - I want to run and use the ADgents application
- 🔍 **[Full Index](#documentation-structure)** - I want to see all documentation

## Documentation Structure

ADgents documentation is organized into two main sections:

### 📦 [Package Integration](packages/README.md)

For developers integrating ADgents into their projects as a Python package:

| Guide | Purpose |
|-------|---------|
| [**Installation & Setup**](packages/installation.md) | System requirements, installation methods |
| [**Integration Guide**](packages/integration.md) | Add agents to your code + patterns |
| [**API Reference**](packages/api_reference.md) | Complete Python SDK documentation |
| [**Crew Management**](packages/crew_management.md) | Multi-agent teams |
| [**Custom Skills**](packages/skills.md) | ⭐ Create & integrate skills |
| [**Advanced Features**](packages/advanced.md) | Memory, LLM routing, optimization |

**Start here:** [Package Integration Guide](packages/README.md)

### 🚀 [Project Application](project/README.md)

For running and using the ADgents application:

| Guide | Purpose |
|-------|---------|
| [**Quickstart**](project/quickstart.md) | Get started in 5 minutes |
| [**Studio Web UI**](project/studio.md) | Interactive agent management |
| [**Architecture**](project/architecture.md) | System design overview |
| [**Crew Coordination**](project/crew.md) | Multi-agent orchestration |
| [**Real-World Use Cases**](project/use_cases.md) | Practical examples |
| [**Deployment**](project/deployment.md) | Production setup |

**Start here:** [Project Quickstart](project/quickstart.md)

### 🔗 [Examples & Resources](../../EXAMPLES.md)

- Complete runnable examples
- Integration patterns
- Web framework examples
- Data analysis examples

### ⚙️ [Contributing & Support](../../CONTRIBUTING.md)

- Development setup
- Code standards
- Testing guidelines
- Contributing workflow

### 🆘 [Troubleshooting](../../TROUBLESHOOTING.md)

- 30+ common issues with solutions
- Installation troubleshooting
- API configuration help
- Performance optimization

---

## Introduction

At its core, ADgents is built upon the idea of the **ReAct (Reasoning + Acting)** loop. An agent doesn't just respond blindly to a user input. It:
1. **Thinks** about the user input.
2. Formulates an **Action** (picking a tool/skill to use).
3. **Observes** the output of that action.
4. **Reflects** to decide if the task is complete, or if it needs to keep thinking and acting.

### Core Components
Every agent instantiated in ADgents relies on the following pillars:
- **Persona:** Defines the agent's behavior, tone, baseline autonomy level, and expertise domain.
- **Memory Engine:** A segmented multi-tier memory system (Working memory for the immediate conversation, Episodic memory for long-term task history, Semantic memory for learned rules).
- **Skill Engine:** A registry of safe, isolated python methods that give the agent agency to affect its environment. (e.g. searching the web, evaluating math calculations, running file IO).

## Supported LLM Providers
ADgents relies on a routing mechanism that allows you to hot-swap LLM engines behind the scenes.
We currently natively support:
- **OpenAI:** `gpt-4o`, `gpt-4o-mini`
- **Anthropic Claude:** `claude-3-5-sonnet-20241022`
- **Google Gemini:** `gemini-1.5-flash`, `gemini-1.5-pro`
- **Ollama (Local):** `llama3`, `mistral`

Check out our [Quickstart Guide](project/quickstart.md) to initialize your first agent!
