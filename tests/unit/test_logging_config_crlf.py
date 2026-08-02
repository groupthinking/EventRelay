"""
Regression tests for CWE-117 (log injection / log forging) hardening in
``StructuredFormatter``.

These assert against the *rendered* handler output — not the return value of any
inline sanitizer — so they cover every sink the formatter touches, including
``exc_info`` tracebacks and structured ``extra`` fields that never pass through
a call-site sanitizer.
"""

import io
import logging

import pytest

from youtube_extension.backend.config.logging_config import (
    _UNSAFE_LOG_CHARS,
    StructuredFormatter,
)


def _render(record_emitter) -> str:
    """Emit one or more records through a StructuredFormatter and return output."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter("%(levelname)s - %(message)s"))
    logger = logging.getLogger("crlf-regression")
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    record_emitter(logger)
    return buf.getvalue()


def _forged_lines(output: str) -> list:
    """Physical lines that would appear as their own forged log entries."""
    return [line for line in output.split("\n") if line.startswith("CRITICAL - FORGED")]


pytestmark = [pytest.mark.unit, pytest.mark.security]


def test_message_crlf_cannot_forge_log_lines():
    out = _render(
        lambda lg: lg.info("video_id=%s", "abc\r\nCRITICAL - FORGED VIA MESSAGE")
    )
    assert "\r" not in out
    assert _forged_lines(out) == []
    # The literal payload is preserved (escaped), so nothing is silently lost.
    assert "CRITICAL - FORGED VIA MESSAGE" in out


def test_exc_info_traceback_cannot_forge_log_lines():
    def emit(lg):
        try:
            raise ValueError("boom\r\nCRITICAL - FORGED VIA EXC")
        except ValueError:
            lg.error("Error in chat endpoint", exc_info=True)

    out = _render(emit)
    # A single ``lg.error(..., exc_info=True)`` must render as exactly one
    # physical line no matter how many newlines the traceback contains.
    physical = [line for line in out.split("\n") if line]
    assert len(physical) == 1
    assert "\r" not in out
    assert _forged_lines(out) == []
    # Traceback content is still present (escaped) for diagnosability.
    assert "Traceback (most recent call last)" in out
    assert "ValueError: boom" in out


def test_structured_extra_and_unicode_separators_cannot_forge_log_lines():
    ls = chr(0x2028)  # Unicode LINE SEPARATOR
    out = _render(
        lambda lg: lg.info(
            "url=%s",
            "http://x" + ls + "CRITICAL - FORGED VIA LS",
            extra={"request_id": "r\n1"},
        )
    )
    assert ls not in out
    assert "\r" not in out
    assert "\n" not in out.rstrip("\n")
    assert _forged_lines(out) == []


@pytest.mark.parametrize("char", sorted(_UNSAFE_LOG_CHARS))
def test_every_declared_unsafe_char_is_neutralized(char):
    payload = "before" + chr(char) + "after"
    out = _render(lambda lg: lg.info("v=%s", payload))
    # Strip only the handler's own trailing line terminator before inspecting
    # the record body — for char == "\n" that terminator is the sole legitimate
    # newline in the stream.
    body = out.rstrip("\n")
    # The raw separator/control character must not survive into the record body.
    assert chr(char) not in body
    # Its escaped form must appear instead.
    assert _UNSAFE_LOG_CHARS[char] in body
    # The record must remain a single physical line.
    assert body.count("\n") == 0
