"""Unit tests for youtube_extension.utils.performance async utilities."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.utils.performance import (
    AsyncLRUCache,
    AsyncRateLimiter,
    CircuitBreaker,
    PerformanceMonitor,
    async_retry,
    extract_video_id,
    memoize_with_ttl,
)

VALID_ID = "auJzb1D-fag"


# ===========================================================================
# extract_video_id (pure function, no async)
# ===========================================================================


class TestExtractVideoIdPerf:
    def test_standard_watch_url(self):
        assert extract_video_id(f"https://www.youtube.com/watch?v={VALID_ID}") == VALID_ID

    def test_short_url(self):
        assert extract_video_id(f"https://youtu.be/{VALID_ID}") == VALID_ID

    def test_embed_url(self):
        assert extract_video_id(f"https://www.youtube.com/embed/{VALID_ID}") == VALID_ID

    def test_direct_id_returned(self):
        assert extract_video_id(VALID_ID) == VALID_ID

    def test_invalid_url_returns_none(self):
        assert extract_video_id("https://notube.com/whatever") is None

    def test_empty_string_returns_none(self):
        assert extract_video_id("") is None


# ===========================================================================
# AsyncRateLimiter
# ===========================================================================


class TestAsyncRateLimiter:
    def test_init_stores_rate(self):
        rl = AsyncRateLimiter(rate=10, per=1.0)
        assert rl.rate == 10

    def test_init_stores_per(self):
        rl = AsyncRateLimiter(rate=10, per=2.0)
        assert rl.per == 2.0

    def test_allowance_starts_at_rate(self):
        rl = AsyncRateLimiter(rate=5)
        assert rl.allowance == 5.0

    @pytest.mark.asyncio
    async def test_acquire_succeeds_when_tokens_available(self):
        rl = AsyncRateLimiter(rate=10, per=1.0)
        await rl.acquire()  # Should not raise or hang

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self):
        rl = AsyncRateLimiter(rate=10, per=1.0)
        async with rl:
            pass  # Should succeed

    @pytest.mark.asyncio
    async def test_exit_returns_false(self):
        rl = AsyncRateLimiter(rate=10, per=1.0)
        result = await rl.__aexit__(None, None, None)
        assert result is False


# ===========================================================================
# AsyncLRUCache
# ===========================================================================


class TestAsyncLRUCache:
    def test_init_defaults(self):
        cache = AsyncLRUCache()
        assert cache.maxsize == 128
        assert cache.ttl is None

    def test_init_custom_maxsize(self):
        cache = AsyncLRUCache(maxsize=50)
        assert cache.maxsize == 50

    def test_init_custom_ttl(self):
        cache = AsyncLRUCache(ttl=300.0)
        assert cache.ttl == 300.0

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self):
        cache = AsyncLRUCache()
        assert await cache.get("missing") is None

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = AsyncLRUCache()
        await cache.set("key", "value")
        assert await cache.get("key") == "value"

    @pytest.mark.asyncio
    async def test_size_increments_on_set(self):
        cache = AsyncLRUCache()
        await cache.set("a", 1)
        await cache.set("b", 2)
        assert await cache.size() == 2

    @pytest.mark.asyncio
    async def test_clear_empties_cache(self):
        cache = AsyncLRUCache()
        await cache.set("k", "v")
        await cache.clear()
        assert await cache.size() == 0

    @pytest.mark.asyncio
    async def test_lru_eviction_at_capacity(self):
        cache = AsyncLRUCache(maxsize=2)
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.set("c", 3)  # evicts "a"
        assert await cache.size() == 2
        assert await cache.get("a") is None

    @pytest.mark.asyncio
    async def test_update_existing_key(self):
        cache = AsyncLRUCache()
        await cache.set("k", "old")
        await cache.set("k", "new")
        assert await cache.get("k") == "new"
        assert await cache.size() == 1

    @pytest.mark.asyncio
    async def test_ttl_expired_returns_none(self):
        cache = AsyncLRUCache(ttl=0.01)
        await cache.set("k", "v")
        await asyncio.sleep(0.05)
        assert await cache.get("k") is None


# ===========================================================================
# CircuitBreaker
# ===========================================================================


class TestCircuitBreaker:
    def test_init_defaults(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.timeout == 60.0
        assert cb._failure_count == 0
        assert cb._state == CircuitBreaker.STATE_CLOSED

    def test_on_success_resets_failure_count(self):
        cb = CircuitBreaker()
        cb._failure_count = 3
        cb._on_success()
        assert cb._failure_count == 0

    def test_on_failure_increments_count(self):
        cb = CircuitBreaker()
        cb._on_failure()
        assert cb._failure_count == 1

    def test_on_failure_opens_circuit_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb._on_failure()
        assert cb._state == CircuitBreaker.STATE_OPEN

    def test_on_success_closes_from_half_open(self):
        cb = CircuitBreaker()
        cb._state = CircuitBreaker.STATE_HALF_OPEN
        cb._on_success()
        assert cb._state == CircuitBreaker.STATE_CLOSED

    @pytest.mark.asyncio
    async def test_closed_circuit_allows_enter(self):
        cb = CircuitBreaker()
        result = await cb.__aenter__()
        assert result is cb

    @pytest.mark.asyncio
    async def test_exit_success_no_suppress(self):
        cb = CircuitBreaker()
        result = await cb.__aexit__(None, None, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_exit_expected_exception_records_failure(self):
        cb = CircuitBreaker(failure_threshold=10, expected_exception=ValueError)
        await cb.__aenter__()
        await cb.__aexit__(ValueError, ValueError("oops"), None)
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_open_circuit_raises(self):
        cb = CircuitBreaker(failure_threshold=1, timeout=9999)
        cb._on_failure()  # opens circuit
        with pytest.raises(Exception, match="OPEN"):
            await cb.__aenter__()


# ===========================================================================
# async_retry decorator
# ===========================================================================


class TestAsyncRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        calls = []

        @async_retry(max_attempts=3)
        async def func():
            calls.append(1)
            return "ok"

        result = await func()
        assert result == "ok"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_retries_on_exception(self):
        calls = []

        @async_retry(max_attempts=3, backoff_base=0.001)
        async def func():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("fail")
            return "ok"

        result = await func()
        assert result == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        @async_retry(max_attempts=2, backoff_base=0.001)
        async def func():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            await func()


# ===========================================================================
# memoize_with_ttl decorator
# ===========================================================================


class TestMemoizeWithTtl:
    @pytest.mark.asyncio
    async def test_caches_result(self):
        calls = []

        @memoize_with_ttl(ttl=300)
        async def compute(x):
            calls.append(x)
            return x * 2

        r1 = await compute(5)
        r2 = await compute(5)
        assert r1 == r2 == 10
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_different_args_different_cache(self):
        calls = []

        @memoize_with_ttl(ttl=300)
        async def compute(x):
            calls.append(x)
            return x * 2

        await compute(5)
        await compute(6)
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_expired_result_recomputed(self):
        calls = []

        @memoize_with_ttl(ttl=0.01)
        async def compute(x):
            calls.append(x)
            return x

        await compute(7)
        await asyncio.sleep(0.05)
        await compute(7)
        assert len(calls) == 2


# ===========================================================================
# PerformanceMonitor
# ===========================================================================


class TestPerformanceMonitor:
    def test_metrics_start_empty(self):
        monitor = PerformanceMonitor()
        assert monitor._metrics == {}

    @pytest.mark.asyncio
    async def test_measure_records_entry(self):
        monitor = PerformanceMonitor()
        async with monitor.measure("op"):
            pass
        stats = await monitor.get_stats("op")
        assert stats["count"] == 1

    @pytest.mark.asyncio
    async def test_stats_empty_for_unknown_metric(self):
        monitor = PerformanceMonitor()
        stats = await monitor.get_stats("nonexistent")
        assert stats == {}

    @pytest.mark.asyncio
    async def test_multiple_measurements(self):
        monitor = PerformanceMonitor()
        for _ in range(3):
            async with monitor.measure("op"):
                pass
        stats = await monitor.get_stats("op")
        assert stats["count"] == 3

    @pytest.mark.asyncio
    async def test_stats_keys_present(self):
        monitor = PerformanceMonitor()
        async with monitor.measure("op"):
            pass
        stats = await monitor.get_stats("op")
        for key in ("count", "mean", "median", "min", "max"):
            assert key in stats
