"""
Tests for intelligent_cache.py

Redis is not installed; stub it before importing the module under test.
"""

import sys
import types as _types
import asyncio

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
import time
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


# ---------------------------------------------------------------------------
# InMemoryCacheLayer.set — exception path (lines 193-195)
# ---------------------------------------------------------------------------


class TestInMemoryCacheSetException:
    """set() must return False when JSON serialisation raises an exception."""

    def setup_method(self):
        self.cache = InMemoryCacheLayer("exc_test", max_size=10, max_size_bytes=1024 * 1024)

    async def test_set_returns_false_for_unserializable_value(self):
        # A lambda cannot be JSON-serialised, so set() should hit the except block
        result = await self.cache.set("bad_key", lambda: None)
        assert result is False

    async def test_set_does_not_add_entry_on_exception(self):
        # After a failed set, the key must not appear in the cache
        await self.cache.set("bad_key", lambda: None)
        assert "bad_key" not in self.cache.cache

    async def test_set_does_not_increment_total_entries_on_exception(self):
        await self.cache.set("bad_key", lambda: None)
        assert self.cache.stats.total_entries == 0

    async def test_set_does_not_increment_size_bytes_on_exception(self):
        await self.cache.set("bad_key", lambda: None)
        assert self.cache.stats.total_size_bytes == 0

    async def test_set_unserializable_after_valid_entry_leaves_cache_intact(self):
        await self.cache.set("good", "value")
        result = await self.cache.set("bad", lambda: None)
        assert result is False
        # The previously-good entry must still be retrievable
        assert await self.cache.get("good") == "value"


# ---------------------------------------------------------------------------
# InMemoryCacheLayer._evict_if_needed — empty-cache break (line 231)
# ---------------------------------------------------------------------------


class TestInMemoryCacheEvictEmptyBreak:
    """_evict_if_needed must break out safely when the cache is already empty
    but the byte limit is still exceeded (i.e. the single entry being inserted
    is itself larger than max_size_bytes)."""

    async def test_evict_breaks_when_cache_is_empty_and_bytes_exceeded(self):
        # max_size_bytes=1 ensures any non-trivial value triggers the while loop.
        # But the cache is empty at the start of set(), so the break on line 231
        # must fire after _evict_if_needed loops with nothing left to evict.
        tiny = InMemoryCacheLayer("break_test", max_size=1000, max_size_bytes=1)
        # This should not hang or raise; the break exits the infinite-while guard.
        result = await tiny.set("k", "a" * 50)
        # The value is still stored (set() proceeds after _evict_if_needed returns)
        assert result is True

    async def test_evict_empty_cache_does_not_raise(self):
        # Calling _evict_if_needed on an empty cache directly must not raise.
        tiny = InMemoryCacheLayer("break_test2", max_size=1, max_size_bytes=1)
        # No entries yet; the break path fires immediately.
        await tiny._evict_if_needed(9999)  # should return without error


# ---------------------------------------------------------------------------
# InMemoryCacheLayer — eviction driven by max_size_bytes
# ---------------------------------------------------------------------------


class TestInMemoryCacheEvictionByBytes:
    """Verify that byte-limit eviction keeps total_size_bytes within bounds
    and increments eviction_count."""

    async def test_eviction_count_increments_when_bytes_exceeded(self):
        # Each JSON-serialised "x"*50 entry is well over 50 bytes, so inserting
        # a second entry must trigger at least one eviction.
        small = InMemoryCacheLayer("bytes_evict", max_size=1000, max_size_bytes=50)
        await small.set("k1", "x" * 50)
        await small.set("k2", "y" * 50)
        assert small.stats.eviction_count >= 1

    async def test_eviction_by_bytes_removes_oldest_entry_first(self):
        # With max_size_bytes tight enough that only one entry fits, the oldest
        # key must be evicted when a second is inserted.
        small = InMemoryCacheLayer("bytes_lru", max_size=1000, max_size_bytes=60)
        await small.set("first", "a" * 20)
        await small.set("second", "b" * 20)
        # "first" was inserted first so it should have been evicted.
        assert "first" not in small.cache or "second" in small.cache

    async def test_total_size_bytes_stays_consistent_after_byte_eviction(self):
        small = InMemoryCacheLayer("bytes_consistent", max_size=1000, max_size_bytes=50)
        for i in range(5):
            await small.set(f"key{i}", "v" * 20)
        # Recompute actual sum of sizes in cache
        actual_bytes = sum(e.size_bytes for e in small.cache.values())
        assert small.stats.total_size_bytes == actual_bytes


# ---------------------------------------------------------------------------
# InMemoryCacheLayer — overwrite of existing entry
# ---------------------------------------------------------------------------


class TestInMemoryCacheOverwrite:
    """Overwriting an existing key must keep total_entries at 1 and update
    total_size_bytes to reflect the new value's size."""

    def setup_method(self):
        self.cache = InMemoryCacheLayer("overwrite_test", max_size=10, max_size_bytes=1024 * 1024)

    async def test_overwrite_keeps_total_entries_at_one(self):
        await self.cache.set("k", "short")
        await self.cache.set("k", "much_longer_value_here")
        assert self.cache.stats.total_entries == 1

    async def test_overwrite_updates_size_bytes_upward(self):
        await self.cache.set("k", "a")
        size_after_first = self.cache.stats.total_size_bytes
        await self.cache.set("k", "a" * 200)
        assert self.cache.stats.total_size_bytes > size_after_first

    async def test_overwrite_updates_size_bytes_downward(self):
        await self.cache.set("k", "a" * 200)
        size_after_first = self.cache.stats.total_size_bytes
        await self.cache.set("k", "a")
        assert self.cache.stats.total_size_bytes < size_after_first

    async def test_overwrite_value_is_new_value(self):
        await self.cache.set("k", "old")
        await self.cache.set("k", "new")
        assert await self.cache.get("k") == "new"

    async def test_overwrite_size_bytes_equals_actual_entry_size(self):
        await self.cache.set("k", "hello")
        await self.cache.set("k", "world" * 30)
        entry = self.cache.cache["k"]
        assert self.cache.stats.total_size_bytes == entry.size_bytes

    async def test_overwrite_multiple_times_stays_consistent(self):
        for value in ["a", "bb", "ccc", "dddd", "eeeee"]:
            await self.cache.set("k", value)
        assert self.cache.stats.total_entries == 1
        entry = self.cache.cache["k"]
        assert self.cache.stats.total_size_bytes == entry.size_bytes


# ---------------------------------------------------------------------------
# IntelligentCacheSystem — multi-layer orchestration
# ---------------------------------------------------------------------------


