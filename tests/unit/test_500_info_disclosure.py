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


# FastAPI exception handlers are a second 500 sink the HTTPException scan above
# does not model: they build a response body directly (dict / JSONResponse) rather
# than raising. A handler must not place the exception message (`str(exc)`) or its
# class name (`exc.__class__.__name__`) into that body — both leak internal state.
# Logging the exception server-side is fine; those tokens appear only in response
# construction, never in a `logger.`/`log`/`raise`/comment line, so we exclude
# those lines to avoid false positives.
_HANDLER_DECORATOR = re.compile(r"^\s*@\w+\.exception_handler\(", re.MULTILINE)
_HANDLER_DISCLOSURE = re.compile(r"str\(\s*(?:exc|e)\s*\)|__class__\.__name__")
# Triple-quoted docstrings, so prose that *mentions* str(exc) is not mistaken for code.
_TRIPLE_STR = re.compile(r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'')


def _strip_docstrings(body: str) -> str:
    """Blank triple-quoted blocks, preserving line count so line numbers stay aligned."""
    return _TRIPLE_STR.sub(lambda m: "\n" * m.group(0).count("\n"), body)


def _exception_handler_bodies(text: str):
    """Yield (start_line, body_text) for each @<app>.exception_handler function."""
    lines = text.splitlines(keepends=True)
    for m in _HANDLER_DECORATOR.finditer(text):
        start_line = text.count("\n", 0, m.start())
        # Find the `def`/`async def` line that the decorator applies to.
        i = start_line
        while i < len(lines) and not lines[i].lstrip().startswith(("def ", "async def ")):
            i += 1
        if i >= len(lines):
            continue
        def_indent = len(lines[i]) - len(lines[i].lstrip())
        j = i + 1
        body: list[str] = []
        while j < len(lines):
            line = lines[j]
            stripped = line.strip()
            if stripped and (len(line) - len(line.lstrip())) <= def_indent:
                break  # dedented back to <= the def's level: end of function
            body.append(line)
            j += 1
        yield i + 1, "".join(body)


def _iter_handler_disclosures(text: str):
    """Yield (line_no, snippet) for exception-handler bodies that leak exc into the response."""
    for start_line, body in _exception_handler_bodies(text):
        if "status_code=500" not in re.sub(r"\s+", "", body):
            continue
        for offset, line in enumerate(_strip_docstrings(body).splitlines()):
            code = line.split("#", 1)[0]  # ignore inline comments
            bare = line.strip()
            if bare.startswith(("logger", "log", "self.logger", "raise")):
                continue
            if _HANDLER_DISCLOSURE.search(code):
                yield start_line + offset, bare[:120]


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


def test_no_disclosure_in_500_exception_handlers() -> None:
    offenders: list[str] = []
    for path in _backend_python_files():
        text = path.read_text(encoding="utf-8")
        for line_no, snippet in _iter_handler_disclosures(text):
            rel = path.relative_to(_BACKEND.parents[2])
            offenders.append(f"{rel}:{line_no}: {snippet}")

    assert not offenders, (
        "A FastAPI exception handler that returns HTTP 500 must not place the "
        "exception message (`str(exc)`) or its class name (`__class__.__name__`) "
        "into the response body — log it server-side instead. Offending sites:\n  "
        + "\n  ".join(offenders)
    )


def test_guard_detects_a_synthetic_handler_leak() -> None:
    """The exception-handler scanner flags exc message/class-name disclosure in a 500 body."""
    leaky = (
        "@app.exception_handler(Exception)\n"
        "async def h(request, exc):\n"
        '    logger.error(f"boom: {exc}", exc_info=True)\n'
        '    body = {"detail": str(exc), "error_type": exc.__class__.__name__}\n'
        "    return JSONResponse(status_code=500, content=body)\n"
    )
    assert list(_iter_handler_disclosures(leaky)), "handler scanner missed a real leak"

    safe = (
        "@app.exception_handler(Exception)\n"
        "async def h(request, exc):\n"
        '    logger.error(f"boom: {exc}", exc_info=True)\n'
        '    body = {"detail": "Internal server error"}\n'
        "    return JSONResponse(status_code=500, content=body)\n"
    )
    assert not list(
        _iter_handler_disclosures(safe)
    ), "handler scanner false-positived a sanitized 500 handler"

    # A 4xx handler may echo the exception (client-supplied validation input).
    client_err = (
        "@app.exception_handler(ValueError)\n"
        "async def h(request, exc):\n"
        '    return JSONResponse(status_code=400, content={"detail": str(exc)})\n'
    )
    assert not list(
        _iter_handler_disclosures(client_err)
    ), "handler scanner must ignore 4xx handlers"


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
