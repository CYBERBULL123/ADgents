"""
ADgents MCP (Model Context Protocol) Server
Exposes ADgents skills and agents as a standard MCP server.
Any MCP-compatible client (Claude Desktop, Cursor, etc.) can connect and use
ADgents agents + skills as native tools.

Protocol: JSON-RPC 2.0 over stdio (for Claude Desktop) or HTTP SSE (for web clients).
Spec: https://modelcontextprotocol.io/specification
"""
import json
import sys
import asyncio
import uuid
from typing import Any, Dict, List, Optional


# ─── JSON-RPC helpers ────────────────────────────────────────────────────────

def _rpc_result(id_: Any, result: Any) -> Dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _rpc_error(id_: Any, code: int, message: str, data: Any = None) -> Dict:
    err = {"code": code, "message": message}
    if data:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def _rpc_notification(method: str, params: Any) -> Dict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


# ─── MCP Server ──────────────────────────────────────────────────────────────

class MCPServer:
    """
    Exposes ADgents skills/agents as an MCP server.
    
    Usage — stdio mode (Claude Desktop integration):
        server = MCPServer(skill_registry=SKILL_REGISTRY, agents=[agent1, agent2])
        asyncio.run(server.run_stdio())
    
    Usage — HTTP mode (web clients):
        server = MCPServer(skill_registry=SKILL_REGISTRY, agents=[agent1, agent2])
        app = server.get_fastapi_router()  # mount on your FastAPI app
    """

    SERVER_NAME = "adgents"
    SERVER_VERSION = "1.0.0"

    def __init__(self, skill_registry=None, agents: list = None):
        self.skill_registry = skill_registry
        self.agents = agents or []
        self._agent_map = {a.persona.id: a for a in self.agents}

    # ── Capability introspection ─────────────────────────────────────────────

    def _list_tools(self) -> List[Dict]:
        """Return all ADgents skills as MCP tools."""
        tools = []
        if self.skill_registry:
            for skill in self.skill_registry.list():
                tools.append({
                    "name": skill.name,
                    "description": skill.description,
                    "inputSchema": skill.parameters,
                })
        # Each agent's think() as a tool
        for agent in self.agents:
            tools.append({
                "name": f"agent_{agent.persona.name.lower().replace(' ', '_')}_chat",
                "description": f"Chat with {agent.persona.name} ({agent.persona.role}). {agent.persona.backstory[:120]}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Your message to the agent"}
                    },
                    "required": ["message"]
                }
            })
        return tools

    def _list_prompts(self) -> List[Dict]:
        """Return agent personas as MCP prompts."""
        return [
            {
                "name": agent.persona.name,
                "description": f"Prompt for {agent.persona.name} — {agent.persona.role}",
                "arguments": [
                    {"name": "task", "description": "The task or question for this agent", "required": True}
                ]
            }
            for agent in self.agents
        ]

    def _get_prompt(self, name: str, arguments: Dict) -> Dict:
        """Return the system prompt + user task for a given agent."""
        agent = next((a for a in self.agents if a.persona.name == name), None)
        if not agent:
            raise ValueError(f"Agent '{name}' not found")
        task = arguments.get("task", "Hello")
        return {
            "description": f"Conversation with {agent.persona.name}",
            "messages": [
                {"role": "assistant", "content": {"type": "text", "text": agent.persona.to_system_prompt()}},
                {"role": "user", "content": {"type": "text", "text": task}},
            ]
        }

    def _call_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute a skill or agent chat."""
        # Agent chat tools
        for agent in self.agents:
            agent_tool_name = f"agent_{agent.persona.name.lower().replace(' ', '_')}_chat"
            if name == agent_tool_name:
                message = arguments.get("message", "")
                reply = agent.think(message)
                return {"content": [{"type": "text", "text": reply}]}

        # Skill tools
        if self.skill_registry:
            result = self.skill_registry.execute(name, **arguments)
            text = result.to_text()
            return {"content": [{"type": "text", "text": text}], "isError": not result.success}

        return {"content": [{"type": "text", "text": f"Tool '{name}' not found."}], "isError": True}

    # ── JSON-RPC dispatcher ──────────────────────────────────────────────────

    def _handle_request(self, req: Dict) -> Optional[Dict]:
        """Handle a single JSON-RPC request and return a response (or None for notifications)."""
        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id")  # None = notification

        try:
            if method == "initialize":
                return _rpc_result(req_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {"name": self.SERVER_NAME, "version": self.SERVER_VERSION}
                })

            elif method == "initialized":
                # Notification — no response needed
                return None

            elif method == "tools/list":
                return _rpc_result(req_id, {"tools": self._list_tools()})

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                result = self._call_tool(tool_name, tool_args)
                return _rpc_result(req_id, result)

            elif method == "prompts/list":
                return _rpc_result(req_id, {"prompts": self._list_prompts()})

            elif method == "prompts/get":
                name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = self._get_prompt(name, arguments)
                return _rpc_result(req_id, result)

            elif method == "resources/list":
                # No resources exposed for now
                return _rpc_result(req_id, {"resources": []})

            elif method == "ping":
                return _rpc_result(req_id, {})

            else:
                if req_id is not None:
                    return _rpc_error(req_id, -32601, f"Method not found: {method}")
                return None

        except Exception as e:
            if req_id is not None:
                return _rpc_error(req_id, -32603, "Internal error", str(e))
            return None

    # ── Stdio transport (Claude Desktop) ─────────────────────────────────────

    async def run_stdio(self):
        """
        Run the MCP server over stdin/stdout.
        Add to Claude Desktop config:
          {
            "mcpServers": {
              "adgents": {
                "command": "python",
                "args": ["-m", "adgents.mcp"],
                "env": {"GEMINI_API_KEY": "..."}
              }
            }
          }
        """
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        _, writer = await loop.connect_write_pipe(
            asyncio.BaseProtocol, sys.stdout.buffer
        )

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                req = json.loads(line.decode())
                response = self._handle_request(req)
                if response is not None:
                    out = json.dumps(response) + "\n"
                    sys.stdout.write(out)
                    sys.stdout.flush()
            except json.JSONDecodeError:
                pass
            except Exception:
                pass

    def get_fastapi_router(self):
        """
        Returns a FastAPI APIRouter that exposes the MCP server over HTTP.
        Mount with: app.include_router(mcp_server.get_fastapi_router(), prefix="/mcp")
        """
        try:
            from fastapi import APIRouter, Request
            from fastapi.responses import StreamingResponse, JSONResponse
        except ImportError:
            raise ImportError("Install fastapi to use the HTTP MCP endpoint")

        router = APIRouter()

        @router.post("/")
        async def mcp_endpoint(request: Request):
            body = await request.json()
            # Support batch requests (array of requests)
            if isinstance(body, list):
                responses = [self._handle_request(r) for r in body]
                responses = [r for r in responses if r is not None]
                return JSONResponse(responses)
            else:
                result = self._handle_request(body)
                if result is None:
                    return JSONResponse({}, status_code=202)
                return JSONResponse(result)

        @router.get("/tools")
        async def list_tools():
            return {"tools": self._list_tools()}

        @router.get("/agents")
        async def list_agents():
            return {"agents": [
                {"id": a.persona.id, "name": a.persona.name, "role": a.persona.role}
                for a in self.agents
            ]}

        return router
