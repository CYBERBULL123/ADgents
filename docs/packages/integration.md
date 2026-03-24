# Integration Guide

Learn how to integrate ADgents into your Python projects.

## Quick Start

### 1. Install ADgents

```bash
pip install adgents
```

Or install from source:

```bash
git clone https://github.com/CYBERBULL123/ADgents.git
cd ADgents
pip install -e .
```

### 2. Set Up LLM Provider & Environment

Create a `.env` file with your chosen LLM provider:

```env
# Choose ONE provider (Gemini recommended)

# Google Gemini (Recommended - Free tier available!)
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-1.5-flash
DEFAULT_LLM_PROVIDER=gemini

# OR OpenAI
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4o-mini
# DEFAULT_LLM_PROVIDER=openai

# OR Anthropic Claude
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
# DEFAULT_LLM_PROVIDER=anthropic

# OR Local Ollama (No API key needed)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama2
# DEFAULT_LLM_PROVIDER=ollama
```

### 3. Create Your First Agent

```python
from core.agent import Agent
from core.persona import Persona

# Create an agent
agent = Agent(persona=Persona(
    name="Researcher",
    role="Research Assistant",
    expertise_domains=["Technology", "AI"]
))

# Chat with it
response = agent.chat("What are the latest AI trends?")
print(response)
```

---

## Common Use Cases

### Use Case 1: Simple Single Agent

When you need help with one specific task:

```python
from core.agent import Agent
from core.persona import Persona

# Create agent
analyst = Agent(persona=Persona(
    name="Data Analyst",
    role="Analyst",
    expertise_domains=["Data Science"]
))

# Use it
result = analyst.chat("Analyze this sales data: Q1 revenue up 20%")
print(result)
```

### Use Case 2: Multi-Agent Crew

When you need multiple agents working together on complex tasks:

```python
from core.agent import Agent
from core.persona import Persona
from core.crew import Crew

# Create agents with different roles
researcher = Agent(persona=Persona(
    name="Sarah",
    role="Researcher",
    expertise_domains=["Research"]
))

writer = Agent(persona=Persona(
    name="Mike",
    role="Writer",
    expertise_domains=["Writing"]
))

reviewer = Agent(persona=Persona(
    name="Lisa",
    role="Quality Reviewer",
    expertise_domains=["Quality Assurance"]
))

# Create crew
crew = Crew(
    name="Content Team",
    agents=[researcher, writer, reviewer]
)

# Run task - the crew will automatically:
# 1. Break the task into sub-tasks
# 2. Assign each sub-task to the best agent
# 3. Combine results
run = crew.run("Write a comprehensive guide about machine learning")
print(run.final_answer)
```

---

## How Crews Work

### What is a Crew?

A Crew is a group of specialized agents that work together. When you give a crew a task, it:

1. **Plans** - Breaks the task into sub-tasks
2. **Assigns** - Gives each sub-task to the best agent
3. **Executes** - Each agent completes their sub-task
4. **Synthesizes** - Combines all results into a final answer

### Crew Setup Example

```python
from core.agent import Agent
from core.persona import Persona
from core.crew import Crew

# Step 1: Create agents
researcher = Agent(persona=Persona(
    name="Dr. Search",
    role="Researcher",
    expertise_domains=["Information Research"]
))

writer = Agent(persona=Persona(
    name="Jane Write",
    role="Writer",
    expertise_domains=["Writing", "Documentation"]
))

# Step 2: Create crew
crew = Crew(
    name="Documentation Team",
    agents=[researcher, writer]
)

# Step 3: Run a task
result = crew.run("Create documentation for TypeScript generators")

# Results
print(f"Status: {result.status}")        # done, running, failed
print(f"Answer: {result.final_answer}")  # The combined result
```

### Understanding Crew Results

```python
run = crew.run("Your task here")

# Access results
print(run.status)           # done | running | failed
print(run.final_answer)     # The complete answer
print(run.plan)             # How the task was decomposed
print(run.sub_tasks)        # List of sub-tasks and results

# See each sub-task
for sub_task in run.sub_tasks:
    print(f"Agent: {sub_task.agent_name}")
    print(f"Task: {sub_task.description}")
    print(f"Result: {sub_task.result}")
```

---

## Choosing Between Single Agent vs Crew

| Scenario | Use | Example |
|----------|-----|---------|
| Quick question | Single Agent | "What is X?" |
| Single domain task | Single Agent | Analyze a CSV file |
| Complex multi-step | Crew | Write documentation (needs research + writing + review) |
| Multiple perspectives | Crew | Compare different viewpoints |
| Brainstorming | Crew | Generate and refine ideas |

---

## Environment Variables

### LLM Provider Configuration

```bash
# Choose ONE of these:

# Google Gemini (Recommended)
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-1.5-flash

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Select default
DEFAULT_LLM_PROVIDER=gemini
```

### Server Configuration

```bash
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

---

## API Key Setup by Provider

### Google Gemini

1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Add to `.env`: `GEMINI_API_KEY=your-key`

**Available Models:**
- `gemini-1.5-flash` (fastest, free tier)
- `gemini-1.5-pro` (higher quality)

### OpenAI

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key
4. Add to `.env`: `OPENAI_API_KEY=sk-your-key`

**Available Models:**
- `gpt-4o-mini` (fast, cheap)
- `gpt-4o` (advanced)
- `gpt-4` (most capable)

### Anthropic Claude

1. Go to https://console.anthropic.com/
2. Create API key
3. Copy the key
4. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-your-key`

**Available Models:**
- `claude-3-5-sonnet-20241022` (recommended)
- `claude-3-opus` (most capable)
- `claude-3-haiku` (budget)

### Ollama (Local)

1. Install from https://ollama.ai
2. Run: `ollama serve`
3. In another terminal: `ollama pull llama2`
4. Add to `.env`:
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

**Available Models:**
- `llama2` (popular)
- `mistral` (fast)
- `neural-chat` (conversation)

---

## Next Steps

- Check [Installation Guide](installation.md) for detailed setup
- See [README](../../README.md) for CLI usage
- Read [How Crews Work](#how-crews-work) above for team setup
