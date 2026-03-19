# API Reference

Complete reference for the ADgents Python API and REST endpoints.

## Python API

### Core Classes

#### `Agent`

Main class for creating and interacting with AI agents.

```python
from core.agent import Agent
from core.persona import Persona

# Initialize with a persona
persona = Persona(
    name="Research Bot",
    role="Research Assistant",
    expertise_domains=["AI", "Machine Learning"],
    autonomy_level=3
)
agent = Agent(persona=persona)
```

**Methods:**

##### `chat(message: str) -> str`
Have a conversational interaction with the agent.

```python
response = agent.chat("What is machine learning?")
print(response)
```

##### `run_task(task: str, max_iterations: int = 5) -> TaskResult`
Execute an autonomous task with the ReAct loop.

```python
result = agent.run_task(
    task="Research the top 3 AI frameworks and compare them",
    max_iterations=5
)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

**Returns:**
- `status`: "completed", "thinking", or "failed"
- `result`: The final output
- `steps`: List of reasoning steps

##### `learn(knowledge: str) -> None`
Add semantic knowledge to the agent's memory.

```python
agent.learn("The company uses Python and FastAPI")
agent.learn("We follow TDD practices")
```

##### `remember(event: str) -> None`
Record an episodic memory (something that happened).

```python
agent.remember("I completed the quarterly report on 2024-03-19")
```

##### `get_memory() -> Dict`
Retrieve the agent's current memory state.

```python
memory = agent.get_memory()
print(memory)
# {
#     "working": {...},
#     "episodic": {...},
#     "semantic": {...}
# }
```

##### `clear_memory(memory_type: str = "all") -> None`
Clear memory. Types: "working", "episodic", "semantic", or "all".

```python
agent.clear_memory("working")  # Clear current session
agent.clear_memory("all")      # Clear everything
```

#### `Persona`

Defines an agent's identity and behavior.

```python
from core.persona import Persona

persona = Persona(
    # Identity
    name="Dr. Elena",
    role="Data Scientist",
    avatar="👩‍🔬",
    
    # Personality
    personality_traits=["analytical", "curious", "thorough"],
    communication_style="technical and precise",
    tone="professional",
    backstory="PhD in ML with 10 years of industry experience",
    
    # Expertise
    expertise_domains=["Machine Learning", "Statistics", "Python"],
    skills=["data_analysis", "model_training", "visualization"],
    knowledge_focus=["Deep Learning", "NLP"],
    
    # Behavior
    autonomy_level=4,  # 1-5: how independent
    verbosity="detailed",
    creativity=0.7,  # 0.0-1.0
    
    # Goals
    primary_goals=["Help clients understand their data", "Build accurate models"],
    values=["accuracy", "transparency", "reproducibility"]
)
```

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "Agent" | Agent's name |
| `role` | str | "Assistant" | Agent's role/title |
| `avatar` | str | "🤖" | Unicode emoji |
| `personality_traits` | List[str] | [] | Personality characteristics |
| `communication_style` | str | "professional" | How agent communicates |
| `tone` | str | "neutral" | Formal, casual, friendly, technical |
| `autonomy_level` | int | 3 | 1-5 scale |
| `verbosity` | str | "balanced" | concise, balanced, detailed |
| `creativity` | float | 0.7 | 0.0-1.0, higher = more creative |
| `expertise_domains` | List[str] | [] | Areas of expertise |
| `skills` | List[str] | [] | Available skills |
| `knowledge_focus` | List[str] | [] | Topics they know deeply |

#### `CrewManager`

Manage agents working together as a team.

```python
from core.crew_manager import CrewManager

crew_mgr = CrewManager()
```

**Methods:**

##### `create_crew(name: str, description: str, organization: str, members: List[Dict], communication_protocol: str = "a2a") -> CrewConfig`

```python
crew = crew_mgr.create_crew(
    name="Research Squad",
    description="Team for market research",
    organization="marketing",
    members=[
        {
            "agent_id": agent1.id,
            "agent_name": "Analyst",
            "role": "lead"
        },
        {
            "agent_id": agent2.id,
            "agent_name": "Writer",
            "role": "contributor"
        }
    ],
    communication_protocol="a2a"
)
```

##### `list_crews() -> List[CrewConfig]`

```python
crews = crew_mgr.list_crews()
for crew in crews:
    print(f"{crew.name}: {len(crew.members)} members")
```

##### `get_crew(crew_id: str) -> Optional[CrewConfig]`

```python
crew = crew_mgr.get_crew(crew_id)
```

##### `delete_crew(crew_id: str) -> bool`

```python
success = crew_mgr.delete_crew(crew_id)
```

##### `create_organization(name: str, description: str = "") -> Dict`

```python
org = crew_mgr.create_organization(
    "Marketing Department",
    "All marketing teams"
)
```

### Memory System

#### Working Memory
Current conversation context (resets per session).

```python
# Automatic - maintained across chat calls
response = agent.chat("Remember: use metric system")
response = agent.chat("Convert 5 feet to metric")  # Agent knows the context
```

#### Episodic Memory
Past events and experiences.

```python
agent.remember("Completed XYZ project on 2024-03-01")
agent.remember("Client requested real-time updates")

