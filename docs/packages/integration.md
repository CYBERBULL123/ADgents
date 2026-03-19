# Integration Guide

Learn how to integrate ADgents into your Python projects.

## Quick Start

### 1. Install ADgents

```bash
pip install adgents
```

Or install from source for development:

```bash
git clone https://github.com/yourusername/ADgents.git
cd ADgents
pip install -e .
```

### 2. Set Up Environment

Create a `.env` file:

```env
# LLM Configuration
USING_MODEL=gemini
GEMINI_API_KEY=your_api_key_here

# Optional: Other providers
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Server Configuration
UVICORN_HOST=127.0.0.1
UVICORN_PORT=8000

# Development
ENV=development
LOG_LEVEL=INFO
```

### 3. Create Your First Agent

```python
from core.agent import Agent
from core.persona import Persona

# Define an agent's personality
researcher = Persona(
    name="Dr. Research",
    role="Research Assistant",
    expertise_domains=["AI", "Technology"],
    autonomy_level=3,
    communication_style="technical"
)

# Create the agent
agent = Agent(persona=researcher)

# Chat with it
response = agent.chat("What are the latest AI trends?")
print(response)
```

## Common Integration Patterns

### Pattern 1: Single Agent for Specific Task

Best for: Delegating a single responsibility to an AI agent.

```python
from core.agent import Agent
from core.persona import Persona

class DataAnalyzer:
    def __init__(self):
        self.agent = Agent(
            persona=Persona(
                name="Data Analyst",
                role="Data Analysis Expert",
                expertise_domains=["Data Science", "Statistics"]
            )
        )
    
    def analyze(self, query: str) -> str:
        """Analyze data using the agent."""
        return self.agent.chat(
            f"Please analyze: {query}"
        )

# Usage
analyzer = DataAnalyzer()
result = analyzer.analyze("Compare sales by region in my Q1 data")
print(result)
```

### Pattern 2: Multi-Agent Crew for Complex Tasks

Best for: Complex problems requiring multiple perspectives.

```python
from core.crew_manager import CrewManager
from core.agent import Agent
from core.persona import Persona

# Create individual agents
agents = [
    Agent(persona=Persona(
        name="Sarah",
        role="Research Lead",
        expertise_domains=["Market Research", "Analysis"]
    )),
    Agent(persona=Persona(
        name="Mike",
        role="Content Writer",
        expertise_domains=["Technical Writing", "Documentation"]
    )),
    Agent(persona=Persona(
        name="Lisa",
        role="Quality Reviewer",
        expertise_domains=["Quality Assurance", "Verification"]
    ))
]

# Organize them in a crew
crew_mgr = CrewManager()
crew = crew_mgr.create_crew(
    name="Content Creation Team",
    description="Research, write, and verify content",
    organization="content",
    members=[
        {"agent_id": agents[0].id, "agent_name": "Sarah", "role": "lead"},
        {"agent_id": agents[1].id, "agent_name": "Mike", "role": "contributor"},
        {"agent_id": agents[2].id, "agent_name": "Lisa", "role": "reviewer"}
    ]
)

# Execute a complex task
result = crew_mgr.get_crew(crew.id)
# The crew will coordinate among members
print(f"Crew created: {result.name}")
```

### Pattern 3: Agent with Memory for Long-Running Applications

Best for: Chatbots, assistants, and systems that need context.

```python
from core.agent import Agent
from core.persona import Persona

class ContextualAssistant:
    def __init__(self):
        self.agent = Agent(
            persona=Persona(
                name="Alex",
                role="Personal Assistant",
                autonomy_level=4
            )
        )
    
    def teach(self, fact: str):
        """Teach the agent new information."""
        self.agent.learn(fact)
        print(f"Learned: {fact}")
    
    def reference(self, query: str) -> str:
        """Query with learned context."""
        return self.agent.chat(f"Using what I've taught you: {query}")
    
    def log_event(self, event: str):
        """Log something that happened."""
        self.agent.remember(event)
        print(f"Remembered: {event}")

# Usage
assistant = ContextualAssistant()

# Teach the assistant
assistant.teach("Our company uses Python and JavaScript")
assistant.teach("We practice test-driven development")
assistant.log_event("Completed sprint on 2024-03-15")

# Get contextual responses
response = assistant.reference(
    "What programming languages should we use for new projects?"
)
print(response)
```

### Pattern 4: Autonomous Task Processing

