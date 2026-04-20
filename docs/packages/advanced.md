# Advanced Features

Deep dive into ADgents' advanced capabilities.

## Memory Systems

ADgents provides a sophisticated multi-tiered memory system.

### 1. Working Memory

Short-term context for the current session.

**Characteristics:**
- Automatically cleared after session ends
- Updated in real-time
- Limited capacity (conversation history)
- Used for immediate context

**Usage:**

```python
from core.agent import Agent
from core.persona import Persona

agent = Agent(persona=Persona(name="Assistant", role="Helper"))

# Working memory is automatic
response1 = agent.chat("Remember: I prefer metric units")
response2 = agent.chat("Convert 5 feet to metric")  # Agent uses context from response1

# Access working memory
memory = agent.memory.working
print(f"Working memory entries: {len(memory)}")
```

**Best For:**
- Maintaining conversation context
- Temporary task information
- Session-specific data

### 2. Episodic Memory

Records of events and experiences.

**Characteristics:**
- Persistent (survives sessions)
- Timestamped entries
- Event-based organization
- Automatically indexed

**Usage:**

```python
# Record experiences
agent.remember("Completed data analysis project on 2024-03-15")
agent.remember("Client expressed concern about data privacy")
agent.remember("Implemented encryption for sensitive data")

# Retrieve episodic memories
episodic = agent.memory.episodic
for event in episodic:
    print(f"{event['timestamp']}: {event['description']}")

# Clear old memories (optional cleanup)
agent.memory.forget_old_events(days=30)  # Forget events older than 30 days
```

**Best For:**
- Learning from past interactions
- Accountability and auditing
- Pattern recognition over time
- Conversation history

### 3. Semantic Memory

Facts, rules, and learned knowledge.

**Characteristics:**
- Persistent knowledge base
- Organized by topic
- Not time-dependent
- Grows with agent experience

**Usage:**

```python
# Teaching facts
agent.learn("Python is a high-level programming language")
agent.learn("The company uses PostgreSQL for main database")
agent.learn("Rule: Always verify user input before processing")

# Organize knowledge by category
agent.learn("Domain:Company::Founded:2015")
agent.learn("Domain:Company::Location:San Francisco")
agent.learn("Domain:Company::Size:150 employees")

# Retrieve semantic knowledge
semantic_knowledge = agent.memory.semantic
print(f"Total facts learned: {len(semantic_knowledge)}")

# Query specific knowledge
company_facts = agent.query_knowledge("Domain:Company")
for fact in company_facts:
    print(fact)
```

**Best For:**
- Building knowledge bases
- Storing domain expertise
- Long-term learning
- Fact retrieval

### Advanced Memory Operations

```python
class SmartMemoryAgent:
    def __init__(self, agent: Agent):
        self.agent = agent
    
    def teach_domain_knowledge(self, domain: str, facts: List[str]):
        """Systematically teach domain knowledge."""
        for fact in facts:
            self.agent.learn(f"Domain:{domain}::{fact}")
    
    def get_domain_expertise(self, domain: str) -> List[str]:
        """Retrieve all knowledge about a domain."""
        return self.agent.query_knowledge(f"Domain:{domain}")
    
    def forget_facts(self, domain: str):
        """Clear knowledge about a domain."""
        facts = self.agent.query_knowledge(f"Domain:{domain}")
        for fact in facts:
            self.agent.unlearn(fact)
    
    def export_memory(self) -> Dict:
        """Export all memory for backup."""
        return {
            "working": self.agent.memory.working,
            "episodic": self.agent.memory.episodic,
            "semantic": self.agent.memory.semantic
        }
    
    def import_memory(self, memory_export: Dict):
        """Import a memory backup."""
        self.agent.memory.import_snapshot(memory_export)

# Usage
smart_agent = SmartMemoryAgent(agent)
smart_agent.teach_domain_knowledge("Product", [
    "Name:Acme Software",
    "Price:$99/month", 
    "Features:Analytics, Reporting, API"
])

expertise = smart_agent.get_domain_expertise("Product")
print(expertise)

# Backup
backup = smart_agent.export_memory()

# Later: restore
smart_agent.import_memory(backup)
```

## Custom Skills

Extend agent capabilities with custom skills.

### Creating Skills

```python
from core.skills import register_skill
from typing import Dict, Any

@register_skill(
    name="calculate_profit_margin",
    description="Calculate profit margin from cost and revenue",
    parameters={
        "cost": "Total cost (float)",
        "revenue": "Total revenue (float)"
    },
    return_type="float"
)
def calculate_profit_margin(cost: float, revenue: float) -> float:
    """Calculate profit margin percentage."""
    if revenue == 0:
        return 0.0
    return ((revenue - cost) / revenue) * 100

# Now agents can use this skill
agent.run_task(
    "If it costs $50 to make a product and we sell it for $150, "
    "what's our profit margin?"
)

@register_skill(
    name="analyze_sentiment",
    description="Analyze sentiment of text",
    parameters={"text": "Text to analyze"},
    return_type="Dict"
)
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment using NLP."""
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        return {
            "polarity": blob.sentiment.polarity,  # -1 to 1
            "subjectivity": blob.sentiment.subjectivity,  # 0 to 1
            "classification": "positive" if blob.sentiment.polarity > 0 else "negative" if blob.sentiment.polarity < 0 else "neutral"
        }
    except ImportError:
        return {"error": "TextBlob not installed"}

# Usage
result = agent.chat(
    "Analyze sentiment: 'I love this product! It works great!'"
)
```

