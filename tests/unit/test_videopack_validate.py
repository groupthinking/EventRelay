"""Unit tests for videopack/validate.py."""

from __future__ import annotations

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
sys.modules.pop("youtube_extension.videopack.validate", None)

from youtube_extension.videopack.schema import (
    Provenance,
    Transcript,
    TranscriptSegment,
    VideoPackV0,
)
from youtube_extension.videopack.validate import validate_pack


def _make_pack(**kwargs):
    defaults = dict(
        video_id="auJzb1D-fag",
        transcript=Transcript(full_text="hello world"),
        provenance=Provenance(created_at=datetime.utcnow()),
    )
    defaults.update(kwargs)
    return VideoPackV0(**defaults)


class TestValidatePack:
    def test_valid_pack_no_exception(self):
        p = _make_pack()
        validate_pack(p)  # Should not raise

    def test_full_text_required_raises(self):
        p = _make_pack()
        # Manually set full_text to empty to bypass Pydantic
        object.__setattr__(p.transcript, "full_text", "   ")
        with pytest.raises(AssertionError):
            validate_pack(p)

    def test_ordered_segments_no_exception(self):
        segs = [
            TranscriptSegment(idx=0, start_s=0.0, end_s=5.0, text="a"),
            TranscriptSegment(idx=1, start_s=5.0, end_s=10.0, text="b"),
        ]
        p = _make_pack(transcript=Transcript(full_text="ab", segments=segs))
        validate_pack(p)

    def test_overlapping_segments_raises(self):
        segs = [
            TranscriptSegment(idx=0, start_s=0.0, end_s=10.0, text="a"),
            TranscriptSegment(idx=1, start_s=5.0, end_s=15.0, text="b"),
        ]
        p = _make_pack(transcript=Transcript(full_text="ab", segments=segs))
        with pytest.raises(AssertionError):
            validate_pack(p)

    def test_start_after_end_raises(self):
        segs = [
            TranscriptSegment(idx=0, start_s=10.0, end_s=5.0, text="a"),
        ]
        p = _make_pack(transcript=Transcript(full_text="a", segments=segs))
        with pytest.raises(AssertionError):
            validate_pack(p)

    def test_empty_segments_no_exception(self):
        p = _make_pack(transcript=Transcript(full_text="hello", segments=[]))
        validate_pack(p)
