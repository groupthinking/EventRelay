from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import unified_ai_sdk.unified_ai_sdk as sdk_mod
from unified_ai_sdk import AIRequest, ModelProvider, TaskType, UnifiedAISDK


class TestUnifiedAISDK:
    @pytest.mark.asyncio
    async def test_unified_request_uses_openai_client(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        choice = SimpleNamespace(message=SimpleNamespace(content="openai response"))
        usage = SimpleNamespace(total_tokens=123)

        sdk._openai_client = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_unified_request_uses_anthropic_client(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        sdk._anthropic_client = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_unified_request_uses_gemini_client(self, monkeypatch):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        config_factory = MagicMock(side_effect=lambda **kwargs: kwargs)
        monkeypatch.setattr(sdk_mod, "_GENAI_AVAILABLE", True)
        monkeypatch.setattr(
            sdk_mod,
            "_genai_types",
            SimpleNamespace(GenerateContentConfig=config_factory),
            raising=False,
        )

        sdk._gemini_client = MagicMock()
        sdk._gemini_client.aio = MagicMock()
        sdk._gemini_client.aio.models = MagicMock()
        sdk._gemini_client.aio.models.generate_content = AsyncMock()

        sdk._gemini_client.aio.models.generate_content.return_value = SimpleNamespace(
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
        assert config_factory.call_args.kwargs == {
            "temperature": 0.7,
            "max_output_tokens": 4000,
        }

    @pytest.mark.asyncio
    async def test_unified_request_uses_grok_client(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        choice = SimpleNamespace(message=SimpleNamespace(content="grok response"))
        usage = SimpleNamespace(total_tokens=456)

        sdk._grok_client = AsyncMock()
        sdk._grok_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[choice],
            usage=usage,
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="What is the latest trend?",
                model="grok-3",
                provider=ModelProvider.GROK,
                task_type=TaskType.TREND_ANALYSIS,
            )
        )

        assert result.success is True
        assert result.content == "grok response"
        assert result.provider == "grok"
        assert result.tokens_used == 456

    @pytest.mark.asyncio
    async def test_unified_request_retries_before_succeeding(self):
        sdk = UnifiedAISDK({"retry_attempts": 2, "retry_base_delay": 0})
        choice = SimpleNamespace(message=SimpleNamespace(content="retried response"))
        usage = SimpleNamespace(total_tokens=77)

        sdk._openai_client = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_unified_request_returns_error_after_retries(self):
        sdk = UnifiedAISDK({"retry_attempts": 2, "retry_base_delay": 0})
        sdk._openai_client = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_unified_request_does_not_retry_on_auth_error(self):
        sdk = UnifiedAISDK({"retry_attempts": 3, "retry_base_delay": 0})
        sdk._openai_client = AsyncMock()
        sdk._openai_client.chat.completions.create.side_effect = RuntimeError(
            "Authentication failed"
        )

        result = await sdk.unified_request(
            AIRequest(
                prompt="Fail fast",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is False
        assert result.metadata["attempts"] == 1

    def test_should_retry_rejects_gemini_400_with_incidental_500(self):
        sdk = UnifiedAISDK({"retry_attempts": 3, "retry_base_delay": 0})

        assert (
            sdk._should_retry(
                RuntimeError(
                    "400 INVALID_ARGUMENT: input token count 500 exceeds model limit"
                )
            )
            is False
        )

    def test_should_retry_ignores_non_status_colon_numbers(self):
        sdk = UnifiedAISDK({"retry_attempts": 3, "retry_base_delay": 0})

        assert (
            sdk._should_retry(
                RuntimeError("invalid_request: expected 3 items: 503 found")
            )
            is False
        )

    @pytest.mark.parametrize(
        "message",
        [
            "500 INTERNAL: upstream unavailable",
            "Response: 500 Internal Server Error",
            "429 RESOURCE_EXHAUSTED: quota exceeded",
        ],
    )
    def test_should_retry_accepts_retryable_status_formats(self, message):
        sdk = UnifiedAISDK({"retry_attempts": 3, "retry_base_delay": 0})

        assert sdk._should_retry(RuntimeError(message)) is True

    @pytest.mark.asyncio
    async def test_structured_output_support(self):
        sdk = UnifiedAISDK({"retry_attempts": 1})
        sdk._openai_client = AsyncMock()
        sdk._openai_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"key": "value"}'))],
            usage=SimpleNamespace(total_tokens=10),
        )

        await sdk.unified_request(
            AIRequest(
                prompt="Give me JSON",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
                structured_output=True,
            )
        )

        _, kwargs = sdk._openai_client.chat.completions.create.call_args
        assert kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_empty_content_triggers_retry(self):
        sdk = UnifiedAISDK({"retry_attempts": 2, "retry_base_delay": 0})
        sdk._openai_client = AsyncMock()

        # First call returns empty content, second call succeeds
        sdk._openai_client.chat.completions.create.side_effect = [
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))], usage=SimpleNamespace(total_tokens=0)),
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="success"))], usage=SimpleNamespace(total_tokens=10)),
        ]

        result = await sdk.unified_request(
            AIRequest(
                prompt="Don't be empty",
                model="gpt-4o",
                provider=ModelProvider.OPENAI,
                task_type=TaskType.GENERIC,
            )
        )

        assert result.success is True
        assert result.content == "success"
        assert result.metadata["attempts"] == 2

    @pytest.mark.asyncio
    async def test_anthropic_call_omits_temperature_with_thinking(self):
        # Anthropic rejects a non-1 temperature when extended thinking is on;
        # the call must not forward request.temperature.
        sdk = UnifiedAISDK({"retry_attempts": 1})
        sdk._anthropic_client = MagicMock()
        sdk._anthropic_client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="ok")],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
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
        _, kwargs = sdk._anthropic_client.messages.create.call_args
        assert "temperature" not in kwargs
        assert kwargs["thinking"] == {"type": "adaptive"}
        # Explicit timeout is forwarded so a slow upstream can't pin the worker.
        assert kwargs["timeout"] == 60.0


