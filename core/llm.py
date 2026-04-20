"""
ADgents LLM Integration Layer
Supports multiple LLM providers with a unified interface.
"""
import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[Dict] = None
    raw: Dict = None
    
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""
    
    name: str = "base"
    
    @abstractmethod
    def complete(self, messages: List[Dict], tools: List[Dict] = None, **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT integration."""
    
    name = "openai"
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def complete(self, messages: List[Dict], tools: List[Dict] = None, 
                 temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers, json=body
            )
            response.raise_for_status()
            data = response.json()
        
        choice = data["choices"][0]["message"]
        tool_calls = None
        if choice.get("tool_calls"):
            tool_calls = [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"])
                }
                for tc in choice["tool_calls"]
            ]
        
        return LLMResponse(
            content=choice.get("content") or "",
            model=data.get("model", self.model),
            provider=self.name,
            input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            output_tokens=data.get("usage", {}).get("completion_tokens", 0),
            tool_calls=tool_calls,
            raw=data
        )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini integration."""
    
    name = "gemini"
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def complete(self, messages: List[Dict], tools: List[Dict] = None,
                 temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        # Convert OpenAI-style messages to Gemini format
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        raw_contents = []

        for msg in messages:
            if msg["role"] == "system":
                continue
            gemini_role = "user" if msg["role"] in ("user", "tool") else "model"
            # Use text content only; Gemini doesn't use OpenAI-style tool_calls fields
            text = str(msg.get("content") or "")
            if text:  # skip empty turns (e.g. assistant message with only tool_calls)
                raw_contents.append({"role": gemini_role, "text": text})

        # Gemini requires strictly alternating user / model turns.
        # Merge consecutive same-role messages into one turn.
        contents = []
        for entry in raw_contents:
            if contents and contents[-1]["role"] == entry["role"]:
                # Append to last turn's parts
                contents[-1]["parts"].append({"text": entry["text"]})
            else:
                contents.append({"role": entry["role"], "parts": [{"text": entry["text"]}]})
        
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if system_msg:
            body["systemInstruction"] = {"parts": [{"text": system_msg}]}
        
        # Convert OpenAI-style tools to Gemini format
        if tools:
            gemini_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    fn = tool["function"]
                    gemini_tools.append({
                        "name": fn["name"],
                        "description": fn["description"],
                        "parameters": fn.get("parameters", {})
                    })
            if gemini_tools:
                body["tools"] = [{"functionDeclarations": gemini_tools}]
        
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(url, json=body)
            if not response.is_success:
                # Include the response body so the real error is visible
                raise RuntimeError(
                    f"Gemini API error {response.status_code}: {response.text[:500]}"
                )
            data = response.json()
        
        candidates = data.get("candidates", [])
        if not candidates:
            # Blocked or empty response — return a safe fallback
            block_reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
            return LLMResponse(
                content=f"[Gemini blocked response: {block_reason}. Try rephrasing the task.]",
                model=self.model, provider=self.name,
                input_tokens=data.get("usageMetadata", {}).get("promptTokenCount", 0),
                output_tokens=0, raw=data
            )

        candidate = candidates[0].get("content", {})
        content = ""
        tool_calls = None
        
        for part in candidate.get("parts", []):
            if "text" in part:
                content += part["text"]
            elif "functionCall" in part:
                if tool_calls is None:
                    tool_calls = []
                fc = part["functionCall"]
                tool_calls.append({
                    "id": f"call_{len(tool_calls)}",
                    "name": fc["name"],
                    "arguments": fc.get("args", {})
                })
        
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            tool_calls=tool_calls,
            raw=data
        )




class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude integration."""
    
    name = "claude"
    
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def complete(self, messages: List[Dict], tools: List[Dict] = None,
                 temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        # Extract system message - Claude uses it separately
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            elif msg["role"] == "tool":
                # Tool results must always be delivered as a fresh user turn.
                # Use a sentinel so the dedup loop below won't merge these away.
                chat_messages.append({
                    "role": "user",
                    "content": f"[Tool Result]\n{msg['content']}",
                    "_is_tool_result": True
                })
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Ensure messages alternate user/assistant (Claude requirement)
        # Tool results are always kept as separate user turns.
        filtered = []
        last_role = None
        for msg in chat_messages:
            is_tool_result = msg.pop("_is_tool_result", False)
            if msg["role"] == last_role and not is_tool_result:
                if msg["role"] == "user":
                    filtered[-1]["content"] += "\n" + msg["content"]
                continue
            filtered.append({"role": msg["role"], "content": msg["content"]})
            last_role = msg["role"]
        
        # Must start with user message
        if filtered and filtered[0]["role"] != "user":
            filtered.insert(0, {"role": "user", "content": "Begin."})
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        body = {
            "model": self.model,
            "messages": filtered,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_msg.strip():
            body["system"] = system_msg.strip()
        
        # Convert OpenAI-style tools to Claude format
        if tools:
            claude_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    fn = tool["function"]
                    claude_tools.append({
                        "name": fn["name"],
                        "description": fn["description"],
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
                    })
            if claude_tools:
                body["tools"] = claude_tools
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(f"{self.base_url}/messages", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        
        content = ""
        tool_calls = None
        
        for block in data.get("content", []):
            if block["type"] == "text":
                content += block["text"]
            elif block["type"] == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "arguments": block.get("input", {})
                })
        
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.name,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            tool_calls=tool_calls,
            raw=data
        )

class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM integration."""
    
    name = "ollama"
    
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def is_available(self) -> bool:
        """Check if Ollama is available (with very short timeout)."""
        try:
            with httpx.Client(timeout=1.0) as client:  # Reduced from 5 to 1 second
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def complete(self, messages: List[Dict], tools: List[Dict] = None,
                 temperature: float = 0.7, max_tokens: int = 4096, **kwargs) -> LLMResponse:
        # Convert to Ollama format
        prompt_parts = []
        for msg in messages:
            role = msg["role"].upper()
            prompt_parts.append(f"[{role}]: {msg['content']}")
        prompt = "\n".join(prompt_parts) + "\n[ASSISTANT]:"
        
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        
        with httpx.Client(timeout=180.0) as client:
            response = client.post(f"{self.base_url}/api/generate", json=body)
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("response", ""),
            model=self.model,
            provider=self.name,
            raw=data
        )


