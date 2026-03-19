# ⚡ ADgents — Autonomous Agent Platform

> Build, deploy, and talk to autonomous AI agents — each with their own **persona**, **memory**, **expertise**, and **skills**.

![ADgents](docs/img.png)

---

## 🌟 What is ADgents?

ADgents treats AI agents like **real people** — each agent has:

| Attribute | Description |
|-----------|-------------|
| 🎭 **Persona** | Name, role, backstory, personality traits |
| 🧠 **Memory** | Working (session), Episodic (past experiences), Semantic (knowledge) |
| 🛠️ **Skills** | Web search, code execution, file I/O, API calls, and more |
| 📚 **Expertise** | Domain knowledge they specialize in |
| 🔄 **Autonomy** | ReAct loop: Think → Act → Observe → Reflect |
| 🤝 **Crews** | Orchestrate multiple agents to collaborate on sub-tasks |
| 🔌 **MCP + ADK** | Expose skills as MCP Tools or deploy as Google ADK nodes |

---

## 🚀 Quick Start

### 1. Install ADgents

**Via pip (recommended):**
```bash
pip install adgents
```

**From source:**
```bash
git clone https://github.com/CYBERBULL123/ADgents.git
cd ADgents
pip install -e .
```

**Set up environment:**
```bash
cp .env.example .env
# Edit .env and add your LLM API keys (Gemini, OpenAI, Anthropic, or use Ollama locally)
```

**Start the server:**
```bash
python start.py
```

Then open: **http://localhost:8000/studio**

### 2. Use the CLI

```bash
# Chat with an agent
python cli.py chat researcher

# Run an autonomous task
python cli.py run engineer "Write a Python script to sort a CSV file by date"

# List templates
python cli.py templates

# Check status
python cli.py status
```

### 3. Use the Python SDK

```python
from sdk.python.adgents import ADgents

sdk = ADgents()

# Create a researcher agent
researcher = sdk.create_agent(template="researcher")

# Chat
response = researcher.chat("What are the latest trends in LLMs?")
print(response)

# Teach the agent
researcher.learn("Our company focuses on B2B SaaS products")

# Run autonomous task
task = researcher.run_task("Research and summarize GPT-4's capabilities")
print(task.result)
```

---

## 📚 Documentation

Complete documentation organized into clear sections:

### For Package Integration
Integrate ADgents into your Python projects:

| Guide | Purpose |
|-------|---------|
| [**Installation**](docs/packages/README.md) | Installation methods and setup |
| [**Quick Integration**](docs/integration.md) | Add agents to your code |
| [**API Reference**](docs/api_reference.md) | All Python APIs |
| [**Custom Skills**](docs/packages/skills.md) | ⭐ Create & integrate custom skills |
| [**Advanced Features**](docs/advanced.md) | Memory, optimization, LLM routing |

**[→ Go to Package Integration Docs](docs/packages/README.md)**

### For Project Application
Run and manage the ADgents application:

| Guide | Purpose |
|-------|---------|
| [**Quickstart**](docs/quickstart.md) | Start in 5 minutes |
| [**Studio UI**](docs/studio.md) | Web-based management |
| [**Deployment**](docs/deployment.md) | Production setup |
| [**Use Cases**](docs/use_cases.md) | Real-world examples |

**[→ Go to Project Application Docs](docs/project/README.md)**

### Support & Resources

- 📝 [Examples & Code Samples](EXAMPLES.md)
- 🤝 [Contributing Guide](CONTRIBUTING.md)  
- 🆘 [Troubleshooting](TROUBLESHOOTING.md)
- 🔗 [Full Documentation Index](docs/index.md)

---

## 🤖 Built-in Agent Templates

