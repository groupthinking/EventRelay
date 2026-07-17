"""Regression guard against information disclosure in HTTP 500 responses.

Context: several handlers historically raised
``HTTPException(status_code=500, detail=str(e))`` (or an f-string embedding the
exception), leaking internal exception text — stack-adjacent messages, backend
API errors, database errors — to clients. See PR #801, which sanitized most but
not all handlers.

This test encodes the invariant directly on the source: a 500 response must use
a *static* message, never one derived from the caught exception. It is hermetic
(pure source scan via ``ast``, no app import / no pydantic) so it runs anywhere
and catches new leaks in any route.

It uses a real **AST** analysis rather than a textual/regex scan, so idiomatic
variations cannot silently disable it:

  * status is recognized as the literal ``500`` **or** the FastAPI constant
    ``status.HTTP_500_INTERNAL_SERVER_ERROR``, in keyword or positional form,
    regardless of whitespace (``status_code = 500``);
  * the caught-exception variable is derived from the enclosing scope — an
    ``except ... as <name>`` target or an ``@app.exception_handler`` function's
    exception parameter — so an arbitrary name (``error``, ``problem``) is
    tracked, not just ``e``/``exc``;
  * leaks reached through a local variable (``msg = str(exc); {"error": msg}``)
    are caught by intra-function taint propagation, not only direct ``str(exc)``
    text in the call.

It models the three distinct 500 sinks in this codebase:
  1. ``HTTPException`` — keyword (``status_code=500, detail=...``) and positional
     (``HTTPException(500, str(e))``) forms. A 500 ``detail`` must be a static
     string literal.
  2. FastAPI ``@app.exception_handler`` functions that build a 500 body directly.
  3. A raw ``JSONResponse(..., status_code=500)`` (e.g. a Ray Serve deployment).

For (2) and (3) the body may legitimately contain non-exception dynamic values
(a correlation id, a UUID), so those sinks flag only values that are *derived
from the caught exception*, via taint tracking — not every dynamic value.

It deliberately does not constrain 4xx responses: those echo client-supplied
validation errors, which are not internal-disclosure vectors.

Scope: the whole deployed package ``src/youtube_extension`` (the production
entry point is ``youtube_extension.main:app`` per the Dockerfile, which lives
outside ``backend/``) plus the ``src/uvai/ml`` serving surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Scan the whole deployed package, not just backend/: the production entry point
# youtube_extension.main:app lives at src/youtube_extension/main.py, outside
# backend/. Also scan the uvai ML serving surface (raw JSONResponse 500s).
_ROOTS = [
    _REPO_ROOT / "src" / "youtube_extension",
    _REPO_ROOT / "src" / "uvai" / "ml",
]

# Fallback names treated as references to a caught exception when no structural
# binding is visible (e.g. a helper that takes the exception as a plain param:
# ``def to_500(exc): return JSONResponse({"error": str(exc)}, status_code=500)``).
# Names provably bound to a constant string in scope are excluded, so a benign
# ``error_message = "Internal server error"`` is not mistaken for a leak.
_EXC_TOKENS = {"e", "ex", "exc", "err", "error", "error_msg", "error_message", "exception"}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in _ROOTS:
        if root.exists():
            files.extend(root.rglob("*.py"))
    return sorted(set(files))


# --- AST helpers -----------------------------------------------------------

def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_500(expr: ast.expr | None) -> bool:
    """True if an expression denotes HTTP status 500 (literal or FastAPI constant)."""
    if isinstance(expr, ast.Constant) and expr.value == 500:
        return True
    # status.HTTP_500_INTERNAL_SERVER_ERROR / http.HTTPStatus.INTERNAL_SERVER_ERROR-style
    if isinstance(expr, ast.Attribute) and (
        expr.attr.startswith("HTTP_500") or expr.attr == "INTERNAL_SERVER_ERROR"
    ):
        return True
    return False


def _is_static_str(expr: ast.expr | None) -> bool:
    return isinstance(expr, ast.Constant) and isinstance(expr.value, str)


def _seg(text: str, node: ast.AST) -> str:
    seg = ast.get_source_segment(text, node)
    if not seg:
        return "<...>"
    return " ".join(seg.split())[:120]


# --- HTTPException status/detail -------------------------------------------

def _http_exc_is_500(call: ast.Call) -> bool:
    sc = _keyword(call, "status_code")
    if sc is not None:
        return _is_500(sc)
    # positional: HTTPException(status_code, detail, ...)
    return bool(call.args) and _is_500(call.args[0])


def _http_exc_detail(call: ast.Call) -> ast.expr | None:
    detail = _keyword(call, "detail")
    if detail is not None:
        return detail
    if len(call.args) >= 2:  # positional detail is the 2nd argument
        return call.args[1]
    return None


# --- JSONResponse status/content -------------------------------------------

def _json_is_500(call: ast.Call) -> bool:
    return _is_500(_keyword(call, "status_code"))


def _json_content(call: ast.Call) -> ast.expr | None:
    content = _keyword(call, "content")
    if content is not None:
        return content
    return call.args[0] if call.args else None


# --- taint: which names carry the caught exception -------------------------

def _is_handler(func: ast.AST) -> bool:
    for dec in getattr(func, "decorator_list", []):
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr == "exception_handler":
            return True
        if isinstance(target, ast.Name) and target.id == "exception_handler":
            return True
    return False


def _constant_str_names(func: ast.AST) -> set[str]:
    """Names provably assigned a constant string somewhere in this function."""
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and _is_static_str(node.value):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_static_str(node.value)
            and isinstance(node.target, ast.Name)
        ):
            names.add(node.target.id)
    return names


def _function_taint(func: ast.AST) -> set[str]:
    """Set of local names that carry (are derived from) the caught exception."""
    const_names = _constant_str_names(func)
    taint: set[str] = set(_EXC_TOKENS) - const_names

    # structural seeds: exception-handler param and `except ... as name`
    if _is_handler(func):
        params = getattr(getattr(func, "args", None), "args", [])
        if len(params) >= 2:  # FastAPI passes (request, exc)
            taint.add(params[1].arg)
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler) and node.name:
            taint.add(node.name)

    # intra-function propagation: x = <expr referencing a tainted name> -> x tainted
    changed = True
    while changed:
        changed = False
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and _expr_uses(node.value, taint):
                for tgt in node.targets:
                    if (
                        isinstance(tgt, ast.Name)
                        and tgt.id not in taint
                        and tgt.id not in const_names
                    ):
                        taint.add(tgt.id)
                        changed = True
    return taint


def _expr_uses(expr: ast.expr | None, taint: set[str]) -> bool:
    """True if the expression references any tainted (exception-derived) name."""
    if expr is None:
        return False
    for node in ast.walk(expr):
        if isinstance(node, ast.Name) and node.id in taint:
            return True
    return False


# --- unified scan ----------------------------------------------------------

def _scan(text: str):
    """Return (http_leaks, json_leaks, handler_leaks) as lists of (line, snippet)."""
    http_leaks: list[tuple[int, str]] = []
    json_leaks: list[tuple[int, str]] = []
    handler_leaks: list[tuple[int, str]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return http_leaks, json_leaks, handler_leaks

    module_taint = set(_EXC_TOKENS) - _constant_str_names(tree)

    def visit(node: ast.AST, taint: set[str], in_handler: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, taint | _function_taint(child), in_handler or _is_handler(child))
                continue
            if isinstance(child, ast.Call):
                name = _call_name(child)
                if name == "HTTPException" and _http_exc_is_500(child):
                    detail = _http_exc_detail(child)
                    if detail is not None and not _is_static_str(detail):
                        http_leaks.append((child.lineno, _seg(text, child)))
                elif name == "JSONResponse" and _json_is_500(child):
                    if _expr_uses(_json_content(child), taint):
                        target = handler_leaks if in_handler else json_leaks
                        target.append((child.lineno, _seg(text, child)))
            visit(child, taint, in_handler)

    visit(tree, module_taint, False)
    return http_leaks, json_leaks, handler_leaks


# --- the guards ------------------------------------------------------------

def test_no_dynamic_detail_in_500_responses() -> None:
    offenders: list[str] = []
    for path in _python_files():
        http_leaks, _, _ = _scan(path.read_text(encoding="utf-8"))
        rel = path.relative_to(_REPO_ROOT)
        offenders.extend(f"{rel}:{ln}: HTTPException({snip})" for ln, snip in http_leaks)

    assert not offenders, (
        "HTTP 500 responses must use a static `detail` string (e.g. "
        '"Internal server error") and never leak the caught exception — in either '
        "the keyword or positional form. Log the full error server-side instead. "
        "Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_no_disclosure_in_500_exception_handlers() -> None:
    offenders: list[str] = []
    for path in _python_files():
        _, _, handler_leaks = _scan(path.read_text(encoding="utf-8"))
        rel = path.relative_to(_REPO_ROOT)
        offenders.extend(f"{rel}:{ln}: {snip}" for ln, snip in handler_leaks)

    assert not offenders, (
        "A FastAPI exception handler that returns HTTP 500 must not place the "
        "caught exception (its message or class name, directly or via a local "
        "variable) into the response body — log it server-side instead. "
        "Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_no_disclosure_in_json_500_responses() -> None:
    offenders: list[str] = []
    for path in _python_files():
        _, json_leaks, _ = _scan(path.read_text(encoding="utf-8"))
        rel = path.relative_to(_REPO_ROOT)
        offenders.extend(f"{rel}:{ln}: JSONResponse({snip})" for ln, snip in json_leaks)

    assert not offenders, (
        "A raw JSONResponse with status_code=500 must not embed the caught "
        "exception in its body (directly or through a local variable) — return a "
        "static message and log the error server-side instead. Offending sites:\n  "
        + "\n  ".join(offenders)
    )


# --- self-tests: the guard actually bites ----------------------------------

def test_guard_detects_a_synthetic_leak() -> None:
    """The HTTPException scanner flags every dynamic-detail shape and idiom."""
    leaks = [
        "raise HTTPException(status_code=500, detail=str(e))",
        'raise HTTPException(status_code=500, detail=f"failed: {e}")',
        "raise HTTPException(status_code=500, detail=error_msg)",  # bare variable
        'raise HTTPException(status_code=500, detail={"message": error_msg})',  # dict
        "raise HTTPException(500, str(e))",  # positional detail
        'raise HTTPException(500, f"boom: {e}")',  # positional f-string
        'raise HTTPException(status_code=500, detail="Request failed: " + str(exc))',  # concat
        'raise HTTPException(500, "boom: " + str(e))',  # positional concat
        # AST-only wins over the old regex scan:
        "raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))",
        "raise HTTPException(status_code = 500, detail = str(exc))",  # whitespace
    ]
    for leak in leaks:
        http, _, _ = _scan(leak)
        assert http, f"scanner missed a real 500 leak: {leak}"

    # Static string literals are the only safe form — keyword or positional.
    safe = [
        'raise HTTPException(status_code=500, detail="Internal server error")',
        'raise HTTPException(500, "Internal server error")',
        "raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\"Internal server error\")",
    ]
    for s in safe:
        http, _, _ = _scan(s)
        assert not http, f"scanner false-positived: {s}"

    # 4xx responses echo client-supplied input and are intentionally out of scope.
    client_errs = [
        "raise HTTPException(status_code=400, detail=str(exc))",
        "raise HTTPException(400, str(exc))",
    ]
    for c in client_errs:
        http, _, _ = _scan(c)
        assert not http, f"scanner must ignore 4xx: {c}"


def test_guard_detects_a_synthetic_handler_leak() -> None:
    """The handler scanner derives the exception param name from the signature."""
    # Exception parameter is named `problem` (not e/exc): structural derivation,
    # not a hardcoded name list, must catch it.
    leaky = (
        "@app.exception_handler(Exception)\n"
        "async def h(request, problem):\n"
        '    logger.error(f"boom: {problem}", exc_info=True)\n'
        '    body = {"detail": str(problem), "error_type": problem.__class__.__name__}\n'
        "    return JSONResponse(status_code=500, content=body)\n"
    )
    _, _, handler = _scan(leaky)
    assert handler, "handler scanner missed a real leak reached via the handler param"

    safe = (
        "@app.exception_handler(Exception)\n"
        "async def h(request, exc):\n"
        '    logger.error(f"boom: {exc}", exc_info=True)\n'
        '    body = {"detail": "Internal server error"}\n'
        "    return JSONResponse(status_code=500, content=body)\n"
    )
    _, _, handler = _scan(safe)
    assert not handler, "handler scanner false-positived a sanitized 500 handler"

    client_err = (
        "@app.exception_handler(ValueError)\n"
        "async def h(request, exc):\n"
        '    return JSONResponse(status_code=400, content={"detail": str(exc)})\n'
    )
    _, _, handler = _scan(client_err)
    assert not handler, "handler scanner must ignore 4xx handlers"


def test_guard_detects_a_synthetic_json_500_leak() -> None:
    """The JSONResponse scanner flags direct and variable-indirection leaks."""
    leaks = [
        'return JSONResponse({"error": str(exc)}, status_code=500)',
        'JSONResponse(content={"m": f"failed: {e}"}, status_code=500)',
        'JSONResponse({"error": str(error)}, status_code=500)',
    ]
    for leak in leaks:
        # wrap in a function with a bound exception so this reflects real code
        src = (
            "def f():\n"
            "    try:\n"
            "        pass\n"
            "    except Exception as e:\n"
            f"        {leak}\n"
        )
        _, json_leaks, _ = _scan(src)
        assert json_leaks, f"json scanner missed: {leak}"

    # Variable indirection: msg is not literally str(exc) at the call site.
    indirection = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception as boom:\n"
        "        error_detail = str(boom)\n"
        '        return JSONResponse({"error": error_detail}, status_code=500)\n'
    )
    _, json_leaks, _ = _scan(indirection)
    assert json_leaks, "json scanner missed a variable-indirection leak (msg = str(exc))"

    # A non-exception dynamic value (correlation id) in a 500 body is allowed.
    allowed = (
        "def f():\n"
        "    correlation_id = new_id()\n"
        '    return JSONResponse({"error": "Internal server error", "id": correlation_id}, status_code=500)\n'
    )
    _, json_leaks, _ = _scan(allowed)
    assert not json_leaks, "json scanner false-positived a non-exception dynamic value"

    safe = (
        "def f():\n"
        '    return JSONResponse({"error": "Internal server error"}, status_code=500)\n'
    )
    _, json_leaks, _ = _scan(safe)
    assert not json_leaks, "json scanner false-positived a static 500 body"

    # 4xx JSONResponses may echo client input.
    client_err = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception as exc:\n"
        '        return JSONResponse({"detail": str(exc)}, status_code=400)\n'
    )
    _, json_leaks, _ = _scan(client_err)
    assert not json_leaks, "json scanner must ignore 4xx"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
