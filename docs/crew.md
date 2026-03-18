# Multi-Agent Crews (Orchestrator)

The **Crew** system unlocks the true power of autonomous AI by allowing multiple specialized agents to collaborate seamlessly on complex, multi-step tasks.

Instead of assigning everything to a single general-purpose agent (which might get overwhelmed), you can build a team (a "Crew") of agents with distinct domain expertise and dedicated backend skills.

---

## 🚀 How It Works

ADgents implements an advanced **Orchestrator** model similar to cutting-edge tools like AutoGen or CrewAI.

1. **You provide a Master Task**: e.g., "Research AI frameworks and write a Next.js blog post about them."
2. **Orchestrator Decomposes the Task**: An intelligent underlying LLM breaks the job down into up to 6 distinct sub-tasks.
3. **Agent Assignment**: The Orchestrator automatically selects the most qualified agent for each specialized sub-task.
4. **Execution**: The specialized agents run autonomously using their ReAct loops and assigned skills.
5. **Synthesis**: The Orchestrator merges all individual outputs into a single, cohesive final answer.

---

## 💻 Using Crews in the Backend Structure

### 1. Initialize Your Specialized Agents
You can use `AGENT_FACTORY` to summon your specialized templates.

```python
from core.agent import AGENT_FACTORY

researcher = AGENT_FACTORY.create_from_template("researcher")
engineer = AGENT_FACTORY.create_from_template("engineer")
marketer = AGENT_FACTORY.create_from_template("analyst") # Or any persona
```

### 2. Form a Collaborative Crew
Group them together inside the `Crew` object.

```python
from core.crew import Crew

my_crew = Crew(
    name="Launch Strategy Team",
    agents=[researcher, engineer, marketer]
)
```

### 3. Kickoff the Task
Assign a complex Master Task and wait for the synthesized results.

```python
run = my_crew.run("Analyze our competitor's GitHub repositories, write code templates to match their features, and draft an SEO-friendly release post.")

print(run.final_answer) 
# Outputs incredibly detailed, multi-faceted generated content from all 3 agents!
```

---

## 🌐 API Endpoints

You can instantly trigger complex crew collaborations through ADgents REST hooks via `/api/crew/run`.

**Request Structure:**
```json
// POST /api/crew/run
{
  "task": "Build a deployment plan for the new micro-service infrastructure.",
  "agent_ids": [
    "e9b4e7a2-f5b2-4d2c-9a1f-b5b6fcd9c3a1",
    "b8c3d6e1-a2c3-4d4e-5f6g-7h8i9j0k1l2m"
  ]
}
```

**Response Output:**
```json
{
  "success": true,
  "run": {
    "task": "Build a deployment plan for the new micro-service infrastructure.",
    "status": "done",
    "sub_tasks": [
      {
        "agent_name": "DevOps Architect",
        "description": "Evaluate kubernetes config optimizations.",
        "result": "...",
        "status": "done"
      }
    ],
    "final_answer": "## Comprehensive Deployment Plan\n..."
  }
}
```