| Template | Avatar | Role | Best For |
|----------|--------|------|----------|
| `researcher` | 🔬 | Dr. Aditi — Research Scientist | Research, analysis, literature review |
| `engineer` | ⚙️ | Karan — Senior Software Engineer | Code, system design, technical problems |
| `analyst` | 📊 | Meera — Business Analyst | Data, strategy, business insights |
| `assistant` | ✨ | Naveen — Personal Assistant | General tasks, scheduling, writing |
| `strategist` | 🧭 | Arjun — Strategic Advisor | Planning, leadership, competitive analysis |

---

## 🛠️ Built-in Skills

| Skill | Category | Description |
|-------|----------|-------------|
| `web_search` | Information | Search the internet |
| `code_execute` | Development | Run Python code |
| `file_read` | Filesystem | Read files |
| `file_write` | Filesystem | Write files |
| `api_call` | Integration | HTTP requests |
| `list_directory` | Filesystem | Browse directories |
| `get_datetime` | Utility | Current date/time |
| `calculate` | Utility | Math expressions |
| `json_parse` | Data | Parse JSON |
| `summarize_text` | Text | Text summarization |

---

## 🧠 Memory Architecture

```
┌─────────────────────────────────────────────┐
│              Agent Memory                    │
│                                             │
│  Working Memory    ← Current session        │
│  (in-context)        conversations          │
│                                             │
│  Episodic Memory   ← Past interactions,     │
│  (SQLite)            experiences            │
│                                             │
│  Knowledge Base    ← Facts, domain          │
│  (SQLite)            knowledge you teach    │
└─────────────────────────────────────────────┘
```

---

## 🔌 LLM Providers

Configure in Settings or `.env`:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

| Provider | Models | Key Required |
|----------|--------|--------------|
| OpenAI | GPT-4o, GPT-4o-mini | Yes |
| Google Gemini | gemini-1.5-flash, gemini-1.5-pro | Yes |
| Ollama | llama3, mistral, etc. | No (local) |
| Mock | Built-in | No (testing) |

---

## 📁 Project Structure

```
ADgents/
├── core/                    # Core engine
│   ├── agent.py             # Agent class with ReAct loop
│   ├── persona.py           # Persona system + templates
│   ├── memory.py            # Multi-layer memory
│   ├── skills.py            # Skills engine + built-ins
│   └── llm.py               # LLM providers
├── studio/                  # Web UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── sdk/python/
│   └── adgents.py           # Python SDK
├── server.py                # FastAPI server
├── cli.py                   # CLI tool
├── start.py                 # Startup script
└── .env.example             # Config template
```

---

## 🔄 Autonomous Workflow (ReAct)

```
User Task
    │
    ▼
📋 Plan ──────────────────────────────────┐
    │                                      │
    ▼                                      │
💭 Think (LLM reasons about next step)    │
    │                                      │
    ▼                                      │
⚡ Act (execute a skill/tool)             │
    │                                      │
    ▼                                      │
👁️ Observe (see the result)               │
    │                                      │
    ▼                                      │
🔮 Reflect ──────► Continue? ─── Yes ────┘
                        │
                       No
                        │
                        ▼
                  ✅ Final Answer
                  💾 Store in Memory
```

---

## 🛣️ Roadmap

- [x] Core agent engine (ReAct loop)
- [x] Persona system with 5 templates
- [x] Multi-layer memory (working, episodic, semantic)
- [x] 10+ built-in skills
- [x] Multi-provider LLM support (OpenAI, Gemini, Anthropic, Ollama)
- [x] Web Studio UI
- [x] REST + WebSocket API
- [x] Python SDK
- [x] CLI tool
- [x] Multi-agent crews and collaboration
- [x] Complete documentation suite
- [x] Installation and integration guides
- [ ] Custom skill plugins marketplace
- [ ] Vector embeddings for smarter memory search
- [ ] JavaScript/TypeScript SDK
- [ ] PyPI package official release
- [ ] Docker deployment templates
- [ ] Fine-tuning support
- [ ] Multi-provider embeddings

---

## 📄 License

MIT — Build freely, ship boldly.
