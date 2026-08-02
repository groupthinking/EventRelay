"""CWE-117 regression tests for StructuredFormatter log-injection hardening.

These assert against the *rendered* handler output (not the return value of an
inline sanitizer), because the vulnerability lived in the paths that inline
sanitization does not cover: `logger.error(..., exc_info=True)`,
`logger.exception(...)`, and structured `extra` fields whose text is appended
to the record by the formatter/framework rather than the message string.
"""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.config.logging_config import (  # noqa: E402
    _UNSAFE_LOG_CHARS,
    StructuredFormatter,
    sanitize_log_record,
)

pytestmark = [pytest.mark.unit, pytest.mark.security]

# A format that mirrors a realistic record: a level/message prefix an attacker
# would try to forge a second, fake copy of.
_FMT = "%(levelname)s - %(message)s"

# The JSON format used by the module in production (`enable_json_logging=True`).
_JSON_FMT = '{"level": "%(levelname)s", "message": "%(message)s", "logger": "%(name)s"}'


def _make_logger(name: str, fmt: str = _FMT) -> tuple[logging.Logger, io.StringIO]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter(fmt))
    logger = logging.getLogger(name)
    logger.handlers[:] = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, buf


def _forged_line_present(rendered: str) -> bool:
    """A forged line is any line *after* the first that looks like its own record."""
    tail = rendered.split("\n", 1)[1] if "\n" in rendered else ""
    return "FORGED ADMIN LINE" in tail


def test_message_crlf_cannot_forge_a_new_line():
    logger, buf = _make_logger("crlf-message")
    logger.info("user said: %s", "hello\r\nCRITICAL - FORGED ADMIN LINE")
    out = buf.getvalue()

    assert "\r" not in out
    # Exactly one physical line (plus the trailing newline the handler adds).
    assert out.count("\n") == 1
    assert not _forged_line_present(out)
    # The payload is preserved, just neutralized to JSON-valid escapes.
    assert "\\u000d\\u000aCRITICAL - FORGED ADMIN LINE" in out


def test_exc_info_traceback_cannot_forge_log_lines():
    logger, buf = _make_logger("crlf-excinfo")
    try:
        raise ValueError("boom\r\nCRITICAL - FORGED ADMIN LINE")
    except ValueError:
        logger.error("Error in chat endpoint", exc_info=True)
    out = buf.getvalue()

    assert "\r" not in out
    # The entire record — message + multi-line traceback — is one physical line.
    assert out.count("\n") == 1
    assert not _forged_line_present(out)
    # Traceback content is retained in escaped form (still debuggable).
    assert "Exception Details:" in out
    assert "ValueError" in out


def test_logger_exception_helper_is_also_covered():
    logger, buf = _make_logger("crlf-exception-helper")
    try:
        raise RuntimeError("nope\nERROR - FORGED ADMIN LINE")
    except RuntimeError:
        logger.exception("handler failed")
    out = buf.getvalue()

    assert out.endswith("\n")  # only the handler's trailing newline
    assert out.count("\n") == 1  # single physical record — no injected line
    assert not _forged_line_present(out)


def test_extra_fields_referenced_by_format_are_sanitized():
    logger, buf = _make_logger(
        "crlf-extra", "%(levelname)s - %(message)s - url=%(video_url)s"
    )
    logger.error(
        "bad request",
        extra={"video_url": "http://x/\r\nCRITICAL - FORGED ADMIN LINE"},
    )
    out = buf.getvalue()

    assert "\r" not in out
    assert out.count("\n") == 1
    assert not _forged_line_present(out)


def test_all_splitlines_boundaries_are_escaped():
    # Every character str.splitlines() treats as a line boundary must be
    # neutralized, or a downstream reader that uses splitlines() could still be
    # tricked into seeing multiple records.
    payload = "".join(chr(c) for c in _UNSAFE_LOG_CHARS if c != ord("\\"))
    assert len(payload.splitlines()) > 1  # sanity: these really are boundaries
    cleaned = sanitize_log_record(payload)
    assert cleaned.splitlines() == [cleaned]  # collapses to a single line


def test_json_logging_output_stays_parseable():
    # With enable_json_logging=True the record is interpolated into a JSON
    # string; the escapes must be JSON-valid so an attacker cannot corrupt or
    # drop downstream JSON logs.
    logger, buf = _make_logger("crlf-json", _JSON_FMT)
    nasty = "line1\r\nline2\x1b[31m\x0bvt\x1crs"
    logger.info("%s", nasty)
    out = buf.getvalue().strip()

    parsed = json.loads(out)  # must not raise
    assert parsed["level"] == "INFO"
    # Round-trips back to the original text: the escapes are lossless.
    assert parsed["message"] == nasty


def test_encoding_is_reversible():
    # A real separator and a literal backslash-escape of it must not collide.
    real_newline = "a\nb"
    literal_text = "a\\nb"  # the two characters backslash + n
    assert sanitize_log_record(real_newline) != sanitize_log_record(literal_text)
    # Backslash is doubled, so the mapping can be inverted unambiguously.
    assert sanitize_log_record(literal_text) == "a\\\\nb"
    assert sanitize_log_record(real_newline) == "a\\u000ab"


def test_benign_records_are_unchanged():
    logger, buf = _make_logger("crlf-benign")
    logger.info("all good %s", "video-123")
    out = buf.getvalue()
    assert out == "INFO - all good video-123\n"


def test_sanitize_log_record_escapes_each_separator_to_json_unicode():
    # Build the input from the table itself so no raw separator is typed by hand
    # (which is easy to get wrong for U+2028 / U+2029).
    specials = {c: repl for c, repl in _UNSAFE_LOG_CHARS.items() if c != ord("\\")}
    raw = "".join(chr(c) for c in specials)
    cleaned = sanitize_log_record(raw)

    assert cleaned == "".join(specials[c] for c in specials)
    for c in specials:
        assert chr(c) not in cleaned  # nothing raw remains
    # The escaped blob is a JSON-valid string body that decodes losslessly back
    # to the original characters (raw has no backslash, so no ambiguity).
    assert json.loads(f'"{cleaned}"') == raw
