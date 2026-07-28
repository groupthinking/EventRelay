"""
Tests for security headers middleware
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.youtube_extension.backend.middleware.security_headers import SecurityHeadersMiddleware


def test_security_headers_middleware():
    """Test that security headers are added to responses"""
    
    # Create test app
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check that all security headers are present
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers
    
    # Check specific values
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_header_with_https():
    """Test that HSTS header is added for HTTPS requests"""
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/test")
    
    # HSTS should be present for HTTPS
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=" in response.headers["Strict-Transport-Security"]


def test_custom_csp_directives():
    """Test custom CSP directives"""
    
    custom_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, csp_directives=custom_csp)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.headers["Content-Security-Policy"] == custom_csp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
