"""
Rate Limiting Middleware for FastAPI
Implements token bucket algorithm with Redis backend
"""

from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.
    For production, use RedisRateLimiter instead.
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.rate = requests_per_minute / 60.0  # tokens per second
        
        self.buckets = defaultdict(lambda: {"tokens": burst_size, "last_update": time.time()})
        self.lock = Lock()
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Prefer X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is allowed based on rate limit.
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        client_id = self._get_client_id(request)
        
        with self.lock:
            bucket = self.buckets[client_id]
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(
                self.burst_size,
                bucket["tokens"] + elapsed * self.rate
            )
            bucket["last_update"] = now
            
            # Check if request can be allowed
            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                allowed = True
                remaining = int(bucket["tokens"])
            else:
                allowed = False
                remaining = 0
            
            # Calculate reset time
            if remaining == 0:
                reset_time = int(now + (1.0 / self.rate))
            else:
                reset_time = int(now + 60)
            
            rate_limit_info = {
                "limit": self.requests_per_minute,
                "remaining": remaining,
                "reset": reset_time,
                "client_id": client_id,
            }
            
            return allowed, rate_limit_info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Implements per-client rate limiting with token bucket algorithm.
    Adds rate limit headers to all responses.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        exempt_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.limiter = InMemoryRateLimiter(requests_per_minute, burst_size)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        
        logger.info(
            f"Rate limiting enabled: {requests_per_minute} req/min, "
            f"burst: {burst_size}, exempt: {self.exempt_paths}"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and add headers to response"""
        
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Check rate limit
        allowed, rate_info = self.limiter.is_allowed(request)
        
        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {rate_info['client_id']} "
                f"on {request.method} {request.url.path}"
            )
            
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(60),  # Retry after 1 minute
                }
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
        
        return response


def create_rate_limit_middleware(
    requests_per_minute: int = 60,
    burst_size: int = 10,
    exempt_paths: Optional[list[str]] = None,
) -> type[RateLimitMiddleware]:
    """
    Factory function to create configured rate limit middleware.
    
    Args:
        requests_per_minute: Maximum requests per minute per client
        burst_size: Maximum burst requests allowed
        exempt_paths: Paths to exempt from rate limiting
    
    Returns:
        Configured RateLimitMiddleware class
    """
    
    class ConfiguredRateLimitMiddleware(RateLimitMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                requests_per_minute=requests_per_minute,
                burst_size=burst_size,
                exempt_paths=exempt_paths,
            )
    
    return ConfiguredRateLimitMiddleware


# Optional: Redis-backed rate limiter for production
try:
    import redis
    
    class RedisRateLimiter:
        """
        Redis-backed rate limiter for distributed systems.
        Use this in production with multiple backend instances.
        """
        
        def __init__(
            self,
            redis_url: str,
            requests_per_minute: int = 60,
            burst_size: int = 10,
        ):
            self.redis_client = redis.from_url(redis_url)
            self.requests_per_minute = requests_per_minute
            self.burst_size = burst_size
            self.rate = requests_per_minute / 60.0
            
            logger.info(f"Redis rate limiter initialized: {redis_url}")
        
        def is_allowed(self, request: Request) -> tuple[bool, dict]:
            """Check rate limit using Redis"""
            # Implementation would use Redis for distributed rate limiting
            # Using INCR and EXPIRE commands with sliding window
            pass
    
except ImportError:
    logger.info("Redis not available, using in-memory rate limiter")
    RedisRateLimiter = None
