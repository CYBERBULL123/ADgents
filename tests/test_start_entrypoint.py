import sys
from types import SimpleNamespace

import start


def test_main_starts_uvicorn_server(monkeypatch):
    calls = []
    monkeypatch.setattr(start, "check_environment", lambda: None)
    monkeypatch.setattr(start.os, "chdir", lambda path: None)
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "8123")
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda *args, **kwargs: calls.append((args, kwargs))))

    start.main()

    assert calls == [(("server:app",), {
        "host": "127.0.0.1",
        "port": 8123,
        "reload": True,
        "log_level": "info",
    })]