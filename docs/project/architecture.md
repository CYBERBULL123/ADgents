# Architecture

This document covers how ADgents handles complex workflows efficiently by utilizing the **ReAct (Reasoning and Acting)** loop at its core. It empowers an LLM agent to methodically think through inputs, decompose user tasks, perform necessary steps using a suite of "skills," and continually reflect on its observations.

## The ReAct Loop

ADgents defines its standard intelligent loop:

```
User Task
    │
    ▼
📋 Plan
    │
    ▼
💭 Think (LLM reasons about next step)
    │
    ▼
⚡ Act (execute a skill/tool) 
    │
    ▼
👁️ Observe (see the result) 
    │
    ▼
🔮 Reflect ──────► Continue? ─── Yes ────┐
                        │                │
                       No                │
                        │                │
                        ▼                │
                  ✅ Final Answer       Wait...
                  💾 Store in Memory
```

When an agent is queried via `chat()` or `run()`, this loop ensures that the agent handles intermediate complexities and edge cases without demanding further explicit manual prompting. The system manages the task context across various provider APIs by seamlessly converting the ReAct chain into message formats that OpenAI, Anthropic, or Gemini recognize natively.

## The Memory Engine

The `Memory` tier stores interactions in an embedded SQLite database (`ADgents/data/agents/<uuid>.db`), isolating different context groups.

**Working Memory:** The immediately available context of the ongoing session (`SessionMemory`).

**Episodic Memory:** Saved conversational highlights and historical task resolutions. When the agent receives a brand new input, it uses keyword-based searches to recall relevant facts or approaches from previous episodic nodes.

**Semantic Memory:** General worldview truths, structured knowledge bases, and explicit facts instructed to the agent (via the `teach_agent` API). 

## Skill Registry

Agents do not execute raw code by default. Instead, they interact with the **Skill Registry**, a strictly typed layer of python functions that expose only safe APIs (like reading a specific whitelisted file, scraping a webpage, doing math, or parsing string payloads into JSON). These skills are exposed to the LLM as structured `Function Call` models.

## WebSocket Streaming

Instead of a blocking REST response waiting 40 seconds for an autonomous workflow loop to complete and return a JSON payload, the `server.py` routes task execution onto a threaded event loop that drains intermediate `ThoughtStep` objects through an open **WebSocket** channel directly into the frontend UI layer. Users watch the agent "think" and "act" iteratively in real-time.

---

## Tech Stack Under the Hood

### 1. The Backend Engine (`FastAPI` + `Python`)
The entire REST API, WebSockets handler, and core ReAct engine are built dynamically with `FastAPI` to ensure extremely high concurrency limits and sub-millisecond route resolution.
By enforcing standard python typing everywhere (via `Pydantic` models), data mutations passing between the Studio UI and the Engine are guaranteed schema-compliant. Multi-threading (`ThreadPoolExecutor`) is specifically utilized in the `POST /api/tasks` endpoint so that the CPU-heavy blocking operations of calling LLMs and executing raw Python skills don't freeze the main `asyncio` loop handling real-time WebSockets to the web clients.

### 2. Embedded Database (`SQLite`)
No complex MongoDB or PostgreSQL installs are required to run ADgents.
- Inside the `ADgents/data/agents` folder, every new Agent spawned creates its own isolated `.db` environment.
- Inside `ADgents/data/server.db`, task histories and metrics are centrally tracked.
Because these deployments are embedded directly via Python's native `sqlite3` driver, the platform is inherently portable. Backing up an agent's "brain" is literally copying a 12kb `.db` file from the host machine to a USB drive!

### 3. The Studio Frontend (`Vanilla JS/CSS`)
The frontend dashboard (`app.js` and `style.css`) is intentionally built completely without heavy frameworks (No React, Angular, or Vue builds required). Using modern vanilla Web API standards (`async/await`, native `WebSocket`, `DOMPurify`, and `marked`) we guarantee instantaneous boot times, a tiny payload size, and zero NPM installations required for an end-user to experiment with changing the CSS styling.
