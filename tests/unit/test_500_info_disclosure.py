"""Regression guard against information disclosure in HTTP 500 responses.

Context: several FastAPI handlers historically returned internal exception text
to clients via 500 responses (CWE-209) — through ``HTTPException`` details and
through ``JSONResponse`` bodies raised by global/middleware exception handlers.
Leaked shapes seen in this codebase:

* ``raise HTTPException(status_code=500, detail=str(e))``
* ``raise HTTPException(status_code=500, detail=f"... {e} ...")``
* ``raise HTTPException(status_code=500, detail=error_msg)``            (variable)
* ``raise HTTPException(status_code=500, detail={"message": error_msg})``  (dict)
* ``JSONResponse(status_code=500, content={"detail": str(exc),
  "path": str(request.url), "error_type": exc.__class__.__name__})``

This test encodes the invariant directly on the source (a pure AST scan — no app
import, no pydantic) so it runs anywhere and catches new leaks in *any* backend
route, global handler, or middleware, not only the ones fixed today. It covers
both 500 response constructors: ``HTTPException`` and ``JSONResponse``.

Rules:

* ``HTTPException(status_code=500, ...)``: ``detail`` must be an inline static
  string literal. Anything else — ``str(...)``, an f-string, a bare variable, a
  dict — is rejected (a 500 detail never legitimately needs to be computed).
* ``JSONResponse(status_code=500, ...)``: the ``content`` (or ``detail``) must
  not reference the caught exception or the request. A ``str(exc)`` / ``repr``,
  an f-string embedding the exception/request, a bare ``exc``/``e``/``error``
  name, or an attribute such as ``request.url`` / ``exc.__class__`` is rejected.
  Safe dynamic values — a ``uuid4()`` error id, a ``datetime.now().isoformat()``
  timestamp — are intentionally allowed.

It deliberately does not constrain 4xx responses: those echo client-supplied
validation input, which is not an internal-disclosure vector.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

<<<<<<< HEAD
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "src" / "youtube_extension" / "backend"
# The Ray Serve ML surface returns raw ``JSONResponse(...)`` bodies and lives
# outside ``backend/``; it must be scanned too or 500 leaks there go unguarded.
_ML_SERVE = _REPO_ROOT / "src" / "uvai" / "ml"
=======
_BACKEND = Path(__file__).resolve().parents[2] / "src" / "youtube_extension" / "backend"
>>>>>>> origin/main

# Identifiers that, when referenced inside a 500 body, indicate a leak of the
# caught exception or the inbound request.
_EXC_NAMES = {"e", "exc", "err", "error", "ex", "exception"}
_REQUEST_NAMES = {"request", "req"}
# Attributes that disclose internals when reached from an exception/request.
_LEAKY_ATTRS = {"url", "__class__", "args", "__cause__", "__context__"}


def _is_static_string(node: ast.AST) -> bool:
    """True iff *node* is an inline string literal (optionally concatenated)."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    # "a" "b" implicit concat / "a" + "b"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_static_string(node.left) and _is_static_string(node.right)
    return False


def _refs_exception_or_request(node: ast.AST) -> bool:
    """True if *node*'s subtree reads the caught exception or the request."""
    for leaf in ast.walk(node):
        if isinstance(leaf, ast.Name) and leaf.id in (_EXC_NAMES | _REQUEST_NAMES):
            return True
        if isinstance(leaf, ast.Attribute):
            if leaf.attr in _LEAKY_ATTRS:
                return True
            base = leaf.value
            if isinstance(base, ast.Name) and base.id in (_EXC_NAMES | _REQUEST_NAMES):
                return True
        if isinstance(leaf, ast.Call):
            fn = leaf.func
            if isinstance(fn, ast.Name) and fn.id in {"str", "repr", "format"}:
                if any(_refs_exception_or_request(a) for a in leaf.args):
                    return True
    return False


<<<<<<< HEAD
def _status_is_500(call: ast.Call, name: str) -> bool:
    for kw in call.keywords:
        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
            return kw.value.value == 500
    # The positional slot of ``status_code`` differs by constructor:
    #   HTTPException(status_code, detail, ...)  -> args[0]
    #   JSONResponse(content, status_code, ...)  -> args[1]
    idx = 1 if name == "JSONResponse" else 0
    if len(call.args) > idx and isinstance(call.args[idx], ast.Constant):
        return call.args[idx].value == 500
