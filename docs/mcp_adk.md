# Advanced Connectivity (MCP + ADK)

ADgents implements two incredibly powerful protocols: The Model Context Protocol (MCP) and Google ADK (Agent Development Kit). 

## 🔌 Model Context Protocol (MCP)

ADgents features a fully compliant native **JSON-RPC 2.0 MCP Server** under the hood, compatible over HTTP and Standard Input/Output (`stdio`).

### What does this mean?
You can use ADgents simply as a "Backend Skill and Agent Provider" for **other AI tools**.
If you are running Cursor, Claude Desktop, or another MCP app, you can "mount" ADgents and it will instantly stream all of your custom-coded skills and your spawned generic Agents to be used directly by those third-party LLMs.

### Connecting Claude Desktop
You can map ADgents directly into tools like Claude Desktop. Just start it with a local python command passing in your environment variables.

*(Claude Desktop Config:)*
```json
{
  "mcpServers": {
    "adgents": {
      "command": "python",
      "args": ["-m", "adgents.mcp"],
      "env": {"GEMINI_API_KEY": "replace-with-your-key"}
    }
  }
}
```
*When connected, Claude can now autonomously execute your specialized scripts or talk to ADgents personas directly!*

---

### External HTTP Binding `/mcp`
Your `server.py` natively hosts your active MCP router at `/mcp`. Any remote application capable of executing JSON-RPC connections can POST a payload containing `"method": "tools/call"` to securely interface off-server scripts asynchronously!

---

## 🛠 Google ADK Adapter

Google's robust **Agent Development Kit (ADK)** sets standard pipeline formatting for sophisticated AI deployment.

ADgents bundles with `core/adk_adapter.py`. This component "wraps" any ADgents setup (a single `Agent` or a full `Crew`) into a Google ADK-compliant structure!

### Seamlessly plug ADgents inside larger Google Pipelines

You can export ADgents logic to be heavily evaluated in testing harnesses or run inside a Google workflow effortlessly.

```python
from core.adk_adapter import ADKAgent
from core.agent import AGENT_FACTORY

# Spawn our standard Agent
base_agent = AGENT_FACTORY.create_from_template("researcher")

# Wrap it in Google ADK Formatting
adk_agent = ADKAgent(base_agent)

# Safely use it directly in standard Google pipelines (synchronous & async)
response = adk_agent.generate_content("Research AI trends in 2025.")

print(response.role) # Output: "model"
print(response.text) # Output: Your AI's content...
```

You can even export complex multi-agent collaborative groups by using `wrap_crew_as_adk_agent(crew)`!
