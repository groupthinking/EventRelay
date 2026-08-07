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
    _describe_exception,
    sanitize_log_record,
    setup_logging,
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


def test_nul_byte_is_neutralized():
    # A NUL is not a splitlines() boundary, so line-oriented checks miss it, but
    # it can truncate a record inside a C-based log shipper. It must be escaped
    # to a JSON-valid sequence rather than reaching the sink raw.
    assert ord("\x00") in _UNSAFE_LOG_CHARS
    logger, buf = _make_logger("crlf-nul")
    logger.info("user said: %s", "before\x00after")
    out = buf.getvalue()

    assert "\x00" not in out  # no raw NUL survives to the sink
    assert "before\\u0000after" in out  # escaped, and content preserved
    assert json.loads(f'"{sanitize_log_record(chr(0))}"') == "\x00"  # reversible


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


# ---------------------------------------------------------------------------
# CWE-117 field forgery in JSON records (#1429)
#
# The tests above cover separators. None of them types a `"`, which is why
# they all passed against the vulnerable code: `_UNSAFE_LOG_CHARS`
# deliberately omits the double-quote, so interpolating a message into the
# JSON *template* let attacker content close a field and open new ones.
# `test_json_logging_output_stays_parseable` came closest -- it already
# asserts `parsed["level"] == "INFO"` -- and would have caught this had its
# payload contained a quote.
#
# The fix is ordering: build a dict, then `json.dumps`, so escaping happens
# per value before any structural quote exists.
# ---------------------------------------------------------------------------

# The exact payload from #1429: no newline, no backslash, only a quote.
_FORGERY = 'benign", "level": "DEBUG", "forged": "yes'


def _make_json_logger(name: str) -> tuple[logging.Logger, io.StringIO]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(
        StructuredFormatter(datefmt="%Y-%m-%d %H:%M:%S", json_output=True)
    )
    logger = logging.getLogger(name)
    logger.handlers[:] = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, buf


def test_quote_in_message_cannot_forge_a_json_field():
    logger, buf = _make_json_logger("json-forgery")
    logger.info(_FORGERY)
    parsed = json.loads(buf.getvalue())

    # Emitted at INFO; it must not parse as DEBUG.
    assert parsed["level"] == "INFO"
    # No field the format never defined.
    assert "forged" not in parsed
    # And the payload survives intact as a *value*.
    assert parsed["message"] == _FORGERY


def test_quote_in_lazy_args_cannot_forge_a_json_field():
    # %-interpolation happens inside getMessage(), so args are an equally
    # attacker-reachable path into `message`.
    logger, buf = _make_json_logger("json-forgery-args")
    logger.info("user=%s", _FORGERY)
    parsed = json.loads(buf.getvalue())

    assert parsed["level"] == "INFO"
    assert "forged" not in parsed
    assert parsed["message"] == f"user={_FORGERY}"


def test_quote_in_traceback_cannot_forge_a_json_field():
    logger, buf = _make_json_logger("json-forgery-exc")
    try:
        raise ValueError(_FORGERY)
    except ValueError:
        logger.error("operation failed", exc_info=True)
    parsed = json.loads(buf.getvalue())

    assert parsed["level"] == "ERROR"
    assert "forged" not in parsed
    # The traceback is carried as its own value, not spliced into the record.
    assert _FORGERY in parsed["exception"]


def test_backslash_cannot_smuggle_a_quote_out_of_a_value():
    # A trailing backslash before the quote is the classic way to defeat a
    # naive escaper that handles `"` but not `\`.
    logger, buf = _make_json_logger("json-forgery-backslash")
    logger.info('trailing\\", "level": "DEBUG')
    parsed = json.loads(buf.getvalue())

    assert parsed["level"] == "INFO"


def test_json_record_stays_a_single_physical_line():
    # The separator guarantee the line-oriented path provides must survive the
    # move to json.dumps -- including NEL/LS/PS, which depend on ensure_ascii.
    logger, buf = _make_json_logger("json-separators")
    nasty = "".join(chr(c) for c in _UNSAFE_LOG_CHARS if c != ord("\\"))
    logger.info(nasty)
    out = buf.getvalue()

    assert out.count("\n") == 1  # only the handler's terminator
    assert out.isascii()  # NEL / U+2028 / U+2029 escaped, not emitted raw
    assert json.loads(out)["message"] == nasty  # lossless round-trip