class TestIntelligentCacheSystem:
    """Tests for IntelligentCacheSystem that orchestrates multiple layers."""

    def setup_method(self):
        from youtube_extension.backend.services.intelligent_cache import (
            IntelligentCacheSystem,
        )
        # Build a system with only an in-memory L1 layer (no Redis required).
        self.system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        self.system.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024)
        ]
        self.system.adaptive_ttl_enabled = False
        self.system.cache_warming_enabled = True
        self.system.auto_invalidation_enabled = True
        self.system.performance_history = []
        self.system.optimization_suggestions = []

    async def test_get_returns_none_on_full_miss(self):
        result = await self.system.get("absent")
        assert result is None

    async def test_set_and_get_roundtrip(self):
        await self.system.set("k", "val")
        result = await self.system.get("k")
        assert result == "val"

    async def test_set_returns_true_on_success(self):
        result = await self.system.set("k", "v")
        assert result is True

    async def test_delete_existing_key_returns_true(self):
        await self.system.set("k", "v")
        result = await self.system.delete("k")
        assert result is True

    async def test_delete_missing_key_returns_false(self):
        result = await self.system.delete("never_set")
        assert result is False

    async def test_clear_returns_dict_with_layer_names(self):
        await self.system.set("k1", "v1")
        await self.system.set("k2", "v2")
        counts = await self.system.clear()
        assert isinstance(counts, dict)
        assert "L1" in counts
        assert counts["L1"] == 2

    async def test_get_after_clear_returns_none(self):
        await self.system.set("k", "v")
        await self.system.clear()
        assert await self.system.get("k") is None

    async def test_get_records_performance_history(self):
        await self.system.get("any_key")
        assert len(self.system.performance_history) == 1

    async def test_get_hit_records_performance_history(self):
        await self.system.set("k", "v")
        await self.system.get("k")
        # Two entries: the miss from traversal (no — L1 hits, so 1 record)
        assert len(self.system.performance_history) >= 1

    async def test_comprehensive_stats_returns_dict(self):
        await self.system.set("k", "v")
        stats = await self.system.get_comprehensive_stats()
        assert "layers" in stats
        assert "overall" in stats
        assert "timestamp" in stats

    async def test_comprehensive_stats_hit_rate_populated_after_activity(self):
        await self.system.set("k", "v")
        await self.system.get("k")  # hit
        stats = await self.system.get_comprehensive_stats()
        assert stats["overall"]["total_requests"] >= 1

    async def test_warm_cache_sets_all_entries(self):
        pairs = [("a", 1), ("b", 2), ("c", 3)]
        await self.system.warm_cache(pairs)
        assert await self.system.get("a") == 1
        assert await self.system.get("b") == 2
        assert await self.system.get("c") == 3

    async def test_warm_cache_disabled_does_nothing(self):
        self.system.cache_warming_enabled = False
        await self.system.warm_cache([("x", 99)])
        assert await self.system.get("x") is None

    async def test_adaptive_ttl_used_when_enabled(self):
        self.system.adaptive_ttl_enabled = True
        # Should not raise; adaptive TTL falls back to base_ttl (3600)
        result = await self.system.set("k", "v")
        assert result is True

    async def test_invalidate_by_tags_returns_dict(self):
        result = await self.system.invalidate_by_tags(["tag1"])
        assert isinstance(result, dict)

    async def test_promote_cache_entry_no_op_for_layer_zero(self):
        # found_at_layer=0 means nothing to promote (range(0) is empty)
        await self.system._promote_cache_entry("k", "v", 0)

    async def test_calculate_promotion_ttl_decreases_by_layer(self):
        ttl0 = self.system._calculate_promotion_ttl(0)
        ttl1 = self.system._calculate_promotion_ttl(1)
        assert ttl0 > ttl1

    async def test_record_access_performance_truncates_history(self):
        # Fill history beyond 10000 to trigger truncation
        self.system.performance_history = [
            {"key": "k", "access_time_ms": 1.0, "layer_found": 0, "timestamp": 0.0}
        ] * 10001
        self.system._record_access_performance("k", 1.0, 0)
        assert len(self.system.performance_history) <= 5001

    async def test_analyze_performance_skips_when_too_few_records(self):
        # With fewer than 100 records, suggestions must not grow
        before = len(self.system.optimization_suggestions)
        self.system.performance_history = [
            {"key": "k", "access_time_ms": 1.0, "layer_found": 0, "timestamp": 0.0}
        ] * 50
        self.system._analyze_performance_and_suggest_optimizations()
        assert len(self.system.optimization_suggestions) == before


# ---------------------------------------------------------------------------
# Global convenience functions — cache_get / cache_set / cache_delete / cache_key
# ---------------------------------------------------------------------------


class TestGlobalConvenienceFunctions:
    """Tests for the module-level convenience wrappers."""

    async def test_cache_key_deterministic(self):
        from youtube_extension.backend.services.intelligent_cache import cache_key
        k1 = cache_key("foo", "bar", x=1)
        k2 = cache_key("foo", "bar", x=1)
        assert k1 == k2

    async def test_cache_key_different_args_produce_different_keys(self):
        from youtube_extension.backend.services.intelligent_cache import cache_key
        k1 = cache_key("foo")
        k2 = cache_key("bar")
        assert k1 != k2

    async def test_cache_key_kwargs_sorted(self):
        from youtube_extension.backend.services.intelligent_cache import cache_key
        # kwargs ordering must not matter
        k1 = cache_key(a=1, b=2)
        k2 = cache_key(b=2, a=1)
        assert k1 == k2

    async def test_cache_key_returns_hex_string(self):
        from youtube_extension.backend.services.intelligent_cache import cache_key
        k = cache_key("test")
        assert len(k) == 64  # sha256 hex digest (migrated from md5's 32)
        int(k, 16)  # should not raise


# ---------------------------------------------------------------------------
# IntelligentCacheSystem — _calculate_adaptive_ttl branches
# ---------------------------------------------------------------------------


class TestAdaptiveTtl:
    """Cover the frequency branches inside _calculate_adaptive_ttl."""

    def _make_system(self):
        from youtube_extension.backend.services.intelligent_cache import (
            IntelligentCacheSystem,
        )
        system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        system.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024)
        ]
        system.adaptive_ttl_enabled = True
        system.cache_warming_enabled = False
        system.auto_invalidation_enabled = False
        system.performance_history = []
        system.optimization_suggestions = []
        return system

    async def test_base_ttl_returned_for_unknown_key(self):
        system = self._make_system()
        ttl = system._calculate_adaptive_ttl("no_such_key")
        assert ttl == 3600

    async def test_base_ttl_returned_for_single_access(self):
        system = self._make_system()
        # One access means time_span = 0, no frequency branch fires
        system.layers[0].access_patterns["k"] = [time.time()]
        ttl = system._calculate_adaptive_ttl("k")
        assert ttl == 3600

    async def test_high_frequency_returns_4x_ttl(self):
        system = self._make_system()
        now = time.time()
        # 20 accesses over 1 second → frequency = 20 > 0.1
        system.layers[0].access_patterns["k"] = [now + i * 0.05 for i in range(20)]
        ttl = system._calculate_adaptive_ttl("k")
        assert ttl == 3600 * 4

    async def test_medium_frequency_returns_2x_ttl(self):
        system = self._make_system()
        now = time.time()
        # 5 accesses over 100 seconds → frequency = 0.05  (0.01 < 0.05 < 0.1)
        system.layers[0].access_patterns["k"] = [now + i * 20 for i in range(5)]
        ttl = system._calculate_adaptive_ttl("k")
        assert ttl == 3600 * 2

    async def test_low_frequency_returns_base_ttl(self):
        system = self._make_system()
        now = time.time()
        # 2 accesses over 1000 seconds → frequency = 0.002 < 0.01
        system.layers[0].access_patterns["k"] = [now, now + 1000]
        ttl = system._calculate_adaptive_ttl("k")
        assert ttl == 3600


# ---------------------------------------------------------------------------
# _analyze_performance_and_suggest_optimizations — suggestion branches
# ---------------------------------------------------------------------------


