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
from http import HTTPStatus
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


def _named_status_code(name: str) -> int | None:
    """Resolve standard HTTP status symbols without importing application code."""
    if name.startswith("HTTP_"):
        code = name.removeprefix("HTTP_").split("_", 1)[0]
        if len(code) == 3 and code.isdigit():
            return int(code)
    member = HTTPStatus.__members__.get(name)
    return int(member) if member is not None else None


def _status_code_value(node: ast.AST, symbols: dict[str, int]) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        return symbols.get(node.id, _named_status_code(node.id))
    if isinstance(node, ast.Attribute):
        if node.attr == "value":
            return _status_code_value(node.value, symbols)
        return _named_status_code(node.attr)
    return None


def _status_symbol_table(tree: ast.Module) -> dict[str, int]:
    """Resolve module constants that alias literal or standard status values."""
    symbols: dict[str, int] = {}
    changed = True
    while changed:
        changed = False
        for node in tree.body:
            targets: list[ast.AST] = []
            value: ast.AST | None = None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            if value is None:
                continue
            status = _status_code_value(value, symbols)
            if status is None:
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and symbols.get(target.id) != status
                ):
                    symbols[target.id] = status
                    changed = True
    return symbols


def _status_is_server_error(
    call: ast.Call, name: str, symbols: dict[str, int]
) -> bool:
    for kw in call.keywords:
        if kw.arg == "status_code":
            status = _status_code_value(kw.value, symbols)
            return status is not None and 500 <= status <= 599
    # The positional slot of ``status_code`` differs by constructor:
    #   HTTPException(status_code, detail, ...)  -> args[0]
    #   JSONResponse(content, status_code, ...)  -> args[1]
    idx = 1 if name == "JSONResponse" else 0
    if len(call.args) > idx:
        status = _status_code_value(call.args[idx], symbols)
        return status is not None and 500 <= status <= 599
    return False


def _call_name(call: ast.Call) -> str | None:
    fn = call.func
    return getattr(fn, "id", None) or getattr(fn, "attr", None)


