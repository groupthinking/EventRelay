"""
Tests for unified_ai_sdk.UnifiedAISDK.

These tests verify that the SDK never returns fabricated success payloads:
- Missing API keys → AIResponse(success=False)
- Unknown providers → AIResponse(success=False)
- health_check with no keys → all providers reported as 'unconfigured'
"""

import pytest

from unified_ai_sdk import AIRequest, AIResponse, ModelProvider, TaskType, UnifiedAISDK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(provider: ModelProvider, model: str = "test-model") -> AIRequest:
    return AIRequest(
        prompt="hello",
        model=model,
        provider=provider,
        task_type=TaskType.GENERIC,
    )


# ---------------------------------------------------------------------------
# unified_request — missing key → success=False (no fabricated success)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unified_request_claude_no_key_returns_failure():
    sdk = UnifiedAISDK(config={})  # no keys in config, no env vars set
    resp = await sdk.unified_request(_make_request(ModelProvider.CLAUDE))
    assert isinstance(resp, AIResponse)
    assert resp.success is False
    assert resp.error is not None
    assert resp.content == ""


@pytest.mark.asyncio
async def test_unified_request_openai_no_key_returns_failure():
    sdk = UnifiedAISDK(config={})
    resp = await sdk.unified_request(_make_request(ModelProvider.OPENAI))
    assert resp.success is False
    assert resp.error is not None


@pytest.mark.asyncio
async def test_unified_request_grok_no_key_returns_failure():
    sdk = UnifiedAISDK(config={})
    resp = await sdk.unified_request(_make_request(ModelProvider.GROK))
    assert resp.success is False
    assert resp.error is not None


@pytest.mark.asyncio
async def test_unified_request_gemini_no_key_returns_failure():
    sdk = UnifiedAISDK(config={})
    resp = await sdk.unified_request(_make_request(ModelProvider.GEMINI))
    assert resp.success is False
    assert resp.error is not None


@pytest.mark.asyncio
async def test_unified_request_unknown_string_provider_returns_failure():
    sdk = UnifiedAISDK(config={})
    req = AIRequest(
        prompt="hello",
        model="some-model",
        provider="totally_unknown_provider",
        task_type=TaskType.GENERIC,
    )
    resp = await sdk.unified_request(req)
    assert resp.success is False
    assert resp.error is not None


# ---------------------------------------------------------------------------
# unified_request — response metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unified_request_failure_preserves_model_and_provider():
    sdk = UnifiedAISDK(config={})
    resp = await sdk.unified_request(
        AIRequest(
            prompt="test",
            model="gpt-4o",
            provider=ModelProvider.OPENAI,
            task_type=TaskType.QUESTION_ANSWERING,
        )
    )
    assert resp.model == "gpt-4o"
    assert resp.provider == "openai"


# ---------------------------------------------------------------------------
# unified_request — no placeholder strings returned as success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unified_request_does_not_return_placeholder_text_as_success():
    """Regression: the old implementation returned '[Placeholder response...]'
    with success=True.  That must never happen."""
    sdk = UnifiedAISDK(config={})
    for provider in ModelProvider:
        resp = await sdk.unified_request(_make_request(provider))
        # If success is True, content must not be a placeholder string
        if resp.success:
            assert "[Placeholder" not in resp.content
            assert "not_implemented" not in resp.content


# ---------------------------------------------------------------------------
# health_check — all providers unconfigured when no keys present
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_all_unconfigured_when_no_keys():
    sdk = UnifiedAISDK(config={})
    result = await sdk.health_check()
    assert "providers" in result
    for status in result["providers"].values():
        assert status == "unconfigured"
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_returns_degraded_when_some_unconfigured():
    sdk = UnifiedAISDK(config={})
    result = await sdk.health_check()
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_does_not_return_placeholder_status():
    """Regression: old implementation returned status='placeholder'."""
    sdk = UnifiedAISDK(config={})
    result = await sdk.health_check()
    assert result.get("status") != "placeholder"
    # Must not contain 'not_implemented' values
    for v in result.get("providers", {}).values():
        assert v != "not_implemented"
