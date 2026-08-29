"""Unit tests for videopack versioning, exceptions, and provenance modules."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# Stub the broken videopack __init__ before importing submodules
if "youtube_extension.videopack" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.videopack")
    _stub.__path__ = [str(_SRC / "youtube_extension/videopack")]
    _stub.__package__ = "youtube_extension.videopack"
    sys.modules["youtube_extension.videopack"] = _stub

sys.modules.pop("youtube_extension.videopack.versioning", None)
sys.modules.pop("youtube_extension.videopack.exceptions", None)
sys.modules.pop("youtube_extension.videopack.provenance", None)

from youtube_extension.videopack.exceptions import (
    VideoPackError,
    VideoPackValidationError,
)
from youtube_extension.videopack.provenance import stable_hash
from youtube_extension.videopack.versioning import UpgradePolicy, upgrade_to_v0

# ===========================================================================
# UpgradePolicy enum
# ===========================================================================


class TestUpgradePolicy:
    def test_hard_fail_value(self):
        assert UpgradePolicy.hard_fail.value == "hard_fail"

    def test_best_effort_value(self):
        assert UpgradePolicy.best_effort.value == "best_effort"

    def test_is_str_enum(self):
        assert isinstance(UpgradePolicy.hard_fail, str)

    def test_has_two_members(self):
        assert len(UpgradePolicy) == 2


# ===========================================================================
# upgrade_to_v0
# ===========================================================================


class TestUpgradeToV0:
    def test_sets_version_default(self):
        result = upgrade_to_v0({})
        assert result["version"] == "v0"

    def test_does_not_overwrite_existing_version(self):
        result = upgrade_to_v0({"version": "v1"})
        assert result["version"] == "v1"

    def test_sets_metrics_default(self):
        result = upgrade_to_v0({})
        assert result["metrics"] == {}

    def test_sets_concepts_default(self):
        result = upgrade_to_v0({})
        assert result["concepts"] == []

    def test_sets_chapters_default(self):
        result = upgrade_to_v0({})
        assert result["chapters"] == []

    def test_sets_keyframes_default(self):
        result = upgrade_to_v0({})
        assert result["keyframes"] == []

    def test_sets_requirements_default(self):
        result = upgrade_to_v0({})
        assert result["requirements"] == []

    def test_sets_code_snippets_default(self):
        result = upgrade_to_v0({})
        assert result["code_snippets"] == []

    def test_sets_code_cues_default(self):
        result = upgrade_to_v0({})
        assert result["code_cues"] == []

    def test_sets_tasks_default(self):
        result = upgrade_to_v0({})
        assert result["tasks"] == []

    def test_sets_artifacts_default(self):
        result = upgrade_to_v0({})
        assert result["artifacts"] == []

    def test_preserves_existing_keys(self):
        result = upgrade_to_v0({"custom_key": "custom_val"})
        assert result["custom_key"] == "custom_val"

    def test_returns_same_dict(self):
        d = {}
        result = upgrade_to_v0(d)
        assert result is d

    def test_does_not_overwrite_existing_concepts(self):
        result = upgrade_to_v0({"concepts": ["ai"]})
        assert result["concepts"] == ["ai"]


# ===========================================================================
# VideoPackError / VideoPackValidationError
# ===========================================================================


class TestVideoPackExceptions:
    def test_video_pack_error_is_exception(self):
        assert issubclass(VideoPackError, Exception)

    def test_video_pack_validation_error_is_video_pack_error(self):
        assert issubclass(VideoPackValidationError, VideoPackError)

    def test_video_pack_error_can_be_raised(self):
        with pytest.raises(VideoPackError):
            raise VideoPackError("test error")

    def test_video_pack_validation_error_can_be_raised(self):
        with pytest.raises(VideoPackValidationError):
            raise VideoPackValidationError("validation failed")

    def test_validation_error_caught_as_base(self):
        with pytest.raises(VideoPackError):
            raise VideoPackValidationError("caught as base")


# ===========================================================================
# stable_hash
# ===========================================================================


class TestStableHash:
    def test_returns_string(self):
        result = stable_hash({"key": "val"})
        assert isinstance(result, str)

    def test_length_64_chars(self):
        result = stable_hash({})
        assert len(result) == 64

    def test_same_dict_same_hash(self):
        d = {"a": 1, "b": 2}
        assert stable_hash(d) == stable_hash(d)

    def test_different_dict_different_hash(self):
        assert stable_hash({"a": 1}) != stable_hash({"b": 2})

    def test_key_order_independent(self):
        assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})

    def test_empty_dict(self):
        result = stable_hash({})
        assert len(result) == 64

    def test_nested_dict(self):
        result = stable_hash({"nested": {"x": 1}})
        assert len(result) == 64
