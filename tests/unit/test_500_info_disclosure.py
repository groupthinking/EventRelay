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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "src" / "youtube_extension" / "backend"
# The Ray Serve ML surface returns raw ``JSONResponse(...)`` bodies and lives
# outside ``backend/``; it must be scanned too or 500 leaks there go unguarded.
_ML_SERVE = _REPO_ROOT / "src" / "uvai" / "ml"

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


def _status_is_server_error(call: ast.Call, name: str) -> bool:
    for kw in call.keywords:
        if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
            status = kw.value.value
            return isinstance(status, int) and 500 <= status <= 599
    # The positional slot of ``status_code`` differs by constructor:
    #   HTTPException(status_code, detail, ...)  -> args[0]
    #   JSONResponse(content, status_code, ...)  -> args[1]
    idx = 1 if name == "JSONResponse" else 0
    if len(call.args) > idx and isinstance(call.args[idx], ast.Constant):
        status = call.args[idx].value
        return isinstance(status, int) and 500 <= status <= 599
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
        if not _status_is_server_error(node, name):
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


def test_no_information_disclosure_in_500_responses() -> None:
    offenders: list[str] = []
    for path in _guarded_python_files():
        text = path.read_text(encoding="utf-8")
        try:
            leaks = list(_iter_500_leaks(text))
        except SyntaxError as exc:  # pragma: no cover - source is valid Python
            raise AssertionError(f"could not parse {path}: {exc}") from exc
        for line_no, reason in leaks:
            rel = path.relative_to(_REPO_ROOT)
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
        'raise HTTPException(status_code=503, detail=str(e))',
        'raise HTTPException(599, f"internal: {exc}")',
        # JSONResponse with a positional body (the real ml_serve leak shape) —
        # status via keyword and fully positional (body=args[0], status=args[1]).
        'return JSONResponse({"error": str(exc)}, status_code=500)',
        'return JSONResponse({"error": str(exc)}, 500)',
        'return JSONResponse({"error": str(exc)}, 503)',
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


# ---------------------------------------------------------------------------
# Response-body disclosure — a third 500-class sink the scan above does not model.
# ---------------------------------------------------------------------------
# Some handlers do not *raise* but *return* a dict body — often a 200
# "degraded"/"failed" payload from a broad ``except Exception`` — that places the
# caught exception under an ``"error"`` key (e.g. ``return {"error": str(e)}``).
# That body reaches the client and leaks internal state exactly like a 500 detail
# would. The ``"error"`` key is targeted specifically: 4xx handlers echo
# client-supplied input under ``"detail"``, which is not a disclosure vector.
#
# The same shape exists more widely across the backend (services/, api/v1/
# router.py, websocket_service.py); sweeping those is tracked separately, so this
# guard is scoped to the request handlers hardened here. Add a file to
# ``_GUARDED_RESPONSE_FILES`` once its response bodies have been sanitized.
_GUARDED_RESPONSE_FILES = {"cloud_api_endpoints.py", "real_api_endpoints.py"}


def _refs_any_name(node: ast.AST, names: set[str]) -> bool:
    """True if *node*'s subtree reads any identifier in *names*."""
    return any(
        isinstance(leaf, ast.Name) and leaf.id in names for leaf in ast.walk(node)
    )