class TestModelProviderContract:
    """Regression guard for the #773 enum drift.

    #773 trimmed ``ModelProvider`` to ``{OPENAI, ANTHROPIC, GEMINI}`` while
    ``UnifiedAISDK._rate_limit_provider`` still referenced ``ModelProvider.CLAUDE``
    and ``.GROK`` by name, so every Claude/Grok request raised
    ``AttributeError`` at runtime and the CI ``test`` job went red. These tests
    assert the enum stays consistent with its consumers so the same class of
    regression fails fast in unit tests rather than in production.
    """

    def test_enum_has_all_members_referenced_by_consumers(self):
        # Members referenced directly by UnifiedAISDK._rate_limit_provider and
        # the provider test suite. Removing any of these reintroduces #773.
        for name, value in (
            ("OPENAI", "openai"),
            ("CLAUDE", "claude"),
            ("ANTHROPIC", "anthropic"),
            ("GEMINI", "gemini"),
            ("GROK", "grok"),
        ):
            member = getattr(ModelProvider, name)
            assert member.value == value

    def test_rate_limit_provider_resolves_every_dispatchable_provider(self):
        # Every provider the SDK can dispatch (see UnifiedAISDK._handlers /
        # _normalize_provider) must map to a ModelProvider without raising.
        sdk = UnifiedAISDK({"retry_attempts": 1})
        for provider_name in ("openai", "claude", "grok", "gemini"):
            provider = sdk._rate_limit_provider(provider_name)
            assert isinstance(provider, ModelProvider)

    def test_normalize_provider_maps_anthropic_alias_to_claude(self):
        # ModelProvider.ANTHROPIC and .CLAUDE both resolve to the "claude" path.
        sdk = UnifiedAISDK({"retry_attempts": 1})
        assert sdk._normalize_provider(ModelProvider.ANTHROPIC) == "claude"
        assert sdk._normalize_provider(ModelProvider.CLAUDE) == "claude"
