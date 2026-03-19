kl# ADgents Crew Management & Agent Communication System

## Overview

This is a complete implementation of a team-based agent organization system with real-time agent-to-agent communication, crew management, and agent templates.

## API Keys & Authentication

### For Google ADK:
- **GOOGLE_API_KEY**: Your Google Cloud API key (enables all Google services)
  - Get from: https://console.cloud.google.com/apis/credentials
  - Required APIs: Gemini API, Google Cloud AI Platform, Cloud Storage API
  
- **GEMINI_API_KEY**: Same as GOOGLE_API_KEY (for backward compatibility)

**Note**: Both point to the same project. Install with:
```bash
pip install google-adk google-genai google-cloud-aiplatform google-cloud-storage
```

## Architecture

### 1. **Crew Manager** (`core/crew_manager.py`)
Manages teams, templates, organizations, and agent coordination.

**Key Classes**:
- `AgentTemplate`: Reusable agent blueprints
- `CrewConfig`: Team configuration and membership
- `CrewMember`: Individual team member with status tracking
- `CrewManager`: High-level crew orchestration

**Features**:
- Create and manage agent teams
- Define agent templates for quick agent creation
- Organize teams into organizations
- Real-time member status tracking
- Built-in A2A communication support

### 2. **A2A Protocol** (`core/a2a_protocol.py`)
Google-style Agent-to-Agent protocol for inter-agent messaging.

**Key Classes**:
- `A2AMessage`: Protocol message structure
- `A2ARequest/A2AResponse`: Request/response patterns
- `A2AProtocol`: Single agent's protocol handler
- `A2AProtocolManager`: Manages all agents' A2A communication

**Message Types**:
- `request`: Agent asks another agent to do something
- `response`: Answer to a request with result/error
- `broadcast`: Message to all agents in crew
- `event`: Notification event (no specific receiver)

**Example**:
```python
# Send a message from agent1 to agent2
message = A2AMessage(
    sender_id="agent1",
    receiver_id="agent2",
    crew_id="crew123",
    message_type="request",
    content={
        "action": "analyze_document",
        "parameters": {"doc_id": "doc456"}
    }
)
await crew_mgr.send_message_between_agents(
    crew_id="crew123",
    from_agent="agent1",
    to_agent="agent2",
    message=message.content
)
```

## REST API Endpoints

### Agent Templates
```
POST   /api/templates/create           - Create template
GET    /api/templates                  - List all templates
GET    /api/templates/{id}             - Get specific template
DELETE /api/templates/{id}             - Delete template
```

### Crew Management
```
POST   /api/crews/create               - Create new crew
GET    /api/crews                      - List crews (filterable by org)
GET    /api/crews/{crew_id}            - Get crew details
POST   /api/crews/{crew_id}/add-member        - Add agent to crew
POST   /api/crews/{crew_id}/remove-member    - Remove agent from crew
POST   /api/crews/{crew_id}/update-member-status - Real-time status update
DELETE /api/crews/{crew_id}            - Delete crew
```

### Organizations
```
POST   /api/organizations/create       - Create organization
GET    /api/organizations              - List organizations
GET    /api/organizations/{org_id}     - Get org details + stats
```

### A2A Communication
```
POST   /api/a2a/send                   - Send message between agents
POST   /api/a2a/broadcast              - Broadcast to crew
GET    /api/a2a/communications/{crew_id}        - Get crew communications
GET    /api/a2a/communications/agent/{agent_id} - Get agent communications
```

## UI - Crew Manager Page

Located at: `studio/crews.html` (accessible via Crew Manager nav item)

**Features**:
1. **Active Crews Tab**: View and manage all teams
2. **Agent Templates Tab**: Create and manage agent blueprints
3. **Organizations Tab**: Create and manage organizational hierarchy
4. **A2A Communications Tab**: Monitor real-time agent-to-agent messages

### Creating a Crew

```json
POST /api/crews/create
{
    "name": "Research Team",
    "description": "AI researchers analyzing trends",
    "organization": "org-123",
    "members": [
        {
            "agent_id": "agent-1",
            "agent_name": "Dr. Aditi",
            "role": "lead_researcher"
        },
        {
            "agent_id": "agent-2",
            "agent_name": "Karan",
            "role": "data_analyst"
        }
    ],
    "communication_protocol": "a2a"
}
```

### Creating an Agent Template

```json
POST /api/templates/create
{
    "name": "Research Scientist",
    "description": "Specialized in deep research",
    "role": "researcher
    "expertise": ["AI", "ML", "NLP"],
    "skills": ["Python", "Data Analysis"],
    "instructions": "You are a research expert...",
    "model": "gemini-2.0-flash"
}
```

## Workflow Example

### 1. Create Organization
```bash
curl -X POST "http://localhost:8000/api/organizations/create?name=TechCorp&description=AI%20Company"
# Returns: org_id
```