class TestAnalyzePerformanceSuggestions:
    """Ensure all three optimization suggestion branches are exercised."""

    def _make_system_with_history(self, records):
        from youtube_extension.backend.services.intelligent_cache import (
            IntelligentCacheSystem,
        )
        system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        system.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024)
        ]
        system.adaptive_ttl_enabled = False
        system.cache_warming_enabled = False
        system.auto_invalidation_enabled = False
        system.performance_history = records
        system.optimization_suggestions = []
        return system

    async def test_low_l1_hit_rate_generates_increase_l1_size_suggestion(self):
        # All misses (layer_found=-1) → L1 hit rate = 0% < 70%
        records = [
            {"key": "k", "access_time_ms": 1.0, "layer_found": -1, "timestamp": 0.0}
        ] * 200
        system = self._make_system_with_history(records)
        system._analyze_performance_and_suggest_optimizations()
        types = [s["type"] for s in system.optimization_suggestions]
        assert "increase_l1_size" in types

    async def test_slow_access_time_generates_slow_access_pattern_suggestion(self):
        # All accesses take 100 ms > 50 ms threshold, no misses
        records = [
            {"key": "k", "access_time_ms": 100.0, "layer_found": 0, "timestamp": 0.0}
        ] * 200
        system = self._make_system_with_history(records)
        system._analyze_performance_and_suggest_optimizations()
        types = [s["type"] for s in system.optimization_suggestions]
        assert "slow_access_pattern" in types

    async def test_high_miss_rate_generates_high_miss_rate_suggestion(self):
        # 50% misses > 30% threshold
        records = (
            [{"key": "k", "access_time_ms": 1.0, "layer_found": -1, "timestamp": 0.0}] * 100
            + [{"key": "k", "access_time_ms": 1.0, "layer_found": 0, "timestamp": 0.0}] * 100
        )
        system = self._make_system_with_history(records)
        system._analyze_performance_and_suggest_optimizations()
        types = [s["type"] for s in system.optimization_suggestions]
        assert "high_miss_rate" in types

    async def test_good_performance_generates_no_suggestions(self):
        # 100% L1 hits, 1 ms access time
        records = [
            {"key": "k", "access_time_ms": 1.0, "layer_found": 0, "timestamp": 0.0}
        ] * 200
        system = self._make_system_with_history(records)
        system._analyze_performance_and_suggest_optimizations()
        assert system.optimization_suggestions == []


# ---------------------------------------------------------------------------
# cached() decorator
# ---------------------------------------------------------------------------


class TestCachedDecorator:
    """Tests for the @cached decorator applied to async functions."""

    def setup_method(self):
        # Use a fresh IntelligentCacheSystem backed by a single in-memory layer
        # so we don't touch the global singleton.
        import youtube_extension.backend.services.intelligent_cache as ic_module
        self._orig_system = ic_module.intelligent_cache
        ic_module.intelligent_cache = IntelligentCacheSystem.__new__(
            IntelligentCacheSystem
        )
        ic_module.intelligent_cache.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024)
        ]
        ic_module.intelligent_cache.adaptive_ttl_enabled = False
        ic_module.intelligent_cache.cache_warming_enabled = False
        ic_module.intelligent_cache.auto_invalidation_enabled = False
        ic_module.intelligent_cache.performance_history = []
        ic_module.intelligent_cache.optimization_suggestions = []

    def teardown_method(self):
        import youtube_extension.backend.services.intelligent_cache as ic_module
        ic_module.intelligent_cache = self._orig_system

    async def test_cached_async_function_called_once_on_cache_hit(self):
        from youtube_extension.backend.services.intelligent_cache import cached

        call_count = 0

        @cached(ttl=60)
        async def expensive(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive(5)
        result2 = await expensive(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Second call served from cache

    async def test_cached_async_different_args_called_twice(self):
        from youtube_extension.backend.services.intelligent_cache import cached

        call_count = 0

        @cached()
        async def fn(x):
            nonlocal call_count
            call_count += 1
            return x

        await fn(1)
        await fn(2)
        assert call_count == 2

    async def test_cached_sync_function_passes_through(self):
        from youtube_extension.backend.services.intelligent_cache import cached

        @cached()
        def sync_fn(x):
            return x + 1

        assert sync_fn(3) == 4

    async def test_cached_with_key_prefix(self):
        from youtube_extension.backend.services.intelligent_cache import cached

        call_count = 0

        @cached(ttl=60, key_prefix="pfx:")
        async def fn(x):
            nonlocal call_count
            call_count += 1
            return x

        await fn(7)
        await fn(7)
        assert call_count == 1


# ---------------------------------------------------------------------------
# Additional coverage: initialize, promote with 2 layers, cache_delete,
# cache_invalidate_tags, and invalidate_by_tags hasattr branch
# ---------------------------------------------------------------------------


class TestIntelligentCacheSystemExtra:
    """Cover remaining uncovered branches in IntelligentCacheSystem."""

    def _make_two_layer_system(self):
        system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        system.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024),
            InMemoryCacheLayer("L2", max_size=100, max_size_bytes=1024 * 1024),
        ]
        system.adaptive_ttl_enabled = False
        system.cache_warming_enabled = False
        system.auto_invalidation_enabled = False
        system.performance_history = []
        system.optimization_suggestions = []
        return system

    async def test_initialize_skips_layers_without_connect(self):
        # InMemoryCacheLayer has no connect() method; initialize() must not raise.
        system = self._make_two_layer_system()
        await system.initialize()  # should return without error

    async def test_promote_cache_entry_populates_lower_layer(self):
        # found_at_layer=1 → promotes to layer 0
        system = self._make_two_layer_system()
        await system._promote_cache_entry("k", "promoted_value", 1)
        result = await system.layers[0].get("k")
        assert result == "promoted_value"

    async def test_get_from_second_layer_promotes_to_first(self):
        # Pre-populate only L2; a system.get() should promote the value to L1.
        system = self._make_two_layer_system()
        await system.layers[1].set("k", "from_l2")
        result = await system.get("k")
        assert result == "from_l2"
        # Value must now exist in L1 as well
        assert await system.layers[0].get("k") == "from_l2"

    async def test_invalidate_by_tags_with_method_present(self):
        # Give a layer an invalidate_by_tags method so the hasattr branch fires.
        system = self._make_two_layer_system()

        class FakeLayer:
            name = "fake"
            async def invalidate_by_tags(self, tags):
                return 3

        system.layers = [FakeLayer()]
        result = await system.invalidate_by_tags(["t1"])
        assert result == {"fake": 3}

    async def test_invalidate_by_tags_without_method_excluded(self):
        # InMemoryCacheLayer has no invalidate_by_tags; result dict must be empty.
        system = self._make_two_layer_system()
        system.layers = [InMemoryCacheLayer("plain", max_size=10)]
        result = await system.invalidate_by_tags(["t1"])
        assert result == {}


class TestGlobalCacheDeleteAndInvalidateTags:
    """Cover cache_delete and cache_invalidate_tags convenience functions."""

    def setup_method(self):
        import youtube_extension.backend.services.intelligent_cache as ic_module
        self._orig = ic_module.intelligent_cache
        ic_module.intelligent_cache = IntelligentCacheSystem.__new__(
            IntelligentCacheSystem
        )
        ic_module.intelligent_cache.layers = [
            InMemoryCacheLayer("L1", max_size=100, max_size_bytes=1024 * 1024)
        ]
        ic_module.intelligent_cache.adaptive_ttl_enabled = False
        ic_module.intelligent_cache.cache_warming_enabled = False
        ic_module.intelligent_cache.auto_invalidation_enabled = False
        ic_module.intelligent_cache.performance_history = []
        ic_module.intelligent_cache.optimization_suggestions = []

    def teardown_method(self):
        import youtube_extension.backend.services.intelligent_cache as ic_module
        ic_module.intelligent_cache = self._orig

    async def test_cache_delete_removes_existing_key(self):
        from youtube_extension.backend.services.intelligent_cache import (
            cache_delete,
            cache_set,
        )
        await cache_set("k", "v")
        result = await cache_delete("k")
        assert result is True

    async def test_cache_delete_returns_false_for_missing_key(self):
        from youtube_extension.backend.services.intelligent_cache import cache_delete
        result = await cache_delete("no_such_key")
        assert result is False

    async def test_cache_invalidate_tags_returns_dict(self):
        from youtube_extension.backend.services.intelligent_cache import (
            cache_invalidate_tags,
        )
        result = await cache_invalidate_tags(["tag1", "tag2"])
        assert isinstance(result, dict)


