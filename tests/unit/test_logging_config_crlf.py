"""CWE-117 regression: StructuredFormatter must neutralize log forging.

These tests assert against the *rendered* handler output (not a sanitizer's
return value), covering the exc_info / logger.exception sinks that append raw
traceback and exception text after the formatted message.
"""

import io
import logging

import pytest

from youtube_extension.backend.config.logging_config import StructuredFormatter


def _render(logger_call) -> str:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter("%(levelname)s - %(message)s"))
    logger = logging.getLogger("crlf-regression")
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger_call(logger)
    handler.flush()
    return buf.getvalue()


def test_crlf_in_message_cannot_forge_a_line():
    out = _render(lambda lg: lg.info("video %s captured", "abc\r\nCRITICAL - FORGED"))
    # Exactly one physical line (plus the trailing newline the handler adds).
    assert out.count("\n") == 1
    assert "\r" not in out
    assert "FORGED" in out  # content preserved, just neutralized
    assert "CRITICAL - FORGED" not in out.splitlines()  # not a standalone line


def test_exc_info_traceback_cannot_forge_log_lines():
    def call(lg):
        try:
            raise ValueError("boom\r\nCRITICAL - FORGED ADMIN LINE")
        except ValueError:
            lg.error("Error in chat endpoint", exc_info=True)

    out = _render(call)
    assert "\r" not in out
    # The forged text must never appear as its own rendered line.
    assert "CRITICAL - FORGED ADMIN LINE" not in out.splitlines()


@pytest.mark.parametrize("sep", [" ", " ", "\x0b", "\x0c", "\x85"])
def test_unicode_line_separators_are_neutralized(sep):
    out = _render(lambda lg: lg.info("session %s", "s" + sep + "INJECTED"))
    assert sep not in out
    assert "INJECTED" in out