=======
def _status_is_500(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
            return kw.value.value == 500
    # positional status_code (JSONResponse(500, ...) / HTTPException(500, ...))
    if call.args and isinstance(call.args[0], ast.Constant):
        return call.args[0].value == 500
>>>>>>> origin/main
    return False


def _call_name(call: ast.Call) -> str | None:
    fn = call.func
    return getattr(fn, "id", None) or getattr(fn, "attr", None)


def _iter_500_leaks(text: str):
    """Yield (line_no, reason) for each 500 response that can leak internals."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ("HTTPException", "JSONResponse"):
            continue
<<<<<<< HEAD
        if not _status_is_500(node, name):
=======
        if not _status_is_500(node):
>>>>>>> origin/main
            continue
        # Check keyword arguments
        for kw in node.keywords:
            if name == "HTTPException" and kw.arg == "detail":
                if not _is_static_string(kw.value):
                    yield node.lineno, "HTTPException 500 detail is not a static string"
            elif name == "JSONResponse" and kw.arg in ("content", "detail"):
                if _refs_exception_or_request(kw.value):
                    yield node.lineno, "JSONResponse 500 body references the exception/request"
        # Check positional detail argument: HTTPException(status_code, detail)
        # args[0] is status_code (already checked by _status_is_500); args[1] is detail.
        if name == "HTTPException" and len(node.args) >= 2:
            if not _is_static_string(node.args[1]):
                yield node.lineno, "HTTPException 500 detail is not a static string"
<<<<<<< HEAD
        # Positional JSONResponse body: JSONResponse(<body>, status_code=500) and
        # the fully positional JSONResponse(<body>, 500). The content is always
        # args[0] for JSONResponse, regardless of how status_code is passed.
        if name == "JSONResponse" and node.args:
            if _refs_exception_or_request(node.args[0]):
                yield node.lineno, "JSONResponse 500 body references the exception/request"


def _guarded_python_files() -> list[Path]:
    files: list[Path] = []
    for root in (_BACKEND, _ML_SERVE):
        if root.exists():
            files.extend(root.rglob("*.py"))
    return sorted(files)
=======


def _backend_python_files() -> list[Path]:
    return sorted(_BACKEND.rglob("*.py"))
>>>>>>> origin/main


def test_no_information_disclosure_in_500_responses() -> None:
    offenders: list[str] = []
<<<<<<< HEAD
    for path in _guarded_python_files():
=======
    for path in _backend_python_files():
>>>>>>> origin/main
        text = path.read_text(encoding="utf-8")
        try:
            leaks = list(_iter_500_leaks(text))
        except SyntaxError as exc:  # pragma: no cover - source is valid Python
            raise AssertionError(f"could not parse {path}: {exc}") from exc
        for line_no, reason in leaks:
<<<<<<< HEAD
            rel = path.relative_to(_REPO_ROOT)
=======
            rel = path.relative_to(_BACKEND.parents[2])
>>>>>>> origin/main
            offenders.append(f"{rel}:{line_no}: {reason}")

    assert not offenders, (
        "HTTP 500 responses must not disclose internal details. Use a static "
        '"Internal server error" body and log the full exception server-side '
        "instead. Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_guard_detects_every_known_leak_shape() -> None:
    """Positive controls: the scanner flags each historical leak shape."""
    leaky_samples = [
        'raise HTTPException(status_code=500, detail=str(e))',
        'raise HTTPException(status_code=500, detail=f"boom: {e}")',
        'raise HTTPException(status_code=500, detail=error_msg)',
        'raise HTTPException(status_code=500, detail={"message": error_msg})',
        'return JSONResponse(status_code=500, content={"detail": str(exc)})',
        'return JSONResponse(status_code=500, content={"path": str(request.url)})',
        'return JSONResponse(status_code=500, content={"t": exc.__class__.__name__})',
        # Positional-argument form: HTTPException(status_code, detail)
        'raise HTTPException(500, str(e))',
        'raise HTTPException(500, f"internal: {exc}")',
        'raise HTTPException(500, error_msg)',
<<<<<<< HEAD
        # JSONResponse with a positional body (the real ml_serve leak shape) —
        # status via keyword and fully positional (body=args[0], status=args[1]).
        'return JSONResponse({"error": str(exc)}, status_code=500)',
        'return JSONResponse({"error": str(exc)}, 500)',
=======
>>>>>>> origin/main
    ]
    for sample in leaky_samples:
        assert list(_iter_500_leaks(sample)), f"scanner missed a real leak: {sample}"


def test_guard_allows_sanitized_and_safe_dynamic_bodies() -> None:
    """Negative controls: static bodies and safe dynamic values are allowed."""
    safe_samples = [
        'raise HTTPException(status_code=500, detail="Internal server error")',
        # Positional form with a static string is safe.
        'raise HTTPException(500, "Internal server error")',
        # 4xx echoing client input is out of scope.
        'raise HTTPException(status_code=400, detail=str(exc))',
        # A random error id + timestamp is not an internal-disclosure vector.
        'return JSONResponse(status_code=500, content={'
        '"id": f"FALLBACK_{uuid.uuid4().hex}", '
        '"message": "An unexpected error occurred.", '
        '"timestamp": datetime.now().isoformat()})',
    ]
    for sample in safe_samples:
        assert not list(_iter_500_leaks(sample)), f"scanner false-positived: {sample}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
