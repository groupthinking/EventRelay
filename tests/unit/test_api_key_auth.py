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

    @app.get("/readyz")
    def readiness():
        return {"ready": True}

    @app.get("/readyz/details")
    def readiness_details():
        return {"private": True}

    @app.get("/api/v1/videos/{vid}")
    def get_video(vid: str):
        return {"vid": vid}

    @app.post("/api/v1/agents/dispatch")
    def dispatch():
        return {"dispatched": True}

    @app.post("/api/v1/video/pack")
    def video_pack():
        return {"ok": True}

    return TestClient(app)


def test_public_route_open_when_key_set(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.get("/health").status_code == 200


def test_only_exact_readiness_route_is_public(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.get("/readyz").status_code == 200
    assert c.get("/readyz/details").status_code == 401


def test_protected_get_requires_key(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    assert c.get("/api/v1/videos/abc").status_code == 401
    assert (
        c.get("/api/v1/videos/abc", headers={"X-API-Key": "wrong"}).status_code == 401
    )
    assert (
        c.get("/api/v1/videos/abc", headers={"X-API-Key": "secret"}).status_code == 200
    )


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


def test_video_pack_identity_emit_does_not_require_api_key(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    r = c.post(
        "/api/v1/video/pack",
        json={"url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    # Sibling video routes stay deny-by-default.
    assert c.get("/api/v1/videos/abc").status_code == 401


def test_options_preflight_not_blocked_by_auth(monkeypatch):
    c = _make_client(monkeypatch, api_key="secret")
    r = c.options("/api/v1/videos/abc")
    assert r.status_code not in (401, 503)


def test_non_ascii_key_returns_401_not_500(monkeypatch):
    # Raw non-ASCII header bytes (latin-1, as Starlette decodes them) make
    # hmac.compare_digest raise ValueError; the middleware must treat it as
    # unauthorized (401), never surface a 500.
    c = _make_client(monkeypatch, api_key="secret")
    r = c.get("/api/v1/videos/abc", headers={"X-API-Key": b"caf\xe9"})
    assert r.status_code == 401