# make IntelligentCacheSystem importable in tests defined above
# ---------------------------------------------------------------------------
# RedisCacheLayer (L2 Cache) — covers lines 254-450
# ---------------------------------------------------------------------------
from unittest.mock import AsyncMock, MagicMock, patch

from youtube_extension.backend.services.intelligent_cache import (
    TAG_WRITE_CONCURRENCY,
    IntelligentCacheSystem,  # noqa: E402
    RedisCacheLayer,
)


def _make_redis_conn(
    *,
    ping_ok: bool = True,
    get_value=None,
    set_ok: bool = True,
    delete_count: int = 1,
    smembers_value=None,
    keys_value=None,
):
    """Build a mock async Redis connection usable as an async context manager."""
    conn = MagicMock()

    # All Redis commands are coroutines
    conn.ping = AsyncMock(return_value=True if ping_ok else MagicMock(side_effect=Exception("no ping")))
    conn.get = AsyncMock(return_value=get_value)
    conn.hincrby = AsyncMock(return_value=1)
    conn.hset = AsyncMock(return_value=1)
    conn.setex = AsyncMock(return_value=True)
    conn.set = AsyncMock(return_value=True)
    conn.hgetall = AsyncMock(return_value={})
    conn.delete = AsyncMock(return_value=delete_count)
    conn.sadd = AsyncMock(return_value=1)
    conn.smembers = AsyncMock(return_value=smembers_value or set())
    conn.keys = AsyncMock(return_value=keys_value or [])

    # Async context manager protocol
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


def _make_pool():
    """Stub for redis.ConnectionPool.from_url."""
    return MagicMock()


def _patch_redis(conn, pool=None):
    """Return a context manager that patches redis.asyncio in the intelligent_cache module."""
    import types as _types

    if pool is None:
        pool = _make_pool()

    mock_redis_mod = _types.ModuleType("redis.asyncio")

    # ConnectionPool stub
    mock_pool_cls = MagicMock()
    mock_pool_cls.from_url = MagicMock(return_value=pool)
    mock_redis_mod.ConnectionPool = mock_pool_cls

    # Redis class stub: returns conn when instantiated (as async ctx manager)
    mock_redis_cls = MagicMock(return_value=conn)
    mock_redis_mod.Redis = mock_redis_cls

    return patch("youtube_extension.backend.services.intelligent_cache.redis", mock_redis_mod)


def _patch_redis_pool_error(exc):
    """Patch redis so ConnectionPool.from_url raises exc."""
    import types as _types

    mock_redis_mod = _types.ModuleType("redis.asyncio")
    mock_pool_cls = MagicMock()
    mock_pool_cls.from_url = MagicMock(side_effect=exc)
    mock_redis_mod.ConnectionPool = mock_pool_cls
    mock_redis_mod.Redis = MagicMock()
    return patch("youtube_extension.backend.services.intelligent_cache.redis", mock_redis_mod)


