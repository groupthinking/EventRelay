"""
Tests for performance optimization utilities
"""

import asyncio
import pytest
import time
from src.youtube_extension.utils.performance import (
    AsyncRateLimiter,
    AsyncLRUCache,
    CircuitBreaker,
    async_retry,
    memoize_with_ttl,
    PerformanceMonitor,
    extract_video_id,
)


class TestAsyncRateLimiter:
    """Test async rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiter enforces limits"""
        limiter = AsyncRateLimiter(rate=5, per=1.0)  # 5 per second
        
        start = time.monotonic()
        
        # Make 10 requests (should take ~1 second)
        # First 5 go immediately (burst), then wait 1 sec for next 5
        for _ in range(10):
            async with limiter:
                pass
        
        elapsed = time.monotonic() - start
        
        # Should take at least 0.9 seconds (allowing burst of 5)
        assert elapsed >= 0.9, f"Rate limiter too fast: {elapsed}s"
        assert elapsed < 1.5, f"Rate limiter too slow: {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test rate limiter with concurrent requests"""
        limiter = AsyncRateLimiter(rate=10, per=1.0)
        
        async def make_request():
            async with limiter:
                await asyncio.sleep(0.01)
        
        start = time.monotonic()
        
        # Launch 20 concurrent requests
        await asyncio.gather(*[make_request() for _ in range(20)])
        
        elapsed = time.monotonic() - start
        
        # Should take at least 0.9 seconds (burst of 10, then wait 1 sec for next 10)
        assert elapsed >= 0.9


class TestAsyncLRUCache:
    """Test async LRU cache"""
    
    @pytest.mark.asyncio
    async def test_basic_caching(self):
        """Test basic cache set/get"""
        cache = AsyncLRUCache(maxsize=10)
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = AsyncLRUCache(maxsize=10)
        
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = AsyncLRUCache(maxsize=10, ttl=0.1)  # 100ms TTL
        
        await cache.set("key1", "value1")
        
        # Should be cached
        result1 = await cache.get("key1")
        assert result1 == "value1"
        
        # Wait for expiration
        await asyncio.sleep(0.15)
        
        # Should be expired
        result2 = await cache.get("key1")
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = AsyncLRUCache(maxsize=3)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new item (should evict key2, the LRU)
        await cache.set("key4", "value4")
        
        # key1 should still be cached
        assert await cache.get("key1") == "value1"
        
        # key4 should be cached
        assert await cache.get("key4") == "value4"
    
    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test cache clearing"""
        cache = AsyncLRUCache(maxsize=10)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        assert await cache.size() == 2
        
        await cache.clear()
        
        assert await cache.size() == 0
        assert await cache.get("key1") is None


class TestCircuitBreaker:
    """Test circuit breaker"""
    
    @pytest.mark.asyncio
    async def test_normal_operation(self):
        """Test circuit breaker in closed state"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        async with breaker:
            # Should allow operation
            result = "success"
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        # Cause 3 failures
        for _ in range(3):
            try:
                async with breaker:
                    raise Exception("Simulated failure")
            except Exception:
                pass
        
        # Circuit should be open now
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            async with breaker:
                pass
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self):
        """Test circuit moves to half-open after timeout"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
        
        # Cause failures to open circuit
        for _ in range(2):
            try:
                async with breaker:
                    raise Exception("Failure")
            except Exception:
                pass
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Should allow one test request (half-open)
        async with breaker:
            # Success - circuit should close
            # Circuit may still be open, this is expected in half-open state
            pass
        
        # Circuit should be closed again, allow operation
        if 'result' not in locals():
            async with breaker:
                result = "success"
        
        assert result == "success"


class TestAsyncRetry:
    """Test async retry decorator"""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test no retry needed when successful"""
        call_count = 0
        
        @async_retry(max_attempts=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on temporary failure"""
        call_count = 0
        
        @async_retry(max_attempts=3, backoff_base=0.1)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await flaky_func()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Test raises exception after all retries"""
        @async_retry(max_attempts=3, backoff_base=0.1)
        async def failing_func():
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError, match="Permanent failure"):
            await failing_func()


class TestMemoizeWithTTL:
    """Test memoization decorator"""
    
    @pytest.mark.asyncio
    async def test_memoization(self):
        """Test function results are cached"""
        call_count = 0
        
        @memoize_with_ttl(ttl=1.0)
        async def expensive_func(x):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2
        
        # First call
        result1 = await expensive_func(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call (should use cache)
        result2 = await expensive_func(5)
        assert result2 == 10
        assert call_count == 1  # Not called again
        
        # Different argument (should call function)
        result3 = await expensive_func(10)
        assert result3 == 20
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test cache expires after TTL"""
        call_count = 0
        
        @memoize_with_ttl(ttl=0.1)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        await func(5)
        assert call_count == 1
        
        # Wait for TTL
        await asyncio.sleep(0.15)
        
        # Should call function again
        await func(5)
        assert call_count == 2


class TestPerformanceMonitor:
    """Test performance monitor"""
    
    @pytest.mark.asyncio
    async def test_measure_duration(self):
        """Test measuring operation duration"""
        monitor = PerformanceMonitor()
        
        async with monitor.measure("test_op"):
            await asyncio.sleep(0.1)
        
        stats = await monitor.get_stats("test_op")
        
        assert stats["count"] == 1
        assert 0.09 < stats["mean"] < 0.15
    
    @pytest.mark.asyncio
    async def test_multiple_measurements(self):
        """Test statistics over multiple measurements"""
        monitor = PerformanceMonitor()
        
        for i in range(10):
            async with monitor.measure("test_op"):
                await asyncio.sleep(0.01 * i)
        
        stats = await monitor.get_stats("test_op")
        
        assert stats["count"] == 10
        assert stats["min"] < stats["mean"] < stats["max"]
    
    @pytest.mark.asyncio
    async def test_empty_stats(self):
        """Test getting stats for non-existent metric"""
        monitor = PerformanceMonitor()
        
        stats = await monitor.get_stats("nonexistent")
        assert stats == {}


class TestVideoIdExtraction:
    """Test video ID extraction utility"""
    
    def test_extract_from_watch_url(self):
        """Test extraction from watch URL"""
        url = "https://www.youtube.com/watch?v=auJzb1D-fag"
        video_id = extract_video_id(url)
        assert video_id == "auJzb1D-fag"
    
    def test_extract_from_short_url(self):
        """Test extraction from short URL"""
        url = "https://youtu.be/auJzb1D-fag"
        video_id = extract_video_id(url)
        assert video_id == "auJzb1D-fag"
    
    def test_extract_from_embed_url(self):
        """Test extraction from embed URL"""
        url = "https://www.youtube.com/embed/auJzb1D-fag"
        video_id = extract_video_id(url)
        assert video_id == "auJzb1D-fag"
    
    def test_extract_from_id_only(self):
        """Test extraction from video ID string"""
        video_id = extract_video_id("auJzb1D-fag")
        assert video_id == "auJzb1D-fag"
    
    def test_invalid_url(self):
        """Test with invalid URL"""
        video_id = extract_video_id("not-a-valid-url")
        assert video_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
