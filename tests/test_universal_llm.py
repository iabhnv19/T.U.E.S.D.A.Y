"""tests/test_universal_llm.py
Unit tests for Universal LLM provider integration (Groq, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.llm import (
    UniversalLLMClient,
    PROVIDER_PRESETS,
    ToolCall,
    AssistantMessage,
    Choice,
    ChatCompletionResponse,
)
from core.config import Config
from core.brain import AIBrain


class TestUniversalLLMClient:
    """Test universal LLM client across providers and schemas."""

    def test_provider_presets_exist(self):
        expected_providers = ["groq", "openai", "openrouter", "deepseek", "ollama", "lmstudio"]
        for p in expected_providers:
            assert p in PROVIDER_PRESETS
            assert "base_url" in PROVIDER_PRESETS[p]
            assert "default_model" in PROVIDER_PRESETS[p]
            assert len(PROVIDER_PRESETS[p]["fallback_models"]) > 0

    def test_ollama_local_provider(self):
        client = UniversalLLMClient(provider="ollama")
        assert "11434" in client.base_url
        assert client.default_model == "llama3.2"
        headers = client._build_headers()
        assert "Authorization" not in headers  # Local Ollama needs no auth header

    def test_openrouter_headers(self):
        client = UniversalLLMClient(provider="openrouter", api_key="sk-or-test-key")
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer sk-or-test-key"
        assert "HTTP-Referer" in headers
        assert "X-Title" in headers

    def test_chat_proxy_interface(self):
        client = UniversalLLMClient(provider="openai", api_key="sk-test-key")
        # Ensure client.chat.completions.create exists and matches OpenAI SDK shape
        assert hasattr(client, "chat")
        assert hasattr(client.chat, "completions")
        assert hasattr(client.chat.completions, "create")

    def test_tool_call_normalization(self):
        # Emulate HTTP response from any OpenAI-compatible provider
        raw_response = {
            "model": "deepseek-chat",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"city": "Mumbai"}'
                                }
                            }
                        ]
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = raw_response

        client = UniversalLLMClient(provider="deepseek", api_key="sk-deepseek")
        with patch.object(client.session, "post", return_value=mock_resp):
            comp = client.create_chat_completion(
                messages=[{"role": "user", "content": "Weather in Mumbai?"}],
                model="deepseek-chat",
            )
            assert comp is not None
            assert len(comp.choices) == 1
            choice = comp.choices[0]
            assert choice.message.tool_calls is not None
            tc = choice.message.tool_calls[0]
            assert tc.id == "call_abc123"
            assert tc.function.name == "get_weather"
            assert "Mumbai" in tc.function.arguments

    def test_brain_works_with_universal_client(self):
        brain = AIBrain()
        assert isinstance(brain.client, UniversalLLMClient)
        assert len(brain.available_models) > 0
