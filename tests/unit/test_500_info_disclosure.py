"""Regression guard against information disclosure in HTTP 500 responses.

Context: several handlers historically raised
``HTTPException(status_code=500, detail=str(e))`` (or an f-string embedding the
exception), leaking internal exception text — stack-adjacent messages, backend
API errors, database errors — to clients. See PR #801, which sanitized most but
not all handlers.

This test encodes the invariant directly on the source: a 500 response must use
a *static* ``detail`` string, never one derived from the caught exception. It is
hermetic (pure source scan, no app import / no pydantic) so it runs anywhere and
catches new leaks in any backend route.

It models the three distinct 500 sinks in this codebase:
  1. ``HTTPException`` — both keyword (``status_code=500, detail=...``) and
     positional (``HTTPException(500, str(e))``) forms.
  2. FastAPI ``@app.exception_handler`` functions that build a 500 body directly.
  3. A raw ``JSONResponse(..., status_code=500)`` (e.g. a Ray Serve deployment).

It deliberately does not constrain 4xx responses: those echo client-supplied
validation errors, which are not internal-disclosure vectors.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "src" / "youtube_extension" / "backend"
# Additional client-facing 500 surfaces outside the FastAPI backend package.
_EXTRA_ROOTS = [_REPO_ROOT / "src" / "uvai" / "ml"]


def _backend_python_files() -> list[Path]:
    files = list(_BACKEND.rglob("*.py"))
    for root in _EXTRA_ROOTS:
        if root.exists():
            files.extend(root.rglob("*.py"))
    return sorted(set(files))


# --- shared parsing helpers ------------------------------------------------

def _balanced_call_args(text: str, open_paren_idx: int) -> str:
    """Return the argument text of a call, balancing nested parens/brackets/braces."""
    depth = 0
    quote: str | None = None
    for i in range(open_paren_idx, len(text)):
        c = text[i]
        if quote:
            if c == quote:
                quote = None
            continue
        if c in "\"'":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_paren_idx + 1 : i]
    return text[open_paren_idx + 1 :]


def _split_top_level_commas(s: str) -> list[str]:
    """Split on commas that are not nested inside parens/brackets/braces/strings."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    buf: list[str] = []
    for c in s:
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            buf.append(c)
        elif c in "([{":
            depth += 1
            buf.append(c)
        elif c in ")]}":
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    parts.append("".join(buf))
    return parts


def _detail_is_dynamic(value: str) -> bool:
    """A detail value is safe only if it is an inline static string literal.

    Anything else — ``str(e)``, an f-string, a bare variable, or a ``{...}`` dict —
    can carry internal state to the client, so it is dynamic.
    """
    v = value.strip()
    if not v:
        return False
    return not v.startswith(('"', "'"))


# --- sink 1: HTTPException (keyword and positional) ------------------------

_HTTP_EXC_OPEN = re.compile(r"HTTPException\(")


def _iter_500_dynamic_detail(text: str):
    """Yield (line_no, snippet) for each 500 HTTPException with a dynamic detail."""
    for m in _HTTP_EXC_OPEN.finditer(text):
        args = _balanced_call_args(text, m.end() - 1)
        parts = _split_top_level_commas(args)
        nospace = re.sub(r"\s+", "", args)
        first = parts[0].strip() if parts else ""
        is_500 = "status_code=500" in nospace or first == "500"
        if not is_500:
            continue

        detail_val: str | None = None
        for p in parts:
            ps = p.strip()
            if ps.startswith("detail="):
                detail_val = ps[len("detail=") :]
                break
        if detail_val is None and len(parts) >= 2:
            # positional detail is the 2nd argument, unless it is a keyword arg.
            second = parts[1]
            if "=" not in second.split("(", 1)[0]:
                detail_val = second

        if detail_val is not None and _detail_is_dynamic(detail_val):
            line_no = text.count("\n", 0, m.start()) + 1
            yield line_no, " ".join(args.split())[:120]


# --- sink 2: FastAPI exception handlers ------------------------------------
#
# Exception handlers build a response body directly (dict / JSONResponse) rather
# than raising. A handler must not place the exception message (`str(exc)`) or its
# class name (`exc.__class__.__name__`) into that body. Logging the exception
# server-side is fine; those tokens never appear on a `logger.`/`log`/`raise`/
# comment line, so we exclude those lines to avoid false positives.
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


# --- sink 3: raw JSONResponse 500s -----------------------------------------
#
# A ``JSONResponse(..., status_code=500)`` body must not embed the exception
# (``str(exc)`` / ``str(e)`` / ``str(error)``) or an f-string interpolating one.
_JSON_RESPONSE = re.compile(r"JSONResponse\(")
# Exception-like variable names, so an f-string interpolating a UUID / error-id
# (e.g. f"FALLBACK_{uuid.uuid4()...}") is not mistaken for an exception leak.
_EXC_TOKENS = r"(?:e|ex|exc|err|error|error_msg|error_message|exception)"
_JSON_DISCLOSURE = re.compile(
    r"str\(\s*(?:exc|e|error)\s*\)"  # str(exc) / str(e) / str(error)
    r"|f[\"'][^\"']*\{[^{}]*\b" + _EXC_TOKENS + r"\b[^{}]*\}"  # f"...{exc-ref}..."
)


