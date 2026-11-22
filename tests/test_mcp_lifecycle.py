from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.mcp_server import MCPServer


def test_stopping_mcp_disables_http_json_rpc_endpoint():
    mcp_server = MCPServer()
    app = FastAPI()
    app.include_router(mcp_server.get_fastapi_router(), prefix="/mcp")
    client = TestClient(app)

    assert client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 200

    mcp_server.enabled = False
    response = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 2, "method": "ping"})

    assert response.status_code == 503
    assert response.json()["error"] == "MCP server is stopped"