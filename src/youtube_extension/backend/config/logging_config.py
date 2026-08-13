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
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

# Characters that can be abused to forge or corrupt log records (CWE-117 log
# injection). Any of these in dynamic content — a log message, an ``exc_info``
# traceback, ``str(exc)``, or a structured ``extra`` field — could otherwise
# inject what looks like an independent log line, or (for JSON logs) break the
# record so downstream parsers drop or corrupt it.
#
# The set is the union of every separator ``str.splitlines()`` recognizes as a
# line boundary (LF, CR, VT, FF, FS, GS, RS, NEL, LS, PS) plus ESC (terminal
# control sequences) and NUL (which can truncate a record inside a C-based log
# shipper). Each is escaped to a ``\uXXXX`` sequence — not a Python
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
    ord("\x00"): "\\u0000",  # NUL — can truncate a record in a C-based log shipper
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


# Last-resort record for the JSON serialization fallback. A module constant of
# pre-validated JSON, so emitting it involves no encoding step that could fail.
_JSON_UNSERIALIZABLE_RECORD = (
    '{"serialization_error": "log record could not be serialized"}'
)


def _int_is_json_safe(value: int) -> bool:
    """Can ``json`` render this int without tripping CPython's digit cap?

    ``json`` renders ints via ``str``, and CPython 3.11+ refuses int-to-str
    conversion beyond ``sys.get_int_max_str_digits()`` (4300 by default). An
    oversized int is therefore *a scalar that still raises*, which is why a
    plain type check is not sufficient on the fallback path.

    ``bit_length`` is used rather than attempting the conversion, because the
    conversion is the operation being guarded against. ``log10(2) ≈ 0.30103``,
    rounded up so the estimate can never understate the digit count.
    """
    get_limit = getattr(sys, "get_int_max_str_digits", None)
    if get_limit is None:  # Python < 3.11 has no cap.
        return True
    limit = int(get_limit())
    if limit <= 0:  # 0 disables the cap.
        return True
    return value.bit_length() * 0.302 + 1 < limit


def _is_json_safe_scalar(value: object) -> bool:
    """Is this a value ``json.dumps`` emits directly, under ``allow_nan=False``?

    The filter for the serialization fallback (#1452). The fallback's dump has
    no ``default=`` — anything reaching ``default`` there would reinstate the
    raising-``__str__`` hole — so this filter is the only thing standing
    between it and a second, fatal raise. It is exact about three things:

    ``type(value) is``, never ``isinstance``. ``isinstance`` consults
    ``value.__class__``, which an object can forge with a property returning
    ``str``. Such a value passes an ``isinstance`` filter, reaches the dump,
    and raises — costing the record the fallback exists to save. ``json``
    dispatches on the real runtime type, which cannot be forged, so matching on
    it is what makes this filter agree with the encoder.

    Non-finite floats are excluded: ``json`` renders them as the JavaScript
    literals ``NaN``/``Infinity``, which are not valid JSON, so a strict
    downstream parser rejects the whole record — the same loss as dropping it,
    moved to the consumer where it is harder to see.

    Oversized ints are excluded per ``_int_is_json_safe``.
    """
    value_type = type(value)
    # `cast` rather than `isinstance` narrowing: the exact-type check above is
    # the whole point of this filter, and `isinstance` is what it exists to
    # avoid. The cast is sound precisely because `type(value) is` already
    # established the runtime type.
    if value_type is float:
        return math.isfinite(cast(float, value))
    if value_type is int:
        return _int_is_json_safe(cast(int, value))
    return value_type in (str, bool, type(None))


def _describe_exception(exc: BaseException) -> str:
    """Name an exception without trusting its ``__str__``.

    Used only by the serialization fallback, which exists precisely because a
    hostile ``__str__`` can raise. The exception caught there may *be* one
    raised from a call site's own ``__str__``, so interpolating ``exc`` can
    raise a second time — inside the handler for the first. The type name is a
    plain attribute lookup and is always safe.
    """
    try:
        return f"{type(exc).__name__}: {exc}"
    except Exception:  # noqa: BLE001 - the fallback must not need a fallback
        return type(exc).__name__


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

        # `default=str` coerces values `json` cannot natively encode, but it is
        # not sufficient on its own to keep a record alive: a circular container
        # is rejected structurally *before* `default` is consulted, and a value
        # whose `__str__` raises propagates straight out of `default`. Either
        # way `logging` swallows the raise via `Handler.handleError` and drops
        # the record. The fallback below re-serializes with only the natively
        # encodable fields, so a bad enrichment costs its own value rather than
        # the whole record.
        #
        # The fallback must not be able to raise, or it loses the record for the
        # same reason one level down. Three inputs defeated the first version of
        # it, each measured against a real handler rather than reasoned about:
        #
        #   * an exception whose own `__str__` raises — the fallback rendered
        #     the caught exception directly, so describing the failure became
        #     the failure. Now via `_describe_exception`.
        #   * a value forging `__class__ = str` — passed the `isinstance`
        #     filter, then raised in the dump. Now excluded by matching on the
        #     real runtime type.
        #   * an int past CPython's 4300-digit `int`->`str` cap — a scalar by
        #     every type test, and still fatal. Now excluded by magnitude.
        #
        # `allow_nan=False` because Python's default emits the JavaScript
        # literals `NaN`/`Infinity`, which are not valid JSON. Raising instead
        # routes the record to the fallback, which drops the offending
        # enrichment and keeps a record every parser accepts.
        #
        # SCOPE, stated precisely because the bug this fixes was a comment
        # claiming more than its code enforced: this guards *serializing* the
        # payload. Building it can still raise above here — `record.getMessage()`
        # on mismatched %-args is the reachable case — and that is out of scope
        # because it fails the line-oriented path identically.
        try:
            return json.dumps(payload, ensure_ascii=True, allow_nan=False, default=str)
        except Exception as exc:  # noqa: BLE001 - never lose a record
            safe: dict[str, Any] = {
                key: value
                for key, value in payload.items()
                if _is_json_safe_scalar(value)
            }
            safe["serialization_error"] = _describe_exception(exc)
            try:
                return json.dumps(safe, ensure_ascii=True, allow_nan=False)
            except Exception:  # noqa: BLE001 - the guarantee stays unconditional
                # Not reachable through any input identified above: every value
                # in `safe` is one the encoder emits directly. It is here so the
                # guarantee is a property of the code rather than of the failure
                # modes that happened to be anticipated — which is the exact
                # gap #1452 was filed about.
                return _JSON_UNSERIALIZABLE_RECORD

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
