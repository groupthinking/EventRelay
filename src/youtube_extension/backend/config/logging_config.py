#!/usr/bin/env python3
"""
Logging Configuration
====================

Structured logging configuration for production-grade monitoring and debugging.
Provides consistent log formatting, multiple handlers, and performance monitoring.
"""

import json
import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Characters that can be abused to forge or corrupt log records (CWE-117 log
# injection). Any of these in dynamic content — a log message, an ``exc_info``
# traceback, ``str(exc)``, or a structured ``extra`` field — could otherwise
# inject what looks like an independent log line, or (for JSON logs) break the
# record so downstream parsers drop or corrupt it.
#
# The set is the union of every separator ``str.splitlines()`` recognizes as a
# line boundary (LF, CR, VT, FF, FS, GS, RS, NEL, LS, PS) plus ESC (terminal
# control sequences). Each is escaped to a ``\uXXXX`` sequence — not a Python
# ``\v``/``\x1b`` shorthand — so the neutralized record remains a single
# physical line for line-oriented sinks.
#
# SCOPE: this table applies to the **line-oriented** formats only. It operates
# on a fully-rendered record, where attacker content and the template's own
# structural characters are already indistinguishable, so it can neutralize
# separators but cannot defend JSON structure. It deliberately does NOT escape
# ``"``: doing so here would corrupt the JSON skeleton rather than protect it.
#
# JSON records do not use this path at all. They are built field-by-field and
# serialized with ``json.dumps`` (see ``StructuredFormatter._format_json``),
# which escapes quotes, backslashes and every separator above *within values*,
# so structure cannot be forged. See #1429 for the field-forgery bug that came
# from applying this table to rendered JSON.
#
# Backslash is escaped FIRST (see ``sanitize_log_record``) so the encoding is
# unambiguous and reversible: a real newline becomes a backslash-u-000a escape,
# while a literal backslash in the source is doubled, so the two never collide
# and the original text can be recovered by reversing the table.
_UNSAFE_LOG_CHARS = {
    ord("\\"): "\\\\",
    ord("\n"): "\\u000a",
    ord("\r"): "\\u000d",
    ord("\v"): "\\u000b",  # VT / 0x0B
    ord("\f"): "\\u000c",  # FF / 0x0C
    ord("\x1b"): "\\u001b",  # ESC — terminal control / escape sequences
    ord("\x1c"): "\\u001c",  # FS — file separator
    ord("\x1d"): "\\u001d",  # GS — group separator
    ord("\x1e"): "\\u001e",  # RS — record separator
    0x85: "\\u0085",  # NEL — Unicode next line
    0x2028: "\\u2028",  # LINE SEPARATOR
    0x2029: "\\u2029",  # PARAGRAPH SEPARATOR
}


def sanitize_log_record(rendered: str) -> str:
    """Neutralize line/record separators in a fully-rendered log record.

    Escapes CR/LF (and every other line separator, plus ESC) to ``\\uXXXX``
    sequences so attacker-controlled content cannot forge, corrupt, or split
    downstream log lines (CWE-117). Backslash is escaped first, so the
    transform is unambiguous and reversible.

    This is for **line-oriented** records. It does not, and cannot, make a
    rendered JSON record safe — see the module comment and ``#1429``.
    """
    return rendered.translate(_UNSAFE_LOG_CHARS)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging with enhanced metadata.

    When ``json_output`` is set, records are assembled as a dict and
    serialized with ``json.dumps`` instead of being interpolated into a JSON
    template. That ordering is the security property: escaping happens per
    *value*, before the structural quotes exist, so a ``"`` in a message
    cannot terminate a field, add one, or shadow an earlier one.
    """

    def __init__(self, *args: Any, json_output: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data"""

        # Add custom fields to log record
        record.service_name = "youtube-extension-api"
        record.version = "2.0.0"
        record.architecture = "service-oriented"

        # Add performance timing if available
        if hasattr(record, 'duration'):
            record.performance_ms = f"{record.duration * 1000:.2f}ms"

        # Add request context if available
        if hasattr(record, 'request_id'):
            record.correlation_id = record.request_id

        if self.json_output:
            return self._format_json(record)

        # Format the base message
        formatted_message = super().format(record)

        # CWE-117: neutralize line/record separators in the FINAL rendered
        # record so message text, exc_info tracebacks, and any structured
        # `extra` fields cannot forge, corrupt, or split downstream log lines
        # even when inline sanitization was not applied at the call site.
        return sanitize_log_record(formatted_message)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Build the record as a dict and serialize it with ``json.dumps``.

        CWE-117: every attacker-reachable value (`message`, the `exception`
        traceback, `stack_info`) enters as a dict value, so ``json.dumps``
        escapes it as string content. A ``"`` becomes ``\\"`` inside the value
        and cannot reach the structural layer.

        ``ensure_ascii=True`` (the default, stated here because the guarantee
        depends on it) escapes every separator ``_UNSAFE_LOG_CHARS`` covers:
        the C0 controls as ``\\n``/``\\r``/``\\uXXXX``, and NEL, LS and PS as
        non-ASCII ``\\uXXXX``. The record therefore stays a single physical
        line, which is the same guarantee the line-oriented path provides.
        """
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "service": record.service_name,
            "version": record.version,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "process": record.process,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        # Optional enrichments, only when the call site supplied them.
        for attribute in ("performance_ms", "correlation_id"):
            if hasattr(record, attribute):
                payload[attribute] = getattr(record, attribute)

        # `default=str` keeps a non-serializable `extra` value from raising
        # inside the logging path, where an exception would be swallowed and
        # the record lost entirely.
        return json.dumps(payload, ensure_ascii=True, default=str)

    def formatException(self, ei) -> str:
        """Format exception with enhanced stack trace"""
        result = super().formatException(ei)
        return f"Exception Details:\n{result}"


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    enable_json_logging: bool = False,
    max_log_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_json_logging: Enable JSON formatted logs for production
        max_log_size: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
    """

    # Ensure logs directory exists
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Define log formats
    detailed_format = (
        "%(asctime)s - %(service_name)s[%(process)d] - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d:%(funcName)s] - %(message)s"
    )

    simple_format = "%(asctime)s - %(levelname)s - %(message)s"

    # Retained as the documented field schema, NOT as the rendering path.
    # `StructuredFormatter._format_json` builds these fields as a dict and
    # serializes them; interpolating attacker content into this template is
    # exactly the field-forgery bug fixed in #1429. Keep the two in step when
    # adding a field.
    json_format = (
        '{"timestamp": "%(asctime)s", "service": "%(service_name)s", '
        '"version": "%(version)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s", '
        '"module": "%(filename)s", "line": %(lineno)d, '
        '"function": "%(funcName)s", "process": %(process)d}'
    )

    # Choose format based on configuration
    if enable_json_logging:
        log_format = json_format
    else:
        log_format = detailed_format if log_level == "DEBUG" else detailed_format

    # Logging configuration dictionary
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
                # Selects dict-then-`json.dumps` assembly over interpolation
                # into `json_format`. Without this the JSON template is filled
                # by printf and a `"` in a message forges fields (#1429).
                "json_output": enable_json_logging
            },
            "simple": {
                "format": simple_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "backend": {  # Our application logger
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            }
        }
    }

    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "structured",
            "filename": log_file,
            "maxBytes": max_log_size,
            "backupCount": backup_count,
            "encoding": "utf8"
        }

        # Add file handler to all loggers
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("file")

        # Add separate error log file
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "structured",
            "filename": log_file.replace(".log", "_errors.log"),
            "maxBytes": max_log_size,
            "backupCount": backup_count,
            "encoding": "utf8"
        }

        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("error_file")

    # Apply configuration
    logging.config.dictConfig(config)

    # Log configuration summary
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file or 'Console only'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class PerformanceLogger:
    """
    Context manager for performance logging.
    """

    def __init__(self, logger: logging.Logger, operation: str, log_level: int = logging.INFO):
        """
        Initialize performance logger.

        Args:
            logger: Logger instance to use
            operation: Description of operation being timed
            log_level: Logging level for performance logs
        """
        self.logger = logger
        self.operation = operation
        self.log_level = log_level
        self.start_time = None

    def __enter__(self):
        """Start timing"""
        self.start_time = datetime.now()
        self.logger.log(self.log_level, f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

            if exc_type:
                self.logger.error(
                    f"{self.operation} failed after {duration:.3f}s - {exc_type.__name__}: {exc_val}"
                )
            else:
                self.logger.log(
                    self.log_level,
                    f"{self.operation} completed in {duration:.3f}s",
                    extra={"duration": duration}
                )


def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""

    # Reduce noise from common libraries
    noisy_loggers = [
        "urllib3.connectionpool",
        "requests.packages.urllib3",
        "aiohttp.access",
        "asyncio"
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

    # Set specific levels for important libraries
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def setup_production_logging():
    """Setup logging configuration optimized for production"""

    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/youtube_extension_api.log")
    enable_json = os.getenv("JSON_LOGGING", "false").lower() == "true"

    # Setup logging
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        enable_json_logging=enable_json
    )

    # Configure third-party loggers
    configure_third_party_loggers()

    logger = get_logger(__name__)
    logger.info("Production logging configuration applied")


def setup_development_logging():
    """Setup logging configuration optimized for development"""

    setup_logging(
        log_level="DEBUG",
        log_file="logs/youtube_extension_dev.log",
        enable_json_logging=False
    )

    # Less restrictive third-party logging in development
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logger = get_logger(__name__)
    logger.info("Development logging configuration applied")


# Auto-configure based on environment
if os.getenv("ENVIRONMENT", "development").lower() == "production":
    setup_production_logging()
else:
    setup_development_logging()
