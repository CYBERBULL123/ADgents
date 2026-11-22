import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import server


def test_loopback_development_remains_usable_without_token(monkeypatch):
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.delenv("ADGENTS_API_TOKEN", raising=False)
    client = TestClient(server.app)

    assert client.get("/api/health").status_code == 200


def test_rest_api_requires_configured_bearer_token(monkeypatch):
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("ADGENTS_API_TOKEN", "test-token")
    client = TestClient(server.app)

    assert client.get("/api/health").status_code == 401
    response = client.get("/api/health", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200


def test_remote_bind_fails_closed_without_token(monkeypatch):
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.delenv("ADGENTS_API_TOKEN", raising=False)
    client = TestClient(server.app)

    response = client.get("/api/health")
    a2a_response = client.post("/a2a/v1", json={})

    assert response.status_code == 503
    assert "ADGENTS_API_TOKEN" in response.json()["detail"]
    assert a2a_response.status_code == 503


def test_websocket_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("ADGENTS_API_TOKEN", "test-token")
    client = TestClient(server.app)

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            "/ws/test-agent",
            subprotocols=["adgents", "adgents-auth.wrong-token"],
        ):
            pass
    assert error.value.code == 4401

    with client.websocket_connect(
        "/ws/test-agent",
        subprotocols=["adgents", "adgents-auth.test-token"],
    ) as websocket:
        assert websocket.receive_json()["type"] == "connected"


def test_websocket_rejects_untrusted_origin(monkeypatch):
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.delenv("ADGENTS_API_TOKEN", raising=False)
    client = TestClient(server.app)

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            "/ws/test-agent",
            headers={"origin": "https://untrusted.example"},
        ):
            pass
    assert error.value.code == 4403


def test_a2a_key_takes_precedence_over_shared_api_token(monkeypatch):
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("ADGENTS_API_TOKEN", "shared-token")
    monkeypatch.setenv("A2A_API_KEY", "a2a-token")
    client = TestClient(server.app)
    request = {"jsonrpc": "2.0", "id": 1, "method": "unknown"}

    rejected = client.post("/a2a/v1", json=request, headers={"Authorization": "Bearer shared-token"})
    accepted = client.post("/a2a/v1", json=request, headers={"Authorization": "Bearer a2a-token"})

    assert rejected.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["error"]["code"] == -32601