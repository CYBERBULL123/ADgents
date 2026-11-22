"""Shared defaults for local development and server exposure."""
import ipaddress
import os


DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


def get_api_host() -> str:
    return os.getenv("API_HOST", DEFAULT_API_HOST)


def get_api_token() -> str:
    return os.getenv("ADGENTS_API_TOKEN", "").strip()


def get_cors_origins() -> list[str]:
    configured = os.getenv("ADGENTS_CORS_ORIGINS")
    if configured is None:
        return list(DEFAULT_CORS_ORIGINS)
    return list(dict.fromkeys(origin.strip() for origin in configured.split(",") if origin.strip()))


def is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False