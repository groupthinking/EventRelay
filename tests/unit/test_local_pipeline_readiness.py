"""F6/F7 readiness helpers on the FastAPI /health surface."""

from __future__ import annotations

from youtube_extension import main as app_main


def test_auth_mode_fail_closed_by_default(monkeypatch):
    monkeypatch.delenv("EVENTRELAY_API_KEY", raising=False)
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED", raising=False)
    assert app_main._auth_mode() == "fail_closed"


def test_auth_mode_open_dev_when_allow_unauthenticated(monkeypatch):
    monkeypatch.delenv("EVENTRELAY_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "1")
    assert app_main._auth_mode() == "open_dev"


def test_auth_mode_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("EVENTRELAY_API_KEY", "test-secret")
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED", raising=False)
    assert app_main._auth_mode() == "api_key"


def test_auth_mode_api_key_when_whitespace_only(monkeypatch):
    # APIKeyAuthMiddleware treats a whitespace-only value as a configured key
    # (it requires that key on protected routes); the diagnostic must agree
    # rather than reporting fail_closed.
    monkeypatch.setenv("EVENTRELAY_API_KEY", "   ")
    monkeypatch.delenv("ALLOW_UNAUTHENTICATED", raising=False)
    assert app_main._auth_mode() == "api_key"


def test_video_dep_status_keys(monkeypatch):
    status = app_main._video_dep_status()
    assert set(status) == {"yt_dlp", "youtube_transcript_api"}
    assert all(isinstance(v, bool) for v in status.values())


async def test_health_check_contract_when_video_ready(monkeypatch):
    monkeypatch.setattr(
        app_main,
        "_video_dep_status",
        lambda: {"yt_dlp": True, "youtube_transcript_api": True},
    )
    monkeypatch.delenv("EVENTRELAY_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "1")

    payload = await app_main.health_check()

    assert set(payload) == {
        "status",
        "service",
        "auth_mode",
        "video_deps",
        "video_path_ready",
    }
    assert payload["status"] == "healthy"
    assert payload["service"] == "uvai-youtube-extension"
    assert payload["auth_mode"] == "open_dev"
    assert payload["video_deps"] == {"yt_dlp": True, "youtube_transcript_api": True}
    assert payload["video_path_ready"] is True


async def test_health_check_contract_when_video_not_ready(monkeypatch):
    monkeypatch.setattr(
        app_main,
        "_video_dep_status",
        lambda: {"yt_dlp": True, "youtube_transcript_api": False},
    )

    payload = await app_main.health_check()

    # A single missing dependency must flip the aggregate to not-ready.
    assert payload["video_deps"] == {"yt_dlp": True, "youtube_transcript_api": False}
    assert payload["video_path_ready"] is False