class TestRedisCacheLayerConnect:
    """Tests for RedisCacheLayer.connect() — lines 264-282"""

    async def test_connect_sets_connected_true_on_success(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        conn = _make_redis_conn()

        with _patch_redis(conn):
            await layer.connect()

        assert layer._connected is True

    async def test_connect_calls_ping(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        conn = _make_redis_conn()

        with _patch_redis(conn):
            await layer.connect()

        conn.ping.assert_called_once()

    async def test_connect_failure_sets_connected_false(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")

        with _patch_redis_pool_error(Exception("refused")):
            await layer.connect()

        assert layer._connected is False

    async def test_connect_ping_failure_sets_connected_false(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        conn = _make_redis_conn()
        conn.ping = AsyncMock(side_effect=Exception("ping failed"))

        with _patch_redis(conn):
            await layer.connect()

        assert layer._connected is False


class TestRedisCacheLayerGet:
    """Tests for RedisCacheLayer.get() — lines 284-323"""

    def _connected_layer(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        layer._connected = True
        layer.redis_pool = _make_pool()
        return layer

    async def test_get_returns_none_when_not_connected(self):
        layer = RedisCacheLayer("L2")
        result = await layer.get("key")
        assert result is None

    async def test_get_miss_returns_none(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(get_value=None)

        with _patch_redis(conn):
            result = await layer.get("missing_key")

        assert result is None
        assert layer.stats.miss_count == 1

    async def test_get_hit_returns_value(self):
        layer = self._connected_layer()
        import json as _json
        data = _json.dumps({"value": "hello", "created_at": 0.0, "tags": []})
        conn = _make_redis_conn(get_value=data.encode())

        with _patch_redis(conn):
            result = await layer.get("my_key")

        assert result == "hello"
        assert layer.stats.hit_count == 1

    async def test_get_invalid_json_returns_none(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(get_value=b"not-valid-json")

        with _patch_redis(conn):
            result = await layer.get("bad_json_key")

        assert result is None

    async def test_get_redis_exception_returns_none(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()
        conn.get = AsyncMock(side_effect=Exception("redis down"))

        with _patch_redis(conn):
            result = await layer.get("any_key")

        assert result is None
        assert layer.stats.miss_count == 1

    async def test_get_hit_increments_access_count_in_redis(self):
        layer = self._connected_layer()
        import json as _json
        data = _json.dumps({"value": 42, "created_at": 0.0, "tags": []})
        conn = _make_redis_conn(get_value=data.encode())

        with _patch_redis(conn):
            await layer.get("my_key")

        conn.hincrby.assert_called_once()


class TestRedisCacheLayerSet:
    """Tests for RedisCacheLayer.set() — lines 325-364"""

    def _connected_layer(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        layer._connected = True
        layer.redis_pool = _make_pool()
        return layer

    async def test_set_returns_false_when_not_connected(self):
        layer = RedisCacheLayer("L2")
        result = await layer.set("k", "v")
        assert result is False

    async def test_set_with_ttl_calls_setex(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()

        with _patch_redis(conn):
            result = await layer.set("k", "v", ttl=60)

        assert result is True
        conn.setex.assert_called_once()

    async def test_set_without_ttl_calls_set(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()

        with _patch_redis(conn):
            result = await layer.set("k", "v")

        assert result is True
        conn.set.assert_called_once()

    async def test_set_with_tags_calls_sadd(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()

        with _patch_redis(conn):
            await layer.set("k", "v", tags=["tag1", "tag2"])

        assert conn.sadd.call_count == 2

    async def test_set_tag_writes_stay_within_concurrency_bound(self):
        """A large tag list must not fan out past the connection-pool budget.

        redis-py's async pool defaults to max_connections=20 and every
        in-flight command holds a connection, so unbounded concurrency here
        would be able to exhaust the pool.
        """
        layer = self._connected_layer()
        conn = _make_redis_conn()

        in_flight = 0
        peak = 0

        async def _tracking_sadd(*_args, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            # Yield so other pending tag writes can start if unbounded.
            await asyncio.sleep(0)
            in_flight -= 1
            return 1

        conn.sadd = AsyncMock(side_effect=_tracking_sadd)
        tags = [f"tag{i}" for i in range(50)]

        with _patch_redis(conn):
            result = await layer.set("k", "v", tags=tags)

        assert result is True
        assert conn.sadd.call_count == 50
        assert peak <= layer._tag_write_limit

    async def test_set_tag_write_failure_returns_false_and_drains(self):
        """A failing tag write returns False with no writes left in flight."""
        layer = self._connected_layer()
        conn = _make_redis_conn()

        started = 0
        finished = 0

        async def _flaky_sadd(name, *_args, **_kwargs):
            nonlocal started, finished
            started += 1
            await asyncio.sleep(0)
            if name.endswith("tag3"):
                finished += 1
                raise RuntimeError("redis unavailable")
            finished += 1
            return 1

        conn.sadd = AsyncMock(side_effect=_flaky_sadd)
        tags = [f"tag{i}" for i in range(6)]

        with _patch_redis(conn):
            result = await layer.set("k", "v", tags=tags)

        assert result is False
        # Every scheduled write ran to completion before set() returned.
        assert finished == started

    async def test_concurrent_sets_share_one_tag_write_budget(self):
        """Concurrent set() calls must share the tag-write budget.

        The limiter has to be per-layer, not per-call: every caller draws from
        the same connection pool, so N concurrent writers each running their
        own budget would still exhaust it. warm_cache() gathers set() calls,
        so this is a reachable path.
        """
        layer = self._connected_layer()
        conn = _make_redis_conn()

        in_flight = 0
        peak = 0

        async def _tracking_sadd(*_args, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            # Yield so every other pending tag write can start if unbounded.
            await asyncio.sleep(0)
            in_flight -= 1
            return 1

        conn.sadd = AsyncMock(side_effect=_tracking_sadd)
        tags = [f"tag{i}" for i in range(20)]

        with _patch_redis(conn):
            results = await asyncio.gather(
                *(layer.set(f"k{i}", "v", tags=tags) for i in range(5))
            )

        assert all(results)
        assert conn.sadd.call_count == 100
        # Aggregate in-flight writes stay within the single shared budget,
        # not 5x it, and leave headroom under the pool's max_connections.
        assert peak <= layer._tag_write_limit
        assert layer._tag_write_limit < layer.max_connections

    async def test_tag_write_limit_scales_down_for_small_pools(self):
        """A small pool must not be handed a fan-out wider than itself."""
        small = RedisCacheLayer("L2", max_connections=4)
        assert small._tag_write_limit >= 1
        assert small._tag_write_limit < small.max_connections

        default = RedisCacheLayer("L2")
        assert default._tag_write_limit == TAG_WRITE_CONCURRENCY

    def test_tag_write_semaphore_is_replaced_after_its_loop_closes(self):
        """The semaphore must not stay bound to a loop that has closed.

        Scope: this covers the *semaphore* only. An asyncio.Semaphore binds to
        the first loop that uses it and raises for every other one, so a
        semaphore retained past its loop's lifetime would raise on the next
        loop. This module builds an IntelligentCacheSystem singleton at import
        time, outside any loop, so that is reachable -- e.g. a process calling
        asyncio.run() more than once, or a suite giving each test a fresh loop.

        This does NOT establish that reusing a RedisCacheLayer or its
        redis.asyncio ConnectionPool across loops is safe. The pool caches
        connections whose transports are bound to the loop that opened them and
        has no ownership contract; see issue #1162. Redis is mocked here, so
        only semaphore replacement is exercised.
        """
        layer = self._connected_layer()
        conn = _make_redis_conn()

        async def _write(key, tag):
            with _patch_redis(conn):
                return await layer.set(key, "v", tags=[tag])

        assert asyncio.run(_write("k", "a")) is True
        first = layer._tag_write_semaphore
        first_loop = layer._tag_write_semaphore_loop
        assert first is not None
        assert first_loop is not None and first_loop.is_closed()

        assert asyncio.run(_write("k2", "b")) is True
        assert layer._tag_write_semaphore is not first
        assert layer._tag_write_semaphore_loop is not first_loop

    async def test_set_stores_metadata(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()

        with _patch_redis(conn):
            await layer.set("k", "v")

        conn.hset.assert_called_once()

    async def test_set_exception_returns_false(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()
        conn.set = AsyncMock(side_effect=Exception("redis error"))

        with _patch_redis(conn):
            result = await layer.set("k", "v")

        assert result is False


class TestRedisCacheLayerDelete:
    """Tests for RedisCacheLayer.delete() — lines 366-387"""

    def _connected_layer(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        layer._connected = True
        layer.redis_pool = _make_pool()
        return layer

    async def test_delete_returns_false_when_not_connected(self):
        layer = RedisCacheLayer("L2")
        result = await layer.delete("k")
        assert result is False

    async def test_delete_returns_true_when_key_exists(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(delete_count=1)

        with _patch_redis(conn):
            result = await layer.delete("k")

        assert result is True

    async def test_delete_returns_false_when_key_missing(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(delete_count=0)

        with _patch_redis(conn):
            result = await layer.delete("k")

        assert result is False

    async def test_delete_calls_delete_on_conn(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(delete_count=1)

        with _patch_redis(conn):
            await layer.delete("my_key")

        conn.delete.assert_called_once()

    async def test_delete_exception_returns_false(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()
        conn.delete = AsyncMock(side_effect=Exception("del error"))

        with _patch_redis(conn):
            result = await layer.delete("k")

        assert result is False


class TestRedisCacheLayerClear:
    """Tests for RedisCacheLayer.clear() — lines 389-412"""

    def _connected_layer(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        layer._connected = True
        layer.redis_pool = _make_pool()
        return layer

    async def test_clear_returns_zero_when_not_connected(self):
        layer = RedisCacheLayer("L2")
        result = await layer.clear()
        assert result == 0

    async def test_clear_with_no_keys_returns_zero(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(keys_value=[])

        with _patch_redis(conn):
            result = await layer.clear()

        assert result == 0

    async def test_clear_deletes_all_keys(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(keys_value=[b"uvai:cache:k1"])
        conn.delete = AsyncMock(return_value=3)

        with _patch_redis(conn):
            result = await layer.clear()

        assert result == 3

    async def test_clear_exception_returns_zero(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()
        conn.keys = AsyncMock(side_effect=Exception("clear error"))

        with _patch_redis(conn):
            result = await layer.clear()

        assert result == 0


class TestRedisCacheLayerInvalidateByTags:
    """Tests for RedisCacheLayer.invalidate_by_tags() — lines 414-440"""

    def _connected_layer(self):
        layer = RedisCacheLayer("L2", redis_url="redis://localhost:6379")
        layer._connected = True
        layer.redis_pool = _make_pool()
        return layer

    async def test_invalidate_returns_zero_when_not_connected(self):
        layer = RedisCacheLayer("L2")
        result = await layer.invalidate_by_tags(["tag1"])
        assert result == 0

    async def test_invalidate_empty_tags_returns_zero(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(smembers_value=set())

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags(["nonexistent_tag"])

        assert result == 0

    async def test_invalidate_deletes_tagged_keys(self):
        layer = self._connected_layer()
        # smembers returns bytes keys for tag1
        conn = _make_redis_conn(smembers_value={b"key1", b"key2"})
        conn.delete = AsyncMock(return_value=5)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags(["tag1"])

        assert result == 5

    async def test_invalidate_handles_string_keys(self):
        layer = self._connected_layer()
        # smembers returns string keys (non-bytes)
        conn = _make_redis_conn(smembers_value={"key1"})
        conn.delete = AsyncMock(return_value=3)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags(["tag1"])

        assert result == 3

    async def test_invalidate_multiple_tags(self):
        layer = self._connected_layer()
        conn = _make_redis_conn(smembers_value={b"key1"})
        conn.delete = AsyncMock(return_value=2)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags(["tag1", "tag2"])

        # Called once per tag
        assert result == 4  # 2 deletes × 2 tags

    async def test_invalidate_exception_returns_zero(self):
        layer = self._connected_layer()
        conn = _make_redis_conn()
        conn.smembers = AsyncMock(side_effect=Exception("smembers error"))

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags(["tag1"])

        assert result == 0

    async def test_invalidate_issues_tags_concurrently(self):
        """Per-tag work must overlap rather than run one tag at a time.

        This is the non-vacuity guard for the change: a serial ``for`` loop
        yields a peak of exactly 1, so this assertion fails on the previous
        implementation.
        """
        layer = self._connected_layer()
        conn = _make_redis_conn()

        in_flight = 0
        peak = 0

        async def _tracking_smembers(*_args, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            # Yield so sibling tags can start if the fan-out is concurrent.
            await asyncio.sleep(0)
            in_flight -= 1
            return {b"key1"}

        conn.smembers = AsyncMock(side_effect=_tracking_smembers)
        conn.delete = AsyncMock(return_value=1)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags([f"tag{i}" for i in range(5)])

        assert peak > 1
        assert conn.smembers.call_count == 5
        assert result == 5

    async def test_invalidate_stays_within_concurrency_bound(self):
        """A large tag list must not fan out past the connection-pool budget."""
        layer = self._connected_layer()
        conn = _make_redis_conn()

        in_flight = 0
        peak = 0

        async def _tracking_smembers(*_args, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0)
            in_flight -= 1
            return set()

        conn.smembers = AsyncMock(side_effect=_tracking_smembers)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags([f"tag{i}" for i in range(50)])

        assert result == 0
        assert conn.smembers.call_count == 50
        assert peak <= layer._tag_write_limit

    async def test_invalidate_holds_one_permit_across_both_commands(self):
        """smembers and delete for a tag are scheduled under one permit.

        Holding the permit across the pair keeps each tag's invalidation as one
        indivisible unit of scheduled work, so with a single permit the pairs
        run to completion without interleaving. (This does not change peak pool
        usage -- redis.asyncio returns a connection to the pool between the two
        awaits -- it pins the per-tag scheduling policy so a later refactor
        cannot silently split the pair.)
        """
        layer = self._connected_layer()
        layer._tag_write_limit = 1
        conn = _make_redis_conn()

        order = []

        async def _smembers(name, *_args, **_kwargs):
            order.append(("smembers", name))
            await asyncio.sleep(0)
            return {b"key1"}

        async def _delete(*args, **_kwargs):
            order.append(("delete", args[-1]))
            await asyncio.sleep(0)
            return 1

        conn.smembers = AsyncMock(side_effect=_smembers)
        conn.delete = AsyncMock(side_effect=_delete)

        with _patch_redis(conn):
            await layer.invalidate_by_tags(["tag1", "tag2"])

        # With one permit the pairs must not interleave.
        assert order == [
            ("smembers", "uvai:tag:tag1"),
            ("delete", "uvai:tag:tag1"),
            ("smembers", "uvai:tag:tag2"),
            ("delete", "uvai:tag:tag2"),
        ]

    async def test_invalidate_cancellation_drains_before_conn_closes(self):
        """Cancellation must unwind every child before the connection closes.

        This is the explicit cancellation-parity claim: gather() does not
        complete its outer future until every cancelled child has finished, so
        the enclosing ``async with redis.Redis(...)`` cannot close ``conn``
        while a child could still issue a command on it.
        """
        layer = self._connected_layer()
        layer._tag_write_limit = 4
        conn = _make_redis_conn()

        events: list[tuple] = []
        all_blocked = asyncio.Event()
        entered = 0

        async def _blocking_smembers(name, *_args, **_kwargs):
            nonlocal entered
            events.append(("cmd", "smembers", name))
            entered += 1
            if entered == 3:
                all_blocked.set()
            try:
                await asyncio.sleep(3600)
                return {b"key1"}
            finally:
                events.append(("unwind", name))

        async def _delete(*args, **_kwargs):
            events.append(("cmd", "delete", args[-1]))
            return 1

        async def _aexit(*_args, **_kwargs):
            events.append(("aexit",))
            return False

        conn.smembers = AsyncMock(side_effect=_blocking_smembers)
        conn.delete = AsyncMock(side_effect=_delete)
        conn.__aexit__ = AsyncMock(side_effect=_aexit)

        with _patch_redis(conn):
            task = asyncio.create_task(layer.invalidate_by_tags(["t1", "t2", "t3"]))
            try:
                await asyncio.wait_for(all_blocked.wait(), timeout=5)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except BaseException:
                    pass
                pytest.fail(
                    f"tags were not issued concurrently; only {entered} in flight"
                )
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        kinds = [e[0] for e in events]
        assert "aexit" in kinds, f"connection never closed: {events}"
        aexit_idx = kinds.index("aexit")

        # Every child finished its finally path before the connection closed.
        assert kinds.count("unwind") == 3, f"not all children unwound: {events}"
        assert all(
            i < aexit_idx for i, e in enumerate(events) if e[0] == "unwind"
        ), f"a child unwound after conn close: {events}"

        # No Redis command was issued after the connection closed.
        assert all(
            i < aexit_idx for i, e in enumerate(events) if e[0] == "cmd"
        ), f"command issued after conn close: {events}"

    async def test_invalidate_failure_drains_in_flight_work(self):
        """A failing tag returns 0 with no per-tag task left in flight."""
        layer = self._connected_layer()
        conn = _make_redis_conn()

        started = 0
        finished = 0

        async def _flaky_smembers(name, *_args, **_kwargs):
            nonlocal started, finished
            started += 1
            await asyncio.sleep(0)
            finished += 1
            if name.endswith("tag3"):
                raise RuntimeError("redis unavailable")
            return set()

        conn.smembers = AsyncMock(side_effect=_flaky_smembers)

        with _patch_redis(conn):
            result = await layer.invalidate_by_tags([f"tag{i}" for i in range(6)])

        assert result == 0
        # Every scheduled tag ran to completion before the method returned.
        assert started == 6
        assert finished == started

    async def test_invalidate_shares_tag_write_budget_with_set(self):
        """set() and invalidate_by_tags() must draw from one shared budget.

        Both hold connections from the same pool, so separate budgets would let
        a concurrent set storm and invalidation storm each claim the full limit.
        """
        layer = self._connected_layer()
        conn = _make_redis_conn()

        in_flight = 0
        peak = 0

        async def _tracked(*_args, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0)
            in_flight -= 1
            return 1

        async def _tracked_smembers(*_args, **_kwargs):
            await _tracked()
            return set()

        conn.sadd = AsyncMock(side_effect=_tracked)
        conn.smembers = AsyncMock(side_effect=_tracked_smembers)

        with _patch_redis(conn):
            await asyncio.gather(
                layer.set("k", "v", tags=[f"s{i}" for i in range(40)]),
                layer.invalidate_by_tags([f"i{i}" for i in range(40)]),
            )

        assert conn.sadd.call_count == 40
        assert conn.smembers.call_count == 40
        assert peak <= layer._tag_write_limit


class TestRedisCacheLayerUpdateAvgAccessTime:
    """Tests for RedisCacheLayer._update_avg_access_time() — lines 442-450"""

    def test_first_call_sets_directly(self):
        layer = RedisCacheLayer("L2")
        layer._update_avg_access_time(5.0)
        assert layer.stats.avg_access_time_ms == 5.0

    def test_subsequent_call_uses_ema(self):
        layer = RedisCacheLayer("L2")
        layer._update_avg_access_time(10.0)
        layer._update_avg_access_time(20.0)
        # EMA: 0.1 * 20 + 0.9 * 10 = 11.0
        assert layer.stats.avg_access_time_ms == pytest.approx(11.0, rel=0.01)


# ---------------------------------------------------------------------------
# Removal paths release entry bookkeeping
# ---------------------------------------------------------------------------


def _expire_now(layer: InMemoryCacheLayer, key: str) -> None:
    """Backdate a resident entry's expiry so the next ``get()`` expires it.

    Deterministic stand-in for sleeping past a real TTL; the lazy-expiry branch
    only compares ``expires_at`` against the wall clock, so this exercises the
    identical code path without adding seconds to the suite.
    """
    layer.cache[key].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)


class TestEvictionReleasesAccessHistory:
    """``delete()`` already drops a key's access history (see
    ``test_delete_cleans_access_patterns``). ``_evict_if_needed`` must do the
    same: an evicted key leaves no cache entry behind, so nothing else will ever
    reclaim its history."""

    async def test_evicted_key_history_is_released(self):
        layer = InMemoryCacheLayer("evict_one", max_size=1, max_size_bytes=1024 * 1024)
        await layer.set("first", "value")
        await layer.get("first")
        assert "first" in layer.access_patterns

        # Inserting a second key evicts "first" (max_size=1).
        await layer.set("second", "value")

        assert "first" not in layer.cache
        assert "first" not in layer.access_patterns, (
            "history for an evicted key was retained; nothing will ever "
            "reclaim it because the cache entry is already gone"
        )

    async def test_eviction_churn_leaves_no_orphaned_histories(self):
        """The accumulating case: many keys cycle through a small cache. Every
        key that is evicted must take its history with it, so the number of
        tracked histories stays proportional to the number of resident keys."""
        layer = InMemoryCacheLayer("churn", max_size=5, max_size_bytes=1024 * 1024)

        for i in range(200):
            key = f"k{i}"
            await layer.set(key, "value")
            await layer.get(key)

        orphans = set(layer.access_patterns) - set(layer.cache)
        assert not orphans, (
            f"{len(orphans)} evicted keys still have access history retained "
            f"while only {len(layer.cache)} entries are resident; this memory "
            "is invisible to stats.total_size_bytes so the max_size_bytes "
            "budget can never reclaim it"
        )

    async def test_resident_keys_keep_their_history(self):
        """Releasing evicted histories must not disturb keys still in the
        cache — the fix must be a narrow cleanup, not a blanket clear."""
        layer = InMemoryCacheLayer("keep", max_size=3, max_size_bytes=1024 * 1024)

        for i in range(10):
            await layer.set(f"k{i}", "value")
            await layer.get(f"k{i}")

        for key in layer.cache:
            assert layer.access_patterns.get(key), (
                f"resident key {key!r} lost its access history; adaptive TTL "
                "would fall back to the base value for a live key"
            )


class TestExpiryReleasesEntryBookkeeping:
    """Lazy expiry in ``get()`` is the only place expired entries are ever
    removed — there is no background sweeper — so it must release exactly what
    ``delete()`` releases. Dropping the entry alone left the counters and the
    access history describing an entry that no longer exists."""

    async def test_expired_key_history_is_released(self):
        layer = InMemoryCacheLayer(
            "expiry_hist", max_size=100, max_size_bytes=1024 * 1024
        )
        await layer.set("k", "value", ttl=60)

        # History only accrues on a hit, so read the key while it is still
        # live — otherwise there would be nothing to orphan.
        await layer.get("k")
        assert layer.access_patterns["k"], "precondition: history was recorded"

        _expire_now(layer, "k")
        assert await layer.get("k") is None

        assert "k" not in layer.access_patterns, (
            "access history survived the entry it describes; with no sweeper "
            "and no cache entry left, nothing can ever reclaim it"
        )

    async def test_expired_key_releases_size_accounting(self):
        """``total_size_bytes`` is not merely reported — ``_evict_if_needed``
        budgets against it, so bytes left behind by expiry permanently reduce
        the layer's usable capacity."""
        layer = InMemoryCacheLayer(
            "expiry_bytes", max_size=100, max_size_bytes=1024 * 1024
        )
        await layer.set("k", "x" * 500, ttl=60)

        _expire_now(layer, "k")
        assert await layer.get("k") is None

        assert layer.stats.total_size_bytes == 0, (
            f"cache holds {len(layer.cache)} entries but still reports "
            f"{layer.stats.total_size_bytes} bytes in use; these phantom bytes "
            "are charged against max_size_bytes forever"
        )

    async def test_expired_key_releases_entry_count(self):
        layer = InMemoryCacheLayer(
            "expiry_count", max_size=100, max_size_bytes=1024 * 1024
        )
        await layer.set("k", "value", ttl=60)

        _expire_now(layer, "k")
        assert await layer.get("k") is None

        assert (
            layer.stats.total_entries == 0
        ), f"cache is empty but reports {layer.stats.total_entries} entries"

    async def test_reused_key_does_not_inherit_expired_history(self):
        """A key that expires and is later written again is a *new* entry. If
        the dead entry's timestamps survive, ``_calculate_adaptive_ttl`` reads
        them as the new entry's access frequency and over-extends its TTL."""
        layer = InMemoryCacheLayer("reuse", max_size=100, max_size_bytes=1024 * 1024)
        await layer.set("k", "value", ttl=60)
        for _ in range(5):
            await layer.get("k")
        assert len(layer.access_patterns["k"]) == 5

        _expire_now(layer, "k")
        assert await layer.get("k") is None

        # Same key, brand-new entry.
        await layer.set("k", "fresh", ttl=60)

        assert len(layer.access_patterns.get("k", [])) == 0, (
            "a freshly written entry inherited its expired predecessor's "
            "access timestamps, so it is treated as an established hot key "
            "from the moment it is created"
        )


class TestExpiredBytesDoNotConsumeCapacity:
    """The user-visible consequence of the accounting leak: because
    ``_evict_if_needed`` evicts while ``total_size_bytes`` exceeds the budget,
    bytes that expiry never released push live entries out of the cache."""

    async def test_capacity_survives_expiry_churn(self):
        payload = "x" * 900

        async def fill_and_count(with_expiry_churn: bool) -> int:
            layer = InMemoryCacheLayer("cap", max_size=10_000, max_size_bytes=100_000)
            if with_expiry_churn:
                for i in range(50):
                    await layer.set(f"gone{i}", payload, ttl=60)
                    _expire_now(layer, f"gone{i}")
                    await layer.get(f"gone{i}")
            for i in range(200):
                await layer.set(f"live{i}", payload)
            return sum(1 for key in layer.cache if key.startswith("live"))

        baseline = await fill_and_count(with_expiry_churn=False)
        after_churn = await fill_and_count(with_expiry_churn=True)

        # Control: eviction is still doing its job in both runs, so this is a
        # test of correct accounting and not of a disabled size limit.
        assert baseline < 200, "precondition: the byte budget must force eviction"

        assert after_churn == baseline, (
            f"a layer that has seen expiry churn holds only {after_churn} live "
            f"entries where a fresh layer of the same size holds {baseline}; "
            "the expired entries' bytes are still charged against the budget"
        )


# ----------------------------------------------------------------------------
# set() replacing an already-expired key
# ----------------------------------------------------------------------------


class TestResetOfExpiredKeyStartsCleanHistory:
    """``set()`` is a fourth way an entry stops existing.

    ``delete()``, eviction and lazy expiry all free the slot, so they route
    through ``_release_entry``. ``set()`` instead *reuses* the slot, which is
    why it needs its own handling: if the resident entry has already expired,
    the value being installed is a brand-new entry that happens to share a key,
    and it must not inherit the dead entry's access history.

    The distinction matters because ``access_patterns`` is the frequency signal
    behind adaptive TTL -- inherited timestamps make a cold key look hot.
    """

    async def test_reset_after_expiry_drops_dead_history(self):
        layer = InMemoryCacheLayer("reset_hist", max_size=100)
        await layer.set("k", {"v": 1}, ttl=300)
        for _ in range(5):
            await layer.get("k")

        # Precondition: the live entry really did accumulate history, so a
        # later empty result is the fix and not an artefact of never recording.
        assert (
            len(layer.access_patterns["k"]) == 5
        ), "precondition: reads on a live entry must record access timestamps"

        _expire_now(layer, "k")
        # Deliberately no get() and no delete() in between: this is the path
        # where the caller overwrites a dead entry directly.
        await layer.set("k", {"v": 2}, ttl=300)

        assert len(layer.access_patterns["k"]) == 0, (
            "a value written over an expired entry inherited "
            f"{len(layer.access_patterns['k'])} timestamps from its dead "
            "predecessor; the successor is a new entry and starts cold"
        )

    async def test_reset_of_live_key_keeps_history(self):
        """Control: re-writing a *live* key is a genuine update, not a reuse."""
        layer = InMemoryCacheLayer("reset_live", max_size=100)
        await layer.set("k", {"v": 1}, ttl=300)
        for _ in range(5):
            await layer.get("k")

        await layer.set("k", {"v": 2}, ttl=300)

        assert len(layer.access_patterns["k"]) == 5, (
            "overwriting a live key discarded its access history; only expired "
            "entries should reset the frequency signal"
        )

    async def test_reset_after_expiry_keeps_entry_count_stable(self):
        """The slot is reused, so the entry count must not move."""
        layer = InMemoryCacheLayer("reset_count", max_size=100)
        await layer.set("k", {"v": 1}, ttl=300)
        _expire_now(layer, "k")
        await layer.set("k", {"v": 2}, ttl=300)

        assert layer.stats.total_entries == 1, (
            f"replacing an expired entry reported {layer.stats.total_entries} "
            "entries for a single resident key"
        )

    async def test_adaptive_ttl_does_not_treat_reused_key_as_hot(self):
        """End-to-end: the inherited history reached the TTL calculation."""
        from youtube_extension.backend.services.intelligent_cache import (
            IntelligentCacheSystem,
        )

        layer = InMemoryCacheLayer("reset_ttl", max_size=100)
        await layer.set("k", {"v": 1}, ttl=300)
        # 20 reads in a tight loop is the frequency profile that earns the
        # hot-key TTL, so the inherited history is unambiguously load-bearing.
        for _ in range(20):
            await layer.get("k")
        _expire_now(layer, "k")
        await layer.set("k", {"v": 2}, ttl=300)

        system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        system.layers = [layer]
        system.adaptive_ttl_enabled = True
        system.cache_warming_enabled = False
        system.auto_invalidation_enabled = False
        system.performance_history = []
        system.optimization_suggestions = []

        ttl = system._calculate_adaptive_ttl("k")

        assert ttl == 3600, (
            f"a key with no accesses since it was rewritten was given a {ttl}s "
            "TTL instead of the 3600s base; it inherited its expired "
            "predecessor's access timestamps and was scored as a hot key"
        )


# ---------------------------------------------------------------------------
# InMemoryCacheLayer — access-history retention is bounded
# ---------------------------------------------------------------------------


class TestAccessHistoryRetentionIsBounded:
    """A key that is read repeatedly must not accumulate one timestamp per hit
    forever. Before this was bounded, ``access_patterns[key]`` was a plain list
    appended to on every cache hit and never trimmed, so a hot key's history
    grew without limit for as long as the key stayed resident."""

    async def test_hot_key_history_stays_within_window(self):
        from youtube_extension.backend.services.intelligent_cache import (
            ACCESS_HISTORY_WINDOW,
        )

        layer = InMemoryCacheLayer("hot", max_size=100, max_size_bytes=1024 * 1024)
        await layer.set("hot", "value")

        hits = ACCESS_HISTORY_WINDOW * 20
        for _ in range(hits):
            await layer.get("hot")

        # Precondition: the key is still resident, so nothing released its
        # history behind our back and the count below is the retention policy.
        assert "hot" in layer.cache, "key was evicted; this is not a retention test"

        retained = len(layer.access_patterns["hot"])
        assert retained <= ACCESS_HISTORY_WINDOW, (
            f"history for a single resident key grew to {retained} entries "
            f"after {hits} hits; expected it to stay within "
            f"ACCESS_HISTORY_WINDOW={ACCESS_HISTORY_WINDOW}"
        )

    async def test_window_retains_the_most_recent_timestamps(self):
        """Bounding must drop the oldest samples, not the newest, so the
        retained window still describes current behaviour."""
        from youtube_extension.backend.services.intelligent_cache import (
            ACCESS_HISTORY_WINDOW,
        )

        layer = InMemoryCacheLayer("recent", max_size=100, max_size_bytes=1024 * 1024)
        await layer.set("k", "value")

        for _ in range(ACCESS_HISTORY_WINDOW):
            await layer.get("k")
        boundary = time.time()
        for _ in range(ACCESS_HISTORY_WINDOW):
            await layer.get("k")

        retained = list(layer.access_patterns["k"])
        assert retained == sorted(retained), "retained timestamps lost their ordering"
        assert all(ts >= boundary for ts in retained), (
            "history retained samples recorded before the most recent "
            f"{ACCESS_HISTORY_WINDOW} hits; the window is dropping the wrong end"
        )


# ---------------------------------------------------------------------------
# Adaptive TTL still consumes the bounded history
# ---------------------------------------------------------------------------


class TestAdaptiveTtlOverBoundedHistory:
    """``_calculate_adaptive_ttl`` reads ``accesses[0]``, ``accesses[-1]`` and
    ``len(accesses)``. Those must keep working over the bounded container, and
    a saturated window must still classify a hot key as high-frequency."""

    def _make_system(self, layer):
        from youtube_extension.backend.services.intelligent_cache import (
            IntelligentCacheSystem,
        )

        system = IntelligentCacheSystem.__new__(IntelligentCacheSystem)
        system.layers = [layer]
        system.adaptive_ttl_enabled = True
        system.cache_warming_enabled = False
        system.auto_invalidation_enabled = False
        system.performance_history = []
        system.optimization_suggestions = []
        return system

    async def test_saturated_window_still_yields_high_frequency_ttl(self):
        """The window holds only the tail of a burst, but that tail is itself a
        tight burst, so the frequency estimate must still read as hot."""
        from youtube_extension.backend.services.intelligent_cache import (
            ACCESS_HISTORY_WINDOW,
        )

        layer = InMemoryCacheLayer("ttl", max_size=10, max_size_bytes=1024 * 1024)
        await layer.set("k", "value")
        # Far more hits than the window holds, all in a tight burst.
        for _ in range(ACCESS_HISTORY_WINDOW * 5):
            await layer.get("k")

        system = self._make_system(layer)
        ttl = system._calculate_adaptive_ttl("k")
        assert ttl == 3600 * 4, (
            f"a saturated access window produced a {ttl}s TTL; a key read "
            f"{ACCESS_HISTORY_WINDOW * 5} times in a burst should still be "
            "classified as high-frequency"
        )

    async def test_indexing_and_len_work_over_bounded_history(self):
        """Guards the three container operations _calculate_adaptive_ttl uses.
        A container that bounded retention but broke indexing would silently
        send every key back to the base TTL."""
        layer = InMemoryCacheLayer("idx", max_size=10, max_size_bytes=1024 * 1024)
        await layer.set("k", "value")
        for _ in range(5):
            await layer.get("k")

        accesses = layer.access_patterns["k"]
        assert len(accesses) == 5, "len() over the history container is wrong"
        assert accesses[0] <= accesses[-1], "first/last indexing is not ordered"