def test_benign_json_record_is_valid_and_faithful():
    # Guards the regression the naive fix caused: adding `"` to the escape
    # table destroyed the JSON skeleton even for harmless messages.
    logger, buf = _make_json_logger("json-benign")
    logger.warning("all good %s", "video-123")
    parsed = json.loads(buf.getvalue())

    assert parsed["message"] == "all good video-123"
    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "json-benign"
    assert parsed["service"] == "youtube-extension-api"
    assert isinstance(parsed["line"], int)


def test_json_metadata_is_authoritative_under_attack():
    # Every field a downstream consumer routes or alerts on must reflect what
    # the logger emitted, not what the message claimed.
    logger, buf = _make_json_logger("json-authority")
    logger.critical('x", "logger": "innocent", "timestamp": "1970-01-01 00:00:00')
    parsed = json.loads(buf.getvalue())

    assert parsed["level"] == "CRITICAL"
    assert parsed["logger"] == "json-authority"
    assert not parsed["timestamp"].startswith("1970")


def test_line_oriented_path_is_untouched_by_the_json_fix():
    # json_output defaults to False, so the existing formatter contract holds.
    logger, buf = _make_logger("json-default-off")
    logger.info("all good %s", "video-123")
    assert buf.getvalue() == "INFO - all good video-123\n"


# --- #1452: a record must survive an unserializable enrichment -------------
#
# `default=str` alone does not deliver "never lose a record". Both payloads
# below raise out of `json.dumps`, inside `Handler.emit`, where `logging`
# swallows the exception via `handleError` and drops the record silently.
# `correlation_id` is the reachable field: it is populated from
# `record.request_id`, which middleware may set to a framework object.


class _ExplodingStr:
    """A value whose ``__str__`` raises — `default=str` propagates it."""

    def __str__(self) -> str:
        raise RuntimeError("str() exploded")


def _circular_container() -> dict:
    """`json.dumps` rejects this structurally, before `default` is consulted."""
    circular: dict = {}
    circular["self"] = circular
    return circular


@pytest.mark.parametrize(
    ("label", "poison"),
    [
        ("circular", _circular_container()),
        ("exploding-str", _ExplodingStr()),
    ],
)
def test_unserializable_enrichment_does_not_cost_the_record(label, poison):
    logger, buf = _make_json_logger(f"json-unserializable-{label}")
    logger.info("healthy before")
    logger.info("poisoned record", extra={"request_id": poison})
    logger.info("healthy after")

    lines = [line for line in buf.getvalue().splitlines() if line.strip()]
    # The pre-#1452 implementation emits 2 — the poisoned record is dropped.
    assert len(lines) == 3

    parsed = json.loads(lines[1])
    # `level` stays authoritative, which is what downstream routing alerts on.
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "poisoned record"
    # The unserializable enrichment is dropped, and says so rather than
    # vanishing silently.
    assert "correlation_id" not in parsed
    assert "serialization_error" in parsed


def test_serialization_fallback_keeps_the_record_a_single_json_line():
    # The fallback must honour the same two guarantees as the happy path:
    # one physical line, and no forged field from attacker content.
    logger, buf = _make_json_logger("json-unserializable-forgery")
    logger.info(_FORGERY, extra={"request_id": _ExplodingStr()})

    rendered = buf.getvalue()
    assert rendered.count("\n") == 1
    parsed = json.loads(rendered)

    assert parsed["level"] == "INFO"
    assert "forged" not in parsed
    assert parsed["message"] == _FORGERY


def test_benign_enrichments_still_reach_the_json_record():
    # The fallback must not fire on serializable values — a scalar
    # `correlation_id` still rides through the normal path.
    logger, buf = _make_json_logger("json-benign-enrichment")
    logger.info("fine", extra={"request_id": "req-123"})
    parsed = json.loads(buf.getvalue())

    assert parsed["correlation_id"] == "req-123"
    assert "serialization_error" not in parsed


