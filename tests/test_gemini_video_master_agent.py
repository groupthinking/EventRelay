import os
import json
import ssl
from types import SimpleNamespace

import pytest

from agents import gemini_video_master_agent as master


<<<<<<< HEAD
=======
@pytest.fixture(autouse=True)
def _isolate_gemini_sdk_client(monkeypatch):
    """Keep unit tests from constructing the SDK's real HTTP transport."""
    if master.GEMINI_AVAILABLE:
        monkeypatch.setattr(
            master.genai,
            "Client",
            lambda **_: SimpleNamespace(),
        )


>>>>>>> origin/main
def test_task_delegation_uses_current_gemini_models(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    agent = master.GeminiVideoMasterAgent()

    delegated_models = {provider.value for provider in agent.task_delegation.values()}
    assert not any("gemini-2.0" in model for model in delegated_models)
    assert master.AIProvider.GEMINI_FLASH.value in delegated_models


@pytest.mark.asyncio
async def test_gemini_empty_response_raises_clear_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    agent = master.GeminiVideoMasterAgent()
    agent.gemini_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **_: SimpleNamespace(text="")
        )
    )

    with pytest.raises(ValueError, match="empty response"):
        await agent._execute_with_gemini(
            "Summarize this video",
            master.AIProvider.GEMINI_FLASH,
            "https://www.youtube.com/watch?v=QKHL_gmlteQ",
        )


@pytest.mark.asyncio
async def test_text_provider_fallback_preserves_video_url(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    agent = master.GeminiVideoMasterAgent()
    seen = {}

    async def fake_gemini(prompt, provider, video_url):
        seen["prompt"] = prompt
        seen["provider"] = provider
        seen["video_url"] = video_url
        return "fallback content"

    monkeypatch.setattr(agent, "_execute_with_gemini", fake_gemini)

    result = await agent._execute_with_claude(
        "Analyze the video",
        "https://www.youtube.com/watch?v=snF5eGKoiJI",
    )

    assert result == "fallback content"
    assert seen["provider"] == master.AIProvider.GEMINI_FLASH
    assert seen["video_url"] == "https://www.youtube.com/watch?v=snF5eGKoiJI"


def test_agent_uses_certificate_validating_ssl_context(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    agent = master.GeminiVideoMasterAgent()

    assert isinstance(agent.ssl_context, ssl.SSLContext)
    assert agent.ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert agent.ssl_context.check_hostname is True


def test_default_input_does_not_surface_banned_video_id():
    prompt = master.build_default_video_prompt()

    assert master.extract_video_id(master.DEFAULT_VIDEO_URL) not in master.BANNED_VIDEO_IDS
    assert "auJzb1D-fag" not in master.DEFAULT_VIDEO_URL
    assert "auJzb1D-fag" not in prompt


def test_normalize_youtube_url_removes_timestamp_params():
    assert (
        master.normalize_youtube_url(
            "https://www.youtube.com/watch?v=snF5eGKoiJI&t=8s"
        )
        == "https://www.youtube.com/watch?v=snF5eGKoiJI"
    )
    assert (
        master.normalize_youtube_url("https://youtu.be/jSWuepkuFrU?t=2696")
        == "https://www.youtube.com/watch?v=jSWuepkuFrU"
    )


@pytest.mark.asyncio
async def test_gemini_tasks_are_batched_into_one_video_request(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    agent = master.GeminiVideoMasterAgent()
    calls = []

    async def fake_gemini(prompt, provider, video_url, **kwargs):
        calls.append((prompt, provider, video_url, kwargs))
        return json.dumps(
            {
                "transcription": "Transcript with timestamps.",
                "summarization": "Three sentence summary.",
            }
        )

    monkeypatch.setattr(agent, "_execute_with_gemini", fake_gemini)

    results = await agent._execute_tasks_with_delegation(
        [
            (master.TaskType.TRANSCRIPTION, "Transcribe"),
            (master.TaskType.SUMMARIZATION, "Summarize"),
        ],
        "https://www.youtube.com/watch?v=QKHL_gmlteQ",
    )

    assert len(calls) == 1
    assert calls[0][1] == master.AIProvider.GEMINI_FLASH
    assert calls[0][3]["response_mime_type"] == "application/json"
    assert {result.task_type for result in results} == {
        master.TaskType.TRANSCRIPTION,
        master.TaskType.SUMMARIZATION,
    }


@pytest.mark.asyncio
async def test_gemini_batch_falls_back_to_text_context_on_video_access_error(
    monkeypatch,
):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    agent = master.GeminiVideoMasterAgent()

    async def fake_video_gemini(*args, **kwargs):
        raise RuntimeError("403 PERMISSION_DENIED. The caller does not have permission")

    async def fake_context(video_url):
        return "Transcript: [0.0s] This is a technical product walkthrough."

    async def fake_text_gemini(prompt, provider, **kwargs):
        return json.dumps({"summarization": "Fallback summary from transcript."})

    monkeypatch.setattr(agent, "_execute_with_gemini", fake_video_gemini)
    monkeypatch.setattr(agent, "_build_youtube_text_context", fake_context)
    monkeypatch.setattr(agent, "_execute_with_gemini_text", fake_text_gemini)

    results = await agent._execute_gemini_task_batch(
        [(master.TaskType.SUMMARIZATION, "Summarize")],
        "https://www.youtube.com/watch?v=snF5eGKoiJI",
        master.AIProvider.GEMINI_FLASH,
    )

    assert len(results) == 1
    assert results[0].benchmark.success is True
    assert results[0].content == "Fallback summary from transcript."
    assert results[0].metadata["source"] == "youtube_text_fallback"


@pytest.mark.asyncio
async def test_malformed_gemini_batch_json_is_repaired(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    agent = master.GeminiVideoMasterAgent()

    async def fake_text_gemini(prompt, provider, **kwargs):
        return json.dumps({"summarization": "Repaired compact summary."})

    monkeypatch.setattr(agent, "_execute_with_gemini_text", fake_text_gemini)

    parsed = await agent._parse_or_repair_gemini_batch_response(
        '{"summarization": "unterminated',
        [(master.TaskType.SUMMARIZATION, "Summarize")],
        master.AIProvider.GEMINI_FLASH,
    )

    assert parsed == {"summarization": "Repaired compact summary."}
