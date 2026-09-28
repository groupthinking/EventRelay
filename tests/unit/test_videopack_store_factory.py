"""Unit tests for videopack store selection and Upstash REST adapter."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if "youtube_extension.videopack" not in sys.modules:
    _stub = types.ModuleType("youtube_extension.videopack")
    _stub.__path__ = [str(_SRC / "youtube_extension/videopack")]
    _stub.__package__ = "youtube_extension.videopack"
    sys.modules["youtube_extension.videopack"] = _stub

from youtube_extension.videopack.credentials import (  # noqa: E402
    UpstashRestCredentials,
    resolve_upstash_redis_credentials,
)
from youtube_extension.videopack.identity import identity_hash  # noqa: E402
from youtube_extension.videopack.store_factory import get_video_pack_store  # noqa: E402
from youtube_extension.videopack.upstash_rest_store import (  # noqa: E402
    UpstashRestVideoPackStore,
    pack_store_key,
)


def test_pack_store_key_matches_web_prefix():
    video_id = "auJzb1D-fag"
    expected_hash = identity_hash(video_id)
    assert pack_store_key(expected_hash) == f"er:videopack:v0:{expected_hash}"


def test_resolve_credentials_accepts_kv_names(monkeypatch):
    monkeypatch.setenv("KV_REST_API_URL", "https://example.upstash.io")
    monkeypatch.setenv("KV_REST_API_TOKEN", "token")
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    creds = resolve_upstash_redis_credentials()
    assert creds is not None
    assert creds.url == "https://example.upstash.io"
    assert creds.token == "token"


def test_factory_requires_upstash_or_explicit_filesystem(monkeypatch, tmp_path):
    for key in (
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "KV_REST_API_URL",
        "KV_REST_API_TOKEN",
        "VIDEO_PACK_FILESYSTEM_STORE",
        "ENVIRONMENT",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="VIDEO_PACK_FILESYSTEM_STORE"):
        get_video_pack_store(filesystem_root=tmp_path)


def test_factory_uses_filesystem_when_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PACK_FILESYSTEM_STORE", "1")
    store = get_video_pack_store(filesystem_root=tmp_path)
    assert store.__class__.__name__ == "VideoPackStore"


def test_upstash_put_uses_pipeline(monkeypatch):
    calls: list[tuple[str, ...]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return [{"result": "OK"}]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, content=None):
            raw = content.decode() if isinstance(content, bytes) else str(content)
            payload = json.loads(raw)
            calls.append(tuple(payload))
            return FakeResponse()

    import youtube_extension.videopack.upstash_rest_store as upstash_mod

    monkeypatch.setattr(upstash_mod.httpx, "Client", FakeClient)
    from youtube_extension.videopack.schema import (  # noqa: E402
        Provenance,
        Transcript,
        VideoPackV0,
    )

    from datetime import datetime, timezone

    pack = VideoPackV0(
        id="vp:v0:auJzb1D-fag",
        video_id="auJzb1D-fag",
        source_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        transcript=Transcript(full_text="cite", segments=[]),
        provenance=Provenance(
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tool_versions={"videopack": "v0"},
            source_hash=identity_hash("auJzb1D-fag"),
            notes="test",
        ),
    )
    store = UpstashRestVideoPackStore(
        UpstashRestCredentials(url="https://example.upstash.io", token="t")
    )
    store.put(pack)
    assert calls[0][0] == "SET"
    assert calls[0][1] == pack_store_key(pack.provenance.source_hash)
