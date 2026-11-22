from core.config import (
    DEFAULT_API_HOST,
    DEFAULT_CORS_ORIGINS,
    get_api_host,
    get_cors_origins,
    is_loopback_host,
)


def test_api_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("API_HOST", raising=False)

    assert get_api_host() == DEFAULT_API_HOST == "127.0.0.1"


def test_api_host_can_be_explicitly_configured(monkeypatch):
    monkeypatch.setenv("API_HOST", "0.0.0.0")

    assert get_api_host() == "0.0.0.0"
    assert not is_loopback_host(get_api_host())


def test_cors_origins_default_to_local_studio(monkeypatch):
    monkeypatch.delenv("ADGENTS_CORS_ORIGINS", raising=False)

    assert get_cors_origins() == list(DEFAULT_CORS_ORIGINS)


def test_cors_origins_parse_and_deduplicate_configuration(monkeypatch):
    monkeypatch.setenv(
        "ADGENTS_CORS_ORIGINS",
        "https://studio.example.com, http://localhost:8000,https://studio.example.com",
    )

    assert get_cors_origins() == [
        "https://studio.example.com",
        "http://localhost:8000",
    ]


def test_loopback_detection_accepts_ip_and_localhost():
    assert is_loopback_host("localhost")
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("::1")
    assert not is_loopback_host("192.0.2.1")