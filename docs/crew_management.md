# Crew Management Guide

Complete guide to creating, managing, and orchestrating agent crews.

## What is a Crew?

A crew is a team of specialized agents working together on complex tasks. Crews enable:

- **Specialization**: Each agent has distinct expertise and roles
- **Collaboration**: Agents communicate and coordinate via A2A protocol
- **Scalability**: Handle complex problems that require multiple perspectives
- **Accountability**: Clear roles and responsibilities within the team

## Basic Crew Operations

### Creating a Crew

#### Via Python API

```python
from core.crew_manager import CrewManager
from core.agent import Agent
from core.persona import Persona

# Step 1: Create agents with specific roles
lead_agent = Agent(
    persona=Persona(
        name="Sarah Chen",
        role="Project Lead",
        expertise_domains=["Project Management", "Leadership"],
        autonomy_level=4
    )
)

developer_agent = Agent(
    persona=Persona(
        name="Mike Johnson",
        role="Senior Developer",
        expertise_domains=["Software Engineering", "Python"],
        autonomy_level=3
    )
)

qa_agent = Agent(
    persona=Persona(
        name="Lisa Rodriguez",
        role="QA Engineer",
        expertise_domains=["Testing", "Quality Assurance"],
        autonomy_level=3
    )
)

# Step 2: Create the crew
crew_manager = CrewManager()
crew = crew_manager.create_crew(
    name="Development Team",
    description="Team responsible for building and testing features",
    organization="Engineering",
    members=[
        {
            "agent_id": lead_agent.id,
            "agent_name": "Sarah Chen",
            "role": "lead",
            "responsibilities": ["Planning", "Coordination", "Decision making"]
        },
        {
            "agent_id": developer_agent.id,
            "agent_name": "Mike Johnson",
            "role": "contributor",
            "responsibilities": ["Implementation", "Code review"]
        },
        {
            "agent_id": qa_agent.id,
            "agent_name": "Lisa Rodriguez",
            "role": "reviewer",
            "responsibilities": ["Testing", "Quality verification"]
        }
    ],
    communication_protocol="a2a"
)

print(f"Crew created: {crew.id}")
print(f"Members: {len(crew.members)}")
```

#### Via REST API

```bash
curl -X POST http://localhost:8000/api/crews/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marketing Team",
    "description": "Content creation and distribution",
    "organization": "Marketing",
    "members": [
      {
        "agent_id": "uuid-1",
        "agent_name": "Content Writer",
        "role": "lead"
      },
      {
        "agent_id": "uuid-2",
        "agent_name": "Designer",
        "role": "contributor"
      }
    ],
    "communication_protocol": "a2a"
  }'
```

### Listing Crews

```python
crew_manager = CrewManager()

# Get all crews
all_crews = crew_manager.list_crews()
for crew in all_crews:
    print(f"{crew.name}: {len(crew.members)} members")

# Filter by organization
dev_crews = crew_manager.list_crews(organization="Engineering")
```

### Getting Crew Details

```python
crew = crew_manager.get_crew(crew_id)

print(f"Crew: {crew.name}")
print(f"Organization: {crew.organization}")
print(f"Description: {crew.description}")
print(f"Created: {crew.created_at}")
print(f"Members:")
for member in crew.members:
    print(f"  - {member['agent_name']} ({member['role']})")
```

### Modifying Crews

```python
# Add a member to existing crew
crew_manager.add_crew_member(
    crew_id=crew.id,
    agent_id=new_agent.id,
    agent_name="New Member",
    role="contributor"
)

# Remove a member
crew_manager.remove_crew_member(
    crew_id=crew.id,
    agent_id=agent_to_remove.id
)

# Update crew metadata
crew_manager.update_crew(
    crew_id=crew.id,
    name="Updated Team Name",
    description="Updated description"
)

# Delete crew
crew_manager.delete_crew(crew.id)
```

## Crew Task Execution

### Running a Crew Task

```python
crew_manager = CrewManager()

# Execute a task as a crew
result = crew_manager.execute_crew_task(
    crew_id="crew-uuid",
    task="Develop and test a new authentication module",
    max_iterations=5
)

print(f"Status: {result['status']}")
print(f"Output: {result['output']}")
print(f"Agents involved: {result['agents_involved']}")
```

### Via REST API

```bash
curl -X POST http://localhost:8000/api/crews/crew-uuid/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Research and compile market trends",
    "max_iterations": 5
  }'
```

### Monitoring Task Execution

