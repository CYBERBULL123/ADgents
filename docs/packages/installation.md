# Installation & Setup Guide

Complete guide to installing and setting up ADgents for development or integration.

## System Requirements

- **Python:** 3.9 or higher
- **OS:** Linux, macOS, or Windows
- **RAM:** 4GB minimum (8GB recommended)
- **Internet:** Required for LLM API calls

## Installation Methods

### 1. Installation from PyPI (Recommended)

```bash
pip install adgents
```

### 2. Installation from Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/CYBERBULL123/ADgents.git
cd ADgents
pip install -e .
```

Install development dependencies:

```bash
pip install -r requirements.txt
```

### 3. Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "start.py"]
```

Build and run:

```bash
docker build -t adgents .
docker run -p 8000:8000 adgents
```

## Configuration

### Environment Variables

Create a `.env` file in your project root with the following options:

#### LLM Provider Configuration

Choose one or more providers and set their credentials:

```bash
# ===== GOOGLE GEMINI (Recommended for quick setup) =====
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash  # Default: gemini-1.5-flash (or gemini-1.5-pro)

# ===== OPENAI GPT MODELS =====
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini  # Default: gpt-4o-mini (or gpt-4, gpt-4-turbo, gpt-3.5-turbo)

# ===== ANTHROPIC CLAUDE =====
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022  # Default: claude-3-5-sonnet (or claude-3-opus, claude-3-haiku)

# ===== LOCAL OLLAMA (No API key needed) =====
OLLAMA_BASE_URL=http://localhost:11434  # Local Ollama instance
OLLAMA_MODEL=llama2  # Default: llama2 (or mistral, neural-chat, etc.)

# ===== DEFAULT PROVIDER SELECTION =====
DEFAULT_LLM_PROVIDER=gemini  # Options: openai, anthropic, gemini, ollama, mock
DEFAULT_LLM_MODEL=gemini-1.5-flash  # Override default model for selected provider
```

#### Server Configuration

```bash
# Server Setup
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# File Storage
DATA_DIR=./data
```

### Programmatic Configuration

```python
from core.llm import LLM_ROUTER, OpenAIProvider, GeminiProvider, AnthropicProvider

# Method 1: Set default provider
LLM_ROUTER.set_default("gemini")

# Method 2: Initialize provider with custom model
gemini = GeminiProvider(model="gemini-1.5-pro")
LLM_ROUTER.register(gemini)

# Method 3: Configure all providers automatically from env vars
# (This happens automatically on import)
```

## Verifying Installation

### Quick Health Check

```bash
python -c "from core.agent import Agent; print('✅ ADgents installed successfully')"
```

### Using CLI

```bash
adgents status
```

Output should show:
```
✅ ADgents System Status
├─ Core System: Ready
├─ LLM Providers: Available
├─ Agents: 0
└─ Skills: Ready
```

### Using Python

```python
from core.agent import Agent
from core.persona import Persona

# Create a test agent
persona = Persona(
    name="Test Agent",
    role="Helper",
    autonomy_level=3
)

agent = Agent(persona=persona)
response = agent.chat("Hello, are you working?")
print(response)
```

## API Key Setup & Provider Configuration

### Google Gemini (Recommended)

**Best for:** Quick setup, free tier available, excellent performance

1. Visit https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy your API key
4. Add to `.env`:

```bash
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro for higher quality
DEFAULT_LLM_PROVIDER=gemini
```

**Available Models:**
- `gemini-1.5-flash` - Fast, cost-effective (default)
- `gemini-1.5-pro` - Higher quality, slower
- `gemini-1.0-pro` - Previous generation

### OpenAI GPT

**Best for:** Advanced reasoning, large projects

1. Visit https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Add to `.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini  # Fast and cheap
DEFAULT_LLM_PROVIDER=openai
```

**Available Models:**
- `gpt-4o-mini` - Fast, cost-effective (recommended)
- `gpt-4` - Most capable
- `gpt-4-turbo` - Good balance
- `gpt-3.5-turbo` - Cheapest

### Anthropic Claude

**Best for:** Extended context, safety-focused

1. Visit https://console.anthropic.com/
2. Create a new API key
3. Add to `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
DEFAULT_LLM_PROVIDER=anthropic
```

**Available Models:**
- `claude-3-5-sonnet-20241022` - Best performance/cost ratio (recommended)
- `claude-3-opus-20240229` - Most capable, slower
- `claude-3-haiku-20240307` - Fastest, budget-friendly

### Ollama (Local, No API Key)

**Best for:** Privacy, offline use, development/testing

1. Install from https://ollama.ai
2. Start Ollama service:

```bash
ollama serve
```

3. Pull a model:

```bash
ollama pull llama2        # Meta's Llama 2
ollama pull mistral       # Mistral AI
ollama pull neural-chat   # Intel's model
```

4. Add to `.env`:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
DEFAULT_LLM_PROVIDER=ollama
```

**Available Models:**
- `llama2` - Popular, good quality
- `mistral` - Fast, efficient
- `neural-chat` - Optimized for conversation
- `dolphin-mixtral` - Creative writing


4. Set environment:

```bash
export DEFAULT_LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

## Starting the Server

### Development Mode

```bash
python start.py
```

Access the Studio UI at: **http://localhost:8000/studio**

### Production Mode

Using Uvicorn with multiple workers:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  adgents:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - DEFAULT_LLM_PROVIDER=gemini
      - DEBUG=false
    volumes:
      - ./data:/app/data
```

Start:

```bash
docker-compose up -d
```

## Troubleshooting

### "Module not found" Error

Make sure ADgents is installed:

```bash
pip list | grep adgents
```

Reinstall if needed:

```bash
pip install --upgrade adgents
```

### "API Key not found" Error

Check environment variables are set:

```bash
# Linux/macOS
echo $GOOGLE_API_KEY

# Windows PowerShell
$env:GOOGLE_API_KEY
```

### Connection Issues

If server won't start:

```bash
# Check if port 8000 is in use
netstat -tulpn | grep 8000

# Use a different port
python start.py --port 8001
```

### Low Performance

- Increase RAM allocation to Python process
- Use fewer concurrent agents
- Switch to faster LLM (e.g., gemini-1.5-flash)
- Enable caching

## Next Steps

- [Quick Start Guide](quickstart.md) - Build your first agent
- [Python SDK](sdk.md) - Integrate into your app
- [Studio UI](studio.md) - Interactive agent management
- [API Reference](api_reference.md) - Complete API docs
