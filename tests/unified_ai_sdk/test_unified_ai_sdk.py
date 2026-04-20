"""Tests for the real provider-backed Unified AI SDK."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure `src/` is importable regardless of pytest cwd.
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from unified_ai_sdk.unified_ai_sdk import (  # noqa: E402
    AIRequest,
    AIResponse,
    ModelProvider,
    TaskType,
    UnifiedAISDK,
    _is_retryable_error,
    _resolve_provider,
    _with_retries,
)


def _make_request(
    provider=ModelProvider.OPENAI,
    model="gpt-4o-mini",
    structured_output=False,
) -> AIRequest:
    return AIRequest(
        prompt="hello",
        model=model,
        provider=provider,
        task_type=TaskType.GENERIC,
        temperature=0.2,
        max_tokens=64,
        structured_output=structured_output,
    )


def _sdk_with_keys(**overrides: Any) -> UnifiedAISDK:
    config = {
        "api_keys": {
            "openai": "sk-openai",
            "claude": "sk-anthropic",
            "gemini": "sk-gemini",
        },
        "retry": {"max_retries": 2, "base_delay": 0, "max_delay": 0},
    }
    config.update(overrides)
    return UnifiedAISDK(config)


class TestResolveProvider:
    def test_enum_passthrough(self):
        assert _resolve_provider(ModelProvider.OPENAI) is ModelProvider.OPENAI

    def test_string_match(self):
        assert _resolve_provider("openai") is ModelProvider.OPENAI
        assert _resolve_provider("CLAUDE") is ModelProvider.CLAUDE

    def test_unknown_returns_none(self):
        assert _resolve_provider("nobody") is None

    def test_none_returns_none(self):
        assert _resolve_provider(None) is None


class TestIsRetryableError:
    def test_status_code_attr(self):
        exc = Exception("boom")
        exc.status_code = 429  # type: ignore[attr-defined]
        assert _is_retryable_error(exc) is True

    def test_response_status(self):
        exc = Exception("oops")
        resp = types.SimpleNamespace(status_code=503)
        exc.response = resp  # type: ignore[attr-defined]
        assert _is_retryable_error(exc) is True

    def test_name_marker(self):
        class RateLimitError(Exception):
            pass

        assert _is_retryable_error(RateLimitError("slow down")) is True

    def test_non_retryable(self):
        assert _is_retryable_error(ValueError("bad input")) is False


class TestWithRetries:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        call = AsyncMock(return_value="ok")
        result = await _with_retries(call, max_retries=3, base_delay=0, max_delay=0)
        assert result == "ok"
        assert call.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_retryable(self):
        attempts = {"n": 0}

        async def flaky():
            attempts["n"] += 1
            if attempts["n"] < 3:
                err = Exception("rate limit")
                err.status_code = 429  # type: ignore[attr-defined]
                raise err
            return "ok"

        result = await _with_retries(flaky, max_retries=5, base_delay=0, max_delay=0)
        assert result == "ok"
        assert attempts["n"] == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable(self):
        async def bad():
            raise ValueError("permanent")

        with pytest.raises(ValueError):
            await _with_retries(bad, max_retries=3, base_delay=0, max_delay=0)

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        async def always_rate_limited():
            err = Exception("rate limit")
            err.status_code = 429  # type: ignore[attr-defined]
            raise err

        with pytest.raises(Exception) as exc_info:
            await _with_retries(
                always_rate_limited, max_retries=2, base_delay=0, max_delay=0
            )
        assert "rate limit" in str(exc_info.value).lower()


class TestUnifiedAISDKConstruction:
    def test_loads_keys_from_config(self):
        sdk = _sdk_with_keys()
        assert sdk._api_keys[ModelProvider.OPENAI] == "sk-openai"
        assert sdk._api_keys[ModelProvider.CLAUDE] == "sk-anthropic"
        assert sdk._api_keys[ModelProvider.GEMINI] == "sk-gemini"

    def test_loads_keys_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic")
        monkeypatch.setenv("GEMINI_API_KEY", "env-gemini")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        sdk = UnifiedAISDK({})
        assert sdk._api_keys[ModelProvider.OPENAI] == "env-openai"
        assert sdk._api_keys[ModelProvider.CLAUDE] == "env-anthropic"
        assert sdk._api_keys[ModelProvider.GEMINI] == "env-gemini"

    def test_alt_env_for_gemini(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        sdk = UnifiedAISDK({})
        assert sdk._api_keys[ModelProvider.GEMINI] == "google-key"


class TestUnifiedRequestErrorPaths:
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error_response(self, monkeypatch):
        # Strip every provider env key.
        for var in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_API_KEY",
        ):
            monkeypatch.delenv(var, raising=False)
        sdk = UnifiedAISDK({})
        resp = await sdk.unified_request(_make_request())
        assert isinstance(resp, AIResponse)
        assert resp.success is False
        assert resp.content == ""
        assert "Missing API key" in (resp.error or "")

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error_response(self):
        sdk = _sdk_with_keys()
        req = AIRequest(
            prompt="hi",
            model="x",
            provider="martian",
            task_type=TaskType.GENERIC,
        )
        resp = await sdk.unified_request(req)
        assert resp.success is False
        assert resp.content == ""
        assert "Unknown provider" in (resp.error or "")

    @pytest.mark.asyncio
    async def test_grok_unsupported_returns_error(self):
        sdk = _sdk_with_keys(api_keys={"grok": "sk-grok"})
        # Overwrite so unsupported branch is reached.
        sdk._api_keys[ModelProvider.GROK] = "sk-grok"
        req = _make_request(provider=ModelProvider.GROK, model="grok-2")
        resp = await sdk.unified_request(req)
        assert resp.success is False
        assert "not supported" in (resp.error or "")

    @pytest.mark.asyncio
    async def test_provider_exception_becomes_error_response(self):
        sdk = _sdk_with_keys()

        async def blowup(*_args, **_kwargs):
            raise RuntimeError("boom")

        with patch.object(sdk, "_call_openai", side_effect=blowup):
            resp = await sdk.unified_request(_make_request())
        assert resp.success is False
        assert resp.content == ""
        assert "RuntimeError" in (resp.error or "")


class TestOpenAIMapping:
    @pytest.mark.asyncio
    async def test_openai_response_mapping(self):
        sdk = _sdk_with_keys()

        message = MagicMock()
        message.content = "hello world"
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "stop"
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = MagicMock(total_tokens=42)
        completion.id = "cmpl-1"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=completion)

        with patch(
            "openai.AsyncOpenAI", return_value=mock_client
        ) as ctor:
            resp = await sdk._call_openai(_make_request(), "sk-openai")

        ctor.assert_called_once_with(api_key="sk-openai")
        kwargs = mock_client.chat.completions.create.await_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"][-1]["content"] == "hello"
        assert "response_format" not in kwargs
        assert resp.success is True
        assert resp.content == "hello world"
        assert resp.tokens_used == 42
        assert resp.provider == "openai"
        assert resp.metadata["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_openai_structured_output_parses_json(self):
        sdk = _sdk_with_keys()

        message = MagicMock()
        message.content = '{"a": 1}'
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "stop"
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = MagicMock(total_tokens=5)
        completion.id = "x"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=completion)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            resp = await sdk._call_openai(
                _make_request(structured_output=True), "sk-openai"
            )
        kwargs = mock_client.chat.completions.create.await_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        assert resp.metadata["structured"] == {"a": 1}


class TestAnthropicMapping:
    @pytest.mark.asyncio
    async def test_anthropic_response_mapping(self):
        sdk = _sdk_with_keys()

        block = MagicMock()
        block.text = "claude says hi"
        message = MagicMock()
        message.content = [block]
        message.usage = MagicMock(input_tokens=3, output_tokens=7)
        message.stop_reason = "end_turn"
        message.id = "msg-1"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=message)

        with patch("anthropic.AsyncAnthropic", return_value=mock_client) as ctor:
            resp = await sdk._call_anthropic(
                _make_request(provider=ModelProvider.CLAUDE, model="claude-sonnet"),
                "sk-anthropic",
            )

        ctor.assert_called_once_with(api_key="sk-anthropic")
        assert resp.success is True
        assert resp.content == "claude says hi"
        assert resp.tokens_used == 10
        assert resp.provider == "claude"
        assert resp.metadata["stop_reason"] == "end_turn"


class TestGeminiMapping:
    @pytest.mark.asyncio
    async def test_gemini_response_mapping(self):
        sdk = _sdk_with_keys()

        response = MagicMock()
        response.text = "gemini says hi"
        response.usage_metadata = MagicMock(
            total_token_count=11, prompt_token_count=4, candidates_token_count=7
        )
        finish = MagicMock()
        finish.name = "STOP"
        response.candidates = [MagicMock(finish_reason=finish)]

        fake_genai = MagicMock()
        model_inst = MagicMock()
        model_inst.generate_content = MagicMock(return_value=response)
        fake_genai.GenerativeModel = MagicMock(return_value=model_inst)
        fake_genai.configure = MagicMock()

        with patch.dict(sys.modules, {"google.generativeai": fake_genai}):
            resp = await sdk._call_gemini(
                _make_request(provider=ModelProvider.GEMINI, model="gemini-1.5-flash"),
                "sk-gemini",
            )

        fake_genai.configure.assert_called_with(api_key="sk-gemini")
        assert resp.success is True
        assert resp.content == "gemini says hi"
        assert resp.tokens_used == 11
        assert resp.provider == "gemini"
        assert resp.metadata["finish_reason"] == "STOP"


class TestUnifiedRequestRetry:
    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        sdk = _sdk_with_keys()
        calls = {"n": 0}

        async def flaky(_req, _key):
            calls["n"] += 1
            if calls["n"] < 2:
                err = Exception("please retry")
                err.status_code = 429  # type: ignore[attr-defined]
                raise err
            return AIResponse(
                content="after retry",
                model=_req.model,
                provider="openai",
                success=True,
                tokens_used=1,
            )

        with patch.object(sdk, "_call_openai", side_effect=flaky):
            resp = await sdk.unified_request(_make_request())
        assert resp.success is True
        assert resp.content == "after retry"
        assert calls["n"] == 2


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_shape_all_healthy(self):
        sdk = _sdk_with_keys()

        async def ok(_key):
            return "ok"

        with patch.object(sdk, "_health_openai", side_effect=ok), patch.object(
            sdk, "_health_anthropic", side_effect=ok
        ), patch.object(sdk, "_health_gemini", side_effect=ok):
            result = await sdk.health_check()
        assert set(result.keys()) == {"status", "providers"}
        assert result["status"] == "healthy"
        assert set(result["providers"].keys()) == {"openai", "claude", "gemini"}
        for entry in result["providers"].values():
            assert entry["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_one_fails(self):
        sdk = _sdk_with_keys()

        async def ok(_key):
            return "ok"

        async def fail(_key):
            raise RuntimeError("down")

        with patch.object(sdk, "_health_openai", side_effect=ok), patch.object(
            sdk, "_health_anthropic", side_effect=ok
        ), patch.object(sdk, "_health_gemini", side_effect=fail):
            result = await sdk.health_check()
        assert result["status"] == "degraded"
        assert result["providers"]["gemini"]["status"] == "unhealthy"
        assert result["providers"]["openai"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unconfigured_when_no_keys(self, monkeypatch):
        for var in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_API_KEY",
        ):
            monkeypatch.delenv(var, raising=False)
        sdk = UnifiedAISDK({})
        result = await sdk.health_check()
        assert result["status"] == "unhealthy"
        for entry in result["providers"].values():
            assert entry["status"] == "unconfigured"

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        sdk = _sdk_with_keys()

        import asyncio

        async def hang(_key):
            await asyncio.sleep(10)

        with patch.object(sdk, "_health_openai", side_effect=hang), patch.object(
            sdk, "_health_anthropic", side_effect=hang
        ), patch.object(sdk, "_health_gemini", side_effect=hang):
            with patch(
                "unified_ai_sdk.unified_ai_sdk._HEALTH_CHECK_TIMEOUT", 0.05
            ):
                result = await sdk.health_check()
        for entry in result["providers"].values():
            assert entry["status"] == "unhealthy"
            assert "timeout" in entry["detail"]


class TestRateLimiterIntegration:
    @pytest.mark.asyncio
    async def test_rate_limiter_is_called_before_provider(self):
        sdk = _sdk_with_keys()
        call_order: list[str] = []

        async def fake_wait(provider, tokens=0):
            call_order.append(f"rl:{provider.value}")

        async def fake_call(_req, _key):
            call_order.append("provider")
            return AIResponse(
                content="ok",
                model=_req.model,
                provider="openai",
                success=True,
                tokens_used=1,
            )

        sdk.rate_limiter.wait_if_needed = fake_wait  # type: ignore[assignment]
        with patch.object(sdk, "_call_openai", side_effect=fake_call):
            resp = await sdk.unified_request(_make_request())
        assert resp.success is True
        assert call_order == ["rl:openai", "provider"]
