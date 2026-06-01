"""Unit tests for youtube_extension.utils.video_utils — pure URL/duration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.utils.video_utils import (
    extract_video_id,
    format_duration,
    is_valid_video_id,
    normalize_video_url,
    parse_duration_to_seconds,
)

_ID = "auJzb1D-fag"  # 11-char valid ID


# ===========================================================================
# extract_video_id
# ===========================================================================


class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id(f"https://www.youtube.com/watch?v={_ID}") == _ID

    def test_short_youtu_be_url(self):
        assert extract_video_id(f"https://youtu.be/{_ID}") == _ID

    def test_embed_url(self):
        assert extract_video_id(f"https://www.youtube.com/embed/{_ID}") == _ID

    def test_shorts_url(self):
        assert extract_video_id(f"https://www.youtube.com/shorts/{_ID}") == _ID

    def test_direct_video_id(self):
        assert extract_video_id(_ID) == _ID

    def test_watch_url_with_extra_params(self):
        assert extract_video_id(f"https://www.youtube.com/watch?v={_ID}&t=120s") == _ID

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not extract"):
            extract_video_id("https://vimeo.com/123456789")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_short_id_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("abc")

    def test_too_long_id_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("a" * 12)


# ===========================================================================
# is_valid_video_id
# ===========================================================================


class TestIsValidVideoId:
    def test_valid_id(self):
        assert is_valid_video_id(_ID) is True

    def test_valid_id_with_underscores_hyphens(self):
        assert is_valid_video_id("a_b-cdefghi") is True

    def test_too_short_returns_false(self):
        assert is_valid_video_id("short") is False

    def test_too_long_returns_false(self):
        assert is_valid_video_id("a" * 12) is False

    def test_none_returns_false(self):
        assert is_valid_video_id(None) is False

    def test_empty_string_returns_false(self):
        assert is_valid_video_id("") is False

    def test_special_chars_returns_false(self):
        assert is_valid_video_id("auJzb1D!fag") is False

    def test_exactly_11_alphanumeric(self):
        assert is_valid_video_id("12345678901") is True


# ===========================================================================
# normalize_video_url
# ===========================================================================


class TestNormalizeVideoUrl:
    def test_short_url_normalized(self):
        result = normalize_video_url(f"https://youtu.be/{_ID}")
        assert result == f"https://www.youtube.com/watch?v={_ID}"

    def test_direct_id_normalized(self):
        result = normalize_video_url(_ID)
        assert result == f"https://www.youtube.com/watch?v={_ID}"

    def test_already_standard_url_normalized(self):
        result = normalize_video_url(f"https://www.youtube.com/watch?v={_ID}")
        assert result == f"https://www.youtube.com/watch?v={_ID}"

    def test_embed_url_normalized(self):
        result = normalize_video_url(f"https://www.youtube.com/embed/{_ID}")
        assert result == f"https://www.youtube.com/watch?v={_ID}"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            normalize_video_url("not-a-url")


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

    def test_minutes_only(self):
        assert parse_duration_to_seconds("PT10M") == 600

    def test_hours_only(self):
        assert parse_duration_to_seconds("PT2H") == 7200

    def test_zero_duration(self):
        assert parse_duration_to_seconds("PT0S") == 0

    def test_invalid_format_returns_zero(self):
        assert parse_duration_to_seconds("not-a-duration") == 0

    def test_empty_string_returns_zero(self):
        assert parse_duration_to_seconds("") == 0


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

    def test_minutes_only(self):
        assert format_duration("PT10M") == "10m 0s"

    def test_hours_only(self):
        assert format_duration("PT2H") == "2h 0m 0s"

    def test_invalid_returns_original(self):
        assert format_duration("not-a-duration") == "not-a-duration"
