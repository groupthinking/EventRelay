"""Unit tests for integrations/cloud_ai/exceptions.py."""

from __future__ import annotations

import pytest

from youtube_extension.integrations.cloud_ai.exceptions import (
    AuthenticationError,
    CloudAIError,
    ConfigurationError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
)


# ===========================================================================
# CloudAIError (base)
# ===========================================================================


class TestCloudAIError:
    def test_message_stored(self):
        e = CloudAIError("something went wrong")
        assert str(e) == "something went wrong"

    def test_provider_default_none(self):
        e = CloudAIError("msg")
        assert e.provider is None

    def test_error_code_default_none(self):
        e = CloudAIError("msg")
        assert e.error_code is None

    def test_details_default_empty_dict(self):
        e = CloudAIError("msg")
        assert e.details == {}

    def test_explicit_provider(self):
        e = CloudAIError("msg", provider="google_cloud")
        assert e.provider == "google_cloud"

    def test_explicit_error_code(self):
        e = CloudAIError("msg", error_code="E001")
        assert e.error_code == "E001"

    def test_explicit_details(self):
        e = CloudAIError("msg", details={"key": "val"})
        assert e.details["key"] == "val"

    def test_is_exception(self):
        assert issubclass(CloudAIError, Exception)

    def test_can_be_raised(self):
        with pytest.raises(CloudAIError):
            raise CloudAIError("boom")


# ===========================================================================
# RateLimitError
# ===========================================================================


class TestRateLimitError:
    def test_inherits_cloud_ai_error(self):
        assert issubclass(RateLimitError, CloudAIError)

    def test_error_code_set(self):
        e = RateLimitError("rate limited")
        assert e.error_code == "RATE_LIMIT_EXCEEDED"

    def test_retry_after_default_none(self):
        e = RateLimitError("rate limited")
        assert e.retry_after is None

    def test_explicit_retry_after(self):
        e = RateLimitError("rate limited", retry_after=60)
        assert e.retry_after == 60

    def test_provider_set(self):
        e = RateLimitError("rate limited", provider="aws")
        assert e.provider == "aws"


# ===========================================================================
# ConfigurationError
# ===========================================================================


class TestConfigurationError:
    def test_inherits_cloud_ai_error(self):
        assert issubclass(ConfigurationError, CloudAIError)

    def test_error_code_set(self):
        e = ConfigurationError("bad config")
        assert e.error_code == "CONFIGURATION_ERROR"

    def test_missing_config_default_none(self):
        e = ConfigurationError("bad config")
        assert e.missing_config is None

    def test_explicit_missing_config(self):
        e = ConfigurationError("missing key", missing_config="api_key")
        assert e.missing_config == "api_key"


# ===========================================================================
# ServiceUnavailableError
# ===========================================================================


class TestServiceUnavailableError:
    def test_inherits_cloud_ai_error(self):
        assert issubclass(ServiceUnavailableError, CloudAIError)

    def test_error_code_set(self):
        e = ServiceUnavailableError("service down")
        assert e.error_code == "SERVICE_UNAVAILABLE"

    def test_message_stored(self):
        e = ServiceUnavailableError("service down")
        assert str(e) == "service down"


# ===========================================================================
# AuthenticationError
# ===========================================================================


class TestAuthenticationError:
    def test_inherits_cloud_ai_error(self):
        assert issubclass(AuthenticationError, CloudAIError)

    def test_error_code_set(self):
        e = AuthenticationError("auth failed")
        assert e.error_code == "AUTHENTICATION_FAILED"

    def test_provider_stored(self):
        e = AuthenticationError("auth failed", provider="azure")
        assert e.provider == "azure"


# ===========================================================================
# QuotaExceededError
# ===========================================================================


class TestQuotaExceededError:
    def test_inherits_cloud_ai_error(self):
        assert issubclass(QuotaExceededError, CloudAIError)

    def test_error_code_set(self):
        e = QuotaExceededError("quota exceeded")
        assert e.error_code == "QUOTA_EXCEEDED"

    def test_quota_type_default_none(self):
        e = QuotaExceededError("quota exceeded")
        assert e.quota_type is None

    def test_explicit_quota_type(self):
        e = QuotaExceededError("quota exceeded", quota_type="requests_per_day")
        assert e.quota_type == "requests_per_day"
