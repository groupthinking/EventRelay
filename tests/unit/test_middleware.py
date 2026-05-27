"""
Unit tests for FastAPI middleware: rate limiting, API key auth, and security headers.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.middleware.api_key_auth import (
    APIKeyAuthMiddleware,
    EXEMPT_METHODS,
    PROTECTED_PREFIXES,
)
from youtube_extension.backend.middleware.rate_limiting import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
    create_rate_limit_middleware,
)
from youtube_extension.backend.middleware.security_headers import (
    SecurityHeadersMiddleware,
    create_security_headers_middleware,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_with_middleware(middleware_cls, **kwargs) -> TestClient:
    """Build a minimal FastAPI app with the given middleware."""
    app = FastAPI()
    app.add_middleware(middleware_cls, **kwargs)

    @app.get("/test")
    def test_route():
        return {"status": "ok"}

    @app.post("/test")
    def test_post():
        return {"status": "ok"}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.post("/api/v1/video-to-software")
    def protected_mutation():
        return {"status": "ok"}

    @app.post("/api/v1/process-video")
    def protected_process():
        return {"status": "ok"}

    @app.post("/api/v1/transcript-action")
    def protected_transcript():
        return {"status": "ok"}

    return TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# InMemoryRateLimiter unit tests
# ===========================================================================


class TestInMemoryRateLimiter:
    def test_initial_bucket_allows_requests(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=5)
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.1")

        allowed, info = limiter.is_allowed(request)

        assert allowed is True
        assert info["limit"] == 60
        assert info["remaining"] == 4  # burst_size - 1

    def test_exhausted_bucket_denies_request(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=2)
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="10.0.0.1")

        # Drain the bucket
        limiter.is_allowed(request)
        limiter.is_allowed(request)

        allowed, info = limiter.is_allowed(request)

        assert allowed is False
        assert info["remaining"] == 0

    def test_x_forwarded_for_used_as_client_id(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=5)
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.5, 192.168.1.1"}
        request.client = MagicMock(host="10.0.0.1")

        _, info = limiter.is_allowed(request)

        assert info["client_id"] == "203.0.113.5"

    def test_first_ip_from_forwarded_for_chain(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=5)
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4,5.6.7.8"}
        request.client = None

        _, info = limiter.is_allowed(request)

        assert info["client_id"] == "1.2.3.4"

    def test_unknown_client_when_no_client_info(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=5)
        request = MagicMock()
        request.headers = {}
        request.client = None

        _, info = limiter.is_allowed(request)

        assert info["client_id"] == "unknown"

    def test_tokens_refill_over_time(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=1)
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="refill-test")

        # Drain the single-token bucket
        limiter.is_allowed(request)
        allowed_immediately, _ = limiter.is_allowed(request)
        assert allowed_immediately is False

        # Simulate time passing: manually advance bucket timestamp
        client_id = limiter._get_client_id(request)
        limiter.buckets[client_id]["last_update"] -= 2.0  # 2 seconds of refill

        allowed_after_refill, _ = limiter.is_allowed(request)
        assert allowed_after_refill is True

    def test_different_clients_have_independent_buckets(self):
        limiter = InMemoryRateLimiter(requests_per_minute=60, burst_size=1)

        req_a = MagicMock()
        req_a.headers = {}
        req_a.client = MagicMock(host="client-a")

        req_b = MagicMock()
        req_b.headers = {}
        req_b.client = MagicMock(host="client-b")

        limiter.is_allowed(req_a)  # drains client-a
        allowed_b, _ = limiter.is_allowed(req_b)

        assert allowed_b is True

    def test_rate_limit_info_contains_all_fields(self):
        limiter = InMemoryRateLimiter(requests_per_minute=30, burst_size=5)
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="info-test")

        _, info = limiter.is_allowed(request)

        assert "limit" in info
        assert "remaining" in info
        assert "reset" in info
        assert "client_id" in info
        assert info["limit"] == 30


# ===========================================================================
# RateLimitMiddleware integration tests (via TestClient)
# ===========================================================================


class TestRateLimitMiddleware:
    def test_request_within_limit_returns_200(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=5
        )
        response = client.get("/test")
        assert response.status_code == 200

    def test_rate_limit_headers_added_to_response(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=5
        )
        response = client.get("/test")
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    def test_exceeded_limit_returns_429(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=2
        )
        client.get("/test")
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429

    def test_429_response_has_json_content_type(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=1
        )
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "application/json" in response.headers.get("content-type", "")

    def test_429_response_includes_retry_after_header(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=1
        )
        client.get("/test")
        response = client.get("/test")
        assert response.status_code == 429
        assert "retry-after" in response.headers

    def test_exempt_path_bypasses_rate_limit(self):
        client = _make_app_with_middleware(
            RateLimitMiddleware, requests_per_minute=60, burst_size=1
        )
        # Exhaust the non-exempt bucket
        client.get("/test")
        # Exempt path should still pass
        response = client.get("/health")
        assert response.status_code == 200

    def test_custom_exempt_paths_respected(self):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
            burst_size=1,
            exempt_paths=["/custom-exempt"],
        )

        @app.get("/custom-exempt")
        def exempt():
            return {}

        @app.get("/not-exempt")
        def not_exempt():
            return {}

        tc = TestClient(app, raise_server_exceptions=False)
        tc.get("/not-exempt")  # drain burst
        tc.get("/not-exempt")  # should 429

        response = tc.get("/custom-exempt")
        assert response.status_code == 200

    def test_create_rate_limit_middleware_factory(self):
        middleware_cls = create_rate_limit_middleware(
            requests_per_minute=10, burst_size=3, exempt_paths=["/exempt"]
        )
        assert issubclass(middleware_cls, RateLimitMiddleware)


# ===========================================================================
# APIKeyAuthMiddleware integration tests
# ===========================================================================


class TestAPIKeyAuthMiddleware:
    def test_no_api_key_configured_allows_all_requests(self):
        with patch.dict("os.environ", {}, clear=False):
            # Ensure the env var is absent
            import os
            os.environ.pop("EVENTRELAY_API_KEY", None)
            client = _make_app_with_middleware(APIKeyAuthMiddleware)

        response = client.post(
            "/api/v1/video-to-software",
            json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert response.status_code != 401

    def test_valid_api_key_allows_mutation(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret-key")
        response = client.post(
            "/api/v1/video-to-software",
            json={},
            headers={"X-API-Key": "secret-key"},
        )
        assert response.status_code != 401

    def test_missing_api_key_header_blocks_mutation(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret-key")
        response = client.post("/api/v1/video-to-software", json={})
        assert response.status_code == 401

    def test_wrong_api_key_returns_401(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="correct-key")
        response = client.post(
            "/api/v1/video-to-software",
            json={},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_lowercase_x_api_key_header_accepted(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="my-key")
        response = client.post(
            "/api/v1/video-to-software",
            json={},
            headers={"x-api-key": "my-key"},
        )
        assert response.status_code != 401

    def test_get_requests_exempt_from_auth(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret")
        response = client.get("/test")
        assert response.status_code != 401

    def test_options_requests_exempt_from_auth(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret")
        response = client.options("/api/v1/video-to-software")
        assert response.status_code != 401

    def test_unprotected_paths_not_blocked(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret")
        response = client.post("/test", json={})
        assert response.status_code != 401

    def test_all_protected_prefixes_require_key(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret")
        for prefix in PROTECTED_PREFIXES:
            # POST to the exact prefix path (these aren't real routes but we only care about 401)
            response = client.post(prefix, json={})
            assert response.status_code == 401, (
                f"Expected 401 for {prefix} without key, got {response.status_code}"
            )

    def test_401_response_contains_hint(self):
        client = _make_app_with_middleware(APIKeyAuthMiddleware, api_key="secret")
        response = client.post("/api/v1/video-to-software", json={})
        body = response.json()
        assert "X-API-Key" in response.text or "API key" in response.text.lower()


# ===========================================================================
# SecurityHeadersMiddleware integration tests
# ===========================================================================


class TestSecurityHeadersMiddleware:
    def test_x_frame_options_deny(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_x_xss_protection_header(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert "x-xss-protection" in response.headers

    def test_referrer_policy_present(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert "referrer-policy" in response.headers

    def test_permissions_policy_present(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert "permissions-policy" in response.headers

    def test_content_security_policy_present(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        assert "content-security-policy" in response.headers

    def test_hsts_not_set_over_http(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware, enable_hsts=True)
        response = client.get("/test")  # TestClient uses http://
        assert "strict-transport-security" not in response.headers

    def test_hsts_disabled_does_not_set_header(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware, enable_hsts=False)
        response = client.get("/test")
        assert "strict-transport-security" not in response.headers

    def test_custom_csp_directives_applied(self):
        custom_csp = "default-src 'none'"
        client = _make_app_with_middleware(
            SecurityHeadersMiddleware, csp_directives=custom_csp
        )
        response = client.get("/test")
        assert response.headers.get("content-security-policy") == custom_csp

    def test_default_csp_blocks_frame_ancestors(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        csp = response.headers.get("content-security-policy", "")
        assert "frame-ancestors" in csp

    def test_permissions_policy_restricts_camera(self):
        client = _make_app_with_middleware(SecurityHeadersMiddleware)
        response = client.get("/test")
        policy = response.headers.get("permissions-policy", "")
        assert "camera=()" in policy

    def test_create_security_headers_middleware_factory(self):
        middleware_cls = create_security_headers_middleware(
            enable_hsts=False, hsts_max_age=3600
        )
        assert issubclass(middleware_cls, SecurityHeadersMiddleware)
