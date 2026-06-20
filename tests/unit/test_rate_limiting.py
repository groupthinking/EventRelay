"""
Tests for rate limiting middleware
"""

import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.youtube_extension.backend.middleware.rate_limiting import RateLimitMiddleware


def test_rate_limiting_allows_requests_within_limit():
    """Test that requests within limit are allowed"""
    
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=10,
        burst_size=5,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    
    # Make 5 requests (within burst size)
    for i in range(5):
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


def test_rate_limiting_blocks_excessive_requests():
    """Test that requests exceeding limit are blocked"""
    
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=10,
        burst_size=3,  # Small burst for testing
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    
    # Make requests up to burst size
    for i in range(3):
        response = client.get("/test")
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    assert "X-RateLimit-Limit" in response.headers
    assert "Retry-After" in response.headers


def test_rate_limiting_exempt_paths():
    """Test that exempt paths are not rate limited"""
    
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=10,
        burst_size=2,
        exempt_paths=["/health"],
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}
    
    client = TestClient(app)
    
    # Exhaust rate limit on /test
    client.get("/test")
    client.get("/test")
    response = client.get("/test")
    assert response.status_code == 429
    
    # /health should still work
    response = client.get("/health")
    assert response.status_code == 200


def test_rate_limit_headers():
    """Test that rate limit headers are present and correct"""
    
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        burst_size=10,
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "60"
    assert int(response.headers["X-RateLimit-Remaining"]) >= 0
    assert "X-RateLimit-Reset" in response.headers


def test_rate_limiter_token_refill():
    """Test that rate limiter refills tokens over time"""
    
    from src.youtube_extension.backend.middleware.rate_limiting import InMemoryRateLimiter
    from fastapi import Request
    
    limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=2)
    
    # Create mock request
    class MockClient:
        host = "127.0.0.1"
    
    class MockRequest:
        client = MockClient()
        headers = {}
    
    request = MockRequest()
    
    # Use up tokens
    allowed, _ = limiter.is_allowed(request)
    assert allowed
    allowed, _ = limiter.is_allowed(request)
    assert allowed
    
    # Should be blocked now
    allowed, _ = limiter.is_allowed(request)
    assert not allowed
    
    # Wait for token refill (1 second = 1 token at 60 req/min)
    time.sleep(1.1)
    
    # Should be allowed again
    allowed, _ = limiter.is_allowed(request)
    assert allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
