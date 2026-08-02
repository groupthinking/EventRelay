"""Unit tests for CacheEntry, CacheStats, and InMemoryCacheLayer (intelligent_cache module)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

pytest.importorskip("redis", reason="redis not installed")

from youtube_extension.backend.services.intelligent_cache import (
    CacheEntry,
    CacheStats,
    InMemoryCacheLayer,
)

# ===========================================================================
# CacheEntry dataclass
# ===========================================================================


class TestCacheEntryPostInit:
    def test_tags_none_becomes_empty_list(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None, tags=None)
        assert e.tags == []

    def test_explicit_tags_preserved(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None, tags=["a", "b"])
        assert e.tags == ["a", "b"]

    def test_last_accessed_none_becomes_created_at(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None, last_accessed=None)
        assert e.last_accessed == now

    def test_explicit_last_accessed_preserved(self):
        now = datetime.now(timezone.utc)
        later = datetime(2025, 1, 1, tzinfo=timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None, last_accessed=later)
        assert e.last_accessed == later

    def test_access_count_defaults_zero(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None)
        assert e.access_count == 0

    def test_size_bytes_defaults_zero(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="k", value="v", created_at=now, expires_at=None)
        assert e.size_bytes == 0

    def test_required_fields_stored(self):
        now = datetime.now(timezone.utc)
        e = CacheEntry(key="mykey", value={"data": 42}, created_at=now, expires_at=None)
        assert e.key == "mykey"
        assert e.value == {"data": 42}
        assert e.created_at == now


# ===========================================================================
# CacheStats
# ===========================================================================


class TestCacheStats:
    def test_defaults_all_zero(self):
        s = CacheStats()
        assert s.hit_count == 0
        assert s.miss_count == 0
        assert s.eviction_count == 0
        assert s.total_entries == 0
        assert s.total_size_bytes == 0
        assert s.avg_access_time_ms == 0.0

    def test_hit_rate_zero_when_no_requests(self):
        s = CacheStats()
        assert s.hit_rate == 0.0

    def test_hit_rate_100_when_all_hits(self):
        s = CacheStats(hit_count=100, miss_count=0)
        assert abs(s.hit_rate - 100.0) < 1e-9

    def test_hit_rate_50_percent(self):
        s = CacheStats(hit_count=50, miss_count=50)
        assert abs(s.hit_rate - 50.0) < 1e-9

    def test_hit_rate_partial(self):
        s = CacheStats(hit_count=80, miss_count=20)
        assert abs(s.hit_rate - 80.0) < 1e-9

    def test_explicit_values(self):
        s = CacheStats(hit_count=10, miss_count=5, eviction_count=2, total_entries=15)
        assert s.hit_count == 10
        assert s.miss_count == 5
        assert s.eviction_count == 2
        assert s.total_entries == 15


# ===========================================================================
# InMemoryCacheLayer
# ===========================================================================


class TestInMemoryCacheLayerInit:
    def test_name_default(self):
        layer = InMemoryCacheLayer()
        assert layer.name == "L1_Memory"

    def test_max_size_default(self):
        layer = InMemoryCacheLayer()
        assert layer.max_size == 10000

    def test_max_size_bytes_default(self):
        layer = InMemoryCacheLayer()
        assert layer.max_size_bytes == 100 * 1024 * 1024

    def test_cache_starts_empty(self):
        layer = InMemoryCacheLayer()
        assert len(layer.cache) == 0

    def test_stats_initialized(self):
        layer = InMemoryCacheLayer()
        assert isinstance(layer.stats, CacheStats)
        assert layer.stats.hit_count == 0

    def test_custom_name(self):
        layer = InMemoryCacheLayer(name="custom_l1")
        assert layer.name == "custom_l1"

    def test_custom_max_size(self):
        layer = InMemoryCacheLayer(max_size=500)
        assert layer.max_size == 500
