"""Unit tests for youtube_extension.utils.video_utils pure functions."""

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

VALID_ID = "auJzb1D-fag"  # 11 chars


# ===========================================================================
# extract_video_id
# ===========================================================================


class TestExtractVideoId:
    def test_standard_watch_url(self):
        assert extract_video_id(f"https://www.youtube.com/watch?v={VALID_ID}") == VALID_ID

    def test_short_url(self):
        assert extract_video_id(f"https://youtu.be/{VALID_ID}") == VALID_ID

    def test_embed_url(self):
        assert extract_video_id(f"https://www.youtube.com/embed/{VALID_ID}") == VALID_ID

    def test_shorts_url(self):
        assert extract_video_id(f"https://www.youtube.com/shorts/{VALID_ID}") == VALID_ID

    def test_direct_video_id(self):
        assert extract_video_id(VALID_ID) == VALID_ID

    def test_watch_url_with_extra_params(self):
        url = f"https://www.youtube.com/watch?v={VALID_ID}&t=30s"
        assert extract_video_id(url) == VALID_ID

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("https://notube.com/x=abc")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_short_id_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_video_id("short")


# ===========================================================================
# is_valid_video_id
# ===========================================================================


class TestIsValidVideoId:
    def test_valid_11_char_id(self):
        assert is_valid_video_id(VALID_ID) is True

    def test_none_returns_false(self):
        assert is_valid_video_id(None) is False

    def test_empty_string_returns_false(self):
        assert is_valid_video_id("") is False

    def test_too_short_returns_false(self):
        assert is_valid_video_id("short") is False

    def test_too_long_returns_false(self):
        assert is_valid_video_id("toolongvideoidhere") is False

    def test_special_chars_returns_false(self):
        assert is_valid_video_id("invalid!char") is False

    def test_underscore_allowed(self):
        assert is_valid_video_id("hello_world") is True

    def test_hyphen_allowed(self):
        assert is_valid_video_id("hello-world") is True

    def test_all_numbers(self):
        assert is_valid_video_id("12345678901") is True

    def test_mixed_case(self):
        assert is_valid_video_id("aAbBcCdDeEf") is True


# ===========================================================================
# normalize_video_url
# ===========================================================================


class TestNormalizeVideoUrl:
    def test_direct_id_normalized(self):
        result = normalize_video_url(VALID_ID)
        assert result == f"https://www.youtube.com/watch?v={VALID_ID}"

    def test_short_url_normalized(self):
        result = normalize_video_url(f"https://youtu.be/{VALID_ID}")
        assert result == f"https://www.youtube.com/watch?v={VALID_ID}"

    def test_watch_url_normalized(self):
        result = normalize_video_url(f"https://www.youtube.com/watch?v={VALID_ID}")
        assert result == f"https://www.youtube.com/watch?v={VALID_ID}"

    def test_embed_url_normalized(self):
        result = normalize_video_url(f"https://www.youtube.com/embed/{VALID_ID}")
        assert result == f"https://www.youtube.com/watch?v={VALID_ID}"


# ===========================================================================
# parse_duration_to_seconds
# ===========================================================================


class TestParseDurationToSeconds:
    def test_full_duration(self):
        assert parse_duration_to_seconds("PT1H2M3S") == 3723

    def test_minutes_and_seconds(self):
        assert parse_duration_to_seconds("PT5M30S") == 330

    def test_seconds_only(self):
        assert parse_duration_to_seconds("PT45S") == 45

    def test_hours_and_minutes(self):
        assert parse_duration_to_seconds("PT2H30M") == 9000

    def test_hours_only(self):
        assert parse_duration_to_seconds("PT1H") == 3600

    def test_minutes_only(self):
        assert parse_duration_to_seconds("PT10M") == 600

    def test_invalid_returns_zero(self):
        assert parse_duration_to_seconds("invalid") == 0

    def test_zero_duration(self):
        assert parse_duration_to_seconds("PT0S") == 0

    def test_large_hours(self):
        assert parse_duration_to_seconds("PT10H") == 36000


# ===========================================================================
# format_duration
# ===========================================================================


class TestFormatDuration:
    def test_full_duration(self):
        assert format_duration("PT1H2M3S") == "1h 2m 3s"

    def test_minutes_and_seconds(self):
        assert format_duration("PT5M30S") == "5m 30s"

    def test_seconds_only(self):
        assert format_duration("PT45S") == "45s"

    def test_hours_and_minutes(self):
        assert format_duration("PT2H30M") == "2h 30m 0s"

    def test_hours_only(self):
        assert format_duration("PT1H") == "1h 0m 0s"

    def test_minutes_only(self):
        assert format_duration("PT10M") == "10m 0s"

    def test_zero_seconds(self):
        assert format_duration("PT0S") == "0s"

    def test_invalid_returns_original(self):
        assert format_duration("invalid") == "invalid"