### Async Skills

```python
from core.skills import register_skill
import asyncio

@register_skill(
    name="fetch_api_data",
    description="Fetch data from an API",
    parameters={
        "url": "API endpoint URL",
        "timeout": "Request timeout in seconds"
    },
    async_support=True
)
async def fetch_api_data(url: str, timeout: int = 10) -> Dict:
    """Fetch data asynchronously."""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                return await response.json()
    except Exception as e:
        return {"error": str(e)}

# Usage in async context
result = await agent.run_task_async(
    "Fetch data from https://api.example.com/data"
)
```

### Conditional Skills

```python
from core.skills import register_skill

@register_skill(
    name="send_alert",
    description="Send alert if value exceeds threshold",
    parameters={
        "value": "Current value",
        "threshold": "Alert threshold",
        "alert_type": "critical|warning|info"
    },
    conditions={
        "requires": ["notification_service"],
        "enabled_in": ["production", "staging"]
    }
)
def send_alert(value: float, threshold: float, alert_type: str = "warning") -> bool:
    """Send alert notification."""
    if value > threshold:
        # Send alert logic
        print(f"[{alert_type.upper()}] Value {value} exceeds threshold {threshold}")
        return True
    return False
```

## LLM Provider Routing

Intelligently route requests to different LLM providers.

### Configuration

```python
from core.llm import configure_llm_routing

# Configure routing rules
routing_config = {
    "rules": [
        {
            "name": "fast_responses",
            "condition": {
                "task_type": "simple_query",
                "max_latency": 2000  # milliseconds
            },
            "provider": "ollama",  # Fast local model
            "model": "mistral"
        },
        {
            "name": "complex_reasoning",
            "condition": {
                "task_type": "reasoning",
                "requires_expertise": True
            },
            "provider": "gemini",  # Powerful reasoning
            "model": "gemini-1.5-pro"
        },
        {
            "name": "creative_writing",
            "condition": {
                "task_type": "creative"
            },
            "provider": "openai",  # Creative capability
            "model": "gpt-4"
        }
    ],
    "fallback_provider": "gemini"
}

configure_llm_routing(routing_config)
```

### Dynamic Provider Selection

```python
class SmartLLMRouter:
    def __init__(self):
        from core.llm import get_router
        self.router = get_router()
    
    def select_provider(self, task_description: str) -> str:
        """Select best provider for task."""
        analysis = self.router.analyze_task(task_description)
        
        if "code" in task_description.lower() and "debug" in analysis:
            return "openai"  # Better code understanding
        elif "analyze" in analysis and "data" in analysis:
            return "gemini"  # Better data analysis
        else:
            return "openai"  # Default
    
    def execute_with_best_provider(self, agent, task: str):
        """Execute task with optimal provider."""
        provider = self.select_provider(task)
        
        # Temporarily set provider
        original_provider = agent.llm_provider
        agent.llm_provider = provider
        
        try:
            result = agent.run_task(task)
        finally:
            agent.llm_provider = original_provider
        
        return result

# Usage
router = SmartLLMRouter()
result = router.execute_with_best_provider(agent, "Debug this Python code")
```

## Persona Customization

Create highly specialized personas.

```python
from core.persona import Persona

# Technical writing expert
tech_writer = Persona(
    name="Technical Documentation Expert",
    role="Technical Writer",
    avatar="📝",
    
    # Personality
    personality_traits=["precise", "detail-oriented", "patient"],
    communication_style="clear and structured",
    tone="professional and educational",
    backstory="15+ years documenting complex software systems",
    
    # Expertise
    expertise_domains=["Technical Writing", "Documentation", "Software"],
    skills=["API documentation", "User guides", "Tutorial writing", "Code examples"],
    knowledge_focus=["Cloud platforms", "Microservices", "APIs"],
    
    # Behavior
    autonomy_level=3,
    verbosity="detailed",
    creativity=0.4,  # Low creativity - focus on clarity
    
    # Goals
    primary_goals=[
        "Create clear and accurate documentation",
        "Make complex topics understandable",
        "Anticipate reader questions"
    ],
    values=["accuracy", "clarity", "completeness"]
)

agent = Agent(persona=tech_writer)
response = agent.chat("Document how to use the authentication API")

# Creative designer
creative_designer = Persona(
    name="Creative UI Designer",
    role="Product Designer",
    avatar="🎨",
    
    personality_traits=["creative", "user-focused", "innovator"],
    communication_style="visual-centric",
    tone="enthusiastic",
    expertise_domains=["UI/UX Design", "Product Design", "User Research"],
    autonomy_level=4,
    creativity=0.9,  # High creativity
    
    primary_goals=[
        "Create beautiful and intuitive interfaces",
        "Solve user problems through design"
    ]
)

designer = Agent(persona=creative_designer)
```