# Retrieve episodic memories
memories = agent.memory.episodic
```

#### Semantic Memory
Rules, facts, and learned knowledge.

```python
agent.learn("Rule: Always verify data sources")
agent.learn("Fact: Company uses PostgreSQL for main database")
agent.learn("Pattern: Q4 always has high demand")
```

### Skills System

#### Using Built-in Skills

Skills are automatically available:

```python
# Agent uses these skills automatically in tasks
# - web_search: Find information online
# - code_execution: Run Python code
# - file_io: Read/write files
# - math_calculation: Complex math
# - data_analysis: Process datasets

result = agent.run_task(
    "Analyze this CSV file and create a summary"
)
# Agent will automatically use file_io and data_analysis
```

#### Creating Custom Skills

```python
from core.skills import register_skill

@register_skill(
    name="send_email",
    description="Send an email to a recipient",
    parameters={
        "to": "Email address",
        "subject": "Email subject",
        "body": "Email body"
    }
)
def send_email(to: str, subject: str, body: str) -> bool:
    # Implementation
    import smtplib
    # ... send email logic
    return True

# Now agents can use it
agent.run_task("Send an email to john@example.com about the quarterly report")
```

## REST API Endpoints

### Agent Endpoints

#### `POST /api/agents`
Create a new agent.

**Request:**
```json
{
    "template": "researcher",  // or provide custom persona
    "name": "Custom Agent",
    "role": "Specialist",
    "model": "gemini-1.5-flash"
}
```

**Response:**
```json
{
    "success": true,
    "agent": {
        "id": "uuid",
        "name": "Custom Agent",
        "persona": {...},
        "created_at": "2024-03-19T10:00:00Z"
    }
}
```

#### `GET /api/agents`
List all agents.

**Response:**
```json
{
    "success": true,
    "agents": [...],
    "count": 5
}
```

#### `GET /api/agents/{agent_id}`
Get agent details.

#### `DELETE /api/agents/{agent_id}`
Delete an agent.

#### `POST /api/agents/{agent_id}/chat`
Chat with an agent.

**Request:**
```json
{
    "message": "What is the capital of France?"
}
```

**Response:**
```json
{
    "success": true,
    "response": "The capital of France is Paris..."
}
```

#### `POST /api/agents/{agent_id}/task`
Run an autonomous task.

**Request:**
```json
{
    "task": "Research AI trends",
    "max_iterations": 5
}
```

**Response:**
```json
{
    "success": true,
    "result": {
        "status": "completed",
        "output": "...",
        "steps": [...]
    }
}
```

#### `POST /api/agents/{agent_id}/learn`
Add knowledge to agent.

**Request:**
```json
{
    "knowledge": "The company uses Python and FastAPI"
}
```

### Crew Endpoints

#### `POST /api/crews/create`
Create a crew.

**Request:**
```json
{
    "name": "Research Team",
    "description": "Market research squad",
    "organization": "marketing",
    "members": [
        {
            "agent_id": "uuid",
            "agent_name": "Analyst",
            "role": "lead"
        }
    ],
    "communication_protocol": "a2a"
}
```

#### `GET /api/crews`
List all crews.

#### `GET /api/crews/{crew_id}`
Get crew details.

#### `DELETE /api/crews/{crew_id}`
Delete a crew.

#### `POST /api/crews/{crew_id}/execute`
Execute a crew task autonomously.

**Request:**
```json
{
    "task": "Analyze market trends",
    "max_iterations": 5
}
```

**Response:**
```json
{
    "success": true,
    "result": {
        "output": "...",
        "agents_involved": ["Agent1", "Agent2"]
    }
}
```

### Organization Endpoints

#### `POST /api/organizations/create`
Create an organization.

**Query Parameters:**
- `name` (required): Organization name
- `description` (optional): Description

#### `GET /api/organizations`
List all organizations.

#### `GET /api/organizations/{org_id}`
Get organization details with statistics.

### A2A Communication Endpoints

#### `GET /api/a2a/communications/{crew_id}`
Get all agent-to-agent communications in a crew.

**Response:**
```json
{
    "success": true,
    "communications": [
        {
            "from": "agent1_name",
            "to": "agent2_name",
            "message": {...},
            "timestamp": "2024-03-19T10:05:00Z"
        }
    ]
}
```

### Health & Status

#### `GET /api/health`
Get system health status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-03-19T10:00:00Z",
    "agents": 5,
    "llm_providers": ["gemini", "openai"],
    "skills": 12
}
```

## Error Handling

All endpoints return error responses in this format:

```json
{
    "success": false,
    "error": "Description of error"
}
```

**Common status codes:**
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Not found (agent/crew doesn't exist)
- `500`: Server error

**Example error handling:**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/agents/invalid/chat",
        json={"message": "Hello"}
    )
    
    if response.status_code == 404:
        print("Agent not found")
    elif response.status_code == 200:
        data = response.json()
        print(data["response"])
```

## Async Support

All API methods support async:

```python
import asyncio
from core.agent import Agent

async def main():
    agent = Agent(persona=persona)
    response = await agent.chat_async(
        "What is artificial intelligence?"
    )
    print(response)

asyncio.run(main())
```

## Rate Limiting

Default rate limits:
- 100 requests per minute per IP
- 50 concurrent agents per server

Customize in configuration:

```python
from server import app
from slowapi.limit import limits

@limits(key_func=get_remote_address, limit="500/minute")
async def create_agent(...):
    ...
```

## Next Steps

- [Integration Guide](integration.md) - Integrate into your project
- [Examples](examples.md) - Code examples
- [Crews Guide](crew.md) - Multi-agent coordination
