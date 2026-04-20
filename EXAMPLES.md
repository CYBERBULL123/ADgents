# Examples

Complete, runnable examples for common ADgents use cases.

## Table of Contents

1. [Basic Agent Chat](#basic-agent-chat)
2. [Autonomous Task Execution](#autonomous-task-execution)
3. [Multi-Agent Crew](#multi-agent-crew)
4. [Web Framework Integration](#web-framework-integration)
5. [Data Analysis Agent](#data-analysis-agent)
6. [Research Team](#research-team)

## Basic Agent Chat

### Simple Conversation

```python
#!/usr/bin/env python
"""Simple agent conversation example."""

from core.agent import Agent
from core.persona import Persona

# Define the agent's personality
assistant_persona = Persona(
    name="Alex",
    role="Personal Assistant",
    expertise_domains=["Task Management", "General Knowledge"],
    personality_traits=["helpful", "friendly", "organized"],
    autonomy_level=2,
    communication_style="conversational"
)

# Create the agent
assistant = Agent(persona=assistant_persona)

# Have a conversation
print("🤖 Assistant:", assistant.chat("Hello! What can you help me with?"))

conversation = [
    "What's a good way to organize my day?",
    "Can you help me prioritize these tasks: email, meeting, coding, exercise?",
    "What time should I schedule the meeting?",
]

for user_input in conversation:
    print(f"👤 You: {user_input}")
    response = assistant.chat(user_input)
    print(f"🤖 Assistant: {response}\n")
```

### Learning and Remembering

```python
#!/usr/bin/env python
"""Agent learning and memory example."""

from core.agent import Agent
from core.persona import Persona

# Create an agent
agent = Agent(
    persona=Persona(
        name="Domain Expert",
        role="Knowledge Assistant"
    )
)

# Teach the agent about your company
print("Teaching agent about the company...")
agent.learn("Our company is TechCorp, founded in 2020")
agent.learn("We specialize in cloud infrastructure")
agent.learn("We have 150 employees across 5 locations")
agent.learn("Our main product is CloudOS platform")
agent.learn("We use Python, Go, and Rust for development")

# Record a past event
agent.remember("Launched CloudOS v2.0 on 2024-03-01")
agent.remember("Hit 10,000 active users on 2024-02-15")

# Now ask questions - agent will use learned knowledge
print("\nQuerying agent with learned knowledge...")
response = agent.chat(
    "What does our company do and what technologies do we use?"
)
print(f"Agent: {response}")

# Ask about remembered events
response = agent.chat("What major milestones have we reached?")
print(f"Agent: {response}")
```

## Autonomous Task Execution

### Research Task

```python
#!/usr/bin/env python
"""Autonomous research task example."""

import asyncio
from core.agent import Agent
from core.persona import Persona

async def research_example():
    """Run a research task autonomously."""
    
    researcher = Agent(
        persona=Persona(
            name="Dr. Research",
            role="Research Scientist",
            expertise_domains=["AI", "Machine Learning", "Technology"],
            autonomy_level=4,  # Highly autonomous
            verbosity="detailed"
        )
    )
    
    print("Starting autonomous research task...\n")
    
    result = await researcher.run_task(
        task="Research the current state of AI in healthcare. "
             "Find at least 3 recent applications and their impact.",
        max_iterations=5
    )
    
    print(f"Status: {result['status']}")
    print(f"\nResult:\n{result['result']}")
    print(f"\nSteps taken: {len(result.get('steps', []))}")

# Run
asyncio.run(research_example())
```

### Code Generation Task

```python
#!/usr/bin/env python
"""Code generation task example."""

import asyncio
from core.agent import Agent
from core.persona import Persona

async def coding_task():
    """Generate Python code autonomously."""
    
    engineer = Agent(
        persona=Persona(
            name="Code Generator",
            role="Senior Python Developer",
            expertise_domains=["Python", "Software Engineering"],
            autonomy_level=4
        )
    )
    
    result = await engineer.run_task(
        task="Write a Python function to parse a CSV file, "
             "calculate statistics (mean, median, std dev) for numeric columns, "
             "and return results as a dictionary. "
             "Include error handling.",
        max_iterations=4
    )
    
    print("Generated Code:")
    print(result['result'])

asyncio.run(coding_task())
```

## Multi-Agent Crew

### Marketing Team Crew

```python
#!/usr/bin/env python
"""Multi-agent marketing team example."""

import asyncio
from core.agent import Agent
from core.persona import Persona
from core.crew_manager import CrewManager

async def marketing_crew_example():
    """Create and run a marketing team."""
    
    # Create individual agents
    content_writer = Agent(
        persona=Persona(
            name="Sarah",
            role="Content Writer",
            expertise_domains=["Copywriting", "Content Strategy"],
            autonomy_level=3
        )
    )
    
    social_media_expert = Agent(
        persona=Persona(
            name="Marcus",
            role="Social Media Manager",
            expertise_domains=["Social Media", "Community Engagement"],
            autonomy_level=3
        )
    )
    
    data_analyst = Agent(
        persona=Persona(
            name="Lisa",
            role="Marketing Analyst",
            expertise_domains=["Data Analysis", "Marketing Metrics"],
            autonomy_level=2
        )
    )
    
    # Create crew
    crew_manager = CrewManager()
    
    marketing_crew = crew_manager.create_crew(
        name="Marketing Team",
        description="Team responsible for content and social media strategy",
        organization="marketing",
        members=[
            {
                "agent_id": content_writer.id,
                "agent_name": "Sarah",
                "role": "lead",
                "responsibilities": ["Content strategy", "Writing", "Planning"]
            },
            {
                "agent_id": social_media_expert.id,
                "agent_name": "Marcus",
                "role": "contributor",
                "responsibilities": ["Social posting", "Engagement", "Community"]
            },
            {
                "agent_id": data_analyst.id,
                "agent_name": "Lisa",
                "role": "reviewer",
                "responsibilities": ["Analytics", "Reporting", "Optimization"]
            }
        ]
    )
    
    print(f"Created crew: {marketing_crew.name}")
    print(f"Members: {[m['agent_name'] for m in marketing_crew.members]}")
    
    # Execute crew task
    print("\nExecuting crew task...")
    result = await crew_manager.execute_crew_task_async(
        crew_id=marketing_crew.id,
        task="Create a social media campaign for our new product launch. "
             "Coordinate across writing, posting, and analytics."
    )
    
    print(f"Status: {result['status']}")
    print(f"Output: {result['output']}")

asyncio.run(marketing_crew_example())
```

## Web Framework Integration

### FastAPI Integration

```python
#!/usr/bin/env python
"""FastAPI integration example."""

from fastapi import FastAPI
from pydantic import BaseModel
from core.agent import Agent
from core.persona import Persona

app = FastAPI(title="ADgents API")

# Create agents at startup
@app.on_event("startup")
async def startup():
    """Initialize agents on startup."""
    global assistant, analyst
    
    assistant = Agent(
        persona=Persona(
            name="API Assistant",
            role="API Helper"
        )
    )
    
    analyst = Agent(
        persona=Persona(
            name="Data Analyst",
            role="Analytics Expert",
            expertise_domains=["Data Analysis", "Statistics"]
        )
    )

# Request/Response models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class AnalysisRequest(BaseModel):
    data: list[float]
    analysis_type: str  # "summary", "trend", "anomaly"

# Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """Chat with the assistant."""
    response = assistant.chat(request.message)
    return ChatResponse(response=response)

@app.post("/analyze", response_model=dict)
async def analyze(request: AnalysisRequest):
    """Analyze data."""
    prompt = f"""
    Perform {request.analysis_type} analysis on: {request.data}
    Provide insights and recommendations.
    """
    result = await analyst.run_task(prompt)
    return {
        "analysis_type": request.analysis_type,
        "result": result['result'],
        "status": result['status']
    }

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}

# Run with: uvicorn script:app --reload
```

## Data Analysis Agent

### Pandas Data Analysis

```python
#!/usr/bin/env python
"""Data analysis agent example."""

import pandas as pd
import asyncio
from core.agent import Agent
from core.persona import Persona

async def data_analysis_example():
    """Analyze data using an agent."""
    
    # Create sample data
    data = {
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'Sales': [4000, 3000, 2000, 2780, 1890, 2390],
        'Customers': [240, 221, 229, 200, 208, 250],
        'Region': ['US', 'US', 'EU', 'EU', 'Asia', 'Asia']
    }
    df = pd.DataFrame(data)
    
    # Create analyst
    analyst = Agent(
        persona=Persona(
            name="Data Analyst",
            role="Business Analyst",
            expertise_domains=["Data Analysis", "Business Intelligence"],
            autonomy_level=3
        )
    )
    
    # Teach about the data
    analyst.learn(f"I have sales data with {len(df)} months of records")
    analyst.learn(f"Columns: {', '.join(df.columns.tolist())}")
    analyst.learn(f"Data summary:\n{df.describe()}")
    analyst.learn(f"High sales month: {df.loc[df['Sales'].idxmax(), 'Month']}")
    analyst.learn(f"Low sales month: {df.loc[df['Sales'].idxmin(), 'Month']}")
    
    # Ask analysis questions
    queries = [
        "What's the trend in sales over time?",
        "Which region has the best customer-to-sales ratio?",
        "What recommendations would you make?",
    ]
    
    print("Data Analysis Session\n" + "="*40)
    for query in queries:
        print(f"\nQuestion: {query}")
        response = analyst.chat(query)
        print(f"Answer: {response}")

asyncio.run(data_analysis_example())
```

## Research Team

### Coordinated Research Project

```python
#!/usr/bin/env python
"""Coordinated research team example."""

import asyncio
from core.agent import Agent
from core.persona import Persona
from core.crew_manager import CrewManager

async def research_project():
    """Run a coordinated research project with multiple agents."""
    
    # Create specialized researchers
    literature_reviewer = Agent(
        persona=Persona(
            name="Dr. Literature",
            role="Literature Reviewer",
            expertise_domains=["Research", "Academic Writing"],
            autonomy_level=3
        )
    )
    
    data_scientist = Agent(
        persona=Persona(
            name="Prof. Data",
            role="Data Scientist",
            expertise_domains=["Data Science", "Statistics"],
            autonomy_level=3
        )
    )
    
    technical_writer = Agent(
        persona=Persona(
            name="Dr. Write",
            role="Technical Writer",
            expertise_domains=["Technical Writing", "Documentation"],
            autonomy_level=2
        )
    )
    
    # Create research crew
    crew_manager = CrewManager()
    
    research_crew = crew_manager.create_crew(
        name="AI Research Team",
        description="Team researching applications of AI in healthcare",
        organization="research",
        members=[
            {
                "agent_id": literature_reviewer.id,
                "agent_name": "Dr. Literature",
                "role": "lead"
            },
            {
                "agent_id": data_scientist.id,
                "agent_name": "Prof. Data",
                "role": "contributor"
            },
            {
                "agent_id": technical_writer.id,
                "agent_name": "Dr. Write",
                "role": "reviewer"
            }
        ]
    )
    
    # Coordinate research
    print("Starting research project...\n")
    
    # Phase 1: Literature Review
    lit_result = await literature_reviewer.run_task(
        "Review recent literature on AI applications in healthcare diagnosis",
        max_iterations=3
    )
    print(f"Literature Review Result:\n{lit_result['result']}\n")
    
    # Phase 2: Data Analysis
    data_result = await data_scientist.run_task(
        "Analyze the effectiveness metrics mentioned in AI healthcare research",
        max_iterations=3
    )
    print(f"Data Analysis Result:\n{data_result['result']}\n")
    
    # Phase 3: Synthesis
    crew_task = await crew_manager.execute_crew_task_async(
        crew_id=research_crew.id,
        task="Synthesize research findings into a comprehensive report on AI in healthcare"
    )
    
    print(f"Final Report:\n{crew_task['output']}")

asyncio.run(research_project())
```

## Real-World Integration: Customer Support

```python
#!/usr/bin/env python
"""Customer support chatbot using ADgents."""

import asyncio
from core.agent import Agent
from core.persona import Persona

async def customer_support():
    """Run a customer support agent."""
    
    support_agent = Agent(
        persona=Persona(
            name="Support Team",
            role="Customer Support Representative",
            expertise_domains=["Customer Service", "Product Knowledge"],
            communication_style="friendly and helpful",
            tone="professional",
            autonomy_level=3,
            personality_traits=["patient", "helpful", "knowledgeable"]
        )
    )
    
    # Train the agent about products
    support_agent.learn("Product: CloudOS - Cloud operating system")
    support_agent.learn("Product: DataVault - Secure data storage")
    support_agent.learn("Product: Analytics Pro - Business analytics tool")
    support_agent.learn("Support hours: 24/7")
    support_agent.learn("Policy: Free support for first 30 days")
    support_agent.learn("Policy: Premium support available for $99/month")
    
    # Simulate support interactions
    customer_queries = [
        "How do I get started with CloudOS?",
        "I'm having trouble with authentication",
        "Do you offer training for your products?",
        "What's included in premium support?"
    ]
    
    print("Customer Support Session\n" + "="*40 + "\n")
    
    for query in customer_queries:
        print(f"Customer: {query}")
        response = support_agent.chat(query)
        print(f"Support Agent: {response}\n")

asyncio.run(customer_support())
```

## Running the Examples

### Prerequisites
```bash
pip install adgents pandas
export USING_MODEL=gemini
export GEMINI_API_KEY=your_api_key_here
```

### Run an Example
```bash
python examples/basic_chat.py
python examples/research_task.py
python examples/marketing_crew.py
```

## More Examples

Check the `examples/` directory in the repository for:
- Complete runnable scripts
- Additional patterns and use cases
- Benchmarks and performance examples
- Integration templates for popular frameworks

---

Have a use case not covered here? [Open an issue](https://github.com/CYBERBULL123/ADgents/issues) and we'll add it!
