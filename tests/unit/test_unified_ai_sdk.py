from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import unified_ai_sdk.unified_ai_sdk as sdk_mod
from unified_ai_sdk import AIRequest, ModelProvider, TaskType, UnifiedAISDK


class TestUnifiedAISDK:
    async def test_unified_request_uses_openai_client(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        choice = SimpleNamespace(message=SimpleNamespace(content="openai response"))
        usage = SimpleNamespace(total_tokens=123)
        sdk._openai_client = MagicMock()
        sdk._openai_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[choice],
            usage=usage,
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="Say hello",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is True
        assert result.content == "openai response"
        assert result.provider == "openai"
        assert result.tokens_used == 123

    async def test_unified_request_uses_anthropic_client(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        sdk._anthropic_client = MagicMock()
        sdk._anthropic_client.messages.create.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", text="hidden"),
                SimpleNamespace(type="text", text="alpha"),
                SimpleNamespace(type="text", text="beta"),
            ],
            usage=SimpleNamespace(input_tokens=11, output_tokens=22),
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="Summarize this",
                model="claude-opus-4-8",
                provider=ModelProvider.CLAUDE,
                task_type=TaskType.SUMMARIZATION,
            )
        )

        assert result.success is True
        assert result.content == "alpha\nbeta"
        assert result.provider == "claude"
        assert result.tokens_used == 33

    async def test_unified_request_uses_gemini_client(self, monkeypatch):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        config_calls: list[dict[str, float | int]] = []
        monkeypatch.setattr(sdk_mod, "_GENAI_AVAILABLE", True)
        monkeypatch.setattr(
            sdk_mod,
            "_genai_types",
            SimpleNamespace(
                GenerateContentConfig=lambda **kwargs: config_calls.append(kwargs)
                or kwargs
            ),
            raising=False,
        )
        sdk._gemini_client = MagicMock()
        sdk._gemini_client.models.generate_content.return_value = SimpleNamespace(
            text=None,
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(text="part one"),
                            SimpleNamespace(text="part two"),
                        ]
                    )
                )
            ],
            usage_metadata=SimpleNamespace(total_token_count=88),
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="Analyze the video",
                model="gemini-2.5-flash",
                provider=ModelProvider.GEMINI,
                task_type=TaskType.VIDEO_ANALYSIS,
            )
        )

        assert result.success is True
        assert result.content == "part one\npart two"
        assert result.provider == "gemini"
        assert result.tokens_used == 88
        assert config_calls == [{"temperature": 0.7, "max_output_tokens": 4000}]

    async def test_unified_request_retries_before_succeeding(self):
        sdk = UnifiedAISDK({"retry_attempts": 2, "retry_base_delay": 0})
        choice = SimpleNamespace(message=SimpleNamespace(content="retried response"))
        usage = SimpleNamespace(total_tokens=77)
        sdk._openai_client = MagicMock()
        sdk._openai_client.chat.completions.create.side_effect = [
            RuntimeError("temporary failure"),
            SimpleNamespace(choices=[choice], usage=usage),
        ]

        result = await sdk.unified_request(
            AIRequest(
                prompt="Retry me",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is True
        assert result.content == "retried response"
        assert result.metadata["attempts"] == 2

    async def test_unified_request_returns_error_after_retries(self):
        sdk = UnifiedAISDK({"retry_attempts": 2, "retry_base_delay": 0})
        sdk._openai_client = MagicMock()
        sdk._openai_client.chat.completions.create.side_effect = RuntimeError(
            "provider unavailable"
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="Fail cleanly",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is False
        assert result.content == ""
        assert "provider unavailable" in (result.error or "")
        assert result.metadata["attempts"] == 2

    async def test_unified_request_reports_model_when_gemini_client_missing(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})

        result = await sdk.unified_request(
            AIRequest(
                prompt="Fail cleanly",
                model="gemini-2.5-flash",
                provider=ModelProvider.GEMINI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is False
        assert "gemini-2.5-flash" in (result.error or "")
