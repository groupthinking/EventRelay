"""
Tests for intelligent_cache.py

Redis is not installed; stub it before importing the module under test.
"""

import sys
import types as _types

# --- Redis stub (must happen before module import) ---
_redis_mod = _types.ModuleType("redis")
_redis_async_mod = _types.ModuleType("redis.asyncio")
_redis_async_mod.Redis = object
_redis_async_mod.ConnectionPool = object
_redis_async_mod.from_url = lambda url, **kw: None
_redis_mod.asyncio = _redis_async_mod
sys.modules.setdefault("redis", _redis_mod)
sys.modules.setdefault("redis.asyncio", _redis_async_mod)
# -----------------------------------------------------

import json
from datetime import datetime, timedelta, timezone

import pytest

from youtube_extension.backend.services.intelligent_cache import (
    CacheEntry,
    CacheStats,
    DateTimeEncoder,
    InMemoryCacheLayer,
    IntelligentCacheLayer,
    datetime_decoder,
)


# ---------------------------------------------------------------------------
# DateTimeEncoder
# ---------------------------------------------------------------------------


class TestDateTimeEncoder:
    def test_encodes_datetime_as_dict(self):
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = json.dumps(dt, cls=DateTimeEncoder)
        parsed = json.loads(result)
        assert parsed["__type__"] == "datetime"
        assert "2024-01-15" in parsed["iso"]

    def test_encodes_datetime_iso_roundtrip(self):
        dt = datetime(2024, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
        result = json.loads(json.dumps(dt, cls=DateTimeEncoder))
        restored = datetime.fromisoformat(result["iso"])
        assert restored == dt

    def test_encodes_regular_types_normally(self):
        data = {"key": "value", "num": 42, "lst": [1, 2, 3]}
        result = json.loads(json.dumps(data, cls=DateTimeEncoder))
        assert result == data

    def test_raises_for_non_serialisable_type(self):
        class Unserializable:
            pass

        with pytest.raises(TypeError):
            json.dumps(Unserializable(), cls=DateTimeEncoder)

    def test_nested_datetime_in_dict(self):
        dt = datetime(2025, 3, 10, tzinfo=timezone.utc)
        data = {"created": dt, "label": "test"}
        result = json.loads(json.dumps(data, cls=DateTimeEncoder))
        assert result["created"]["__type__"] == "datetime"
        assert result["label"] == "test"


# ---------------------------------------------------------------------------
# datetime_decoder
# ---------------------------------------------------------------------------


class TestDatetimeDecoder:
    def test_decodes_datetime_dict(self):
        dt = datetime(2024, 5, 20, 10, 0, 0, tzinfo=timezone.utc)
        encoded = json.dumps(dt, cls=DateTimeEncoder)
        decoded = json.loads(encoded, object_hook=datetime_decoder)
        assert isinstance(decoded, datetime)
        assert decoded == dt

    def test_leaves_plain_dict_unchanged(self):
        data = {"a": 1, "b": "hello"}
        result = json.loads(json.dumps(data), object_hook=datetime_decoder)
        assert result == data


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------


class TestCacheEntry:
    def _make_entry(self, **kwargs):
        defaults = dict(
            key="k",
            value="v",
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        defaults.update(kwargs)
        return CacheEntry(**defaults)

    def test_tags_defaults_to_empty_list(self):
        entry = self._make_entry()
        assert entry.tags == []

    def test_last_accessed_defaults_to_created_at(self):
        created = datetime.now(timezone.utc)
        entry = self._make_entry(created_at=created)
        assert entry.last_accessed == created

    def test_explicit_tags_preserved(self):
        entry = self._make_entry(tags=["a", "b"])
        assert entry.tags == ["a", "b"]

    def test_explicit_last_accessed_preserved(self):
        created = datetime.now(timezone.utc)
        accessed = created + timedelta(seconds=5)
        entry = self._make_entry(created_at=created, last_accessed=accessed)
        assert entry.last_accessed == accessed

    def test_default_access_count_is_zero(self):
        entry = self._make_entry()
        assert entry.access_count == 0

    def test_size_bytes_default_zero(self):
        entry = self._make_entry()
        assert entry.size_bytes == 0

    def test_expires_at_none_by_default(self):
        entry = self._make_entry()
        assert entry.expires_at is None


# ---------------------------------------------------------------------------
# CacheStats
# ---------------------------------------------------------------------------


class TestCacheStats:
    def test_hit_rate_zero_when_no_requests(self):
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_100_when_all_hits(self):
        stats = CacheStats(hit_count=10, miss_count=0)
        assert stats.hit_rate == 100.0

    def test_hit_rate_0_when_all_misses(self):
        stats = CacheStats(hit_count=0, miss_count=10)
        assert stats.hit_rate == 0.0

    def test_hit_rate_50_percent(self):
        stats = CacheStats(hit_count=5, miss_count=5)
        assert stats.hit_rate == 50.0

    def test_hit_rate_calculation(self):
        stats = CacheStats(hit_count=3, miss_count=1)
        assert stats.hit_rate == 75.0

    def test_default_values(self):
        stats = CacheStats()
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.eviction_count == 0
        assert stats.total_entries == 0
        assert stats.total_size_bytes == 0
        assert stats.avg_access_time_ms == 0


# ---------------------------------------------------------------------------
# IntelligentCacheLayer (base class)
# ---------------------------------------------------------------------------


class TestIntelligentCacheLayer:
    def test_init_stores_name_and_max_size(self):
        layer = IntelligentCacheLayer("test_layer", max_size=500)
        assert layer.name == "test_layer"
        assert layer.max_size == 500

    def test_init_creates_stats(self):
        layer = IntelligentCacheLayer("test_layer")
        assert isinstance(layer.stats, CacheStats)

    async def test_get_raises_not_implemented(self):
        layer = IntelligentCacheLayer("test_layer")
        with pytest.raises(NotImplementedError):
            await layer.get("key")

    async def test_set_raises_not_implemented(self):
        layer = IntelligentCacheLayer("test_layer")
        with pytest.raises(NotImplementedError):
            await layer.set("key", "value")

    async def test_delete_raises_not_implemented(self):
        layer = IntelligentCacheLayer("test_layer")
        with pytest.raises(NotImplementedError):
            await layer.delete("key")

    async def test_clear_raises_not_implemented(self):
        layer = IntelligentCacheLayer("test_layer")
        with pytest.raises(NotImplementedError):
            await layer.clear()

    async def test_get_stats_returns_stats(self):
        layer = IntelligentCacheLayer("test_layer")
        result = await layer.get_stats()
        assert result is layer.stats


# ---------------------------------------------------------------------------
# InMemoryCacheLayer
# ---------------------------------------------------------------------------


class TestInMemoryCacheLayer:
    def setup_method(self):
        self.cache = InMemoryCacheLayer("test_l1", max_size=10, max_size_bytes=1024 * 1024)

    async def test_get_miss_returns_none(self):
        result = await self.cache.get("nonexistent")
        assert result is None

    async def test_get_miss_increments_miss_count(self):
        await self.cache.get("nonexistent")
        assert self.cache.stats.miss_count == 1

    async def test_set_and_get_roundtrip(self):
        await self.cache.set("key1", "hello")
        result = await self.cache.get("key1")
        assert result == "hello"

    async def test_set_and_get_increments_hit_count(self):
        await self.cache.set("key1", "hello")
        await self.cache.get("key1")
        assert self.cache.stats.hit_count == 1

    async def test_set_increments_total_entries(self):
        await self.cache.set("k1", "v1")
        await self.cache.set("k2", "v2")
        assert self.cache.stats.total_entries == 2

    async def test_set_updates_size_bytes(self):
        await self.cache.set("k1", "hello")
        assert self.cache.stats.total_size_bytes > 0

    async def test_set_overwrites_existing_key(self):
        await self.cache.set("k1", "first")
        await self.cache.set("k1", "second")
        result = await self.cache.get("k1")
        assert result == "second"
        # Entry count should stay the same
        assert self.cache.stats.total_entries == 1

    async def test_set_overwrites_updates_size_bytes_correctly(self):
        await self.cache.set("k1", "a")
        size_after_first = self.cache.stats.total_size_bytes
        await self.cache.set("k1", "b" * 100)
        assert self.cache.stats.total_size_bytes > size_after_first

    async def test_delete_existing_key_returns_true(self):
        await self.cache.set("k1", "v1")
        result = await self.cache.delete("k1")
        assert result is True

    async def test_delete_missing_key_returns_false(self):
        result = await self.cache.delete("nonexistent")
        assert result is False

    async def test_delete_removes_from_cache(self):
        await self.cache.set("k1", "v1")
        await self.cache.delete("k1")
        result = await self.cache.get("k1")
        assert result is None

    async def test_delete_decrements_total_entries(self):
        await self.cache.set("k1", "v1")
        await self.cache.delete("k1")
        assert self.cache.stats.total_entries == 0

    async def test_delete_decrements_size_bytes(self):
        await self.cache.set("k1", "v1")
        size_before = self.cache.stats.total_size_bytes
        await self.cache.delete("k1")
        assert self.cache.stats.total_size_bytes < size_before

    async def test_clear_returns_entry_count(self):
        await self.cache.set("k1", "v1")
        await self.cache.set("k2", "v2")
        count = await self.cache.clear()
        assert count == 2

    async def test_clear_empties_cache(self):
        await self.cache.set("k1", "v1")
        await self.cache.clear()
        assert len(self.cache.cache) == 0

    async def test_clear_resets_stats(self):
        await self.cache.set("k1", "v1")
        await self.cache.clear()
        assert self.cache.stats.total_entries == 0
        assert self.cache.stats.total_size_bytes == 0

    async def test_ttl_expiration_returns_none(self):
        # Set with 1-second TTL and then fake expiry by manipulating expires_at
        await self.cache.set("k1", "v1", ttl=10)
        # Force expiration by moving expires_at into the past
        entry = self.cache.cache["k1"]
        entry.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        result = await self.cache.get("k1")
        assert result is None

    async def test_ttl_expiration_increments_miss_count(self):
        await self.cache.set("k1", "v1", ttl=10)
        entry = self.cache.cache["k1"]
        entry.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await self.cache.get("k1")
        assert self.cache.stats.miss_count == 1

    async def test_no_ttl_entry_does_not_expire(self):
        await self.cache.set("k1", "v1")
        result = await self.cache.get("k1")
        assert result == "v1"

    async def test_get_increments_access_count(self):
        await self.cache.set("k1", "v1")
        await self.cache.get("k1")
        await self.cache.get("k1")
        assert self.cache.cache["k1"].access_count == 2

    async def test_evict_if_needed_when_max_size_exceeded(self):
        small_cache = InMemoryCacheLayer("small", max_size=3, max_size_bytes=1024 * 1024)
        for i in range(4):
            await small_cache.set(f"key{i}", f"value{i}")
        assert len(small_cache.cache) <= 3
        assert small_cache.stats.eviction_count >= 1

    async def test_evict_if_needed_when_max_bytes_exceeded(self):
        # 50-byte limit — a typical JSON-serialised entry will exceed this quickly
        tiny_cache = InMemoryCacheLayer("tiny", max_size=1000, max_size_bytes=50)
        await tiny_cache.set("k1", "a" * 10)
        await tiny_cache.set("k2", "b" * 10)
        # At some point eviction must have triggered to keep bytes ≤ 50
        assert tiny_cache.stats.total_size_bytes <= 50 or tiny_cache.stats.eviction_count > 0

    async def test_lru_order_moves_accessed_to_end(self):
        """After a get(), the key should be at the most-recent end of the OrderedDict."""
        await self.cache.set("first", "v1")
        await self.cache.set("second", "v2")
        await self.cache.get("first")  # touch "first"
        keys = list(self.cache.cache.keys())
        assert keys[-1] == "first"

    async def test_set_with_tags_stored_correctly(self):
        await self.cache.set("k1", "v1", tags=["tag_a", "tag_b"])
        entry = self.cache.cache["k1"]
        assert entry.tags == ["tag_a", "tag_b"]

    async def test_set_returns_true_on_success(self):
        result = await self.cache.set("k1", "v1")
        assert result is True

    async def test_stats_hit_rate_after_mixed_ops(self):
        await self.cache.set("k1", "v1")
        await self.cache.get("k1")   # hit
        await self.cache.get("k1")   # hit
        await self.cache.get("missing")  # miss
        assert self.cache.stats.hit_rate == pytest.approx(66.666, rel=0.01)

    async def test_update_avg_access_time_first_call_sets_directly(self):
        self.cache._update_avg_access_time(5.0)
        assert self.cache.stats.avg_access_time_ms == 5.0

    async def test_update_avg_access_time_ema(self):
        self.cache._update_avg_access_time(10.0)
        self.cache._update_avg_access_time(20.0)
        # EMA: 0.1 * 20 + 0.9 * 10 = 11.0
        assert self.cache.stats.avg_access_time_ms == pytest.approx(11.0, rel=0.01)

    async def test_update_avg_access_time_multiple_steps(self):
        self.cache._update_avg_access_time(100.0)
        self.cache._update_avg_access_time(100.0)
        # Should stay at 100 (alpha doesn't matter when new == old)
        assert self.cache.stats.avg_access_time_ms == pytest.approx(100.0, rel=0.01)

    async def test_delete_cleans_access_patterns(self):
        await self.cache.set("k1", "v1")
        await self.cache.get("k1")
        await self.cache.delete("k1")
        assert "k1" not in self.cache.access_patterns

    async def test_complex_value_stored_and_retrieved(self):
        value = {"nested": {"list": [1, 2, 3]}, "flag": True}
        await self.cache.set("complex", value)
        result = await self.cache.get("complex")
        assert result == value

    async def test_get_stats_returns_stats_object(self):
        stats = await self.cache.get_stats()
        assert isinstance(stats, CacheStats)
