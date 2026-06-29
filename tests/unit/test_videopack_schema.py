"""Unit tests for videopack/schema.py Pydantic models."""

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

from youtube_extension.videopack.schema import (
    ArtifactRef,
    CodeSnippet,
    Keyframe,
    Metrics,
    Provenance,
    Requirement,
    Transcript,
    TranscriptSegment,
    VPVersion,
    VideoPackV0,
    VisualContext,
    VisualElement,
)


# ===========================================================================
# VPVersion enum
# ===========================================================================


class TestVPVersion:
    def test_v0_value(self):
        assert VPVersion.v0.value == "v0"

    def test_is_str_enum(self):
        assert isinstance(VPVersion.v0, str)


# ===========================================================================
# TranscriptSegment
# ===========================================================================


class TestTranscriptSegment:
    def test_required_fields(self):
        s = TranscriptSegment(idx=0, start_s=0.0, end_s=5.0, text="hello")
        assert s.idx == 0
        assert s.text == "hello"

    def test_start_s_must_be_nonnegative(self):
        with pytest.raises(Exception):
            TranscriptSegment(idx=0, start_s=-1.0, end_s=5.0, text="hi")


# ===========================================================================
# Transcript
# ===========================================================================


class TestTranscript:
    def test_full_text_required(self):
        t = Transcript(full_text="hello world")
        assert t.full_text == "hello world"

    def test_segments_default_empty(self):
        t = Transcript(full_text="hello")
        assert t.segments == []

    def test_language_default_none(self):
        t = Transcript(full_text="hello")
        assert t.language is None

    def test_explicit_language(self):
        t = Transcript(full_text="hello", language="en")
        assert t.language == "en"

    def test_explicit_segments(self):
        seg = TranscriptSegment(idx=0, start_s=0.0, end_s=5.0, text="hi")
        t = Transcript(full_text="hi", segments=[seg])
        assert len(t.segments) == 1


# ===========================================================================
# Keyframe
# ===========================================================================


class TestKeyframe:
    def test_t_s_required(self):
        kf = Keyframe(t_s=1.5, desc="some frame")
        assert kf.t_s == 1.5

    def test_image_path_default_none(self):
        kf = Keyframe(t_s=1.0, desc="x")
        assert kf.image_path is None

    def test_desc_default_none(self):
        kf = Keyframe(t_s=1.0, image_path="img.png")
        assert kf.desc is None

    def test_t_s_must_be_nonnegative(self):
        with pytest.raises(Exception):
            Keyframe(t_s=-1.0, desc="x")


# ===========================================================================
# Requirement
# ===========================================================================


class TestRequirement:
    def test_required_fields(self):
        r = Requirement(id="req-1", title="Do something")
        assert r.id == "req-1"
        assert r.title == "Do something"

    def test_detail_default_none(self):
        r = Requirement(id="r1", title="T")
        assert r.detail is None

    def test_priority_default(self):
        r = Requirement(id="r1", title="T")
        assert r.priority == "normal"

    def test_tags_default_empty(self):
        r = Requirement(id="r1", title="T")
        assert r.tags == []


# ===========================================================================
# CodeSnippet
# ===========================================================================


class TestCodeSnippet:
    def test_content_required(self):
        cs = CodeSnippet(content="print('hello')")
        assert cs.content == "print('hello')"

    def test_path_hint_default_none(self):
        cs = CodeSnippet(content="x = 1")
        assert cs.path_hint is None

    def test_lang_default_none(self):
        cs = CodeSnippet(content="x = 1")
        assert cs.lang is None


# ===========================================================================
# Metrics
# ===========================================================================


class TestMetrics:
    def test_all_defaults_none(self):
        m = Metrics()
        assert m.cost_usd is None
        assert m.latency_ms is None
        assert m.tokens_in is None
        assert m.tokens_out is None

    def test_explicit_values(self):
        m = Metrics(cost_usd=0.05, latency_ms=200, tokens_in=100, tokens_out=50)
        assert m.cost_usd == 0.05
        assert m.tokens_in == 100


# ===========================================================================
# Provenance
# ===========================================================================


class TestProvenance:
    def test_created_at_required(self):
        now = datetime.utcnow()
        p = Provenance(created_at=now)
        assert p.created_at == now

    def test_tool_versions_default_empty(self):
        p = Provenance(created_at=datetime.utcnow())
        assert p.tool_versions == {}

    def test_source_hash_default_none(self):
        p = Provenance(created_at=datetime.utcnow())
        assert p.source_hash is None

    def test_notes_default_none(self):
        p = Provenance(created_at=datetime.utcnow())
        assert p.notes is None


# ===========================================================================
# VisualElement
# ===========================================================================


class TestVisualElement:
    def test_required_fields(self):
        ve = VisualElement(timestamp=1.5, element_type="code", content="x=1")
        assert ve.timestamp == 1.5
        assert ve.element_type == "code"

    def test_confidence_default(self):
        ve = VisualElement(timestamp=0.0, element_type="text", content="hi")
        assert ve.confidence == 0.9

    def test_frame_path_default_none(self):
        ve = VisualElement(timestamp=0.0, element_type="text", content="hi")
        assert ve.frame_path is None

    def test_timestamp_must_be_nonnegative(self):
        with pytest.raises(Exception):
            VisualElement(timestamp=-1.0, element_type="code", content="x")


# ===========================================================================
# VisualContext
# ===========================================================================


class TestVisualContext:
    def test_defaults(self):
        vc = VisualContext()
        assert vc.visual_elements == []
        assert vc.summary is None
        assert vc.frame_analysis_count == 0
        assert vc.processing_timestamp is None


# ===========================================================================
# VideoPackV0
# ===========================================================================


def _make_pack(**kwargs):
    now = datetime.utcnow()
    defaults = dict(
        video_id="auJzb1D-fag",
        transcript=Transcript(full_text="hello world"),
        provenance=Provenance(created_at=now),
    )
    defaults.update(kwargs)
    return VideoPackV0(**defaults)


class TestVideoPackV0:
    def test_version_default(self):
        p = _make_pack()
        assert p.version == VPVersion.v0

    def test_id_auto_generated(self):
        p = _make_pack()
        assert len(p.id) == 36  # UUID format

    def test_video_id_stored(self):
        p = _make_pack()
        assert p.video_id == "auJzb1D-fag"

    def test_keyframes_default_empty(self):
        p = _make_pack()
        assert p.keyframes == []

    def test_concepts_default_empty(self):
        p = _make_pack()
        assert p.concepts == []

    def test_requirements_default_empty(self):
        p = _make_pack()
        assert p.requirements == []

    def test_code_snippets_default_empty(self):
        p = _make_pack()
        assert p.code_snippets == []

    def test_artifacts_default_empty(self):
        p = _make_pack()
        assert p.artifacts == []

    def test_metrics_default(self):
        p = _make_pack()
        assert isinstance(p.metrics, Metrics)

    def test_keyframe_validator_requires_desc_or_path(self):
        with pytest.raises(Exception):
            _make_pack(keyframes=[Keyframe(t_s=1.0)])  # no desc or image_path

    def test_keyframe_with_desc_accepted(self):
        p = _make_pack(keyframes=[Keyframe(t_s=1.0, desc="frame")])
        assert len(p.keyframes) == 1
