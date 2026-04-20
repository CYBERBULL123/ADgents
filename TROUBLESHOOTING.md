# Troubleshooting Guide

Common issues and their solutions.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API Key & Configuration](#api-key--configuration)
3. [Agent Issues](#agent-issues)
4. [Task Execution Problems](#task-execution-problems)
5. [Crew & Communication](#crew--communication)
6. [Memory Issues](#memory-issues)
7. [Performance & Optimization](#performance--optimization)
8. [Web UI Issues](#web-ui-issues)

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'core'`

**Cause:** Module not in Python path or not installed properly.

**Solutions:**
```bash
# Option 1: Install in development mode
pip install -e .

# Option 2: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/ADgents"

# Option 3: Run from the ADgents directory
cd /path/to/ADgents
python your_script.py
```

### Issue: `pip install` fails with permission error

**Cause:** Insufficient permissions or using system Python.

**Solutions:**
```bash
# Option 1: Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install adgents

# Option 2: Install for current user only
pip install --user adgents

# Option 3: Use sudo (not recommended)
sudo pip install adgents
```

### Issue: Version conflicts with dependencies

**Cause:** Conflicting package versions in environment.

**Solutions:**
```bash
# Clear pip cache
pip cache purge

# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install fresh in virtual environment
python -m venv venv_fresh
source venv_fresh/bin/activate
pip install adgents
```

### Issue: `ImportError` with optional dependencies

**Cause:** Optional packages not installed.

**Solutions:**
```bash
# Install with all optional dependencies
pip install adgents[all]

# Install specific optional dependencies
pip install adgents[pandas,scipy]  # For data processing
pip install adgents[dev]  # For development
```

## API Key & Configuration

### Issue: `API key not found` or `Unauthorized`

**Cause:** Missing or invalid API key.

**Solutions:**

1. **Check environment variable:**
```bash
# Linux/Mac
echo $GEMINI_API_KEY

# Windows PowerShell
$env:GEMINI_API_KEY
```

2. **Verify `.env` file:**
```bash
cat .env
# or
type .env  # Windows
```

3. **Add correct API key:**
```bash
# Create/update .env
export GEMINI_API_KEY="your_actual_key_here"
export OPENAI_API_KEY="your_key_here"
```

4. **Verify key format:**
```python
import os
key = os.getenv("GEMINI_API_KEY")
if key and len(key) > 10:
    print("Key found and looks valid")
else:
    print("Key is missing or too short")
```

### Issue: `Invalid API key format`

**Cause:** Key is malformed or from wrong provider.

**Solutions:**
- Verify you're using the correct API key for the provider
- Check for extra whitespace: `key = key.strip()`
- Ensure you copied the entire key

### Issue: Rate limiting errors (429)

**Cause:** Too many API calls in short time.

**Solutions:**
```python
# Add delays between calls
import time
from core.agent import Agent

agent = Agent(persona=persona)

for i in range(10):
    response = agent.chat("Query " + str(i))
    time.sleep(2)  # Wait 2 seconds between calls

# Or use async with proper rate limiting
import asyncio
from core.agent import Agent

async def rate_limited_requests():
    agent = Agent(persona=persona)
    
    for i in range(10):
        response = await agent.chat("Query")
        await asyncio.sleep(2)
```

### Issue: `Connection timeout`

**Cause:** Network issue or API server down.

**Solutions:**
```python
# Increase timeout
import httpx

# In core/llm.py, modify timeout
timeout = httpx.Timeout(30.0)  # 30 seconds

# Check API status
curl https://api.google.com/status

# Check internet connection
ping google.com
```

## Agent Issues

### Issue: Agent returns empty or no response

**Cause:** Multiple possible causes.

**Solutions:**

1. **Check LLM configuration:**
```python
from core.llm import get_llm

llm = get_llm()
print(f"Provider: {llm.provider}")
print(f"Model: {llm.model}")
```

2. **Test with a simple query:**
```python
from core.agent import Agent

agent = Agent(persona=Persona(name="Test", role="Test"))
response = agent.chat("Hello")
print(f"Response: {response}")
print(f"Length: {len(response)}")
```

3. **Check API key validity:**
```python
# Try direct API call (without agent)
from core.llm import get_llm

llm = get_llm()
result = llm.generate("Test prompt")
```

4. **Enable debug logging:**
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("core")
logger.setLevel(logging.DEBUG)
```

### Issue: `Agent seems to ignore instructions`

**Cause:** Persona not being used correctly or LLM not understanding.

**Solutions:**

1. **Reinforce instructions in persona:**
```python
persona = Persona(
    name="Technical Writer",
    role="Documentation Expert",
    expertise_domains=["Technical Writing"],
    communication_style="clear and structured",
    # Add specific instructions
    system_prompt="Always provide structured, clear documentation"
)
agent = Agent(persona=persona)
```

2. **Use explicit instructions in messages:**
```python
# More specific prompts
response = agent.chat(
    "You are a technical writer. "
    "Explain this in simple terms: quantum computing"
)
```

3. **Re-teach important facts:**
```python
agent.learn("Rule: Always verify sources")
agent.learn("Style: Use simple English")
agent.learn("Format: Use bullet points")
```

### Issue: Agent memory seems to disappear

**Cause:** Memory not persisted or session cleared.

**Solutions:**

1. **Check memory persistence:**
```python
# Save memory
memory_export = agent.export_memory()

# Verify it's not empty
print(f"Semantic memory size: {len(memory_export['semantic'])}")
print(f"Episodic memory size: {len(memory_export['episodic'])}")
```

2. **Explicitly save memory:**
```python
agent.memory.persist()  # Force save
```

3. **Use episodic/semantic memory correctly:**
```python
# Episodic: events that happened
agent.remember("Completed task X on 2024-03-01")

# Semantic: facts
agent.learn("Fact: Company was founded in 2020")

# Both should persist
```

## Task Execution Problems

### Issue: Task never completes (stuck)

**Cause:** Task complexity, infinite loop, or LLM not responding.

**Solutions:**

1. **Add iteration limit:**
```python
result = agent.run_task(
    task="Some complex task",
    max_iterations=5  # Limit iterations
)
```

2. **Set timeout:**
```python
import asyncio

try:
    result = asyncio.wait_for(
        agent.run_task("Task"),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    print("Task took too long")
```

3. **Test with simpler task first:**
```python
# Start simple
simple_result = agent.run_task("Count to 5")

# Then try complex
complex_result = agent.run_task("Long task")
```

### Issue: Task returns error or fails

**Cause:** Task too complex, missing skills, or invalid input.

**Solutions:**

1. **Check error message:**
```python
result = agent.run_task("Task")
print(f"Status: {result['status']}")
print(f"Error: {result.get('error')}")
```

2. **Simplify the task:**
```python
# Too complex
# task = "Analyze big data, create visualizations, write report"

# Simpler
task = "Analyze this data and summarize in 3 points"
```

3. **Provide more context:**
```python
agent.learn("Context about the task")
agent.learn("Available resources")

result = agent.run_task("More specific task")
```

4. **Check available skills:**
```python
from core.skills import SKILL_REGISTRY

print("Available skills:")
for skill_name in SKILL_REGISTRY.keys():
    print(f"  - {skill_name}")
```

### Issue: Task outputs don't match expectations

**Cause:** Prompt not clear or agent misunderstood.

**Solutions:**

1. **Be more specific:**
```python
# Generic
# task = "Analyze data"

# Specific
task = "Analyze sales data by region and identify top 3 regions by revenue"
```

2. **Include examples:**
```python
task = """
Analyze this data and output:
1. Total records
2. Average value
3. Max value

Example output format:
Total: 100
Average: 50
Max: 99
"""
```

3. **Use step-by-step approach:**
```python
# Step 1
result1 = agent.run_task("Step 1: Gather data")

# Step 2 (use previous result)
result2 = agent.run_task(f"Step 2: Analyze {result1['output']}")
```

## Crew & Communication

### Issue: Crew members not communicating

**Cause:** A2A protocol not enabled or members not configured correctly.

**Solutions:**

1. **Verify A2A is enabled:**
```python
crew = crew_manager.get_crew(crew_id)
print(f"Communication Protocol: {crew.get('communication_protocol')}")
# Should be 'a2a'
```

2. **Check member configurations:**
```python
for member in crew['members']:
    print(f"{member['agent_name']}: Agent ID {member['agent_id']}")
```

3. **Verify agents exist:**
```python
from core.agent import get_agent_by_id

for member in crew['members']:
    agent = get_agent_by_id(member['agent_id'])
    if agent is None:
        print(f"Agent {member['agent_id']} not found")
```

### Issue: Crew task not executing

**Cause:** Missing members, invalid crew ID, or server issue.

**Solutions:**

1. **Verify crew exists:**
```python
crew = crew_manager.get_crew(crew_id)
if crew is None:
    print("Crew not found")
else:
    print(f"Crew: {crew['name']}, Members: {len(crew['members'])}")
```

2. **Ensure crew has members:**
```python
if len(crew['members']) < 1:
    print("Crew has no members")
else:
    print(f"Crew has {len(crew['members'])} members")
```

3. **Check crew is active:**
```python
if not crew.get('active', True):
    # Reactivate
    crew_manager.update_crew(crew_id, active=True)
```

### Issue: No communication history recorded

**Cause:** Communications not being logged or A2A not working.

**Solutions:**

1. **Check communications exist:**
```python
comms = crew_manager.get_crew_communications(crew_id)
print(f"Total communications: {len(comms)}")
```

2. **Enable communication logging:**
```python
# In server configuration
LOG_LEVEL = "DEBUG"  # To see all communications
```

3. **Verify task actually ran:**
```python
result = crew_manager.execute_crew_task(crew_id, task)
print(f"Task status: {result['status']}")
# Status should be 'completed' for communications to occur
```

## Memory Issues

### Issue: Agent memory usage growing too large

**Cause:** Continuous learning without cleanup.

**Solutions:**

1. **Clear old memory periodically:**
```python
# Clear working memory (current session)
agent.clear_memory("working")

# Clear old episodic memories
agent.memory.forget_old_events(days=30)

# Keep only recent knowledge
agent.memory.cleanup()
```

2. **Monitor memory size:**
```python
memory = agent.get_memory()
print(f"Working: {len(memory['working'])} items")
print(f"Episodic: {len(memory['episodic'])} items")
print(f"Semantic: {len(memory['semantic'])} items")
```

3. **Use memory limits:**
```python
agent.memory.set_limit(
    working_max=100,
    episodic_max=1000,
    semantic_max=5000
)
```

### Issue: Memory not persisting between sessions

**Cause:** Memory not being saved or loaded correctly.

**Solutions:**

1. **Explicitly save:**
```python
# At end of session
agent.memory.persist()

# Or use context manager
with agent.persistent_session():
    # Your code here
    pass  # Automatically persists
```

2. **Verify persistence:**
```python
# Save ID for later
agent_id = agent.id

# Later session
from core.agent import load_agent

agent = load_agent(agent_id)  # Loads with persisted memory
```

3. **Check storage location:**
```python
# Memory is typically stored in
# /data/agents/{agent_id}/memory/

import os
memory_path = f"data/agents/{agent.id}/memory/"
if os.path.exists(memory_path):
    print(f"Memory files found in {memory_path}")
```

## Performance & Optimization

### Issue: Slow response times

**Cause:** LLM latency, network issues, or inefficient code.

**Solutions:**

1. **Use faster LLM:**
```python
agent = Agent(
    persona=persona,
    model="gpt-4o-mini"  # Faster than full GPT-4
)
# Or Ollama for local execution
agent = Agent(
    persona=persona,
    provider="ollama",
    model="mistral"  # Fast local model
)
```

2. **Add caching:**
```python
from functools import lru_cache

class CachedAgent:
    @lru_cache(maxsize=128)
    def cached_chat(self, message: str):
        return self.agent.chat(message)
```

3. **Batch requests:**
```python
from concurrent.futures import ThreadPoolExecutor

queries = ["Query 1", "Query 2", "Query 3"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(agent.chat, queries))
```

### Issue: High memory usage

**Cause:** Large context windows, storing too much data.

**Solutions:**

1. **Reduce context size:**
```python
agent.context_size = 4096  # Instead of 8192
```

2. **Use memory management:**
```python
agent.clear_memory("working")  # Clear conversation history
agent.memory.cleanup()  # Remove old entries
```

3. **Stream responses:**
```python
# Instead of loading full response
for chunk in agent.stream_response("Query"):
    print(chunk, end='')
```

## Web UI Issues

### Issue: Studio page won't load

**Cause:** Server not running or connection issue.

**Solutions:**

1. **Check server status:**
```bash
# Should see server running
python start.py

# Or check if port is in use
netstat -an | grep 8000  # Linux/Mac
netstat -an | findstr 8000  # Windows
```

2. **Try different port:**
```bash
# Edit start.py
UVICORN_PORT=9000
python start.py

# Visit http://localhost:9000/studio
```

3. **Clear browser cache:**
- Ctrl+Shift+Delete (Chrome/Firefox)
- Or hard refresh: Ctrl+Shift+R

### Issue: Crews page shows no data

**Cause:** API not returning data or UI not loading properly.

**Solutions:**

1. **Check API endpoint:**
```bash
curl http://localhost:8000/api/crews
# Should return JSON array
```

2. **Check browser console:**
- Open DevTools (F12)
- Check Console for JavaScript errors
- Check Network tab for failed requests

3. **Verify crews exist:**
```python
from core.crew_manager import CrewManager

mgr = CrewManager()
crews = mgr.list_crews()
print(f"Total crews: {len(crews)}")
```

### Issue: Can't create agents/crews from UI

**Cause:** API error or form validation issue.

**Solutions:**

1. **Check server logs:**
```bash
# Look for error messages
python start.py 2>&1 | grep -i error
```

2. **Verify form inputs:**
- All required fields filled
- No special characters that might break JSON
- Proper format for API key

3. **Check form submission:**
- Open DevTools Network tab
- Submit form
- Check request/response details

## Getting More Help

### Resources

- **GitHub Issues:** Report bugs at [github.com/CYBERBULL123/ADgents/issues](https://github.com/CYBERBULL123/ADgents/issues)
- **Documentation:** Visit [docs/](docs/) for detailed guides
- **Community:** Join our Discord for chat support
- **Email:** contact@adgents.io for enterprise support

### Debugging Tips

1. **Enable verbose logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Use print statements:**
```python
print(f"Variable: {var}")
print(f"Type: {type(var)}")
print(f"Length: {len(var)}")
```

3. **Check Python version:**
```bash
python --version  # Should be 3.9+
```

4. **Use debugger:**
```python
import pdb
pdb.set_trace()  # Will pause execution
```

---

**Still stuck?** Please open an issue with:
- Error message (full traceback)
- Steps to reproduce
- Your environment (OS, Python version, etc.)
- What you've already tried
