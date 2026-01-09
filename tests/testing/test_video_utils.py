#!/usr/bin/env python3
"""
Tests for Video Utilities
=========================

Tests for the centralized video ID extraction and validation utilities.
"""

import pytest
from youtube_extension.utils import (
    extract_video_id,
    is_valid_video_id,
    normalize_video_url,
    parse_duration_to_seconds,
    format_duration,
)


class TestExtractVideoId:
    """Tests for extract_video_id function"""
    
    def test_standard_watch_url(self):
        """Test extraction from standard watch URL"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_short_url(self):
        """Test extraction from short URL"""
        url = "https://youtu.be/auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_embed_url(self):
        """Test extraction from embed URL"""
        url = "https://www.youtube.com/embed/auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_shorts_url(self):
        """Test extraction from shorts URL"""
        url = "https://www.youtube.com/shorts/auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_watch_url_with_params(self):
        """Test extraction from URL with additional parameters"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag&t=10s&list=PLtest"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_direct_video_id(self):
        """Test with direct 11-character video ID"""
        video_id = "auJzb1D-fag"
        assert extract_video_id(video_id) == "auJzb1D-fag"
    
    def test_v_format_url(self):
        """Test extraction from /v/ format URL"""
        url = "https://www.youtube.com/v/auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_invalid_url_raises_error(self):
        """Test that invalid URL raises ValueError"""
        with pytest.raises(ValueError, match="Could not extract valid YouTube video ID"):
            extract_video_id("https://example.com/video")
    
    def test_empty_string_raises_error(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError):
            extract_video_id("")
    
    def test_wrong_length_id_raises_error(self):
        """Test that incorrect length ID raises ValueError"""
        with pytest.raises(ValueError):
            extract_video_id("short123")  # Only 8 characters


class TestIsValidVideoId:
    """Tests for is_valid_video_id function"""
    
    def test_valid_video_id(self):
        """Test with valid video ID"""
        assert is_valid_video_id("auJzb1D-fag") is True
    
    def test_valid_video_id_with_underscore(self):
        """Test with valid video ID containing underscore"""
        assert is_valid_video_id("abc_DEF-123") is True
    
    def test_invalid_too_short(self):
        """Test with ID that's too short"""
        assert is_valid_video_id("short") is False
    
    def test_invalid_too_long(self):
        """Test with ID that's too long"""
        assert is_valid_video_id("toolong12345") is False
    
    def test_invalid_characters(self):
        """Test with invalid characters"""
        assert is_valid_video_id("invalid@id!") is False
    
    def test_empty_string(self):
        """Test with empty string"""
        assert is_valid_video_id("") is False
    
    def test_none_value(self):
        """Test with None value"""
        assert is_valid_video_id(None) is False
    
    def test_non_string(self):
        """Test with non-string value"""
        assert is_valid_video_id(12345678901) is False


class TestNormalizeVideoUrl:
    """Tests for normalize_video_url function"""
    
    def test_normalize_direct_id(self):
        """Test normalizing direct video ID"""
        result = normalize_video_url("auJzb1D-fag")
        assert result == "https://www.youtube.com/watch?v=auJzb1D-fag"
    
    def test_normalize_short_url(self):
        """Test normalizing short URL"""
        result = normalize_video_url("https://youtu.be/auJzb1D-fag")
        assert result == "https://www.youtube.com/watch?v=auJzb1D-fag"
    
    def test_normalize_embed_url(self):
        """Test normalizing embed URL"""
        result = normalize_video_url("https://www.youtube.com/embed/auJzb1D-fag")
        assert result == "https://www.youtube.com/watch?v=auJzb1D-fag"
    
    def test_normalize_shorts_url(self):
        """Test normalizing shorts URL"""
        result = normalize_video_url("https://www.youtube.com/shorts/auJzb1D-fag")
        assert result == "https://www.youtube.com/watch?v=auJzb1D-fag"
    
    def test_normalize_already_standard(self):
        """Test normalizing already standard URL"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag"
        result = normalize_video_url(url)
        assert result == url
    
    def test_normalize_invalid_raises_error(self):
        """Test that invalid URL raises ValueError"""
        with pytest.raises(ValueError):
            normalize_video_url("https://example.com/video")


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_video_id_with_all_valid_characters(self):
        """Test video ID with all valid character types"""
        video_id = "aZ9_-123456"  # Letters, numbers, underscore, hyphen
        assert is_valid_video_id(video_id) is True
        assert extract_video_id(video_id) == video_id
    
    def test_url_with_timestamp(self):
        """Test URL with timestamp parameter"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag&t=123s"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_url_with_playlist(self):
        """Test URL with playlist parameter"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag&list=PLtest123"
        assert extract_video_id(url) == "auJzb1D-fag"
    
    def test_mobile_url(self):
        """Test mobile YouTube URL"""
        url = "https://m.youtube.com/watch?v=auJzb1D-fag"
        assert extract_video_id(url) == "auJzb1D-fag"


class TestParseDurationToSeconds:
    """Tests for parse_duration_to_seconds function"""
    
    def test_hours_minutes_seconds(self):
        """Test parsing duration with hours, minutes, and seconds"""
        assert parse_duration_to_seconds("PT1H2M3S") == 3723
    
    def test_minutes_seconds(self):
        """Test parsing duration with minutes and seconds"""
        assert parse_duration_to_seconds("PT5M30S") == 330
    
    def test_seconds_only(self):
        """Test parsing duration with seconds only"""
        assert parse_duration_to_seconds("PT45S") == 45
    
    def test_hours_only(self):
        """Test parsing duration with hours only"""
        assert parse_duration_to_seconds("PT2H") == 7200
    
    def test_minutes_only(self):
        """Test parsing duration with minutes only"""
        assert parse_duration_to_seconds("PT10M") == 600
    
    def test_invalid_format(self):
        """Test parsing invalid duration format"""
        assert parse_duration_to_seconds("invalid") == 0
    
    def test_empty_string(self):
        """Test parsing empty string"""
        assert parse_duration_to_seconds("") == 0


class TestFormatDuration:
    """Tests for format_duration function"""
    
    def test_format_hours_minutes_seconds(self):
        """Test formatting duration with hours, minutes, and seconds"""
        assert format_duration("PT1H2M3S") == "1h 2m 3s"
    
    def test_format_minutes_seconds(self):
        """Test formatting duration with minutes and seconds"""
        assert format_duration("PT5M30S") == "5m 30s"
    
    def test_format_seconds_only(self):
        """Test formatting duration with seconds only"""
        assert format_duration("PT45S") == "45s"
    
    def test_format_hours_only(self):
        """Test formatting duration with hours only"""
        assert format_duration("PT2H") == "2h 0m 0s"
    
    def test_format_invalid(self):
        """Test formatting invalid duration returns original"""
        invalid = "invalid_duration"
        assert format_duration(invalid) == invalid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