Best for: Running complex, multi-step tasks autonomously.

```python
from core.agent import Agent
from core.persona import Persona

class ResearchBot:
    def __init__(self):
        self.agent = Agent(
            persona=Persona(
                name="Researcher",
                role="Research Agent",
                autonomy_level=5,  # Highly autonomous
                expertise_domains=["Research", "Analysis"]
            )
        )
    
    async def research_topic(self, topic: str):
        """Research a topic autonomously."""
        result = await self.agent.run_task(
            task=f"Thoroughly research {topic}. Find sources, analyze information, and provide conclusions.",
            max_iterations=5
        )
        return result

# Usage
import asyncio

async def main():
    bot = ResearchBot()
    result = await bot.research_topic("The future of AI in healthcare")
    
    print(f"Status: {result.status}")
    print(f"Result: {result.result}")
    print(f"Steps taken: {len(result.steps)}")

asyncio.run(main())
```

## Integration with Web Frameworks

### FastAPI Integration

```python
from fastapi import FastAPI
from core.agent import Agent
from core.persona import Persona

app = FastAPI()

# Create agent at startup
agent = Agent(
    persona=Persona(
        name="API Agent",
        role="API Assistant"
    )
)

@app.post("/ask")
async def ask_agent(question: str):
    """Ask the agent a question."""
    response = agent.chat(question)
    return {"question": question, "answer": response}

@app.post("/analyze")
async def analyze_data(data: str):
    """Analyze data using the agent."""
    result = await agent.run_task(
        task=f"Analyze and summarize: {data}",
        max_iterations=3
    )
    return {"analysis": result.result}

# Run: uvicorn script:app --reload
```

### Flask Integration

```python
from flask import Flask, request, jsonify
from core.agent import Agent
from core.persona import Persona

app = Flask(__name__)

agent = Agent(
    persona=Persona(
        name="Flask Agent",
        role="Flask Assistant"
    )
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message")
    response = agent.chat(message)
    return jsonify({"response": response})

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    topic = data.get("topic")
    result = agent.run_task(
        task=f"Analyze: {topic}",
        max_iterations=5
    )
    return jsonify({
        "status": result.status,
        "result": result.result
    })

if __name__ == "__main__":
    app.run(debug=True)
```

## Integration with Data Processing

### Pandas + ADgents

```python
import pandas as pd
from core.agent import Agent
from core.persona import Persona

class DataFrameAdvisor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.agent = Agent(
            persona=Persona(
                name="Data Advisor",
                role="Data Science Expert",
                expertise_domains=["Data Analysis", "Statistics"]
            )
        )
        
        # Teach the agent about the data
        self.agent.learn(f"I have a dataset with columns: {', '.join(df.columns)}")
        self.agent.learn(f"The dataset has {len(df)} rows and {len(df.columns)} columns")
        self.agent.learn(f"Data types: {df.dtypes.to_dict()}")
    
    def get_insight(self, question: str) -> str:
        """Get an insight about the data."""
        return self.agent.chat(f"Based on the data I described: {question}")

# Usage
df = pd.read_csv("sales_data.csv")
advisor = DataFrameAdvisor(df)

insight = advisor.get_insight("What patterns do you see in the data?")
print(insight)

recommendation = advisor.get_insight("What improvements would you recommend?")
print(recommendation)
```

## REST API Client Integration

### Using httpx (Async)

```python
import httpx
import json

class ADgentsClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def chat(self, agent_id: str, message: str) -> str:
        """Chat with an agent via REST API."""
        response = await self.client.post(
            f"{self.base_url}/api/agents/{agent_id}/chat",
            json={"message": message}
        )
        data = response.json()
        return data["response"]
    
    async def create_agent(self, name: str, role: str):
        """Create a new agent via REST API."""
        response = await self.client.post(
            f"{self.base_url}/api/agents",
            json={"name": name, "role": role}
        )
        return response.json()["agent"]
    
    async def run_task(self, agent_id: str, task: str):
        """Run a task on an agent."""
        response = await self.client.post(
            f"{self.base_url}/api/agents/{agent_id}/task",
            json={"task": task, "max_iterations": 5}
        )
        return response.json()["result"]

# Usage
import asyncio

async def main():
    client = ADgentsClient()
    
    # Create agent
    agent = await client.create_agent("Research Bot", "Researcher")
    agent_id = agent["id"]
    
    # Chat with it
    response = await client.chat(agent_id, "What is machine learning?")
    print(response)
    
    # Run a task
    result = await client.run_task(agent_id, "Research Python frameworks")
    print(result["output"])

asyncio.run(main())
```

