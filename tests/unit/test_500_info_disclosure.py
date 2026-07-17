"""Regression guard against information disclosure in HTTP 500 responses.

Context: several FastAPI handlers historically raised
``HTTPException(status_code=500, detail=str(e))`` (or an f-string / dict
embedding the exception), leaking internal exception text — stack-adjacent
messages, backend API errors, database errors — to clients (CWE-209). See PR
#801, which sanitized most but not all handlers.

This test encodes the invariant directly on the source of the routers this PR
hardens: a 500 response must use a *static* string ``detail``, never one derived
from the caught exception or any runtime value. The scan is AST-based, so it
catches every call form — positional ``HTTPException(500, str(e))`` and keyword
``HTTPException(status_code=500, detail=...)`` alike, and flags ``str(...)``,
f-strings, dicts, and bare variables such as ``detail=error_msg``. It is hermetic
(no app import / no pydantic) so it runs anywhere.

Scope note: ``_GUARDED_FILES`` is deliberately limited to the routers sanitized
here. Other backend modules still carry legacy dynamic 500 details (e.g.
``api/advanced_video_routes.py``); hardening those is tracked separately. Add a
router to ``_GUARDED_FILES`` once it has been sanitized to bring it under guard —
that is the intended way to widen coverage.

It deliberately does not constrain 4xx responses: those echo client-supplied
validation errors, which are not internal-disclosure vectors.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "src" / "youtube_extension" / "backend"

# Routers sanitized by this PR — the invariant is enforced exactly here.
_GUARDED_FILES = (
    "cloud_ai_routes.py",
    "cloud_api_endpoints.py",
    "real_api_endpoints.py",
)


def _is_httpexception(call: ast.Call) -> bool:
    func = call.func
    return (isinstance(func, ast.Name) and func.id == "HTTPException") or (
        isinstance(func, ast.Attribute) and func.attr == "HTTPException"
    )


def _is_500(call: ast.Call) -> bool:
    # Positional form: HTTPException(500, ...)
    if call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == 500:
        return True
    # Keyword form: HTTPException(status_code=500, ...)
    for kw in call.keywords:
        if (
            kw.arg == "status_code"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value == 500
        ):
            return True
    return False


def _detail_node(call: ast.Call) -> ast.expr | None:
    # Keyword form: detail=...
    for kw in call.keywords:
        if kw.arg == "detail":
            return kw.value
    # Positional form: HTTPException(<status>, <detail>)
    if len(call.args) >= 2:
        return call.args[1]
    return None


def _iter_500_dynamic_detail(text: str):
    """Yield (line_no, snippet) for each 500 ``HTTPException`` whose ``detail`` is
    anything other than a static string literal."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_httpexception(node):
            continue
        if not _is_500(node):
            continue
        detail = _detail_node(node)
        if detail is None:
            continue  # no detail argument at all — nothing to leak
        # A static string literal is the only safe form.
        if isinstance(detail, ast.Constant) and isinstance(detail.value, str):
            continue
        yield node.lineno, ast.unparse(node)[:160]


def test_no_dynamic_detail_in_500_responses() -> None:
    offenders: list[str] = []
    for name in _GUARDED_FILES:
        path = _BACKEND / name
        assert path.exists(), f"guarded file no longer exists: {name}"
        for line_no, snippet in _iter_500_dynamic_detail(path.read_text(encoding="utf-8")):
            offenders.append(f"{name}:{line_no}: {snippet}")

    assert not offenders, (
        "HTTP 500 responses must use a static `detail` string (e.g. "
        '"Internal server error") and never leak the caught exception or any '
        "runtime value. Log the full error server-side instead. Offending sites:\n  "
        + "\n  ".join(offenders)
    )


def test_guard_detects_synthetic_leaks() -> None:
    """Sanity check: the scanner flags every dynamic 500 detail form and ignores
    static details and 4xx responses."""
    leaky = [
        "raise HTTPException(status_code=500, detail=str(e))",
        "raise HTTPException(500, str(e))",  # positional status + detail
        'raise HTTPException(status_code=500, detail=f"failed: {e}")',
        "raise HTTPException(status_code=500, detail=error_msg)",  # bare variable
        'raise HTTPException(status_code=500, detail={"message": str(e)})',  # dict
    ]
    for src in leaky:
        assert list(_iter_500_dynamic_detail(src)), f"scanner missed a real leak: {src}"

    safe = [
        'raise HTTPException(status_code=500, detail="Internal server error")',
        'raise HTTPException(500, "Internal server error")',
        "raise HTTPException(status_code=400, detail=str(exc))",  # 4xx echoes client input
        "raise HTTPException(status_code=429, detail=f'Rate limit: {e}')",
    ]
    for src in safe:
        assert not list(
            _iter_500_dynamic_detail(src)
        ), f"scanner false-positived: {src}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
