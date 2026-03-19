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

Create a `.env` file in your project root:

```bash
# LLM Providers (choose one or more)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=your-api-key
OLLAMA_BASE_URL=http://localhost:11434

# Default LLM Provider
DEFAULT_LLM_PROVIDER=gemini  # Options: openai, anthropic, gemini, ollama

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# File Storage
DATA_DIR=./data
```

### Programmatic Configuration

```python
from core.llm import LLM_ROUTER

# Set default provider
LLM_ROUTER.set_default_provider("gemini")

# Register custom provider
LLM_ROUTER.register_provider("custom", CustomLLMProvider())
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

## API Key Setup

### Google Gemini

1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Add to environment:

```bash
export GOOGLE_API_KEY=your-key-here
```

### OpenAI

1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Add to environment:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Anthropic Claude

1. Visit https://console.anthropic.com/
2. Create a new API key
3. Add to environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Running Locally with Ollama

1. Install Ollama: https://ollama.ai
2. Start Ollama:

```bash
ollama serve
```

3. Pull a model:

```bash
ollama pull llama2
```

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
