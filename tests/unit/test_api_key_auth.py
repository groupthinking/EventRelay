"""Tests for the deny-by-default API key authentication middleware."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from youtube_extension.backend.middleware.api_key_auth import APIKeyAuthMiddleware


def _make_client(monkeypatch, *, api_key=None, allow_unauth=None):
    monkeypatch.delenv("EVENTRELAY_API_KEY", raising=False)
    if allow_unauth is None:
        monkeypatch.delenv("ALLOW_UNAUTHENTICATED", raising=False)
    else:
        monkeypatch.setenv("ALLOW_UNAUTHENTICATED", allow_unauth)

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware, api_key=api_key)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/v1/videos/{vid}")
    def get_video(vid: str):
        return {"vid": vid}

    @app.post("/api/v1/agents/dispatch")
    def dispatch():
        return {"dispatched": True}

    return TestClient(app)


def test_public_route_open_when_key_set(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.get("/health").status_code == 200


def test_protected_get_requires_key(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.get("/api/v1/videos/abc").status_code == 401
    assert c.get("/api/v1/videos/abc", headers={"X-API-Key": "wrong"}).status_code == 401
    assert c.get("/api/v1/videos/abc", headers={"X-API-Key": "secret"}).status_code == 200


def test_protected_post_requires_key(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.post("/api/v1/agents/dispatch").status_code == 401
    assert (
        c.post("/api/v1/agents/dispatch", headers={"X-API-Key": "secret"}).status_code
        == 200
    )


def test_fails_closed_when_key_unset(monkeypatch):
    c = _make_client(monkeypatch, api_key=None)  # ALLOW_UNAUTHENTICATED also unset
    assert c.get("/health").status_code == 200  # public route still open
    assert c.get("/api/v1/videos/abc").status_code == 503  # protected fails closed
    assert c.post("/api/v1/agents/dispatch").status_code == 503


def test_dev_optin_opens_everything(monkeypatch):
    c = _make_client(monkeypatch, api_key=None, allow_unauth="1")
    assert c.get("/api/v1/videos/abc").status_code == 200
    assert c.post("/api/v1/agents/dispatch").status_code == 200


def test_options_preflight_not_blocked_by_auth(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    r = c.options("/api/v1/videos/abc")
    assert r.status_code not in (401, 503)