### Using requests (Sync)

```python
import requests
import json

class ADgentsClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def chat(self, agent_id: str, message: str) -> str:
        """Chat with an agent."""
        response = requests.post(
            f"{self.base_url}/api/agents/{agent_id}/chat",
            json={"message": message}
        )
        return response.json()["response"]
    
    def list_agents(self):
        """List all agents."""
        response = requests.get(f"{self.base_url}/api/agents")
        return response.json()["agents"]
    
    def create_crew(self, name: str, members: list):
        """Create a crew."""
        response = requests.post(
            f"{self.base_url}/api/crews/create",
            json={
                "name": name,
                "description": f"Crew: {name}",
                "organization": "default",
                "members": members
            }
        )
        return response.json()["crew"]

# Usage
client = ADgentsClient()
agents = client.list_agents()
print(f"Available agents: {len(agents)}")
```

## Custom Skills Integration

### Creating Reusable Skills

```python
from core.skills import register_skill

@register_skill(
    name="fetch_weather",
    description="Get current weather for a location",
    parameters={
        "location": "City name",
        "format": "celsius or fahrenheit"
    }
)
def fetch_weather(location: str, format: str = "celsius") -> str:
    # Import weather library
    import requests
    # Get weather (example)
    # return weather_data
    pass

@register_skill(
    name="send_notification",
    description="Send a notification to the user",
    parameters={
        "title": "Notification title",
        "message": "Notification message",
        "priority": "low, medium, or high"
    }
)
def send_notification(title: str, message: str, priority: str = "medium") -> bool:
    # Send notification logic
    print(f"[{priority.upper()}] {title}: {message}")
    return True

# Now agents can use these skills
from core.agent import Agent

agent = Agent(persona=Persona(name="Helper", role="Assistant"))

# Agent will automatically use these skills when needed
response = agent.chat("Get the weather in Paris and notify me if it's rain expected")
```

## Environment Management

### Configuration Profiles

```python
from pathlib import Path
import os
from dotenv import load_dotenv

class Config:
    """Base configuration."""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    UVICORN_RELOAD = True
    
class ProductionConfig(Config):
    """Production configuration."""
    UVICORN_WORKERS = 4
    LOG_LEVEL = "WARNING"

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    LOG_LEVEL = "DEBUG"

# Load configuration
def get_config():
    env = os.getenv("ENV", "development")
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }
    return config_map.get(env, DevelopmentConfig)

config = get_config()
```

## Error Handling

```python
from core.agent import Agent
from core.exceptions import AgentError, TaskError

class SafeAgentWrapper:
    def __init__(self, agent: Agent):
        self.agent = agent
    
    def safe_chat(self, message: str, max_retries: int = 3) -> str:
        """Chat with retry logic."""
        for attempt in range(max_retries):
            try:
                return self.agent.chat(message)
            except AgentError as e:
                print(f"Agent error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
    
    def safe_task(self, task: str) -> dict:
        """Run task with error handling."""
        try:
            result = self.agent.run_task(task)
            return {
                "success": True,
                "status": result.status,
                "result": result.result
            }
        except TaskError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": "An unexpected error occurred"
            }

# Usage
wrapper = SafeAgentWrapper(agent)
response = wrapper.safe_chat("Hello!")
```

## Testing Agents

```python
import pytest
from core.agent import Agent
from core.persona import Persona

@pytest.fixture
def test_agent():
    """Create a test agent."""
    return Agent(
        persona=Persona(
            name="Test Agent",
            role="Tester"
        )
    )

def test_agent_chat(test_agent):
    """Test agent chatting."""
    response = test_agent.chat("What is 2 + 2?")
    assert response is not None
    assert len(response) > 0

@pytest.mark.asyncio
async def test_agent_task(test_agent):
    """Test agent task execution."""
    result = await test_agent.run_task("Count to 5")
    assert result.status in ["completed", "thinking"]

def test_agent_memory(test_agent):
    """Test agent memory."""
    test_agent.learn("Test fact")
    memory = test_agent.get_memory()
    assert "semantic" in memory
```

## Next Steps

- [API Reference](api_reference.md) - Complete API documentation
- [Crew Management](crew.md) - Advanced crew coordination
- [Advanced Features](advanced.md) - Memory systems, custom skills, LLM routing
