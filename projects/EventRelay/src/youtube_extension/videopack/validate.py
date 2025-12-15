from __future__ import annotations
from .schema import VideoPackV0

def validate_pack(pack: VideoPackV0) -> None:
    # Invariants reflecting docs/VIDEO_PACK_V0_SPEC.md
    assert pack.version == pack.version.v0, "Only v0 supported here"
    assert pack.transcript.full_text.strip(), "full_text is required"
    # Example: ensure segments are ordered and non-overlapping
    last_end = 0.0
    for seg in pack.transcript.segments:
        assert seg.start_s <= seg.end_s, "segment start<=end"
        assert seg.start_s >= last_end - 1e-6, "segments must be non-overlapping"
        last_end = seg.end_s