### 2. Create Crew Templates
```bash
curl -X POST "http://localhost:8000/api/templates/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Senior Engineer",
    "role": "engineer",
    "expertise": ["Python", "Systems Design"],
    "description": "Expert engineer"
  }'
# Returns: template_id
```

### 3. Create Crew
```bash
curl -X POST "http://localhost:8000/api/crews/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Backend Team",
    "organization": "org-123",
    "communication_protocol": "a2a",
    "members": [
      {"agent_id": "agent1", "agent_name": "Alice", "role": "lead"}
    ]
  }'
# Returns: crew_id
```

### 4. Send A2A Message
```bash
curl -X POST "http://localhost:8000/api/a2a/send" \
  -H "Content-Type: application/json" \
  -d '{
    "crew_id": "crew-123",
    "from_agent": "agent1",
    "to_agent": "agent2",
    "message_type": "request",
    "content": {
      "action": "code_review",
      "parameters": {"pr_id": "pr-456"}
    }
  }'
```

## Advanced Features

### Real-Time Status Updates
```bash
POST /api/crews/{crew_id}/update-member-status
{
    "agent_id": "agent1",
    "status": "active",  # idle, active, communicating, waiting
    "current_task": "Analyzing data..."
}
```

### A2A Request/Response Pattern
```python
# Sender side
msg, request = a2a_protocol.create_request(
    receiver_id="agent2",
    action="analyze",
    parameters={"data": {...}},
    timeout=30
)
await a2a_protocol.send_message(msg)

# Receiver side (in handler)
response_msg = a2a_protocol.create_response(
    request_message=request_msg,
    success=True,
    result={"analysis": "..."}
)

# Sender side (wait for response)
response = await a2a_protocol.wait_for_response(request.message_id)
```

### Broadcasting Messages
```bash
POST /api/a2a/broadcast
{
    "crew_id": "crew-123",
    "from_agent": "agent1",
    "message_type": "event",
    "content": {
        "event_type": "meeting_scheduled",
        "data": {"time": "2026-03-19T14:00:00Z"}
    }
}
```

## Integration with Google ADK

The Crew Manager integrates seamlessly with Google ADK:

```python
from core.crew_manager import get_crew_manager
from core.a2a_protocol import get_a2a_manager

# Create crew with A2A protocol
crew_mgr = get_crew_manager()
crew = crew_mgr.create_crew(
    name="AI Team",
    communication_protocol="a2a"  # or "adk"
)

# Send message via A2A
a2a_mgr = get_a2a_manager()
# Messages flow through A2A protocol
```

For ADK integration:
```
GET /api/google-adk/status  # Check if ADK available
POST /api/google-adk/create-agent  # Create ADK agent
POST /api/google-adk/create-*-workflow  # Sequential/Parallel/Loop workflows
```

## Database Persistence

All data is persisted locally:
- **Crews**: `data/crews/{crew_id}.json`
- **Templates**: `data/templates/{template_id}.json`
- **Organizations**: In-memory (can be extended to disk)
- **A2A Messages**: In-memory during session (can be logged to disk)

## WebSocket & Real-Time

For real-time updates, the system supports:
- Crew member status updates
- Real-time A2A message flow
- Event broadcasting
- Agent state synchronization

Future enhancement: WebSocket endpoint for live crew updates
```javascript
ws = new WebSocket('ws://localhost:8000/ws/crew/crew-123');
ws.onmessage = (msg) => {
    // Real-time crew updates
};
```

## Environment Variables

```bash
# Google Cloud / ADK
GOOGLE_API_KEY=your-key
GOOGLE_PROJECT_ID=your-project
GOOGLE_CLOUD_REGION=us-central1

# Existing keys
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## File Structure

```
core/
├── crew_manager.py      # Team & template management
├── a2a_protocol.py      # Agent-to-Agent communication
├── google_adk_integration.py  # ADK wrapper
└── [existing files...]

studio/
├── crews.html           # Crew Manager UI
├── index.html           # Updated with Crews nav
└── [existing files...]

data/
├── crews/              # Persisted crew configs
├── templates/          # Persisted templates
└── [existing dirs...]
```

## Next Steps

1. **Test Real Agents**: Create actual agents and add to crews
2. **Enable WebSocket**: Live streaming of crew activities
3. **Metrics & Logging**: Track A2A messages, latencies
4. **Persistence Layer**: Store message history
5. **ADK Workflows**: Create Sequential/Parallel task workflows
6. **Agent Autonomy**: Agents auto-select tasks from crew queue

## Troubleshooting

### Google ADK Not Available
```
Error: "Google ADK not available"
Solution: pip install google-adk
```

### Crew Creation Fails
- Ensure agents exist and have valid IDs
- Check organization exists
- Verify API key set

### A2A Messages Not Flowing
- Both agents must be in same crew
- Check agent IDs are correct
- Verify message content is valid JSON

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Next Update**: Vertex AI integration, distributed crew coordination
