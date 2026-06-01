"""Unit tests for CacheType, CacheStatus, CacheEntry, and CacheStats models."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.cache import (
    CacheEntry,
    CacheStats,
    CacheStatus,
    CacheType,
)


def _ns(**attrs) -> SimpleNamespace:
    return SimpleNamespace(**attrs)


# ===========================================================================
# CacheType enum
# ===========================================================================


class TestCacheTypeEnum:
    def test_video_metadata_value(self):
        assert CacheType.VIDEO_METADATA.value == "video_metadata"

    def test_transcript_value(self):
        assert CacheType.TRANSCRIPT.value == "transcript"

    def test_analysis_result_value(self):
        assert CacheType.ANALYSIS_RESULT.value == "analysis_result"

    def test_learning_extraction_value(self):
        assert CacheType.LEARNING_EXTRACTION.value == "learning_extraction"

    def test_api_response_value(self):
        assert CacheType.API_RESPONSE.value == "api_response"

    def test_thumbnail_value(self):
        assert CacheType.THUMBNAIL.value == "thumbnail"

    def test_user_session_value(self):
        assert CacheType.USER_SESSION.value == "user_session"

    def test_search_result_value(self):
        assert CacheType.SEARCH_RESULT.value == "search_result"

    def test_has_eight_members(self):
        assert len(CacheType) == 8


# ===========================================================================
# CacheStatus enum
# ===========================================================================


class TestCacheStatusEnum:
    def test_active_value(self):
        assert CacheStatus.ACTIVE.value == "active"

    def test_expired_value(self):
        assert CacheStatus.EXPIRED.value == "expired"

    def test_invalidated_value(self):
        assert CacheStatus.INVALIDATED.value == "invalidated"

    def test_warming_value(self):
        assert CacheStatus.WARMING.value == "warming"

    def test_error_value(self):
        assert CacheStatus.ERROR.value == "error"

    def test_has_five_members(self):
        assert len(CacheStatus) == 5


# ===========================================================================
# CacheEntry.is_expired
# ===========================================================================


class TestCacheEntryIsExpired:
    def test_past_expires_at_is_expired(self):
        entry = _ns(expires_at=datetime.utcnow() - timedelta(hours=1))
        assert CacheEntry.is_expired(entry) is True

    def test_future_expires_at_is_not_expired(self):
        entry = _ns(expires_at=datetime.utcnow() + timedelta(hours=1))
        assert CacheEntry.is_expired(entry) is False


# ===========================================================================
# CacheEntry.is_near_expiry
# ===========================================================================


class TestCacheEntryIsNearExpiry:
    def test_entry_expiring_in_15_minutes_is_near_with_30min_window(self):
        entry = _ns(expires_at=datetime.utcnow() + timedelta(minutes=15))
        assert CacheEntry.is_near_expiry(entry, minutes=30) is True

    def test_entry_expiring_in_2_hours_is_not_near_with_30min_window(self):
        entry = _ns(expires_at=datetime.utcnow() + timedelta(hours=2))
        assert CacheEntry.is_near_expiry(entry, minutes=30) is False

    def test_already_expired_is_near_expiry(self):
        entry = _ns(expires_at=datetime.utcnow() - timedelta(hours=1))
        assert CacheEntry.is_near_expiry(entry, minutes=30) is True


# ===========================================================================
# CacheEntry.record_hit
# ===========================================================================


class TestCacheEntryRecordHit:
    def test_increments_hit_count(self):
        entry = _ns(hit_count=5, last_accessed_at=None, created_at=datetime.utcnow(), access_frequency=0.0)
        entry._update_access_frequency = lambda: None  # stub side-effect
        CacheEntry.record_hit(entry)
        assert entry.hit_count == 6

    def test_sets_last_accessed_at(self):
        before = datetime.utcnow()
        entry = _ns(hit_count=0, last_accessed_at=None, created_at=datetime.utcnow(), access_frequency=0.0)
        entry._update_access_frequency = lambda: None
        CacheEntry.record_hit(entry)
        assert entry.last_accessed_at >= before


# ===========================================================================
# CacheEntry.invalidate
# ===========================================================================


class TestCacheEntryInvalidate:
    def test_sets_status_to_invalidated(self):
        entry = _ns(status=CacheStatus.ACTIVE)
        CacheEntry.invalidate(entry)
        assert entry.status == CacheStatus.INVALIDATED


# ===========================================================================
# CacheEntry.get_efficiency_score
# ===========================================================================


class TestCacheEntryGetEfficiencyScore:
    def test_returns_zero_when_no_generation_time(self):
        entry = _ns(generation_time_ms=None, hit_count=10)
        assert CacheEntry.get_efficiency_score(entry) == 0.0

    def test_returns_zero_when_no_hits(self):
        entry = _ns(generation_time_ms=500, hit_count=0)
        assert CacheEntry.get_efficiency_score(entry) == 0.0

    def test_calculates_efficiency(self):
        # (10-1) * 500ms / 1000 = 4.5
        entry = _ns(generation_time_ms=500, hit_count=10)
        assert abs(CacheEntry.get_efficiency_score(entry) - 4.5) < 1e-9

    def test_caps_at_100(self):
        # (1000-1) * 500ms / 1000 = ~499.5 → capped at 100
        entry = _ns(generation_time_ms=500, hit_count=1000)
        assert CacheEntry.get_efficiency_score(entry) == 100.0

    def test_single_hit_gives_zero_efficiency(self):
        # (1-1) * anything = 0
        entry = _ns(generation_time_ms=200, hit_count=1)
        assert CacheEntry.get_efficiency_score(entry) == 0.0


# ===========================================================================
# CacheEntry.extend_expiry
# ===========================================================================


class TestCacheEntryExtendExpiry:
    def test_sets_expires_at_in_future(self):
        before = datetime.utcnow()
        entry = _ns(expires_at=datetime.utcnow())
        CacheEntry.extend_expiry(entry, hours=24)
        assert entry.expires_at > before + timedelta(hours=23)

    def test_custom_hours(self):
        before = datetime.utcnow()
        entry = _ns(expires_at=datetime.utcnow())
        CacheEntry.extend_expiry(entry, hours=1)
        assert entry.expires_at > before + timedelta(minutes=59)


# ===========================================================================
# CacheStats.calculate_efficiency
# ===========================================================================


class TestCacheStatsCalculateEfficiency:
    def test_zero_when_no_hits_or_misses(self):
        s = _ns(total_hits=0, total_misses=0)
        assert CacheStats.calculate_efficiency(s) == 0.0

    def test_100_percent_when_all_hits(self):
        s = _ns(total_hits=100, total_misses=0)
        assert abs(CacheStats.calculate_efficiency(s) - 100.0) < 1e-9

    def test_50_percent_efficiency(self):
        s = _ns(total_hits=50, total_misses=50)
        assert abs(CacheStats.calculate_efficiency(s) - 50.0) < 1e-9

    def test_partial_hit_rate(self):
        s = _ns(total_hits=80, total_misses=20)
        assert abs(CacheStats.calculate_efficiency(s) - 80.0) < 1e-9


# ===========================================================================
# CacheStats.get_storage_efficiency
# ===========================================================================


class TestCacheStatsGetStorageEfficiency:
    def test_zero_when_no_storage_cost(self):
        s = _ns(storage_cost=0, generation_cost_saved=10.0)
        assert CacheStats.get_storage_efficiency(s) == 0.0

    def test_ratio_calculated(self):
        s = _ns(storage_cost=2.0, generation_cost_saved=10.0)
        assert abs(CacheStats.get_storage_efficiency(s) - 5.0) < 1e-9

    def test_less_than_one_when_inefficient(self):
        s = _ns(storage_cost=10.0, generation_cost_saved=5.0)
        assert abs(CacheStats.get_storage_efficiency(s) - 0.5) < 1e-9


# ===========================================================================
# CacheStats.get_size_summary
# ===========================================================================


class TestCacheStatsGetSizeSummary:
    def test_returns_dict_with_expected_keys(self):
        s = _ns(total_size_bytes=1024, average_entry_size=512.0, largest_entry_size=2048)
        summary = CacheStats.get_size_summary(s)
        assert "total_size" in summary
        assert "average_entry" in summary
        assert "largest_entry" in summary

    def test_bytes_unit_for_small_size(self):
        s = _ns(total_size_bytes=500, average_entry_size=100.0, largest_entry_size=200)
        summary = CacheStats.get_size_summary(s)
        assert "B" in summary["total_size"]

    def test_kb_unit_for_medium_size(self):
        s = _ns(total_size_bytes=2048, average_entry_size=1024.0, largest_entry_size=4096)
        summary = CacheStats.get_size_summary(s)
        assert "KB" in summary["total_size"]

    def test_mb_unit_for_large_size(self):
        s = _ns(total_size_bytes=2 * 1024 * 1024, average_entry_size=1024.0, largest_entry_size=4096)
        summary = CacheStats.get_size_summary(s)
        assert "MB" in summary["total_size"]