## Advanced Task Execution

### Multi-Step Task Orchestration

```python
class TaskOrchestrator:
    def __init__(self, crew_manager):
        self.crew_mgr = crew_mgr
        self.task_history = []
    
    async def execute_workflow(self, workflow: List[Dict]) -> Dict:
        """Execute a multi-step workflow."""
        results = {}
        
        for step in workflow:
            # Check dependencies
            if "depends_on" in step:
                for dep in step["depends_on"]:
                    if dep not in results:
                        print(f"Skipping {step['name']} - dependency {dep} not complete")
                        continue
            
            # Execute step
            crew_id = step["crew_id"]
            task = step["task"]
            
            print(f"Executing step: {step['name']}")
            result = await self.crew_mgr.execute_crew_task_async(
                crew_id=crew_id,
                task=task
            )
            
            results[step["name"]] = result
            self.task_history.append({
                "step": step["name"],
                "status": result.get("status"),
                "timestamp": datetime.now()
            })
        
        return results

# Define workflow
workflow = [
    {
        "name": "requirements",
        "crew_id": "analysis_crew",
        "task": "Gather and analyze project requirements",
        "depends_on": []
    },
    {
        "name": "design",
        "crew_id": "architecture_crew",
        "task": "Design system architecture based on requirements",
        "depends_on": ["requirements"]
    },
    {
        "name": "implementation",
        "crew_id": "dev_crew",
        "task": "Implement system according to design",
        "depends_on": ["design"]
    },
    {
        "name": "testing",
        "crew_id": "qa_crew",
        "task": "Test implementation",
        "depends_on": ["implementation"]
    }
]

# Execute
orchestrator = TaskOrchestrator(crew_manager)
results = asyncio.run(orchestrator.execute_workflow(workflow))
```

### Conditional Task Branching

```python
async def intelligent_task_routing(agent, initial_task: str):
    """Route subsequent tasks based on initial result."""
    
    # Execute initial analysis
    analysis = await agent.run_task(initial_task)
    
    # Route based on result
    if "error" in analysis["result"].lower():
        # Error recovery path
        recovery_task = f"Fix the issue: {analysis['result']}"
        return await agent.run_task(recovery_task)
    
    elif "investigate" in analysis["result"].lower():
        # Investigation path
        investigation_task = f"Investigate further: {analysis['result']}"
        return await agent.run_task(investigation_task)
    
    else:
        # Success path - optional refinement
        refinement = f"Refine the solution: {analysis['result']}"
        return await agent.run_task(refinement)
```

## Performance Optimization

### Caching Results

```python
from functools import lru_cache
from core.llm import get_llm

class CachedAgent:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.response_cache = {}
    
    @lru_cache(maxsize=128)
    def cached_chat(self, message: str) -> str:
        """Cache chat responses."""
        return self.agent.chat(message)
    
    def chat(self, message: str, use_cache: bool = True) -> str:
        """Chat with optional caching."""
        if use_cache and message in self.response_cache:
            print(f"Cache hit for: {message[:50]}...")
            return self.response_cache[message]
        
        response = self.agent.chat(message)
        self.response_cache[message] = response
        return response
    
    def clear_cache(self):
        """Clear response cache."""
        self.response_cache.clear()

# Usage
cached_agent = CachedAgent(agent)
response1 = cached_agent.chat("What is Python?")  # Computes
response2 = cached_agent.chat("What is Python?")  # Uses cache
```

### Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_process_tasks(agent: Agent, tasks: List[str], max_workers: int = 4) -> Dict:
    """Process multiple tasks in parallel."""
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(agent.chat, task): task 
            for task in tasks
        }
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results[task] = result
            except Exception as e:
                results[task] = f"Error: {str(e)}"
    
    return results

# Usage
tasks = [
    "Summarize Python",
    "Explain machine learning",
    "Describe databases"
]

results = batch_process_tasks(agent, tasks)
for task, result in results.items():
    print(f"{task}: {result[:100]}...")
```

## Monitoring and Observability

```python
from datetime import datetime

class AgentAnalytics:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.metrics = {
            "total_chats": 0,
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_response_time": 0,
            "response_times": []
        }
    
    async def monitored_chat(self, message: str) -> str:
        """Chat with monitoring."""
        start = datetime.now()
        
        try:
            response = await self.agent.chat(message)
            self.metrics["total_chats"] += 1
            return response
        finally:
            duration = (datetime.now() - start).total_seconds()
            self.metrics["response_times"].append(duration)
            self.metrics["average_response_time"] = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
    
    def get_analytics(self) -> Dict:
        """Get analytics summary."""
        return {
            **self.metrics,
            "success_rate": self.metrics["successful_tasks"] / max(1, self.metrics["total_tasks"]),
            "agent_name": self.agent.persona.name
        }

# Usage
analytics = AgentAnalytics(agent)
response = asyncio.run(analytics.monitored_chat("Hello"))
print(analytics.get_analytics())
```

## Next Steps

- [API Reference](api_reference.md) - Complete API documentation
- [Crew Management](crew_management.md) - Team coordination
- [Integration Guide](integration.md) - Integration patterns