```python
import asyncio
from core.crew_manager import CrewManager

async def monitor_task(crew_id: str, task: str):
    """Monitor task execution in real-time."""
    crew_manager = CrewManager()
    
    # Start task execution
    result = await crew_manager.execute_crew_task_async(
        crew_id=crew_id,
        task=task
    )
    
    # Monitor steps
    for i, step in enumerate(result.get('steps', []), 1):
        print(f"Step {i}: {step['description']}")
        print(f"Status: {step['status']}")
        await asyncio.sleep(1)  # Update interval
    
    return result

# Run monitoring
result = asyncio.run(monitor_task("crew-uuid", "Complete task"))
```

## Agent-to-Agent Communication

### Enabling Communication

```python
# Communication is enabled by default with "a2a" protocol
crew = crew_manager.create_crew(
    name="Collaborative Team",
    organization="Engineering",
    members=[...],
    communication_protocol="a2a"  # Enable A2A communication
)
```

### Tracking Communications

```python
# Get all communications within a crew
communications = crew_manager.get_crew_communications(crew_id)

for comm in communications:
    print(f"{comm['from']} → {comm['to']}:")
    print(f"  Message: {comm['message']}")
    print(f"  Time: {comm['timestamp']}")
```

### Message Formats

A2A messages follow this structure:

```python
{
    "from": "agent_name",
    "to": "agent_name",
    "message": {
        "type": "request|response|status",
        "content": "...",
        "metadata": {
            "priority": "high|normal|low",
            "timestamp": "ISO-8601"
        }
    }
}
```

## Crew Role Definitions

### Standard Roles

| Role | Responsibility | Autonomy |
|------|-----------------|----------|
| **lead** | Decision-making, coordination, planning | High |
| **contributor** | Task execution, implementation | Medium |
| **reviewer** | Verification, quality control | Medium |
| **specialist** | Domain-specific expertise | High |
| **observer** | Monitoring, reporting, analysis | Low |

### Custom Roles

```python
custom_role = {
    "name": "architect",
    "title": "System Architect",
    "responsibilities": [
        "Design system architecture",
        "Make technical decisions",
        "Review design decisions"
    ],
    "permissions": ["read", "write", "delegate"],
    "autonomy_level": 4
}

crew_manager.create_custom_role(custom_role)
```

## Crew Templates

### Using Pre-built Templates

```python
# Available templates: research, development, marketing, customer_service, data_science

crew = crew_manager.create_crew_from_template(
    template_name="research",
    name="Market Research Team",
    organization="Marketing"
)
```

### Creating Custom Templates

```python
research_template = {
    "name": "custom_research",
    "description": "Custom research team template",
    "roles": [
        {
            "name": "lead",
            "persona": {
                "role": "Research Director",
                "expertise_domains": ["Research", "Analysis"]
            }
        },
        {
            "name": "contributor",
            "persona": {
                "role": "Researcher",
                "expertise_domains": ["Data Collection", "Analysis"]
            }
        }
    ]
}

crew_manager.create_template(research_template)

# Use the template
crew = crew_manager.create_crew_from_template(
    template_name="custom_research",
    name="My Research Team",
    organization="Research"
)
```

## Best Practices

### 1. Role Clarity

Define clear responsibilities for each member:

```python
members = [
    {
        "agent_id": agent1.id,
        "agent_name": "Alice",
        "role": "lead",
        "responsibilities": [
            "Overall task coordination",
            "Final decision making",
            "Team management"
        ]
    },
    {
        "agent_id": agent2.id,
        "agent_name": "Bob",
        "role": "contributor",
        "responsibilities": [
            "Implementation of assigned tasks",
            "Progress reporting",
            "Risk identification"
        ]
    }
]
```

### 2. Team Size

Optimal crew sizes:
- **Small task**: 2-3 agents (one lead, 1-2 contributors)
- **Medium task**: 3-5 agents (lead, contributors, reviewer)
- **Complex task**: 5-8 agents (lead, specialists, reviewers, coordinator)

### 3. Specialization

Create specialized crews for specific domains:

```python
# Data Science Team
data_science_crew = crew_manager.create_crew(
    name="Data Science Team",
    members=[
        # ML Engineer (model development)
        # Data Engineer (data pipeline)
        # Data Analyst (analysis and insights)
        # Visualization Specialist (dashboards)
    ]
)

# DevOps Team
devops_crew = crew_manager.create_crew(
    name="DevOps Team",
    members=[
        # Infrastructure Lead
        # System Administrator
        # CI/CD Specialist
        # Monitoring Specialist
    ]
)
```

### 4. Communication Protocol

Use A2A communication for complex coordination:

```python
# Enable rich agent-to-agent communication
crew = crew_manager.create_crew(
    name="Coordinated Team",
    members=[...],
    communication_protocol="a2a",
    # Optional: Custom communication rules
    communication_rules={
        "request_timeout": 30,  # seconds
        "max_retries": 3,
        "priority_handling": True
    }
)
```

### 5. Task Decomposition

