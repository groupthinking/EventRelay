"""Unit tests for videopack/* modules."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# Import package directly to verify __init__.py works and is covered
import youtube_extension.videopack  # noqa: F401

from youtube_extension.videopack.schema import (
    ArtifactRef,
    CodeSnippet,
    Keyframe,
    Metrics,
    Provenance,
    Requirement,
    Transcript,
    TranscriptSegment,
    VideoPackV0,
    VPVersion,
    VisualContext,
    VisualElement,
)
from youtube_extension.videopack.io import load_json, read_pack, save_json, write_pack
from youtube_extension.videopack.validate import validate_pack
from youtube_extension.videopack.versioning import UpgradePolicy, upgrade_to_v0
from youtube_extension.videopack.provenance import stable_hash
from youtube_extension.videopack.exceptions import VideoPackError, VideoPackValidationError

_NOW = datetime(2024, 1, 1, 12, 0, 0)


def _make_pack(**overrides) -> VideoPackV0:
    defaults: dict = {
        "video_id": "abc123def45",
        "transcript": Transcript(full_text="Hello world", segments=[]),
        "provenance": Provenance(created_at=_NOW),
    }
    defaults.update(overrides)
    return VideoPackV0(**defaults)


# ===========================================================================
# VPVersion
# ===========================================================================


class TestVPVersion:
    def test_v0_value(self):
        assert VPVersion.v0 == "v0"


# ===========================================================================
# TranscriptSegment
# ===========================================================================


class TestTranscriptSegment:
    def test_basic_creation(self):
        seg = TranscriptSegment(idx=0, start_s=0.0, end_s=5.0, text="Hello")
        assert seg.text == "Hello"
        assert seg.start_s == 0.0
        assert seg.end_s == 5.0

    def test_idx_stored(self):
        seg = TranscriptSegment(idx=3, start_s=1.0, end_s=2.0, text="Test")
        assert seg.idx == 3


# ===========================================================================
# Transcript
# ===========================================================================


class TestTranscript:
    def test_full_text_stored(self):
        t = Transcript(full_text="some text")
        assert t.full_text == "some text"

    def test_segments_default_empty(self):
        t = Transcript(full_text="text")
        assert t.segments == []

    def test_language_optional(self):
        t = Transcript(full_text="text", language="en")
        assert t.language == "en"

    def test_language_defaults_none(self):
        t = Transcript(full_text="text")
        assert t.language is None


# ===========================================================================
# Keyframe
# ===========================================================================


class TestKeyframe:
    def test_timestamp_stored(self):
        kf = Keyframe(t_s=1.5, desc="intro frame")
        assert kf.t_s == 1.5

    def test_image_path_optional(self):
        kf = Keyframe(t_s=2.0, image_path="/frames/0.png")
        assert kf.image_path == "/frames/0.png"

    def test_desc_optional(self):
        kf = Keyframe(t_s=3.0, desc="some description")
        assert kf.desc == "some description"

    def test_both_none_initially_allowed_by_model(self):
        # Pydantic model creation succeeds; the validator on VideoPackV0 rejects it
        kf = Keyframe(t_s=0.5)
        assert kf.image_path is None
        assert kf.desc is None


# ===========================================================================
# Requirement
# ===========================================================================


class TestRequirement:
    def test_basic_fields(self):
        req = Requirement(id="R001", title="Login flow")
        assert req.id == "R001"
        assert req.title == "Login flow"

    def test_priority_default_normal(self):
        req = Requirement(id="R001", title="test")
        assert req.priority == "normal"

    def test_custom_priority(self):
        req = Requirement(id="R001", title="test", priority="high")
        assert req.priority == "high"

    def test_tags_default_empty(self):
        req = Requirement(id="R001", title="test")
        assert req.tags == []

    def test_detail_optional(self):
        req = Requirement(id="R001", title="test", detail="some detail")
        assert req.detail == "some detail"


# ===========================================================================
# CodeSnippet
# ===========================================================================


class TestCodeSnippet:
    def test_content_required(self):
        cs = CodeSnippet(content="print('hello')")
        assert cs.content == "print('hello')"

    def test_lang_optional(self):
        cs = CodeSnippet(content="x = 1", lang="python")
        assert cs.lang == "python"

    def test_path_hint_optional(self):
        cs = CodeSnippet(content="x = 1", path_hint="src/main.py")
        assert cs.path_hint == "src/main.py"

    def test_lang_defaults_none(self):
        cs = CodeSnippet(content="x = 1")
        assert cs.lang is None


# ===========================================================================
# ArtifactRef
# ===========================================================================


class TestArtifactRef:
    def test_kind_required(self):
        ar = ArtifactRef(kind="repo")
        assert ar.kind == "repo"

    def test_meta_default_empty(self):
        ar = ArtifactRef(kind="file", path="/some/path")
        assert ar.meta == {}

    def test_path_optional(self):
        ar = ArtifactRef(kind="url")
        assert ar.path is None


# ===========================================================================
# Metrics
# ===========================================================================


class TestMetrics:
    def test_all_fields_optional(self):
        m = Metrics()
        assert m.cost_usd is None
        assert m.latency_ms is None
        assert m.tokens_in is None
        assert m.tokens_out is None

    def test_with_values(self):
        m = Metrics(cost_usd=0.01, latency_ms=500, tokens_in=100, tokens_out=200)
        assert m.cost_usd == 0.01
        assert m.tokens_in == 100


# ===========================================================================
# Provenance
# ===========================================================================


class TestProvenance:
    def test_created_at_stored(self):
        p = Provenance(created_at=_NOW)
        assert p.created_at == _NOW

    def test_tool_versions_default_empty(self):
        p = Provenance(created_at=_NOW)
        assert p.tool_versions == {}

    def test_source_hash_optional(self):
        p = Provenance(created_at=_NOW, source_hash="abc123")
        assert p.source_hash == "abc123"

    def test_notes_optional(self):
        p = Provenance(created_at=_NOW, notes="test run")
        assert p.notes == "test run"


# ===========================================================================
# VisualElement
# ===========================================================================


class TestVisualElement:
    def test_basic_creation(self):
        ve = VisualElement(timestamp=1.5, element_type="code", content="x = 1")
        assert ve.timestamp == 1.5
        assert ve.element_type == "code"
        assert ve.content == "x = 1"

    def test_confidence_default(self):
        ve = VisualElement(timestamp=0.0, element_type="text", content="hello")
        assert ve.confidence == 0.9

    def test_custom_confidence(self):
        ve = VisualElement(timestamp=0.0, element_type="diagram", content="flowchart", confidence=0.75)
        assert ve.confidence == 0.75

    def test_frame_path_optional(self):
        ve = VisualElement(timestamp=0.0, element_type="UI", content="button", frame_path="/frames/1.png")
        assert ve.frame_path == "/frames/1.png"


# ===========================================================================
# VisualContext
# ===========================================================================


class TestVisualContext:
    def test_defaults(self):
        vc = VisualContext()
        assert vc.visual_elements == []
        assert vc.frame_analysis_count == 0

    def test_summary_optional(self):
        vc = VisualContext(summary="good video")
        assert vc.summary == "good video"

    def test_summary_defaults_none(self):
        vc = VisualContext()
        assert vc.summary is None


# ===========================================================================
# VideoPackV0
# ===========================================================================


class TestVideoPackV0:
    def test_version_default(self):
        pack = _make_pack()
        assert pack.version == VPVersion.v0

    def test_id_auto_generated_uuid(self):
        pack = _make_pack()
        assert len(pack.id) == 36

    def test_unique_ids(self):
        p1 = _make_pack()
        p2 = _make_pack()
        assert p1.id != p2.id

    def test_video_id_stored(self):
        pack = _make_pack()
        assert pack.video_id == "abc123def45"

    def test_concepts_default_empty(self):
        pack = _make_pack()
        assert pack.concepts == []

    def test_requirements_default_empty(self):
        pack = _make_pack()
        assert pack.requirements == []

    def test_code_snippets_default_empty(self):
        pack = _make_pack()
        assert pack.code_snippets == []

    def test_keyframe_without_path_or_desc_rejected(self):
        with pytest.raises(Exception):
            _make_pack(keyframes=[Keyframe(t_s=1.0)])

    def test_keyframe_with_desc_accepted(self):
        pack = _make_pack(keyframes=[Keyframe(t_s=1.0, desc="intro")])
        assert len(pack.keyframes) == 1

    def test_keyframe_with_image_path_accepted(self):
        pack = _make_pack(keyframes=[Keyframe(t_s=2.0, image_path="/f/1.png")])
        assert len(pack.keyframes) == 1

    def test_metrics_defaults(self):
        pack = _make_pack()
        assert pack.metrics.cost_usd is None

    def test_visual_context_optional(self):
        pack = _make_pack()
        assert pack.visual_context is None


# ===========================================================================
# validate_pack
# ===========================================================================


class TestValidatePack:
    def test_valid_pack_passes(self):
        validate_pack(_make_pack())  # should not raise

    def test_whitespace_only_full_text_fails(self):
        pack = _make_pack(transcript=Transcript(full_text="   "))
        with pytest.raises(AssertionError):
            validate_pack(pack)

    def test_empty_full_text_fails(self):
        pack = _make_pack(transcript=Transcript(full_text=""))
        with pytest.raises(AssertionError):
            validate_pack(pack)

    def test_ordered_segments_pass(self):
        segs = [
            TranscriptSegment(idx=0, start_s=0.0, end_s=1.0, text="a"),
            TranscriptSegment(idx=1, start_s=1.0, end_s=2.0, text="b"),
        ]
        pack = _make_pack(transcript=Transcript(full_text="a b", segments=segs))
        validate_pack(pack)

    def test_overlapping_segments_fail(self):
        segs = [
            TranscriptSegment(idx=0, start_s=0.0, end_s=2.0, text="a"),
            TranscriptSegment(idx=1, start_s=1.0, end_s=3.0, text="b"),
        ]
        pack = _make_pack(transcript=Transcript(full_text="a b", segments=segs))
        with pytest.raises(AssertionError):
            validate_pack(pack)

    def test_start_after_end_fails(self):
        segs = [TranscriptSegment(idx=0, start_s=5.0, end_s=2.0, text="bad")]
        pack = _make_pack(transcript=Transcript(full_text="bad", segments=segs))
        with pytest.raises(AssertionError):
            validate_pack(pack)


# ===========================================================================
# stable_hash (provenance.py)
# ===========================================================================


class TestStableHash:
    def test_returns_string(self):
        assert isinstance(stable_hash({"key": "value"}), str)

    def test_sha256_length(self):
        assert len(stable_hash({"key": "value"})) == 64

    def test_deterministic(self):
        assert stable_hash({"a": 1, "b": 2}) == stable_hash({"a": 1, "b": 2})

    def test_key_order_independent(self):
        assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})

    def test_different_inputs_differ(self):
        assert stable_hash({"a": 1}) != stable_hash({"a": 2})


# ===========================================================================
# UpgradePolicy / upgrade_to_v0 (versioning.py)
# ===========================================================================


class TestUpgradePolicy:
    def test_hard_fail_value(self):
        assert UpgradePolicy.hard_fail == "hard_fail"

    def test_best_effort_value(self):
        assert UpgradePolicy.best_effort == "best_effort"


class TestUpgradeToV0:
    def test_adds_version_default(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert d["version"] == "v0"

    def test_preserves_existing_version(self):
        d = {"version": "v1"}
        upgrade_to_v0(d)
        assert d["version"] == "v1"

    def test_adds_metrics(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert "metrics" in d

    def test_adds_concepts(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert "concepts" in d

    def test_adds_keyframes(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert "keyframes" in d

    def test_adds_requirements(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert "requirements" in d

    def test_adds_artifacts(self):
        d: dict = {}
        upgrade_to_v0(d)
        assert "artifacts" in d

    def test_returns_same_dict(self):
        d = {"foo": "bar"}
        result = upgrade_to_v0(d)
        assert result is d


# ===========================================================================
# VideoPackError / VideoPackValidationError (exceptions.py)
# ===========================================================================


class TestVideoPackExceptions:
    def test_video_pack_error_is_exception(self):
        with pytest.raises(VideoPackError):
            raise VideoPackError("test error")

    def test_validation_error_is_video_pack_error(self):
        with pytest.raises(VideoPackError):
            raise VideoPackValidationError("validation failed")

    def test_validation_error_is_exception(self):
        with pytest.raises(VideoPackValidationError):
            raise VideoPackValidationError("test")


# ===========================================================================
# load_json / save_json (io.py)
# ===========================================================================


class TestLoadSaveJson:
    def test_roundtrip(self, tmp_path):
        data = {"key": "value", "num": 42}
        path = tmp_path / "test.json"
        save_json(path, data)
        assert load_json(path) == data

    def test_save_creates_parent_dirs(self, tmp_path):
        data = {"hello": "world"}
        path = tmp_path / "nested" / "dir" / "data.json"
        save_json(path, data)
        assert path.exists()

    def test_load_returns_dict(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text('{"a": 1}')
        assert isinstance(load_json(path), dict)

    def test_save_produces_valid_json(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(path, {"x": [1, 2, 3]})
        parsed = json.loads(path.read_text())
        assert parsed["x"] == [1, 2, 3]


# ===========================================================================
# read_pack / write_pack (io.py)
# ===========================================================================


class TestReadWritePack:
    def test_read_pack_returns_videopackv0(self, tmp_path):
        data = {
            "video_id": "vid12345678",
            "transcript": {"full_text": "hello", "segments": []},
            "provenance": {"created_at": "2024-01-01T12:00:00"},
        }
        path = tmp_path / "pack.json"
        path.write_text(json.dumps(data))
        pack = read_pack(path)
        assert isinstance(pack, VideoPackV0)
        assert pack.video_id == "vid12345678"

    def test_write_pack_creates_file(self, tmp_path):
        pack = _make_pack()
        path = tmp_path / "out.json"
        write_pack(path, pack)
        assert path.exists()

    def test_write_pack_contains_video_id(self, tmp_path):
        pack = _make_pack()
        path = tmp_path / "out.json"
        write_pack(path, pack)
        data = json.loads(path.read_text())
        assert data["video_id"] == "abc123def45"
