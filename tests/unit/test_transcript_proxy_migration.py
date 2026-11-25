from __future__ import annotations

from types import SimpleNamespace

import pytest

from youtube_extension.utils.proxy import get_proxy_url


def test_malformed_proxy_port_falls_back_to_direct_connection(monkeypatch):
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://proxy.example:invalid")

    assert get_proxy_url() is None


@pytest.mark.asyncio
async def test_integration_transcript_client_uses_v1_proxy_config(monkeypatch):
    import integration.youtube_api as youtube_api

    captured: dict[str, object] = {}

    class FakeTranscript:
        def fetch(self, video_id: str, languages: list[str]):
            assert video_id == "auJzb1D-fag"
            assert languages == ["en"]
            return SimpleNamespace(
                to_raw_data=lambda: [
                    {"text": "hello", "start": 0.0, "duration": 1.0}
                ]
            )

    def fake_api(**kwargs):
        captured.update(kwargs)
        return FakeTranscript()

    proxy_config = object()
    monkeypatch.setattr(youtube_api, "YouTubeTranscriptApi", fake_api)
    monkeypatch.setattr(
        youtube_api, "get_transcript_proxy_config", lambda: proxy_config
    )

    service = youtube_api.YouTubeAPIService(api_key="test")
    try:
        result = await service.get_transcript("auJzb1D-fag")
    finally:
        await service.close()

    assert captured == {"proxy_config": proxy_config}
    assert result[0].text == "hello"


def test_process_video_yt_dlp_options_include_central_proxy(monkeypatch):
    import agents.process_video_with_mcp as processor

    captured: dict[str, object] = {}

    class FailingTranscriptApi:
        def __init__(self, **_kwargs):
            pass

        def fetch(self, *_args, **_kwargs):
            raise RuntimeError("transcript unavailable")

        def list(self, *_args, **_kwargs):
            raise RuntimeError("transcript unavailable")

    class FakeYoutubeDL:
        def __init__(self, options):
            captured.update(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, *_args, **_kwargs):
            return {"title": "video"}

    monkeypatch.setattr(
        processor,
        "get_proxy_url",
        lambda: "******proxy.example:8080",
    )
    monkeypatch.setattr(processor, "YouTubeTranscriptApi", FailingTranscriptApi)
    monkeypatch.setattr(
        processor.yt_dlp, "YoutubeDL", FakeYoutubeDL, raising=False
    )

    import asyncio

    asyncio.run(
        processor.RealVideoProcessor()._extract_transcript_with_rotation(
            "auJzb1D-fag"
        )
    )

    assert captured["proxy"] == "******proxy.example:8080"
