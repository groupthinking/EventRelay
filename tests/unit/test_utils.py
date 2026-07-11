"""Unit tests for utils/repro.py and utils/video_utils.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

sys.modules.pop("youtube_extension.utils.repro", None)
sys.modules.pop("youtube_extension.utils.video_utils", None)

from youtube_extension.utils.repro import attach_repro_id_to_payload, get_repro_id
from youtube_extension.utils.video_utils import (
    extract_video_id,
    format_duration,
    is_valid_video_id,
    normalize_video_url,
    parse_duration_to_seconds,
)

_VID = "auJzb1D-fag"  # 11-char valid video ID


# ===========================================================================
# get_repro_id
# ===========================================================================


class TestGetReproId:
    def test_returns_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "abc-123")
        assert get_repro_id() == "abc-123"

    def test_env_var_stripped(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "  trimmed  ")
        assert get_repro_id() == "trimmed"

    def test_default_returned_when_no_env(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        assert get_repro_id("my-default") == "my-default"

    def test_default_stripped(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        assert get_repro_id("  padded  ") == "padded"

    def test_uuid_generated_when_no_env_no_default(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = get_repro_id()
        assert len(result) == 36  # UUID4 format

    def test_blank_env_falls_through_to_default(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "   ")
        assert get_repro_id("fallback") == "fallback"

    def test_blank_env_and_blank_default_generates_uuid(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "   ")
        result = get_repro_id("  ")
        assert len(result) == 36

    def test_env_takes_precedence_over_default(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "from-env")
        result = get_repro_id("default-val")
        assert result == "from-env"


# ===========================================================================
# attach_repro_id_to_payload
# ===========================================================================


class TestAttachReproIdToPayload:
    def test_returns_dict_with_repro_id(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = attach_repro_id_to_payload({"key": "val"}, repro_id="id-1")
        assert result["repro-id"] == "id-1"

    def test_preserves_existing_keys(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = attach_repro_id_to_payload({"x": 1, "y": 2}, repro_id="id-1")
        assert result["x"] == 1
        assert result["y"] == 2

    def test_does_not_mutate_original(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        original = {"a": 1}
        attach_repro_id_to_payload(original, repro_id="id-1")
        assert "repro-id" not in original

    def test_uses_env_repro_id_when_not_provided(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "env-id")
        result = attach_repro_id_to_payload({"k": "v"})
        assert result["repro-id"] == "env-id"

    def test_explicit_repro_id_overrides_env(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "env-id")
        result = attach_repro_id_to_payload({"k": "v"}, repro_id="explicit")
        assert result["repro-id"] == "explicit"


# ===========================================================================
# extract_video_id
# ===========================================================================


class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id(f"https://www.youtube.com/watch?v={_VID}") == _VID

    def test_short_youtu_be_url(self):
        assert extract_video_id(f"https://youtu.be/{_VID}") == _VID

    def test_embed_url(self):
        assert extract_video_id(f"https://www.youtube.com/embed/{_VID}") == _VID

    def test_shorts_url(self):
        assert extract_video_id(f"https://www.youtube.com/shorts/{_VID}") == _VID

    def test_direct_video_id(self):
        assert extract_video_id(_VID) == _VID

    def test_watch_url_with_extra_params(self):
        url = f"https://www.youtube.com/watch?v={_VID}&t=30s"
        assert extract_video_id(url) == _VID

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/")

    def test_short_id_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("short")

    def test_too_long_id_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("a" * 20)


# ===========================================================================
# is_valid_video_id
# ===========================================================================


class TestIsValidVideoId:
    def test_valid_id_returns_true(self):
        assert is_valid_video_id(_VID) is True

    def test_none_returns_false(self):
        assert is_valid_video_id(None) is False

    def test_empty_string_returns_false(self):
        assert is_valid_video_id("") is False

    def test_too_short_returns_false(self):
        assert is_valid_video_id("short") is False

    def test_too_long_returns_false(self):
        assert is_valid_video_id("a" * 12) is False

    def test_valid_with_hyphen(self):
        assert is_valid_video_id("abc-defghij") is True  # 11 chars with hyphen

    def test_exactly_11_chars(self):
        assert is_valid_video_id("12345678901") is True

    def test_with_underscore(self):
        assert is_valid_video_id("abc_defghij") is True

    def test_special_chars_invalid(self):
        assert is_valid_video_id("abc!defghij") is False

    def test_non_string_returns_false(self):
        assert is_valid_video_id(12345678901) is False


# ===========================================================================
# normalize_video_url
# ===========================================================================


class TestNormalizeVideoUrl:
    def test_direct_id_normalized(self):
        result = normalize_video_url(_VID)
        assert result == f"https://www.youtube.com/watch?v={_VID}"

    def test_short_url_normalized(self):
        result = normalize_video_url(f"https://youtu.be/{_VID}")
        assert result == f"https://www.youtube.com/watch?v={_VID}"

    def test_already_watch_url_normalized(self):
        result = normalize_video_url(f"https://www.youtube.com/watch?v={_VID}&t=10s")
        assert result == f"https://www.youtube.com/watch?v={_VID}"


# ===========================================================================
# parse_duration_to_seconds
# ===========================================================================


class TestParseDurationToSeconds:
    def test_full_hms(self):
        assert parse_duration_to_seconds("PT1H2M3S") == 3723

    def test_minutes_and_seconds(self):
        assert parse_duration_to_seconds("PT5M30S") == 330

    def test_seconds_only(self):
        assert parse_duration_to_seconds("PT45S") == 45

    def test_hours_only(self):
        assert parse_duration_to_seconds("PT2H") == 7200

    def test_minutes_only(self):
        assert parse_duration_to_seconds("PT10M") == 600

    def test_zero(self):
        assert parse_duration_to_seconds("PT0S") == 0

    def test_invalid_returns_zero(self):
        assert parse_duration_to_seconds("invalid") == 0


# ===========================================================================
# format_duration
# ===========================================================================


class TestFormatDuration:
    def test_full_hms(self):
        assert format_duration("PT1H2M3S") == "1h 2m 3s"

    def test_minutes_and_seconds(self):
        assert format_duration("PT5M30S") == "5m 30s"

    def test_seconds_only(self):
        assert format_duration("PT45S") == "45s"

    def test_hours_zero_minutes_zero_seconds(self):
        result = format_duration("PT2H")
        assert "2h" in result

    def test_invalid_returns_original(self):
        assert format_duration("invalid") == "invalid"
