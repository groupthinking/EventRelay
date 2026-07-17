"""Regression guard against information disclosure in HTTP 500 responses.

Context: several FastAPI handlers historically raised
``HTTPException(status_code=500, detail=str(e))`` (or an f-string embedding the
exception), leaking internal exception text — stack-adjacent messages, backend
API errors, database errors — to clients. See PR #801, which sanitized most but
not all handlers.

This test encodes the invariant directly on the source: a 500 response must use
a *static* ``detail`` string, never one derived from the caught exception. It is
hermetic (pure source scan, no app import / no pydantic) so it runs anywhere and
catches new leaks in any backend route, not just the ones fixed today.

It deliberately does not constrain 4xx responses: those echo client-supplied
validation errors, which are not internal-disclosure vectors.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "src" / "youtube_extension" / "backend"

# Match a single `raise HTTPException(...)` call, capturing its argument list,
# tolerant of the call spanning multiple lines.
_HTTP_EXC = re.compile(r"HTTPException\((?P<args>.*?)\)", re.DOTALL)

# A 500 `detail=` is safe only when it is an inline *static string literal*
# (``detail="Internal server error"``). Anything else can carry internal state to
# the client and is flagged:
#   detail=str(e)          detail=f"... {e} ..."      (inline dynamic string)
#   detail=error_msg       (a variable — may hold f"...{e}...")
#   detail={...}           (a dict whose values embed the exception)
# The value after ``detail=`` is dynamic unless its first non-space character
# opens a plain string literal (``"`` or ``'``). A leading ``{`` (dict) or any
# identifier char — ``f`` of an f-string, ``s`` of ``str(``, or a bare variable
# name — means it is not a static literal.
_DYNAMIC_DETAIL = re.compile(r"""detail\s*=\s*(?:\{|[A-Za-z_])""")


def _backend_python_files() -> list[Path]:
    return sorted(_BACKEND.rglob("*.py"))


def _iter_500_dynamic_detail(text: str):
    """Yield (line_no, snippet) for each 500 HTTPException with a dynamic detail."""
    for m in _HTTP_EXC.finditer(text):
        args = m.group("args")
        if "status_code=500" not in args.replace(" ", "").replace(
            "status_code =", "status_code="
        ):
            # normalize minor spacing; only care about 500 responses
            if "status_code=500" not in re.sub(r"\s+", "", args):
                continue
        if _DYNAMIC_DETAIL.search(args):
            line_no = text.count("\n", 0, m.start()) + 1
            yield line_no, " ".join(args.split())[:120]


def test_no_dynamic_detail_in_500_responses() -> None:
    offenders: list[str] = []
    for path in _backend_python_files():
        text = path.read_text(encoding="utf-8")
        for line_no, snippet in _iter_500_dynamic_detail(text):
            rel = path.relative_to(_BACKEND.parents[2])
            offenders.append(f"{rel}:{line_no}: HTTPException({snippet})")

    assert not offenders, (
        "HTTP 500 responses must use a static `detail` string (e.g. "
        '"Internal server error") and never leak the caught exception. '
        "Log the full error server-side instead. Offending sites:\n  "
        + "\n  ".join(offenders)
    )


def test_guard_detects_a_synthetic_leak() -> None:
    """Sanity check: the scanner flags every dynamic-detail shape, not just str(e)."""
    # Each of these leaks internal state and must be flagged.
    leaks = [
        "raise HTTPException(status_code=500, detail=str(e))",
        'raise HTTPException(status_code=500, detail=f"failed: {e}")',
        "raise HTTPException(status_code=500, detail=error_msg)",  # bare variable
        'raise HTTPException(status_code=500, detail={"message": error_msg})',  # dict
    ]
    for leak in leaks:
        assert list(_iter_500_dynamic_detail(leak)), f"scanner missed a real 500 leak: {leak}"

    # A static string literal is the only safe form.
    safe = 'raise HTTPException(status_code=500, detail="Internal server error")'
    assert not list(
        _iter_500_dynamic_detail(safe)
    ), "scanner false-positived a static detail"

    # 4xx responses echo client-supplied input and are intentionally out of scope.
    client_err = "raise HTTPException(status_code=400, detail=str(exc))"
    assert not list(
        _iter_500_dynamic_detail(client_err)
    ), "scanner must ignore 4xx responses"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
