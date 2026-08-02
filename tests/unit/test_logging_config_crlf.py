"""Regression tests for CWE-117 log-injection hardening in StructuredFormatter.

These assert against the *rendered* handler output (not a helper's return
value), because the log-forging vector lives in the fully formatted record:
the interpolated message, ``exc_info=True`` tracebacks, and structured
``extra`` fields all reach the log stream through ``StructuredFormatter.format``.
"""

import io
import logging

import pytest

from youtube_extension.backend.config.logging_config import (
    _LOG_FORGING_ESCAPES,
    StructuredFormatter,
)


def _render(logger_name, emit):
    """Render one or more log records through StructuredFormatter and return
    the raw stream contents. ``emit`` receives the configured logger."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter("%(levelname)s - %(message)s"))
    logger = logging.getLogger(logger_name)
    logger.handlers[:] = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    emit(logger)
    handler.flush()
    return buf.getvalue()


def _payload_lines(out):
    """Physical lines excluding the trailing record terminator."""
    return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


@pytest.mark.unit
def test_message_crlf_cannot_forge_a_log_line():
    forged = "CRITICAL - FORGED ADMIN LINE"
    out = _render(
        "crlf-msg",
        lambda lg: lg.info("video=%s", f"abc\r\n{forged}"),
    )

    # Exactly one record => one physical line (plus the stream terminator).
    assert len(_payload_lines(out)) == 1
    # No raw CR/LF survived; they were escaped to visible sequences.
    assert "\r" not in out.rstrip("\n")
    assert "\\r\\n" in out
    # The forged text never begins its own physical line.
    assert not any(line.startswith(forged) for line in out.split("\n"))
    # ...but its text is preserved (greppable) on the single record line.
    assert forged in out


@pytest.mark.unit
def test_exc_info_traceback_cannot_forge_a_log_line():
    forged = "CRITICAL - FORGED ADMIN LINE"

    def emit(lg):
        try:
            raise ValueError(f"boom\r\n{forged}")
        except ValueError:
            lg.error("chat failed: %s", "x", exc_info=True)

    out = _render("crlf-exc", emit)

    # The whole record (message + traceback) collapses to one physical line.
    assert len(_payload_lines(out)) == 1
    assert "\r" not in out.rstrip("\n")
    # The exception's injected CR/LF is neutralized, so the forged text cannot
    # start a new physical line even though it rode in on the traceback.
    assert not any(line.startswith(forged) for line in out.split("\n"))
    assert "Traceback (most recent call last):" in out
    assert forged in out


@pytest.mark.unit
def test_all_line_separators_are_escaped():
    # Every separator the mitigation targets round-trips to a visible escape.
    for cp in _LOG_FORGING_ESCAPES:
        out = _render("crlf-sep", lambda lg, c=cp: lg.info("x%sy", chr(c)))
        assert len(_payload_lines(out)) == 1, f"cp={cp:#x} split the record"


@pytest.mark.unit
def test_clean_message_is_unchanged():
    out = _render("crlf-clean", lambda lg: lg.info("ordinary message 123"))
    assert "ordinary message 123" in out
    # No spurious escaping of a clean payload.
    assert "\\n" not in out.rstrip("\n")
