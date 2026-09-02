"""Hash-stability tests for Video Pack identity (UVAI step 2).

The identity hash is the immutable cite key: same YouTube video ID must
always produce the same SHA-256; a different video ID must not.
Content extract (Qwen) is out of scope — this locks the identity contract.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types as _types
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

if "youtube_extension.videopack" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.videopack")
    _stub.__path__ = [str(_SRC / "youtube_extension/videopack")]
    _stub.__package__ = "youtube_extension.videopack"
    sys.modules["youtube_extension.videopack"] = _stub

sys.modules.pop("youtube_extension.videopack.identity", None)
sys.modules.pop("youtube_extension.videopack.provenance", None)

from youtube_extension.videopack.identity import (  # noqa: E402
    IDENTITY_VERSION,
    build_identity_pack,
    identity_hash,
    identity_payload,
    resolve_video_id,
)

CANON_A = "auJzb1D-fag"
CANON_B = "jNQXAC9IVRw"

# Compact canonical JSON, keys sorted: version < video_id
GOLDEN_A = "2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea"
GOLDEN_B = "97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d"


class TestIdentityPayload:
    def test_payload_is_version_and_video_id_only(self):
        payload = identity_payload(CANON_A)
        assert payload == {"version": IDENTITY_VERSION, "video_id": CANON_A}

    def test_canonical_json_matches_compact_sorted_form(self):
        encoded = json.dumps(identity_payload(CANON_A), sort_keys=True, separators=(",", ":"))
        assert encoded == '{"version":"v0","video_id":"auJzb1D-fag"}'


class TestIdentityHashStability:
    def test_same_video_id_same_hash(self):
        assert identity_hash(CANON_A) == identity_hash(CANON_A)

    def test_same_video_id_matches_golden(self):
        assert identity_hash(CANON_A) == GOLDEN_A

    def test_different_video_id_different_hash(self):
        assert identity_hash(CANON_A) != identity_hash(CANON_B)
        assert identity_hash(CANON_B) == GOLDEN_B

    def test_hash_is_sha256_hex(self):
        digest = identity_hash(CANON_A)
        assert len(digest) == 64
        assert digest == hashlib.sha256(
            b'{"version":"v0","video_id":"auJzb1D-fag"}'
        ).hexdigest()

    def test_url_variants_collapse_to_same_video_id(self):
        watch = "https://www.youtube.com/watch?v=auJzb1D-fag"
        short = "https://youtu.be/auJzb1D-fag?si=abc"
        shorts = "https://www.youtube.com/shorts/auJzb1D-fag"
        assert resolve_video_id(watch) == CANON_A
        assert resolve_video_id(short) == CANON_A
        assert resolve_video_id(shorts) == CANON_A
        assert identity_hash(resolve_video_id(watch)) == identity_hash(resolve_video_id(short))


class TestBuildIdentityPack:
    def test_pack_is_v0_with_source_hash(self):
        pack = build_identity_pack(CANON_A)
        assert pack.version.value == "v0"
        assert pack.video_id == CANON_A
        assert pack.id == f"vp:v0:{CANON_A}"
        assert pack.provenance.source_hash == GOLDEN_A

    def test_different_video_ids_get_different_pack_hashes(self):
        a = build_identity_pack(CANON_A)
        b = build_identity_pack(CANON_B)
        assert a.provenance.source_hash != b.provenance.source_hash

    def test_transcript_is_a_cite_not_extracted_speech(self):
        pack = build_identity_pack(CANON_A)
        assert pack.transcript.full_text == f"cite:youtube:{CANON_A}"
        assert pack.transcript.segments == []

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            resolve_video_id("https://example.com/watch")
