"""Unit tests for AsyncLRUCache, CircuitBreaker, AsyncRateLimiter, and InMemoryRateLimiter."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.utils.performance import (
    AsyncLRUCache,
    AsyncRateLimiter,
    CircuitBreaker,
)
from youtube_extension.backend.middleware.rate_limiting import InMemoryRateLimiter


# ===========================================================================
# AsyncLRUCache
# ===========================================================================


class TestAsyncLRUCacheBasic:
    @pytest.fixture
    def cache(self):
        return AsyncLRUCache(maxsize=3)

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, cache):
        assert await cache.get("absent") is None

    @pytest.mark.asyncio
    async def test_set_then_get_returns_value(self, cache):
        await cache.set("k1", "v1")
        assert await cache.get("k1") == "v1"

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, cache):
        await cache.set("k", "old")
        await cache.set("k", "new")
        assert await cache.get("k") == "new"

    @pytest.mark.asyncio
    async def test_size_increments(self, cache):
        assert await cache.size() == 0
        await cache.set("a", 1)
        assert await cache.size() == 1

    @pytest.mark.asyncio
    async def test_clear_empties_cache(self, cache):
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.clear()
        assert await cache.size() == 0
        assert await cache.get("a") is None

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_full(self, cache):
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.set("c", 3)
        await cache.set("d", 4)  # triggers eviction of "a"
        assert await cache.get("a") is None
        assert await cache.get("d") == 4

    @pytest.mark.asyncio
    async def test_maxsize_not_exceeded(self, cache):
        for i in range(10):
            await cache.set(str(i), i)
        assert await cache.size() <= 3


class TestAsyncLRUCacheTTL:
    @pytest.mark.asyncio
    async def test_ttl_expired_returns_none(self):
        cache = AsyncLRUCache(maxsize=10, ttl=0.05)
        await cache.set("k", "v")
        time.sleep(0.1)
        assert await cache.get("k") is None

    @pytest.mark.asyncio
    async def test_ttl_not_expired_returns_value(self):
        cache = AsyncLRUCache(maxsize=10, ttl=60.0)
        await cache.set("k", "v")
        assert await cache.get("k") == "v"

    @pytest.mark.asyncio
    async def test_no_ttl_never_expires(self):
        cache = AsyncLRUCache(maxsize=10, ttl=None)
        await cache.set("k", "v")
        time.sleep(0.05)
        assert await cache.get("k") == "v"


# ===========================================================================
# CircuitBreaker
# ===========================================================================


class TestCircuitBreakerInitialState:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)
        assert cb._state == CircuitBreaker.STATE_CLOSED

    def test_failure_count_starts_zero(self):
        cb = CircuitBreaker()
        assert cb._failure_count == 0

    def test_configurable_threshold(self):
        cb = CircuitBreaker(failure_threshold=10)
        assert cb.failure_threshold == 10

    def test_configurable_timeout(self):
        cb = CircuitBreaker(timeout=120.0)
        assert cb.timeout == 120.0


class TestCircuitBreakerOnSuccess:
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb._failure_count = 3
        cb._on_success()
        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_success_closes_half_open(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb._state = CircuitBreaker.STATE_HALF_OPEN
        cb._on_success()
        assert cb._state == CircuitBreaker.STATE_CLOSED


class TestCircuitBreakerOnFailure:
    def test_failure_increments_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb._on_failure()
        assert cb._failure_count == 1

    def test_threshold_triggers_open(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb._on_failure()
        assert cb._state == CircuitBreaker.STATE_OPEN

    def test_below_threshold_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb._on_failure()
        assert cb._state == CircuitBreaker.STATE_CLOSED

    @pytest.mark.asyncio
    async def test_open_circuit_raises(self):
        cb = CircuitBreaker(failure_threshold=1, timeout=999)
        cb._on_failure()
        assert cb._state == CircuitBreaker.STATE_OPEN
        with pytest.raises(Exception, match="OPEN"):
            async with cb:
                pass

    @pytest.mark.asyncio
    async def test_closed_circuit_allows_operation(self):
        cb = CircuitBreaker(failure_threshold=5)
        result = None
        async with cb:
            result = "ok"
        assert result == "ok"


# ===========================================================================
# AsyncRateLimiter
# ===========================================================================


class TestAsyncRateLimiterInit:
    def test_rate_stored(self):
        limiter = AsyncRateLimiter(rate=10, per=1.0)
        assert limiter.rate == 10

    def test_per_stored(self):
        limiter = AsyncRateLimiter(rate=5, per=2.0)
        assert limiter.per == 2.0

    def test_allowance_starts_full(self):
        limiter = AsyncRateLimiter(rate=10)
        assert limiter.allowance == 10.0

    @pytest.mark.asyncio
    async def test_acquire_consumes_token(self):
        limiter = AsyncRateLimiter(rate=10, per=1.0)
        await limiter.acquire()
        # Allowance should have decreased by 1 (approx — may have refilled slightly)
        assert limiter.allowance < 10.0


# ===========================================================================
# InMemoryRateLimiter
# ===========================================================================


def _make_request(ip: str = "127.0.0.1", forwarded: str = None) -> MagicMock:
    """Build a minimal mock Request with dict-like headers."""
    headers_dict: dict = {}
    if forwarded:
        headers_dict["X-Forwarded-For"] = forwarded
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip
    req.headers = MagicMock()
    req.headers.get = lambda k, d=None: headers_dict.get(k, d)
    return req


class TestInMemoryRateLimiterInit:
    def test_default_rate_is_60(self):
        limiter = InMemoryRateLimiter()
        assert limiter.requests_per_minute == 60

    def test_default_burst_is_10(self):
        limiter = InMemoryRateLimiter()
        assert limiter.burst_size == 10

    def test_custom_rate(self):
        limiter = InMemoryRateLimiter(requests_per_minute=120)
        assert limiter.requests_per_minute == 120

    def test_rate_per_second(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60)
        assert limiter.rate == 1.0


class TestInMemoryRateLimiterIsAllowed:
    def test_first_request_allowed(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=5)
        req = _make_request("10.0.0.1")
        allowed, info = limiter.is_allowed(req)
        assert allowed is True

    def test_info_has_required_keys(self):
        limiter = InMemoryRateLimiter()
        req = _make_request("10.0.0.2")
        _, info = limiter.is_allowed(req)
        assert "limit" in info
        assert "remaining" in info
        assert "reset" in info
        assert "client_id" in info

    def test_info_limit_matches_config(self):
        limiter = InMemoryRateLimiter(requests_per_minute=30)
        req = _make_request("10.0.0.3")
        _, info = limiter.is_allowed(req)
        assert info["limit"] == 30

    def test_burst_exhaustion_blocks(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=2)
        req = _make_request("10.0.0.4")
        # Drain burst
        limiter.is_allowed(req)
        limiter.is_allowed(req)
        # Third request should be denied
        allowed, _ = limiter.is_allowed(req)
        assert allowed is False

    def test_client_id_from_forwarded_for(self):
        limiter = InMemoryRateLimiter()
        req = _make_request("192.168.1.1", forwarded="203.0.113.5, 10.0.0.1")
        _, info = limiter.is_allowed(req)
        assert info["client_id"] == "203.0.113.5"

    def test_client_id_falls_back_to_host(self):
        limiter = InMemoryRateLimiter()
        req = _make_request("172.16.0.1")
        _, info = limiter.is_allowed(req)
        assert info["client_id"] == "172.16.0.1"