def _assigned_names(target: ast.AST) -> list[str]:
    """Names bound by an assignment target (handles tuple/list unpacking)."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        out: list[str] = []
        for elt in target.elts:
            out.extend(_assigned_names(elt))
        return out
    return []


def _tainted_names(handler: ast.ExceptHandler) -> set[str]:
    """Names that carry the caught exception's text within *handler*.

    Seeds with the handler-bound name and propagates to any variable assigned
    from an expression that references an already-tainted name — so an
    intermediate alias (``message = str(failure); {"error": message}``) does not
    launder the leak past the guard. Iterates to a fixpoint; taint is monotonic.
    """
    tainted = {handler.name} if handler.name else set()
    if not tainted:
        return tainted
    changed = True
    while changed:
        changed = False
        for node in ast.walk(handler):
            targets: list[ast.AST] = []
            value: ast.AST | None = None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value:
                targets, value = [node.target], node.value
            if value is not None and _refs_any_name(value, tainted):
                for tgt in targets:
                    for name in _assigned_names(tgt):
                        if name not in tainted:
                            tainted.add(name)
                            changed = True
    return tainted


def _iter_response_error_leaks(text: str):
    """Yield (line_no, reason) for dict bodies that put the exception under "error".

    A value discloses the caught exception two ways, both flagged:

    * it references the request or a conventionally-named exception variable, or
      calls ``str``/``repr`` on one (via ``_refs_exception_or_request``); or
    * it references the identifier bound by the *enclosing*
      ``except ... as <name>`` handler — whatever that name is (``e``, ``exc``,
      ``failure`` …), so an ordinary rename cannot bypass the guard.
    """
    tree = ast.parse(text)
    seen: set[int] = set()
    reason = 'response body "error" field references the caught exception'

    def _error_dict_values(scope: ast.AST):
        for node in ast.walk(scope):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "error":
                    yield node, value

    # Pass 1: values that reference the exception/request by convention.
    for node, value in _error_dict_values(tree):
        line = getattr(value, "lineno", node.lineno)
        if _refs_exception_or_request(value) and line not in seen:
            seen.add(line)
            yield line, reason

    # Pass 2: values that reference the *enclosing* except handler's bound name
    # (including nonstandard names such as ``except Exception as failure``) or any
    # intermediate alias assigned from it (``message = str(failure)``).
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler) or not handler.name:
            continue
        tainted = _tainted_names(handler)
        for node, value in _error_dict_values(handler):
            line = getattr(value, "lineno", node.lineno)
            if _refs_any_name(value, tainted) and line not in seen:
                seen.add(line)
                yield line, reason


def test_no_exception_in_response_error_fields() -> None:
    offenders: list[str] = []
    for path in _guarded_python_files():
        if path.name not in _GUARDED_RESPONSE_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, reason in _iter_response_error_leaks(text):
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}:{line_no}: {reason}")

    assert not offenders, (
        'A response body must not place the caught exception under an "error" key '
        "(CWE-209), including on non-500 'degraded'/'failed' payloads. Return a "
        "static status string and log the exception server-side. Offending "
        "sites:\n  " + "\n  ".join(offenders)
    )


def test_response_body_guard_flags_and_allows() -> None:
    """Controls for the response-body scanner."""
    for leak in (
        'x = {"error": str(e)}',
        'x = {"status": "error", "error": str(exc)}',
        'x = {"error": f"failed: {e}"}',
        # A nonstandard exception name must not bypass the guard: the identifier
        # is derived from the enclosing `except ... as <name>` handler.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    return {"error": str(failure)}\n',
        "try:\n    pass\nexcept Exception as boom:\n    return {"
        '"status": "error", "error": boom}\n',
        # An intermediate alias must not launder the taint past the guard.
        "try:\n    pass\nexcept Exception as failure:\n"
        "    message = str(failure)\n"
        '    return {"error": message}\n',
        "try:\n    pass\nexcept Exception as failure:\n"
        '    detail = f"boom: {failure}"\n'
        '    return {"error": detail}\n',
    ):
        assert list(_iter_response_error_leaks(leak)), f"scanner missed a leak: {leak}"

    for safe in (
        'x = {"error": "Internal server error"}',
        'x = {"status": "error", "error": "Service unavailable"}',
        'x = {"error": "failed", "timestamp": datetime.now().isoformat()}',
        # Static body inside a nonstandard-named handler is fine.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    return {"error": "Internal server error"}\n',
        # A static alias (not derived from the exception) is not tainted.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    message = "Internal server error"\n'
        '    return {"error": message}\n',
    ):
        assert not list(
            _iter_response_error_leaks(safe)
        ), f"scanner false-positived: {safe}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