class MockProvider(BaseLLMProvider):
    """Mock provider for testing without API keys."""
    
    name = "mock"
    
    def is_available(self) -> bool:
        return True
    
    def complete(self, messages: List[Dict], tools: List[Dict] = None, **kwargs) -> LLMResponse:
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        agent_name = "Agent"
        
        # Extract agent name from system prompt
        sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        if "You are " in sys_msg:
            parts = sys_msg.split("You are ")[1].split(",")[0].split(".")[0]
            agent_name = parts.strip()
        
        return LLMResponse(
            content=f"[{agent_name} - Mock Response] I received your message: '{user_msg[:100]}'. "
                    f"To enable real AI responses, configure an API key (OpenAI, Gemini, or Ollama) in the settings.",
            model="mock-1.0",
            provider=self.name
        )


class LLMRouter:
    """Routes requests to the best available LLM provider."""
    
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._default_provider: str = None
        
        # Auto-register providers based on available config
        self._auto_register()
    
    def _auto_register(self):
        # Try each provider (quick checks only - skip Ollama during startup to avoid blocking)
        providers = [
            OpenAIProvider(),
            GeminiProvider(),
            AnthropicProvider(),
            # OllamaProvider(),  # Commented out to prevent blocking startup
            MockProvider()  # Always available as fallback
        ]
        
        for provider in providers:
            try:
                self.register(provider)
                # Only check availability for quick providers
                if provider.is_available() and self._default_provider is None:
                    if provider.name != "mock":  # Prefer real providers
                        self._default_provider = provider.name
            except Exception as e:
                print(f"Warning: Failed to register {provider().name if hasattr(provider, 'name') else 'provider'}: {e}")
        
        # Check for explicit DEFAULT_LLM_PROVIDER environment variable
        env_provider = os.getenv("DEFAULT_LLM_PROVIDER")
        if env_provider and env_provider in self._providers:
            self._default_provider = env_provider
        
        if not self._default_provider:
            self._default_provider = "mock"
        
        # Register Ollama separately if explicitly configured
        try:
            ollama = OllamaProvider()
            if ollama.is_available():
                self.register(ollama)
        except Exception:
            pass  # Ollama not available, skip
    
    def register(self, provider: BaseLLMProvider):
        self._providers[provider.name] = provider
    
    def set_default(self, provider_name: str):
        if provider_name in self._providers:
            self._default_provider = provider_name
    
    def complete(self, messages: List[Dict], provider: str = None, 
                 tools: List[Dict] = None, **kwargs) -> LLMResponse:
        provider_name = provider or self._default_provider
        p = self._providers.get(provider_name)
        
        if not p:
            p = self._providers["mock"]
        
        return p.complete(messages, tools=tools, **kwargs)
    
    def available_providers(self) -> List[str]:
        return [name for name, p in self._providers.items() if p.is_available()]
    
    def status(self) -> Dict:
        return {
            name: {"available": p.is_available(), "default": name == self._default_provider}
            for name, p in self._providers.items()
        }


# Global router
LLM_ROUTER = LLMRouter()
