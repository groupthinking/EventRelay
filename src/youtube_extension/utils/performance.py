"""
Performance Optimization Utilities for EventRelay
=================================================

Helper classes and functions to improve application performance.
"""

import asyncio
import time
from functools import wraps
from typing import Optional, Callable, Any, Dict, Tuple, List
from collections import deque
import logging

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """
    Token bucket rate limiter for async operations.
    
    Usage:
        limiter = AsyncRateLimiter(rate=10, per=1.0)  # 10 requests per second
        
        async def api_call():
            async with limiter:
                # Make API call
                pass
    """
    
    def __init__(self, rate: int, per: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of operations allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = float(rate)
        self.last_check = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry - acquire rate limit slot"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        return False
    
    async def acquire(self):
        """Acquire permission to proceed, waiting if necessary"""
        while True:
            async with self._lock:
                current = time.monotonic()
                elapsed = current - self.last_check
                
                # Add tokens based on time elapsed
                self.allowance += elapsed * (self.rate / self.per)
                
                # Cap at max rate
                if self.allowance > self.rate:
                    self.allowance = float(self.rate)
                
                self.last_check = current
                
                # If we have a token, consume it and proceed
                if self.allowance >= 1.0:
                    self.allowance -= 1.0
                    return
                
                # Calculate how long to wait for next token
                deficit = 1.0 - self.allowance
                sleep_time = deficit * (self.per / self.rate)
            
            # Wait outside the lock
            await asyncio.sleep(sleep_time)


class AsyncLRUCache:
    """
    Async-safe LRU cache with TTL support.
    
    Usage:
        cache = AsyncLRUCache(maxsize=100, ttl=300)
        
        result = await cache.get(key)
        if result is None:
            result = await expensive_operation()
            await cache.set(key, result)
    """
    
    def __init__(self, maxsize: int = 128, ttl: Optional[float] = None):
        """
        Initialize cache.
        
        Args:
            maxsize: Maximum number of items to cache
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self.maxsize = maxsize
        self.ttl = ttl
        from collections import OrderedDict
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if not found or expired"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            # Check TTL
            if self.ttl and key in self._timestamps:
                age = time.monotonic() - self._timestamps[key]
                if age > self.ttl:
                    del self._cache[key]
                    del self._timestamps[key]
                    return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
    
    async def set(self, key: str, value: Any):
        """Set value in cache, evicting LRU if needed"""
        async with self._lock:
            # If key exists, update it
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
                self._timestamps[key] = time.monotonic()
                return
            
            # Evict if at capacity
            if len(self._cache) >= self.maxsize:
                # Remove oldest (first) item
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if oldest_key in self._timestamps:
                    del self._timestamps[oldest_key]
            
            # Add new item
            self._cache[key] = value
            self._timestamps[key] = time.monotonic()
    
    async def clear(self):
        """Clear all cached items"""
        async with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    async def size(self) -> int:
        """Get current cache size"""
        async with self._lock:
            return len(self._cache)


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance.
    
    Prevents cascading failures by short-circuiting calls to failing services.
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def api_call():
            async with breaker:
                return await external_api.call()
    """
    
    STATE_CLOSED = "closed"      # Normal operation
    STATE_OPEN = "open"          # Failing, reject calls
    STATE_HALF_OPEN = "half_open"  # Testing if recovered
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (half-open)
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = self.STATE_CLOSED
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Check circuit state before allowing operation"""
        async with self._lock:
            if self._state == self.STATE_OPEN:
                # Check if timeout has passed
                if (time.monotonic() - self._last_failure_time) > self.timeout:
                    self._state = self.STATE_HALF_OPEN
                    logger.info("Circuit breaker moving to half-open state")
                else:
                    raise Exception("Circuit breaker is OPEN")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Record success or failure"""
        async with self._lock:
            if exc_type is None:
                # Success
                self._on_success()
                return False
            
            if isinstance(exc_val, self.expected_exception):
                # Expected failure
                self._on_failure()
                return False  # Don't suppress exception
            
            # Unexpected exception, let it propagate
            return False
    
    def _on_success(self):
        """Handle successful call"""
        self._failure_count = 0
        if self._state == self.STATE_HALF_OPEN:
            self._state = self.STATE_CLOSED
            logger.info("Circuit breaker closed after successful test")
    
    def _on_failure(self):
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        
        if self._failure_count >= self.failure_threshold:
            self._state = self.STATE_OPEN
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )


def async_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @async_retry(max_attempts=3, backoff_base=2.0)
        async def flaky_api_call():
            return await api.call()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate backoff time
                        backoff = backoff_base ** attempt
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {backoff}s: {e}"
                        )
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
            
            # All attempts failed
            if last_exception is not None:
                raise last_exception
            else:
                raise RuntimeError(
                    f"{func.__name__} failed after {max_attempts} attempts, but no exception was captured."
                )
        
        return wrapper
    return decorator


def memoize_with_ttl(ttl: float):
    """
    Memoization decorator with time-to-live.
    
    Usage:
        @memoize_with_ttl(ttl=300)  # Cache for 5 minutes
        async def expensive_computation(x):
            return x ** 2
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, Tuple[Any, float]] = {}
        lock = asyncio.Lock()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from args/kwargs
            key = str((args, tuple(sorted(kwargs.items()))))
            
            async with lock:
                if key in cache:
                    value, timestamp = cache[key]
                    if (time.monotonic() - timestamp) < ttl:
                        return value
                
                # Not in cache or expired
                result = await func(*args, **kwargs)
                cache[key] = (result, time.monotonic())
                return result
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """
    Monitor and log performance metrics.
    
    Usage:
        monitor = PerformanceMonitor()
        
        async with monitor.measure("api_call"):
            await api.call()
        
        print(monitor.get_stats("api_call"))
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    def measure(self, name: str):
        """Context manager to measure operation duration"""
        return self._MeasureContext(self, name)
    
    class _MeasureContext:
        def __init__(self, monitor, name):
            self.monitor = monitor
            self.name = name
            self.start_time = None
        
        async def __aenter__(self):
            self.start_time = time.monotonic()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            duration = time.monotonic() - self.start_time
            await self.monitor._record(self.name, duration)
            return False
        
    async def _record(self, name: str, duration: float):
        """Record a measurement"""
        async with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(duration)
            
            # Keep only last 1000 measurements
            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-1000:]
    
    async def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        async with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return {}
            
            values = self._metrics[name]
            sorted_values = sorted(values)
            count = len(values)
            
            return {
                "count": count,
                "mean": sum(values) / count,
                "median": sorted_values[count // 2],
                "p95": sorted_values[int(count * 0.95)],
                "p99": sorted_values[int(count * 0.99)],
                "min": sorted_values[0],
                "max": sorted_values[-1]
            }


# Pre-compiled regex patterns for common operations
import re

VIDEO_ID_PATTERNS = [
    re.compile(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'),
    re.compile(r'(?:embed\/)([0-9A-Za-z_-]{11})'),
    re.compile(r'(?:watch\?v=)([0-9A-Za-z_-]{11})')
]


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.
    Uses pre-compiled regex patterns for efficiency.
    """
    for pattern in VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    
    # If it's already an ID
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
    
    return None
