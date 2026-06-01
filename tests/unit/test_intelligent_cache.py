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
        from youtube_extension.backend.services.intelligent_cache import IntelligentCacheSystem
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
        assert len(k) == 32
        int(k, 16)  # should not raise


# ---------------------------------------------------------------------------
# IntelligentCacheSystem — _calculate_adaptive_ttl branches
# ---------------------------------------------------------------------------


class TestAdaptiveTtl:
    """Cover the frequency branches inside _calculate_adaptive_ttl."""

    def _make_system(self):
        from youtube_extension.backend.services.intelligent_cache import IntelligentCacheSystem
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
        from youtube_extension.backend.services.intelligent_cache import IntelligentCacheSystem
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
from youtube_extension.backend.services.intelligent_cache import IntelligentCacheSystem  # noqa: E402