Break complex tasks into crew-manageable units:

```python
# Instead of one massive task
# task = "Build, test, deploy, and monitor a new microservice"

# Break into phases
tasks = [
    {
        "phase": "design",
        "crew": "architecture_team",
        "task": "Design the microservice architecture",
        "depends_on": []
    },
    {
        "phase": "development",
        "crew": "dev_team",
        "task": "Implement the microservice based on design",
        "depends_on": ["design"]
    },
    {
        "phase": "testing",
        "crew": "qa_team",
        "task": "Test and verify the microservice",
        "depends_on": ["development"]
    },
    {
        "phase": "deployment",
        "crew": "devops_team",
        "task": "Deploy and configure monitoring",
        "depends_on": ["testing"]
    }
]
```

### 6. Monitor Crew Health

```python
def get_crew_health(crew_id: str):
    """Check crew health status."""
    crew = crew_manager.get_crew(crew_id)
    
    metrics = {
        "id": crew.id,
        "name": crew.name,
        "members": len(crew.members),
        "active_members": sum(1 for m in crew.members if m.get("active", True)),
        "completed_tasks": crew.get("completed_tasks", 0),
        "failed_tasks": crew.get("failed_tasks", 0),
        "avg_task_duration": crew.get("avg_task_duration", 0)
    }
    
    return metrics

health = get_crew_health(crew_id)
print(f"Crew Health: {health['active_members']}/{health['members']} active")
print(f"Success rate: {health['completed_tasks']}/{health['completed_tasks'] + health['failed_tasks']}")
```

## Advanced Crew Management

### Dynamic Crew Assembly

```python
def create_dynamic_crew_for_task(task_description: str):
    """Create a crew composition based on task requirements."""
    
    # Analyze task requirements
    from core.llm import get_llm
    llm = get_llm()
    
    requirements = llm.analyze_requirements(task_description)
    
    # Select appropriate agents based on requirements
    agents = []
    for skillset in requirements['required_skills']:
        agent = find_agent_by_skill(skillset)
        if agent:
            agents.append(agent)
    
    # Create crew
    members = [
        {
            "agent_id": agents[0].id,
            "agent_name": agents[0].name,
            "role": "lead"
        }
    ]
    
    for agent in agents[1:]:
        members.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "role": "contributor"
        })
    
    crew = crew_manager.create_crew(
        name=f"Dynamic Crew for {task_description[:30]}...",
        description=task_description,
        organization="dynamic",
        members=members
    )
    
    return crew
```

### Crew Performance Analytics

```python
def analyze_crew_performance(crew_id: str):
    """Analyze crew performance metrics."""
    
    crew = crew_manager.get_crew(crew_id)
    communications = crew_manager.get_crew_communications(crew_id)
    
    analytics = {
        "crew_id": crew_id,
        "name": crew.name,
        "total_communication_events": len(communications),
        "agents_per_member": {},
        "communication_patterns": {}
    }
    
    # Analyze communication patterns
    for comm in communications:
        from_agent = comm['from']
        to_agent = comm['to']
        
        if from_agent not in analytics["communication_patterns"]:
            analytics["communication_patterns"][from_agent] = {}
        
        if to_agent not in analytics["communication_patterns"][from_agent]:
            analytics["communication_patterns"][from_agent][to_agent] = 0
        
        analytics["communication_patterns"][from_agent][to_agent] += 1
    
    return analytics
```

## Troubleshooting

### Crew Not Executing Tasks

```python
# Check crew status
crew = crew_manager.get_crew(crew_id)
if not crew:
    print("Crew not found")
elif not crew.get("active", True):
    print("Crew is inactive")
elif len(crew.members) < 1:
    print("Crew has no members")
else:
    print("Check server logs for execution errors")
```

### Communication Failures

```python
# Check A2A communication
communications = crew_manager.get_crew_communications(crew_id)
if not communications:
    print("No communications recorded")
    print("Check if A2A protocol is enabled")
else:
    # Analyze communication health
    for comm in communications:
        if comm.get("status") == "failed":
            print(f"Failed: {comm['from']} → {comm['to']}")
```

### Member Availability

```python
def check_member_availability(crew_id: str):
    """Check if all crew members are available."""
    crew = crew_manager.get_crew(crew_id)
    
    for member in crew.members:
        agent_id = member['agent_id']
        try:
            agent = get_agent(agent_id)
            status = "available" if agent else "not_found"
        except Exception as e:
            status = f"error: {str(e)}"
        
        print(f"{member['agent_name']}: {status}")
```

## Next Steps

- [API Reference](api_reference.md) - Complete API documentation
- [Integration Guide](integration.md) - Integration patterns
- [Advanced Features](advanced.md) - Custom skills, memory systems