def _iter_json_500_disclosures(text: str):
    """Yield (line_no, snippet) for JSONResponse 500s whose body embeds the exception."""
    for m in _JSON_RESPONSE.finditer(text):
        args = _balanced_call_args(text, m.end() - 1)
        if "status_code=500" not in re.sub(r"\s+", "", args):
            continue
        if _JSON_DISCLOSURE.search(args):
            line_no = text.count("\n", 0, m.start()) + 1
            yield line_no, " ".join(args.split())[:120]


# --- the guards ------------------------------------------------------------

def test_no_dynamic_detail_in_500_responses() -> None:
    offenders: list[str] = []
    for path in _backend_python_files():
        text = path.read_text(encoding="utf-8")
        for line_no, snippet in _iter_500_dynamic_detail(text):
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}:{line_no}: HTTPException({snippet})")

    assert not offenders, (
        "HTTP 500 responses must use a static `detail` string (e.g. "
        '"Internal server error") and never leak the caught exception — in either '
        "the keyword or positional form. Log the full error server-side instead. "
        "Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_no_disclosure_in_500_exception_handlers() -> None:
    offenders: list[str] = []
    for path in _backend_python_files():
        text = path.read_text(encoding="utf-8")
        for line_no, snippet in _iter_handler_disclosures(text):
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}:{line_no}: {snippet}")

    assert not offenders, (
        "A FastAPI exception handler that returns HTTP 500 must not place the "
        "exception message (`str(exc)`) or its class name (`__class__.__name__`) "
        "into the response body — log it server-side instead. Offending sites:\n  "
        + "\n  ".join(offenders)
    )


def test_no_disclosure_in_json_500_responses() -> None:
    offenders: list[str] = []
    for path in _backend_python_files():
        text = path.read_text(encoding="utf-8")
        for line_no, snippet in _iter_json_500_disclosures(text):
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}:{line_no}: JSONResponse({snippet})")

    assert not offenders, (
        "A raw JSONResponse with status_code=500 must not embed the caught "
        "exception in its body — return a static message and log the error "
        "server-side instead. Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_guard_detects_a_synthetic_leak() -> None:
    """The HTTPException scanner flags every dynamic-detail shape, keyword and positional."""
    leaks = [
        "raise HTTPException(status_code=500, detail=str(e))",
        'raise HTTPException(status_code=500, detail=f"failed: {e}")',
        "raise HTTPException(status_code=500, detail=error_msg)",  # bare variable
        'raise HTTPException(status_code=500, detail={"message": error_msg})',  # dict
        "raise HTTPException(500, str(e))",  # positional detail
        'raise HTTPException(500, f"boom: {e}")',  # positional f-string
    ]
    for leak in leaks:
        assert list(_iter_500_dynamic_detail(leak)), f"scanner missed a real 500 leak: {leak}"

    # Static string literals are the only safe form — keyword or positional.
    safe = [
        'raise HTTPException(status_code=500, detail="Internal server error")',
        'raise HTTPException(500, "Internal server error")',
    ]
    for s in safe:
        assert not list(_iter_500_dynamic_detail(s)), f"scanner false-positived: {s}"

    # 4xx responses echo client-supplied input and are intentionally out of scope.
    client_errs = [
        "raise HTTPException(status_code=400, detail=str(exc))",
        "raise HTTPException(400, str(exc))",
    ]
    for c in client_errs:
        assert not list(_iter_500_dynamic_detail(c)), f"scanner must ignore 4xx: {c}"


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

    client_err = (
        "@app.exception_handler(ValueError)\n"
        "async def h(request, exc):\n"
        '    return JSONResponse(status_code=400, content={"detail": str(exc)})\n'
    )
    assert not list(
        _iter_handler_disclosures(client_err)
    ), "handler scanner must ignore 4xx handlers"


def test_guard_detects_a_synthetic_json_500_leak() -> None:
    """The JSONResponse scanner flags exception disclosure across nested braces."""
    leaks = [
        'return JSONResponse({"error": str(exc)}, status_code=500)',
        'JSONResponse(content={"m": f"failed: {e}"}, status_code=500)',
        'JSONResponse({"error": str(error)}, status_code=500)',
    ]
    for leak in leaks:
        assert list(_iter_json_500_disclosures(leak)), f"json scanner missed: {leak}"

    safe = 'JSONResponse({"error": "Internal server error"}, status_code=500)'
    assert not list(_iter_json_500_disclosures(safe)), "json scanner false-positived"

    # 4xx JSONResponses may echo client input.
    client_err = 'JSONResponse({"detail": str(exc)}, status_code=400)'
    assert not list(
        _iter_json_500_disclosures(client_err)
    ), "json scanner must ignore 4xx"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
