"""Unit tests for videopack/io.py read/write functions."""

from __future__ import annotations

import json
import sys
import types as _types
from datetime import datetime
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

if "youtube_extension.videopack" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.videopack")
    _stub.__path__ = [str(_SRC / "youtube_extension/videopack")]
    _stub.__package__ = "youtube_extension.videopack"
    sys.modules["youtube_extension.videopack"] = _stub

sys.modules.pop("youtube_extension.videopack.schema", None)
sys.modules.pop("youtube_extension.videopack.io", None)

from youtube_extension.videopack.io import load_json, read_pack, save_json, write_pack
from youtube_extension.videopack.schema import Metrics, Provenance, Transcript, VideoPackV0


def _pack(video_id="auJzb1D-fag") -> VideoPackV0:
    return VideoPackV0(
        video_id=video_id,
        transcript=Transcript(full_text="hello"),
        provenance=Provenance(created_at=datetime.utcnow()),
    )


# ===========================================================================
# load_json / save_json
# ===========================================================================


class TestLoadJson:
    def test_loads_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        result = load_json(f)
        assert result == {"key": "value"}

    def test_loads_list(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text('[1, 2, 3]', encoding="utf-8")
        result = load_json(f)
        assert result == [1, 2, 3]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_json(tmp_path / "nonexistent.json")


class TestSaveJson:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(path, {"x": 1})
        assert path.exists()

    def test_content_correct(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(path, {"hello": "world"})
        data = json.loads(path.read_text())
        assert data["hello"] == "world"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "a" / "b" / "c" / "out.json"
        save_json(path, {})
        assert path.exists()


# ===========================================================================
# write_pack / read_pack
# ===========================================================================


class TestWritePackReadPack:
    def test_write_creates_file(self, tmp_path):
        p = _pack()
        path = tmp_path / "pack.json"
        write_pack(path, p)
        assert path.exists()

    def test_read_returns_video_pack(self, tmp_path):
        p = _pack()
        path = tmp_path / "pack.json"
        write_pack(path, p)
        loaded = read_pack(path)
        assert isinstance(loaded, VideoPackV0)

    def test_roundtrip_preserves_video_id(self, tmp_path):
        p = _pack(video_id="auJzb1D-fag")
        path = tmp_path / "pack.json"
        write_pack(path, p)
        loaded = read_pack(path)
        assert loaded.video_id == "auJzb1D-fag"

    def test_roundtrip_preserves_transcript(self, tmp_path):
        p = _pack()
        path = tmp_path / "pack.json"
        write_pack(path, p)
        loaded = read_pack(path)
        assert loaded.transcript.full_text == "hello"
