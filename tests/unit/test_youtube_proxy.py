from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.libs import youtube_proxy as proxy_mod


def _make_proxy() -> proxy_mod.YouTubeAPIProxy:
    return proxy_mod.YouTubeAPIProxy("AIzaSy" + "x" * 33)


def test_get_proxy_url_valid(monkeypatch):
    proxy = _make_proxy()
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://user:pass@proxy.webshare.io:8080")

    assert proxy._get_proxy_url() == "http://user:pass@proxy.webshare.io:8080"


def test_get_proxy_url_invalid_falls_back(monkeypatch):
    proxy = _make_proxy()
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "proxy.webshare.io:8080")

    assert proxy._get_proxy_url() is None


def test_redact_proxy_url_and_error():
    proxy = _make_proxy()
    proxy_url = "http://user:secret@proxy.webshare.io:8080"

    assert proxy._redact_proxy_url(proxy_url) == "http://proxy.webshare.io:8080"
    assert "secret" not in proxy._redact_error(Exception(f"boom {proxy_url}"), proxy_url)
    assert "proxy.webshare.io:8080" in proxy._redact_error(Exception(f"boom {proxy_url}"), proxy_url)


@pytest.mark.asyncio
async def test_get_transcript_passes_proxy_to_transcript_api_and_ytdlp(monkeypatch):
    proxy = _make_proxy()
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://user:pass@proxy.webshare.io:8080")

    transcript_api = MagicMock()
    transcript_api.get_transcript.side_effect = Exception("direct failed")
    transcript_api.list_transcripts.side_effect = Exception("list failed")
    monkeypatch.setattr(proxy_mod, "YouTubeTranscriptApi", transcript_api, raising=False)

    captured_opts: dict[str, object] = {}

    class FakeYDL:
        def __init__(self, opts):
            captured_opts.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return {"subtitles": {"en": [{"url": "https://example.com/sub.vtt"}]}, "automatic_captions": {}}

    monkeypatch.setattr(proxy_mod, "yt_dlp", MagicMock(YoutubeDL=FakeYDL), raising=False)

    result = await proxy.get_transcript("aircAruvnKk")

    assert result[0]["text"] == "Transcript extracted via yt-dlp"
    assert transcript_api.get_transcript.call_args.kwargs["proxies"] == {
        "http": "http://user:pass@proxy.webshare.io:8080",
        "https": "http://user:pass@proxy.webshare.io:8080",
    }
    assert transcript_api.list_transcripts.call_args.kwargs["proxies"] == {
        "http": "http://user:pass@proxy.webshare.io:8080",
        "https": "http://user:pass@proxy.webshare.io:8080",
    }
    assert captured_opts["proxy"] == "http://user:pass@proxy.webshare.io:8080"


@pytest.mark.asyncio
async def test_health_check_uses_public_video_lookup(monkeypatch):
    proxy = _make_proxy()

    execute = MagicMock(return_value={"items": [{"id": "aircAruvnKk"}]})
    request = MagicMock(execute=execute)
    videos = MagicMock(list=MagicMock(return_value=request))
    youtube = MagicMock(videos=MagicMock(return_value=videos))
    build = MagicMock(return_value=youtube)
    monkeypatch.setattr(proxy_mod, "build", build, raising=False)

    result = await proxy.health_check()

    assert result["status"] == "healthy"
    videos.list.assert_called_once_with(part="id", id="aircAruvnKk")
