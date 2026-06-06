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
from service.app.pipeline.transcript import TranscriptUnavailable, YouTubeCaptionsProvider


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

def test_captions_provider_uses_stt_fallback() -> None:
    class FakeStt:
        async def transcribe(self, video_id: str, language: str | None) -> str:
            return "stt transcript"

    # youtube-transcript-api is not installed here, so the captions path raises
    # ImportError and the STT fallback should take over.
    provider = YouTubeCaptionsProvider(stt=FakeStt())
    assert asyncio.run(provider.fetch("vid")) == "stt transcript"


def test_captions_provider_without_fallback_raises() -> None:
    provider = YouTubeCaptionsProvider()
    with pytest.raises(TranscriptUnavailable):
        asyncio.run(provider.fetch("vid"))