class _ForgedClassStr:
    """A value that lies about its type *and* raises from `__str__`.

    `isinstance(x, str)` consults `x.__class__`, which this forges. It
    therefore passes an `isinstance`-based scalar filter, reaches the
    fallback's `default`-less `json.dumps`, and raises `TypeError` — losing the
    record the fallback exists to save. `json` dispatches on the real runtime
    type, so `type(value) is` agrees with the encoder and `isinstance` does not.
    """

    @property
    def __class__(self):  # type: ignore[override]
        return str

    def __str__(self) -> str:
        raise RuntimeError("str() exploded")


def test_fallback_filter_is_not_fooled_by_a_forged_class():
    # Pins `type(value) is ...` over `isinstance(...)` in _is_json_safe_scalar.
    # With the isinstance form this value is retained and the record is dropped.
    logger, buf = _make_json_logger("json-forged-class")
    logger.info("before")
    logger.info("survives a liar", extra={"request_id": _ForgedClassStr()})
    logger.info("after")

    messages = [
        json.loads(line)["message"]
        for line in buf.getvalue().splitlines()
        if line.strip()
    ]
    assert messages == ["before", "survives a liar", "after"]

    parsed = json.loads(buf.getvalue().splitlines()[1])
    assert parsed["level"] == "INFO"
    assert "correlation_id" not in parsed
    assert parsed["serialization_error"].startswith("RuntimeError")


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_non_finite_enrichment_does_not_produce_invalid_json(value):
    # Python's json emits the JavaScript literals NaN/Infinity for these, which
    # are not valid JSON — a strict downstream parser rejects the whole record,
    # which is the same loss as dropping it, moved to the consumer. `json.loads`
    # accepts them by default, so this asserts against a *strict* parse.
    logger, buf = _make_json_logger(f"json-non-finite-{value}")
    logger.info("measured", extra={"request_id": value})

    rendered = buf.getvalue()

    def _reject(constant: str) -> None:
        raise AssertionError(f"non-JSON constant in record: {constant}")

    parsed = json.loads(rendered, parse_constant=_reject)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "measured"
    assert "correlation_id" not in parsed
    assert "serialization_error" in parsed


def test_finite_float_enrichment_is_kept():
    # The non-finite guard must not cost ordinary numeric enrichments.
    logger, buf = _make_json_logger("json-finite-float")
    logger.info("measured", extra={"request_id": 12.5})
    parsed = json.loads(buf.getvalue())

    assert parsed["correlation_id"] == 12.5
    assert "serialization_error" not in parsed


def test_describe_exception_survives_an_exception_that_cannot_be_stringified():
    # The fallback formats the error it caught. If that exception's own
    # __str__ raises, describing it must not re-raise and re-lose the record.
    class _Unprintable(Exception):
        def __str__(self) -> str:
            raise RuntimeError("nested boom")

    assert _describe_exception(_Unprintable()) == "_Unprintable"


@pytest.fixture
def _restore_root_logging():
    """`setup_logging` calls dictConfig, which mutates global logging state."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


@pytest.mark.parametrize("enable_json", [True, False])
def test_setup_logging_wires_json_output_to_the_formatter(
    tmp_path, _restore_root_logging, enable_json
):
    # The formatter is only safe on the JSON path if `setup_logging` actually
    # selects it. Dropping `"json_output": enable_json_logging` from the
    # dictConfig would silently restore #1429 while every formatter-level test
    # above kept passing, so pin the wiring itself.
    setup_logging(
        log_level="INFO",
        log_file=str(tmp_path / "wiring.log"),
        enable_json_logging=enable_json,
    )

    formatters = [
        handler.formatter
        for handler in logging.getLogger().handlers
        if isinstance(handler.formatter, StructuredFormatter)
    ]
    assert formatters, "expected StructuredFormatter on the root logger"
    assert all(f.json_output is enable_json for f in formatters)
