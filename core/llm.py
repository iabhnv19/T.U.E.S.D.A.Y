"""core/llm.py
Universal LLM client supporting any AI API provider:
- Groq (default, ultra-fast free tier)
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- OpenRouter (Claude, Gemini, Llama, DeepSeek via unified gateway)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Ollama (Local offline models: llama3.2, qwen2.5, mistral)
- LM Studio / LocalAI / vLLM / Custom OpenAI-compatible endpoints
"""

import json
import os
import requests
from typing import Optional, List, Dict, Any


class ToolCallFunction:
    """Wrapper matching OpenAI / Groq tool call function structure."""
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class ToolCall:
    """Wrapper matching OpenAI / Groq tool call structure."""
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.type = "function"
        self.function = ToolCallFunction(name, arguments)


class AssistantMessage:
    """Standardized assistant reply message."""
    def __init__(self, content: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None):
        self.role = "assistant"
        self.content = content or ""
        self.tool_calls = tool_calls or None


class Choice:
    """Standardized response choice wrapper."""
    def __init__(self, message: AssistantMessage):
        self.message = message


class ChatCompletionResponse:
    """Standardized completion response for the brain agent loop."""
    def __init__(self, choices: List[Choice], model: str = ""):
        self.choices = choices
        self.model = model


# ── Provider Presets ────────────────────────────────────────────────────────

PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "openai/gpt-oss-120b",
        "fallback_models": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
        ],
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "fallback_models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "fallback_models": [
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "google/gemini-2.0-flash-exp:free",
        ],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "fallback_models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "fallback_models": ["llama3.2", "qwen2.5", "mistral"],
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "fallback_models": ["local-model"],
    },
}

DEFAULT_FALLBACK_MODELS: List[str] = list(PROVIDER_PRESETS["groq"]["fallback_models"])


class UniversalLLMClient:
    """
    Connects to any AI provider using the standard OpenAI-compatible completions API.
    Uses native Groq SDK if available for Groq, or direct HTTP requests for any endpoint.
    """

    def __init__(
        self,
        provider: str = "groq",
        api_key: str = "",
        base_url: str = "",
        default_model: str = "",
    ):
        self.provider = provider.lower().strip() or "groq"
        preset = PROVIDER_PRESETS.get(self.provider, {})

        if self.provider in ("ollama", "lmstudio"):
            self.api_key = api_key
        else:
            self.api_key = api_key or os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or preset.get("base_url") or "https://api.groq.com/openai/v1").rstrip("/")
        self.default_model = default_model or preset.get("default_model") or "qwen/qwen3.8-27b"
        self.fallback_models = list(preset.get("fallback_models") or [self.default_model])

        self.session = requests.Session()
        self.chat = _ChatProxy(self)
        self.models = _ModelsProxy(self)

        # Optional native Groq SDK optimization
        self._groq_client = None
        if self.provider == "groq" and self.api_key and "groq.com" in self.base_url:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.api_key)
            except Exception:
                self._groq_client = None

    def list_models(self) -> List[str]:
        """Fetch available models from the provider endpoint."""
        if self._groq_client:
            try:
                m_list = self._groq_client.models.list()
                return [m.id for m in m_list.data if m.id]
            except Exception:
                pass

        try:
            headers = self._build_headers()
            url = f"{self.base_url}/models"
            resp = self.session.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                models = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
                if models:
                    return models
        except Exception:
            pass

        return self.fallback_models

    def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[ChatCompletionResponse]:
        """Send chat completion request to the active AI provider."""
        # Fast path via native Groq SDK if available
        if self._groq_client:
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools

                sdk_resp = self._groq_client.chat.completions.create(**kwargs)
                return sdk_resp
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in ["rate limit", "429", "tokens per day", "tokens per minute"]):
                    raise e

        # Universal HTTP POST to /chat/completions
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=25)

            if resp.status_code == 429:
                raise Exception(f"RateLimitError: 429 Too Many Requests from {self.provider}")

            if resp.status_code != 200:
                err_body = resp.text[:300]
                if any(x in err_body.lower() for x in ["rate limit", "quota", "tpm", "rpd"]):
                    raise Exception(f"RateLimitError: {err_body}")
                print(f"[LLM] Error {resp.status_code} from {self.provider}: {err_body}")
                return None

            data = resp.json()
            raw_choices = data.get("choices", [])
            if not raw_choices:
                return None

            choices_list = []
            for rc in raw_choices:
                msg_data = rc.get("message", {})
                raw_tc = msg_data.get("tool_calls")
                parsed_tc = None
                if raw_tc and isinstance(raw_tc, list):
                    parsed_tc = []
                    for t in raw_tc:
                        fn = t.get("function", {})
                        parsed_tc.append(
                            ToolCall(
                                id=t.get("id", "call_id"),
                                name=fn.get("name", ""),
                                arguments=fn.get("arguments", "{}"),
                            )
                        )
                msg_obj = AssistantMessage(
                    content=msg_data.get("content", ""),
                    tool_calls=parsed_tc,
                )
                choices_list.append(Choice(msg_obj))

            return ChatCompletionResponse(choices=choices_list, model=data.get("model", model))

        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["ratelimit", "429", "quota", "too many requests"]):
                raise e
            print(f"[LLM] Request failed: {e}")
            return None

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """Stream token strings as they are generated by the LLM."""
        # 1. Native Groq SDK streaming
        if self._groq_client:
            try:
                stream_resp = self._groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in stream_resp:
                    if chunk.choices and chunk.choices[0].delta:
                        content = chunk.choices[0].delta.content or ""
                        if content:
                            yield content
                return
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in ["rate limit", "429", "tokens per day", "tokens per minute"]):
                    raise e
                print(f"[LLM] Native streaming fallback triggered: {e}")

        # 2. Universal HTTP SSE streaming
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=25, stream=True)
            if resp.status_code == 429:
                raise Exception(f"RateLimitError: 429 Too Many Requests from {self.provider}")
            if resp.status_code != 200:
                err_body = resp.text[:200]
                if any(x in err_body.lower() for x in ["rate limit", "quota", "tpm", "rpd"]):
                    raise Exception(f"RateLimitError: {err_body}")
                print(f"[LLM] Streaming error {resp.status_code}: {err_body}")
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str.startswith("data: "):
                    data_str = line_str[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except Exception:
                        pass
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["ratelimit", "429", "quota", "too many requests"]):
                raise e
            print(f"[LLM] Stream request failed: {e}")

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "T.U.E.S.D.A.Y-Desktop-Assistant/2.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/TUESDAY"
            headers["X-Title"] = "T.U.E.S.D.A.Y Voice Assistant"

        return headers


class _CompletionsProxy:
    """OpenAI-compatible proxy interface: client.chat.completions.create(...)"""
    def __init__(self, client: UniversalLLMClient):
        self._client = client

    def create(self, **kwargs) -> Any:
        return self._client.create_chat_completion(
            messages=kwargs.get("messages", []),
            model=kwargs.get("model", self._client.default_model),
            tools=kwargs.get("tools"),
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 500),
        )


class _ChatProxy:
    def __init__(self, client: UniversalLLMClient):
        self.completions = _CompletionsProxy(client)


class _ModelsProxy:
    def __init__(self, client: UniversalLLMClient):
        self._client = client

    def list(self):
        class ModelItem:
            def __init__(self, mid):
                self.id = mid
        class ModelListResponse:
            def __init__(self, ids):
                self.data = [ModelItem(i) for i in ids]
        return ModelListResponse(self._client.list_models())
