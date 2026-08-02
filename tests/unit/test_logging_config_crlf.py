"""CWE-117 regression: the log formatter must neutralize CR/LF in the FINAL
rendered record, including exc_info tracebacks and structured ``extra`` fields.

This guards the vector that per-call ``_safe_log`` cannot reach: ``exc_info=True``
appends the raw exception text (and ``logger.exception`` renders ``extra``),
which can carry attacker-controlled ``\\r\\n`` and forge a log line.
"""

import io
import logging

import pytest

from youtube_extension.backend.config.logging_config import StructuredFormatter
from youtube_extension.utils.logsafe import safe_log


def _render(record_call) -> str:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(StructuredFormatter("%(levelname)s - %(message)s"))
    logger = logging.getLogger("crlf-regression")
    logger.handlers[:] = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    record_call(logger)
    return buf.getvalue()


def test_exc_info_traceback_cannot_forge_log_lines():
    def call(logger):
        try:
            raise ValueError("boom\r\nCRITICAL - FORGED ADMIN LINE")
        except ValueError as exc:
            # Message is already sanitized at the call site; the traceback is
            # the vector under test.
            logger.error("Error in chat endpoint: %s", safe_log(exc), exc_info=True)

    # The StreamHandler appends one trailing "\n" terminator — the legitimate
    # record boundary. The record *content* must contain no CR/LF, so the whole
    # record is a single line and nothing can be forged.
    out = _render(call)
    assert out.count("\n") == 1 and out.endswith("\n")
    body = out[:-1]
    assert "\r" not in body and "\n" not in body
    assert "FORGED ADMIN LINE" in body  # present, but on the one safe line


def test_extra_field_cannot_forge_log_lines():
    def call(logger):
        logger.info(
            "processing %(video_url)s",
            {"video_url": "http://x\r\nADMIN forged-from-extra"},
        )

    out = _render(call)
    body = out[:-1] if out.endswith("\n") else out
    assert "\r" not in body and "\n" not in body


@pytest.mark.parametrize(
    "codepoint",
    [0x0D, 0x0A, 0x1B, 0x0B, 0x0C, 0x85, 0x2028, 0x2029],
)
def test_all_line_separators_stripped_from_rendered_record(codepoint):
    sep = chr(codepoint)

    def call(logger):
        logger.warning("value=%s", f"a{sep}FORGED")

    out = _render(call)
    # Ignore the single trailing terminator the handler appends.
    body = out[:-1] if out.endswith("\n") else out
    assert sep not in body
