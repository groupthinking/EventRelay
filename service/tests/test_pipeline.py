"""Unit tests for the pipeline stages in isolation (no HTTP layer).

pytest-asyncio is not assumed available, so async stages are driven with
asyncio.run.
"""
from __future__ import annotations

import asyncio

import pytest

from service.app.domain.events import Event
from service.app.llm.fake import FakeLLMClient
from service.app.pipeline.artifacts import derive_artifacts
from service.app.pipeline.extract import extract_events
from service.app.pipeline.transcript import (
    TranscriptUnavailable,
    YouTubeCaptionsProvider,
)

# --- SC3 ---

def test_extract_events_validates_taxonomy() -> None:
    llm = FakeLLMClient([{"events": [{"type": "youtube.video.captured", "payload": {"a": 1}}]}])
    events = asyncio.run(extract_events("t", llm))
    assert events[0].type == "youtube.video.captured"
    assert events[0].payload == {"a": 1}


def test_extract_events_rejects_bad_name() -> None:
    llm = FakeLLMClient([{"events": [{"type": "bad name"}]}])
    with pytest.raises(ValueError):
        asyncio.run(extract_events("t", llm))


# --- SC4 ---

def test_derive_artifacts_shapes_output() -> None:
    llm = FakeLLMClient([{"summary": "s", "tasks": ["x", "y"], "insights": {"k": "v"}}])
    artifacts = asyncio.run(derive_artifacts("t", [Event(type="a.b.c")], llm))
    assert artifacts.summary == "s"
    assert artifacts.tasks == ["x", "y"]
    assert artifacts.insights == {"k": "v"}


def test_derive_artifacts_requires_summary() -> None:
    llm = FakeLLMClient([{"tasks": []}])  # missing required 'summary'
    with pytest.raises(KeyError):
        asyncio.run(derive_artifacts("t", [], llm))


# --- SC2 fallback ---

def test_captions_provider_uses_stt_on_any_fetch_failure() -> None:
    class FakeStt:
        async def transcribe(self, video_id: str, language: str | None) -> str:
            return "stt transcript"

    # YouTubeCaptionsProvider catches any Exception during caption fetching and
    # falls back to STT. In this test environment, youtube-transcript-api may
    # raise ImportError or any other exception, and the provider should use STT.
    provider = YouTubeCaptionsProvider(stt=FakeStt())
    assert asyncio.run(provider.fetch("vid")) == "stt transcript"


def test_captions_provider_raises_when_no_fallback_configured() -> None:
    # Without an STT fallback, any caption fetch failure raises TranscriptUnavailable.
    provider = YouTubeCaptionsProvider()
    with pytest.raises(TranscriptUnavailable):
        asyncio.run(provider.fetch("vid"))
