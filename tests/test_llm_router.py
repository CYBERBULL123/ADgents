from core.llm import GeminiProvider, LLMRouter, OllamaProvider, OpenAIProvider


def test_provider_models_use_environment_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom-openai")
    monkeypatch.setenv("GEMINI_MODEL", "custom-gemini")
    monkeypatch.setenv("ANTHROPIC_MODEL", "custom-claude")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    assert OpenAIProvider().model == "custom-openai"
    gemini = GeminiProvider()
    assert gemini.model == "custom-gemini"
    assert gemini.api_key == "google-key"


def test_router_reload_preserves_identity_and_uses_configured_default(monkeypatch):
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "custom-openai")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "openai")
    router = LLMRouter()

    monkeypatch.setenv("OPENAI_MODEL", "reloaded-openai")
    router.reload_from_environment()

    assert router._default_provider == "openai"
    assert router._providers["openai"].model == "reloaded-openai"