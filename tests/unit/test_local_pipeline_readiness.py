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


def test_video_dep_status_keys(monkeypatch):
    status = app_main._video_dep_status()
    assert set(status) == {"yt_dlp", "youtube_transcript_api"}
    assert all(isinstance(v, bool) for v in status.values())
