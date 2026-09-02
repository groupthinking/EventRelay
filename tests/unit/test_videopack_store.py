"""Get-or-create persistence for Video Pack identity (UVAI step 2)."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

if "youtube_extension.videopack" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.videopack")
    _stub.__path__ = [str(_SRC / "youtube_extension/videopack")]
    _stub.__package__ = "youtube_extension.videopack"
    sys.modules["youtube_extension.videopack"] = _stub

sys.modules.pop("youtube_extension.videopack.identity", None)
sys.modules.pop("youtube_extension.videopack.store", None)
sys.modules.pop("youtube_extension.videopack.io", None)
sys.modules.pop("youtube_extension.videopack.schema", None)

from youtube_extension.videopack.identity import emit_video_pack, identity_hash
from youtube_extension.videopack.store import VideoPackStore

CANON_A = "auJzb1D-fag"
CANON_B = "jNQXAC9IVRw"
URL_A = "https://www.youtube.com/watch?v=auJzb1D-fag"
URL_A_SHORT = "https://youtu.be/auJzb1D-fag?si=retry"
URL_B = "https://youtu.be/jNQXAC9IVRw"


class TestVideoPackStoreReuse:
    def test_second_emit_reuses_stored_pack(self, tmp_path):
        store = VideoPackStore(tmp_path)
        first = emit_video_pack(video_url=URL_A, store=store)
        second = emit_video_pack(video_url=URL_A_SHORT, store=store)

        assert first.id == second.id == f"vp:v0:{CANON_A}"
        assert first.provenance.source_hash == second.provenance.source_hash
        assert first.provenance.source_hash == identity_hash(CANON_A)
        assert first.provenance.created_at == second.provenance.created_at
        assert (tmp_path / CANON_A / "pack.json").is_file()

    def test_different_video_ids_are_distinct_files(self, tmp_path):
        store = VideoPackStore(tmp_path)
        a = emit_video_pack(video_url=URL_A, store=store)
        b = emit_video_pack(video_url=URL_B, store=store)

        assert a.video_id == CANON_A
        assert b.video_id == CANON_B
        assert a.provenance.source_hash != b.provenance.source_hash
        assert (tmp_path / CANON_A / "pack.json").is_file()
        assert (tmp_path / CANON_B / "pack.json").is_file()

    def test_video_id_argument_without_url(self, tmp_path):
        store = VideoPackStore(tmp_path)
        pack = emit_video_pack(video_id=CANON_A, store=store)
        assert pack.video_id == CANON_A
        assert pack.provenance.source_hash == identity_hash(CANON_A)
