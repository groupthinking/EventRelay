"""
Cloud AI Integration Exceptions

Custom exceptions for cloud AI service integrations.
"""

from typing import Any, Optional


class CloudAIError(Exception):
    """Base exception for cloud AI integration errors."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 error_code: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code
        self.details = details or {}


class RateLimitError(CloudAIError):
    """Exception raised when API rate limits are exceeded."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 retry_after: Optional[int] = None):
        super().__init__(message, provider, "RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class ConfigurationError(CloudAIError):
    """Exception raised when configuration is invalid or missing."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 missing_config: Optional[str] = None):
        super().__init__(message, provider, "CONFIGURATION_ERROR")
        self.missing_config = missing_config


class ServiceUnavailableError(CloudAIError):
    """Exception raised when cloud AI service is temporarily unavailable."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, provider, "SERVICE_UNAVAILABLE")


class AuthenticationError(CloudAIError):
    """Exception raised when authentication fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, provider, "AUTHENTICATION_FAILED")


class QuotaExceededError(CloudAIError):
    """Exception raised when service quota is exceeded."""

    def __init__(self, message: str, provider: Optional[str] = None,
                 quota_type: Optional[str] = None):
        super().__init__(message, provider, "QUOTA_EXCEEDED")
        self.quota_type = quota_type


class UnsafeMediaPathError(CloudAIError):
    """Exception raised when a caller-supplied local media path is rejected.

    Raised instead of reading the file, so a traversal attempt fails loudly
    rather than silently returning empty bytes. ``requested_path`` echoes only
    the value the caller already supplied -- the resolved server-side path is
    deliberately not included, to avoid disclosing the filesystem layout.
    """

    def __init__(self, message: str, provider: Optional[str] = None,
                 requested_path: Optional[str] = None):
        super().__init__(message, provider, "UNSAFE_MEDIA_PATH")
        self.requested_path = requested_path
