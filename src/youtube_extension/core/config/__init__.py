"""
UVAI Configuration Management

This module provides centralized configuration management for all UVAI components,
including environment-aware settings, secrets management, and validation.

Components:
- logging_config: Structured logging configuration
- settings: Pydantic-based application settings
- environment: Environment detection and management
- secrets: Secure credential management
- validation: Configuration validation
"""

<<<<<<< HEAD
from .logging_config import (
    LogContext,
    LogDestination,
    LogFormat,
    LogLevel,
    UVAILogger,
    configure_from_environment,
    get_logger,
    setup_logging,
)
=======
try:  # pragma: no cover
    from .logging_config import (
        LogContext,
        LogDestination,
        LogFormat,
        LogLevel,
        UVAILogger,
        configure_from_environment,
        get_logger,
        setup_logging,
    )
except ImportError:  # pragma: no cover
    pass
>>>>>>> origin/main

__all__ = [
    "setup_logging",
    "get_logger",
    "configure_from_environment",
    "UVAILogger",
    "LogContext",
    "LogLevel",
    "LogFormat",
    "LogDestination"
]
