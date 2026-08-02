"""Regression tests for CWE-117 log-injection hardening in StructuredFormatter.

These assert against the *rendered* handler output (not a helper's return
value), covering the two ways CR/LF can reach a log record:

1. User-controlled data interpolated into the log message.
2. Raw exception text appended via ``exc_info`` / ``logger.exception`` — the
   sink that inline message sanitization does not reach.
"""

import io
import logging

import pytest

from youtube_extension.backend.config.logging_config import (
    _UNSAFE_LOG_CHARS,
    StructuredFormatter,
)

FORGED = "CRITICAL - FORGED ADMIN LINE"


def _render(logger_name, emit):
    """Render one record through StructuredFormatter and return the raw output."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter("%(levelname)s - %(message)s"))
    logger = logging.getLogger(logger_name)
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    emit(logger)
    return buf.getvalue()


def test_crlf_in_message_cannot_forge_log_lines():
    out = _render(
        "crlf-message",
        lambda lg: lg.info("video_id=%s captured", f"abc\r\nINFO - {FORGED}"),
    )
    assert out.count("\n") == 1  # exactly one trailing newline -> one physical line
    assert "\r" not in out
    assert not any(line.strip() == FORGED for line in out.split("\n"))


def test_exc_info_traceback_cannot_forge_log_lines():
    def emit(lg):
        try:
            raise ValueError(f"boom\r\n{FORGED}")
        except ValueError:
            lg.error("Error in chat endpoint: %s", "safe-arg", exc_info=True)

    out = _render("crlf-exc-info", emit)

    # The whole record — message + traceback — is a single physical line.
    assert out.count("\n") == 1
    assert "\r" not in out
    # The forged payload survives as inline, escaped text, never as its own line.
    assert not any(line.strip() == FORGED for line in out.split("\n"))
    assert "\\r\\n" in out


def test_logger_exception_and_structured_extra_are_scrubbed():
    def emit(lg):
        try:
            raise RuntimeError(f"db down\r\n{FORGED}")
        except RuntimeError:
            lg.exception("failure", extra={"request_id": "id\r\nWARNING - forged"})

    out = _render("crlf-extra", emit)
    assert out.count("\n") == 1
    assert "\r" not in out
    assert not any(line.strip() == FORGED for line in out.split("\n"))


@pytest.mark.parametrize("ch", sorted(_UNSAFE_LOG_CHARS))
def test_every_unsafe_char_is_escaped(ch):
    payload = f"before{chr(ch)}after"
    out = _render(f"crlf-charset-{ch}", lambda lg: lg.info("v=%s", payload))
    body = out.rstrip("\n")  # drop the handler's single line terminator
    assert chr(ch) not in body  # raw control char never survives in the record
    assert out.count("\n") == 1
    assert _UNSAFE_LOG_CHARS[ch] in body  # replaced by its visible escape


def test_ordinary_message_is_unchanged():
    out = _render("crlf-plain", lambda lg: lg.info("plain message %s", "value"))
    assert out == "INFO - plain message value\n"
