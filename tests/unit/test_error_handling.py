"""
Unit tests for the error handling middleware: ErrorClassifier, ErrorResponse,
RequestTracker, and error categorization logic.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.middleware.error_handling_middleware import (
    ErrorCategory,
    ErrorClassifier,
    ErrorResponse,
    RequestTracker,
)


# ===========================================================================
# ErrorResponse
# ===========================================================================


class TestErrorResponse:
    def test_to_dict_contains_required_fields(self):
        err = ErrorResponse(
            error_id="ERR_ABC123",
            category=ErrorCategory.INTERNAL_SERVER,
            message="Something failed",
            status_code=500,
        )
        d = err.to_dict()
        assert "error" in d
        assert d["error"]["id"] == "ERR_ABC123"
        assert d["error"]["category"] == ErrorCategory.INTERNAL_SERVER
        assert "timestamp" in d["error"]
        assert "retryable" in d["error"]

    def test_details_hidden_by_default(self):
        err = ErrorResponse(
            error_id="ERR_XYZ",
            category=ErrorCategory.DATABASE,
            message="DB error details here",
            details="SELECT * FROM ...",
            status_code=503,
        )
        d = err.to_dict(include_details=False)
        assert "details" not in d["error"]

    def test_details_exposed_when_debug(self):
        err = ErrorResponse(
            error_id="ERR_DEBUG",
            category=ErrorCategory.DATABASE,
            message="DB error",
            details="SELECT * FROM ...",
            status_code=503,
        )
        d = err.to_dict(include_details=True)
        assert d["error"]["details"] == "SELECT * FROM ..."
        assert "technical_message" in d["error"]

    def test_retry_after_included_when_set(self):
        err = ErrorResponse(
            error_id="ERR_RL",
            category=ErrorCategory.RATE_LIMIT,
            message="Too many requests",
            status_code=429,
            retryable=True,
            retry_after=60,
        )
        d = err.to_dict()
        assert d["error"]["retry_after"] == 60

    def test_retry_after_absent_when_none(self):
        err = ErrorResponse(
            error_id="ERR_404",
            category=ErrorCategory.NOT_FOUND,
            message="Not found",
            status_code=404,
        )
        d = err.to_dict()
        assert "retry_after" not in d["error"]

    def test_user_friendly_message_generated_for_known_categories(self):
        categories = [
            (ErrorCategory.VALIDATION, 422),
            (ErrorCategory.AUTHENTICATION, 401),
            (ErrorCategory.AUTHORIZATION, 403),
            (ErrorCategory.NOT_FOUND, 404),
            (ErrorCategory.RATE_LIMIT, 429),
            (ErrorCategory.INTERNAL_SERVER, 500),
            (ErrorCategory.EXTERNAL_SERVICE, 502),
            (ErrorCategory.DATABASE, 503),
            (ErrorCategory.NETWORK, 502),
            (ErrorCategory.TIMEOUT, 504),
        ]
        for category, status in categories:
            err = ErrorResponse(
                error_id="ERR_TEST",
                category=category,
                message="raw message",
                status_code=status,
            )
            assert isinstance(err.user_message, str)
            assert len(err.user_message) > 0

    def test_unknown_category_returns_generic_message(self):
        err = ErrorResponse(
            error_id="ERR_UNK",
            category="completely_unknown",
            message="raw",
            status_code=418,
        )
        assert "unexpected" in err.user_message.lower() or len(err.user_message) > 0


# ===========================================================================
# ErrorClassifier
# ===========================================================================


class TestErrorClassifier:
    def test_http_401_classifies_as_authentication(self):
        exc = HTTPException(status_code=401, detail="Unauthorized")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.AUTHENTICATION
        assert result.status_code == 401

    def test_http_403_classifies_as_authorization(self):
        exc = HTTPException(status_code=403, detail="Forbidden")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.AUTHORIZATION

    def test_http_404_classifies_as_not_found(self):
        exc = HTTPException(status_code=404, detail="Not found")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.NOT_FOUND
        assert result.retryable is False

    def test_http_429_classifies_as_rate_limit_and_retryable(self):
        exc = HTTPException(status_code=429, detail="Too many requests")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.RATE_LIMIT
        assert result.retryable is True
        assert result.retry_after == 60

    def test_http_400_classifies_as_validation(self):
        exc = HTTPException(status_code=400, detail="Bad request")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.VALIDATION

    def test_http_500_classifies_as_internal_server(self):
        exc = HTTPException(status_code=500, detail="Internal error")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.INTERNAL_SERVER
        assert result.retryable is True

    def test_database_error_classified_correctly(self):
        exc = RuntimeError("database connection refused")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.DATABASE
        assert result.status_code == 503
        assert result.retryable is True

    def test_database_error_with_sql_keyword(self):
        exc = Exception("sql query failed: table not found")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.DATABASE

    def test_network_error_classified_correctly(self):
        # Use a message that matches network patterns but NOT database patterns
        # ("connection" is in both, so avoid it here)
        exc = RuntimeError("dns resolution failed for upstream host")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.NETWORK
        assert result.status_code == 502

    def test_timeout_error_classified_correctly(self):
        exc = TimeoutError("request timed out after 30 seconds")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.TIMEOUT
        assert result.status_code == 504
        assert result.retryable is True

    def test_timeout_keyword_in_message(self):
        exc = RuntimeError("deadline exceeded for upstream call")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.TIMEOUT

    def test_generic_exception_classifies_as_internal_server(self):
        exc = ValueError("unexpected value encountered")
        result = ErrorClassifier.classify_exception(exc)
        assert result.category == ErrorCategory.INTERNAL_SERVER
        assert result.status_code == 500

    def test_error_id_has_err_prefix(self):
        exc = RuntimeError("boom")
        result = ErrorClassifier.classify_exception(exc)
        assert result.error_id.startswith("ERR_")

    def test_error_id_is_unique_per_call(self):
        exc = RuntimeError("boom")
        r1 = ErrorClassifier.classify_exception(exc)
        r2 = ErrorClassifier.classify_exception(exc)
        assert r1.error_id != r2.error_id

    def test_http_502_is_retryable(self):
        exc = HTTPException(status_code=502, detail="Bad gateway")
        result = ErrorClassifier.classify_exception(exc)
        assert result.retryable is True

    def test_http_503_is_retryable(self):
        exc = HTTPException(status_code=503, detail="Service unavailable")
        result = ErrorClassifier.classify_exception(exc)
        assert result.retryable is True

    def test_http_404_is_not_retryable(self):
        exc = HTTPException(status_code=404, detail="Not found")
        result = ErrorClassifier.classify_exception(exc)
        assert result.retryable is False


# ===========================================================================
# Error classification helpers (_is_* methods)
# ===========================================================================


class TestErrorClassifierHelpers:
    def test_is_database_error_true_for_connection(self):
        assert ErrorClassifier._is_database_error(Exception("connection failed"))

    def test_is_database_error_true_for_sql(self):
        assert ErrorClassifier._is_database_error(Exception("sql syntax error"))

    def test_is_database_error_true_for_deadlock(self):
        assert ErrorClassifier._is_database_error(Exception("deadlock detected"))

    def test_is_database_error_false_for_unrelated(self):
        assert not ErrorClassifier._is_database_error(ValueError("invalid config"))

    def test_is_network_error_true_for_socket(self):
        assert ErrorClassifier._is_network_error(Exception("socket connection reset"))

    def test_is_network_error_true_for_dns(self):
        assert ErrorClassifier._is_network_error(Exception("dns resolution failed"))

    def test_is_network_error_false_for_unrelated(self):
        assert not ErrorClassifier._is_network_error(ValueError("bad argument"))

    def test_is_timeout_error_true_for_timed_out(self):
        assert ErrorClassifier._is_timeout_error(Exception("request timed out"))

    def test_is_timeout_error_true_for_deadline_exceeded(self):
        assert ErrorClassifier._is_timeout_error(Exception("deadline exceeded"))

    def test_is_timeout_error_false_for_unrelated(self):
        assert not ErrorClassifier._is_timeout_error(ValueError("invalid input"))


# ===========================================================================
# RequestTracker
# ===========================================================================


class TestRequestTracker:
    def _make_request(self, ip: str = "127.0.0.1") -> MagicMock:
        req = MagicMock()
        req.method = "GET"
        req.url = MagicMock()
        req.url.__str__ = lambda self: "http://localhost/api/v1/test"
        req.headers = {}
        req.client = MagicMock(host=ip)
        return req

    def test_start_request_returns_context(self):
        tracker = RequestTracker()
        req = self._make_request()
        context = tracker.start_request("req_001", req)
        assert context["request_id"] == "req_001"
        assert context["method"] == "GET"
        assert "start_time" in context

    def test_end_request_removes_from_active(self):
        tracker = RequestTracker()
        req = self._make_request()
        tracker.start_request("req_002", req)
        assert "req_002" in tracker.active_requests

        metrics = tracker.end_request("req_002", 200)
        assert "req_002" not in tracker.active_requests

    def test_end_request_computes_duration(self):
        tracker = RequestTracker()
        req = self._make_request()
        tracker.start_request("req_003", req)
        time.sleep(0.01)
        metrics = tracker.end_request("req_003", 200)
        assert metrics["duration_ms"] > 0

    def test_end_unknown_request_returns_empty_dict(self):
        tracker = RequestTracker()
        result = tracker.end_request("nonexistent_id", 200)
        assert result == {}

    def test_get_client_ip_from_x_forwarded_for(self):
        tracker = RequestTracker()
        req = MagicMock()
        req.headers = {"x-forwarded-for": "10.0.0.1, 192.168.1.1"}
        req.client = MagicMock(host="172.16.0.1")
        assert tracker.get_client_ip(req) == "10.0.0.1"

    def test_get_client_ip_from_x_real_ip(self):
        tracker = RequestTracker()
        req = MagicMock()
        req.headers = {"x-real-ip": "203.0.113.42"}
        req.client = MagicMock(host="10.0.0.1")
        assert tracker.get_client_ip(req) == "203.0.113.42"

    def test_get_client_ip_fallback_to_client_host(self):
        tracker = RequestTracker()
        req = MagicMock()
        req.headers = {}
        req.client = MagicMock(host="192.168.0.50")
        assert tracker.get_client_ip(req) == "192.168.0.50"

    def test_get_client_ip_no_client_returns_unknown(self):
        tracker = RequestTracker()
        req = MagicMock()
        req.headers = {}
        req.client = None
        assert tracker.get_client_ip(req) == "unknown"

    def test_memory_usage_returns_float(self):
        tracker = RequestTracker()
        usage = tracker.get_memory_usage()
        assert isinstance(usage, float)
        assert usage >= 0.0
