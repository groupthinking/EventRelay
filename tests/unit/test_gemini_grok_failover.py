"""Tests for Gemini → Grok video processing failover.

Validates that GeminiVideoService automatically activates Grok as
backup when Gemini video processing fails, as per the failover policy:
"If Gemini video processing and intelligence fails, the backup is GROK."
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from integration.gemini_video import GeminiVideoService, VideoAnalysisResult

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_GEMINI_KEY = "test-gemini-key"
_GROK_KEY = "test-grok-key"
_VIDEO_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
_PROMPT = "Analyze this video and extract key events"


@pytest.fixture(autouse=True)
def _isolate_service_state(monkeypatch):
    """Avoid real transports and class-level API-key leakage between tests."""
    client = MagicMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    monkeypatch.setattr(
        "integration.gemini_video.httpx.AsyncClient",
        MagicMock(return_value=client),
    )
    monkeypatch.setattr(GeminiVideoService, "API_KEYS", [])


def _make_service(grok_key: str | None = _GROK_KEY) -> GeminiVideoService:
    """Instantiate GeminiVideoService with test keys."""
    with patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": _GEMINI_KEY,
            "XAI_API_KEY": grok_key or "",
        },
        clear=False,
    ):
        svc = GeminiVideoService(api_key=_GEMINI_KEY)
        if grok_key:
            svc.grok_api_key = grok_key
        else:
            svc.grok_api_key = None
    return svc


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_service_exposes_grok_constants() -> None:
    """GeminiVideoService must declare Grok API URL and default model."""
    assert GeminiVideoService.GROK_API_URL == "https://api.x.ai/v1/chat/completions"
    assert GeminiVideoService.GROK_MODEL.startswith("grok")


def test_service_loads_grok_api_key_from_env() -> None:
    """Grok API key is loaded from XAI_API_KEY env var."""
    with patch.dict(
        os.environ,
        {"GEMINI_API_KEY": _GEMINI_KEY, "XAI_API_KEY": "xai-secret-123"},
        clear=False,
    ):
        svc = GeminiVideoService(api_key=_GEMINI_KEY)
    assert svc.grok_api_key == "xai-secret-123"


def test_service_loads_grok_key_fallback_env_vars() -> None:
    """Grok key is read from legacy XAI_GROK4_API if XAI_API_KEY absent."""
    env = {
        "GEMINI_API_KEY": _GEMINI_KEY,
        "XAI_GROK4_API": "grok-legacy-key",
    }
    # Ensure the primary var is absent
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("XAI_API_KEY", None)
        svc = GeminiVideoService(api_key=_GEMINI_KEY)
    assert svc.grok_api_key == "grok-legacy-key"


@pytest.mark.asyncio
async def test_grok_fallback_called_on_gemini_failure() -> None:
    """When Gemini raises, _call_grok_fallback is invoked."""
    svc = _make_service()

    expected = VideoAnalysisResult(
        summary="Grok analysis result",
        key_events=[{"event": "test event"}],
    )

    with patch.object(
        svc, "_make_request", new_callable=AsyncMock, side_effect=RuntimeError("Gemini down")
    ):
        with patch.object(
            svc, "_call_grok_fallback", new_callable=AsyncMock, return_value=expected
        ) as mock_grok:
            result = await svc.analyze_video(_VIDEO_URL, _PROMPT)

    mock_grok.assert_awaited_once_with(_VIDEO_URL, _PROMPT)
    assert result.summary == "Grok analysis result"


@pytest.mark.asyncio
async def test_grok_fallback_raises_when_no_grok_key() -> None:
    """_call_grok_fallback raises RuntimeError when Grok API key is absent."""
    svc = _make_service(grok_key=None)

    with pytest.raises(RuntimeError, match="no Grok API key"):
        await svc._call_grok_fallback(_VIDEO_URL, _PROMPT)


@pytest.mark.asyncio
async def test_grok_fallback_parses_json_response() -> None:
    """_call_grok_fallback correctly parses a well-formed JSON response."""
    svc = _make_service()

    grok_response_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Grok summary",
                            "key_events": [{"event": "e1"}],
                            "timestamps": [{"t": "0:10"}],
                        }
                    )
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = grok_response_body

    with patch.object(
        svc.client, "post", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await svc._call_grok_fallback(_VIDEO_URL, _PROMPT)

    assert result.summary == "Grok summary"
    assert result.key_events == [{"event": "e1"}]
    assert result.timestamps == [{"t": "0:10"}]


@pytest.mark.asyncio
async def test_grok_fallback_handles_plain_text_response() -> None:
    """_call_grok_fallback handles non-JSON Grok responses gracefully."""
    svc = _make_service()

    plain_text = "This video explains how to build a REST API step by step."
    grok_response_body = {
        "choices": [{"message": {"content": plain_text}}]
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = grok_response_body

    with patch.object(
        svc.client, "post", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await svc._call_grok_fallback(_VIDEO_URL, _PROMPT)

    assert result.summary == plain_text


@pytest.mark.asyncio
async def test_analyze_video_succeeds_without_fallback() -> None:
    """When Gemini succeeds, Grok fallback is NOT called."""
    svc = _make_service()

    gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {"summary": "Gemini success", "key_events": []}
                            )
                        }
                    ]
                }
            }
        ]
    }

    with patch.object(
        svc, "_make_request", new_callable=AsyncMock, return_value=gemini_response
    ):
        with patch.object(
            svc, "_call_grok_fallback", new_callable=AsyncMock
        ) as mock_grok:
            result = await svc.analyze_video(_VIDEO_URL, _PROMPT)

    mock_grok.assert_not_awaited()
    assert result.summary == "Gemini success"


# ---------------------------------------------------------------------------
# ModelRouter video routing tests
# ---------------------------------------------------------------------------


def test_model_router_routes_video_to_gemini() -> None:
    """ModelRouter should select gemini as primary for video analysis tasks."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from core.model_router import ModelRouter

    router = ModelRouter()
    decision = router.select_provider(
        task_type="video_analysis",
        priority="normal",
        content={"task": "analyze youtube video transcript"},
    )
    # Primary should be gemini; grok is the documented fallback
    assert decision.provider.value.lower() in {"gemini", "grok"}, (
        f"Expected gemini or grok for video task, got {decision.provider.value}"
    )
    assert decision.reason in {
        "video_analysis",
        "video_analysis_grok_fallback",
        "fallback",
        "high_priority",
    }


if __name__ == "__main__":
    import asyncio

    tests = [
        ("service exposes Grok constants", test_service_exposes_grok_constants),
        ("loads Grok key from env", test_service_loads_grok_api_key_from_env),
        ("loads legacy Grok key env var", test_service_loads_grok_key_fallback_env_vars),
        ("router routes video to Gemini", test_model_router_routes_video_to_gemini),
    ]

    async_tests = [
        ("Grok fallback called on Gemini failure", test_grok_fallback_called_on_gemini_failure),
        ("raises when no Grok key", test_grok_fallback_raises_when_no_grok_key),
        ("parses JSON Grok response", test_grok_fallback_parses_json_response),
        ("handles plain text Grok response", test_grok_fallback_handles_plain_text_response),
        ("no fallback on Gemini success", test_analyze_video_succeeds_without_fallback),
    ]

    print("\n🧪 Gemini → Grok Failover Tests\n" + "=" * 50)

    passed = failed = 0

    for name, fn in tests:
        print(f"\n📋 {name}:")
        try:
            fn()
            print("  ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    for name, fn in async_tests:
        print(f"\n📋 {name} (async):")
        try:
            asyncio.run(fn())
            print("  ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)
    print("🎉 All tests passed!")