def _iter_500_leaks(text: str):
    """Yield (line_no, reason) for each 500 response that can leak internals."""
    tree = ast.parse(text)
    status_symbols = _status_symbol_table(tree)

    # Bind every response constructor to the exception aliases visible from
    # its enclosing handler.  The fixed conventional-name set remains useful
    # outside a handler, but it must not be the tree-wide security boundary:
    # ``except Exception as failure`` and aliases derived from ``failure`` are
    # equally sensitive.
    handler_taint_by_call: dict[int, set[str]] = {}
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler) or not handler.name:
            continue
        tainted = _tainted_names(handler)
        for child in ast.walk(handler):
            if isinstance(child, ast.Call):
                handler_taint_by_call.setdefault(id(child), set()).update(tainted)

    def _refs_server_error_state(call: ast.Call, value: ast.AST) -> bool:
        return _refs_exception_or_request(value) or _refs_any_name(
            value, handler_taint_by_call.get(id(call), set())
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ("HTTPException", "JSONResponse"):
            continue
        if not _status_is_server_error(node, name, status_symbols):
            continue
        # Check keyword arguments
        for kw in node.keywords:
            if name == "HTTPException" and kw.arg == "detail":
                if not _is_static_string(kw.value):
                    yield node.lineno, "HTTPException 500 detail is not a static string"
            elif name == "JSONResponse" and kw.arg in ("content", "detail"):
                if _refs_server_error_state(node, kw.value):
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
            if _refs_server_error_state(node, node.args[0]):
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
        'raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))',
        'raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))',
        'SERVER_FAILURE = status.HTTP_502_BAD_GATEWAY\n'
        'raise HTTPException(status_code=SERVER_FAILURE, detail=str(e))',
        'raise HTTPException(599, f"internal: {exc}")',
        # JSONResponse with a positional body (the real ml_serve leak shape) —
        # status via keyword and fully positional (body=args[0], status=args[1]).
        'return JSONResponse({"error": str(exc)}, status_code=500)',
        'return JSONResponse({"error": str(exc)}, 500)',
        'return JSONResponse({"error": str(exc)}, 503)',
        # A nonstandard handler name and intermediate alias must remain tainted
        # in the tree-wide 5xx scanner.
        "try:\n    pass\nexcept Exception as failure:\n"
        "    message = str(failure)\n"
        '    return JSONResponse({"error": message}, status_code=503)\n',
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
        'raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))',
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
# ``errors`` (plural) is scanned too: an AI/batch processor records per-step
# failures as a list of scalar strings under this key, so ``{"errors":
# [str(e)]}`` leaks the caught exception exactly like a scalar ``error`` field
# and a future regression could reintroduce CWE-209 while the guard stayed green.
_RESPONSE_ERROR_FIELDS = {"error", "error_message", "errors"}


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
    """Yield (line_no, reason) for responses that can expose an ``error`` value.

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

    def _error_values(scope: ast.AST):
        for node in ast.walk(scope):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value in _RESPONSE_ERROR_FIELDS
                    ):
                        yield node, value
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg in _RESPONSE_ERROR_FIELDS:
                        yield node, keyword.value

    def _uses_public_error_sanitizer(node: ast.AST) -> bool:
        return isinstance(node, ast.Call) and _call_name(node) in {
            "_client_safe_error",
            "_sanitize_public_error",
            "_sanitize_response_errors",
            "_sanitize_error_list",
        }

    # Pass 1: values that reference the exception/request by convention.
    for node, value in _error_values(tree):
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
        for node, value in _error_values(handler):
            line = getattr(value, "lineno", node.lineno)
            if _refs_any_name(value, tainted) and line not in seen:
                seen.add(line)
                yield line, reason

    # Response-model keyword arguments are client sinks even when their value
    # is not syntactically tied to the surrounding exception.  A processor can
    # return exception text through ``result.get("error")``; require an
    # explicit boundary sanitizer for every dynamic ``error=...`` value.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg not in _RESPONSE_ERROR_FIELDS:
                continue
            value = keyword.value
            line = getattr(value, "lineno", node.lineno)
            if (
                line not in seen
                and not _is_static_string(value)
                and not (
                    isinstance(value, ast.Constant) and value.value is None
                )
                and not _uses_public_error_sanitizer(value)
            ):
                seen.add(line)
                yield line, 'response model "error" value is not sanitized'

    # Flag the direct pass-through shape used by batch endpoints.  This narrow
    # data-flow rule follows values returned by the two processor entry points
    # that are allowed to carry diagnostic ``error`` records.
    processor_results: set[str] = set()
    for node in ast.walk(tree):
        targets: list[ast.AST]
        raw_value: ast.AST | None
        if isinstance(node, ast.Assign):
            targets, raw_value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, raw_value = [node.target], node.value
        else:
            continue
        if raw_value is None:
            continue
        value = raw_value.value if isinstance(raw_value, ast.Await) else raw_value
        if not isinstance(value, ast.Call) or _call_name(value) not in {
            "process_video",
            "batch_process_videos",
        }:
            continue
        for target in targets:
            processor_results.update(_assigned_names(target))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Name)
            and node.value.id in processor_results
            and node.lineno not in seen
        ):
            seen.add(node.lineno)
            yield node.lineno, "processor result is returned without error sanitization"


# ---------------------------------------------------------------------------
# Returned-exception disclosure — a service/adapter ``return``s exception text.
# ---------------------------------------------------------------------------
# The scans above model handlers that *raise* a 500 or *return* an ``error``-keyed
# body. A third live shape slips past both: a service method catches an exception
# and ``return``s its text as an ordinary value (string/tuple), which a caller
# then forwards to the client. The real leak was
# ``official_api.validate_video_url`` returning ``f"Video validation failed:
# {e}"`` as its ``message`` element, echoed verbatim by /api/v2/validate-video
# under ``"message"`` with HTTP 200 — a live CWE-209 path the endpoint's own 500
# handler never sees because the adapter swallows the exception and hands it back
# as data. This scan is scoped to files whose returned values reach a client and
# flags any ``return`` inside an ``except ... as <name>`` handler that carries the
# caught exception (or an alias assigned from it). ``raise`` and ``logger`` calls
# are not returns and are unaffected.
_RETURNED_EXCEPTION_FILES = {
    "official_api.py",
    "real_api_endpoints.py",
    "cloud_api_endpoints.py",
}


def _iter_returned_exception_leaks(text: str):
    """Yield (line_no, reason) for ``return``s that carry the caught exception."""
    tree = ast.parse(text)
    reason = "return value inside except handler carries the caught exception"
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler) or not handler.name:
            continue
        tainted = _tainted_names(handler)
        for node in ast.walk(handler):
            if (
                isinstance(node, ast.Return)
                and node.value is not None
                and _refs_any_name(node.value, tainted)
            ):
                yield node.lineno, reason


def test_no_returned_exception_in_guarded_files() -> None:
    offenders: list[str] = []
    for path in _guarded_python_files():
        if path.name not in _RETURNED_EXCEPTION_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, reason in _iter_returned_exception_leaks(text):
            rel = path.relative_to(_REPO_ROOT)
            offenders.append(f"{rel}:{line_no}: {reason}")

    assert not offenders, (
        "A service/adapter must not return the caught exception as a value that "
        "reaches a client (CWE-209). Return a static message and log the "
        "exception server-side. Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_returned_exception_guard_flags_and_allows() -> None:
    """Controls for the returned-exception scanner."""
    for leak in (
        # The real validate_video_url leak shape.
        "try:\n    pass\nexcept Exception as e:\n"
        '    return False, "", f"Video validation failed: {e}"\n',
        # A nonstandard handler name is still tracked.
        "try:\n    pass\nexcept ValueError as boom:\n"
        '    return False, "", f"Invalid URL: {boom}"\n',
        # An intermediate alias must not launder the taint.
        "try:\n    pass\nexcept Exception as failure:\n"
        "    msg = str(failure)\n"
        '    return False, "", msg\n',
        "try:\n    pass\nexcept Exception as exc:\n    return str(exc)\n",
    ):
        assert list(
            _iter_returned_exception_leaks(leak)
        ), f"scanner missed a returned-exception leak: {leak}"

    for safe in (
        # Static message inside a handler is fine (no binding referenced).
        "try:\n    pass\nexcept Exception as e:\n"
        '    return False, "", "Video validation failed"\n',
        # Logging the exception and raising a static 500 is fine — not a return.
        "try:\n    pass\nexcept Exception as e:\n"
        "    logger.error('failed', exc_info=True)\n"
        '    raise HTTPException(500, "Internal server error")\n',
        # A static alias is not tainted.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    msg = "Video validation failed"\n'
        '    return False, "", msg\n',
    ):
        assert not list(
            _iter_returned_exception_leaks(safe)
        ), f"scanner false-positived: {safe}"


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
        'x = {"error_message": str(e)}',
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
        'response = VideoAnalysisResponse(error=result.get("error"))',
        'response = VideoAnalysisResponse(error_message=state.error_message)',
        # Plural ``errors`` sink: a scalar exception string in the list leaks
        # just like a scalar ``error`` field.
        'x = {"errors": [str(e)]}',
        "try:\n    pass\nexcept Exception as failure:\n"
        '    return {"errors": [str(failure)]}\n',
        "async def endpoint():\n"
        "    result = await processor.batch_process_videos([])\n"
        "    return result\n",
        "async def endpoint():\n"
        "    result: dict[str, object] = await "
        "processor.batch_process_videos([])\n"
        "    return result\n",
    ):
        assert list(_iter_response_error_leaks(leak)), f"scanner missed a leak: {leak}"

    for safe in (
        'x = {"error": "Internal server error"}',
        'x = {"status": "error", "error": "Service unavailable"}',
        'x = {"error": "failed", "timestamp": datetime.now().isoformat()}',
        'x = {"error_message": "Internal server error"}',
        # Static body inside a nonstandard-named handler is fine.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    return {"error": "Internal server error"}\n',
        # A static alias (not derived from the exception) is not tainted.
        "try:\n    pass\nexcept Exception as failure:\n"
        '    message = "Internal server error"\n'
        '    return {"error": message}\n',
        'response = VideoAnalysisResponse(error=_sanitize_public_error('
        'result.get("error")))',
        # A static or sanitized plural ``errors`` collection is fine.
        'x = {"errors": ["Internal server error"]}',
        'x = {"errors": _sanitize_error_list(result.get("errors"))}',
        "async def endpoint():\n"
        "    result = await processor.batch_process_videos([])\n"
        "    return _sanitize_response_errors(result)\n",
        "async def endpoint():\n"
        "    result: dict[str, object] = await "
        "processor.batch_process_videos([])\n"
        "    return _sanitize_response_errors(result)\n",
    ):
        assert not list(
            _iter_response_error_leaks(safe)
        ), f"scanner false-positived: {safe}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
