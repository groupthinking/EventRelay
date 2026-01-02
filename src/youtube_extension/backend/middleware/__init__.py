"""
Middleware package for YouTube Extension backend.

Contains:
- Security headers middleware (OWASP recommended headers)
- Rate limiting middleware (token bucket algorithm)
"""

from .rate_limiting import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
    create_rate_limit_middleware,
)
from .security_headers import (
    SecurityHeadersMiddleware,
    create_security_headers_middleware,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "create_security_headers_middleware",
    "RateLimitMiddleware",
    "create_rate_limit_middleware",
    "InMemoryRateLimiter",
]
