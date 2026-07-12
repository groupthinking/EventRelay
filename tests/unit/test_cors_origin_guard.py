"""Regression tests for the CORS origin allowlist guard in ``youtube_extension.main``.

Because the API is served with ``allow_credentials=True``, a wildcard (``*``) or
the literal ``null`` in the allowlist causes Starlette to reflect *any* request
origin with credentials — the exact credentialed cross-origin bypass the OWASP
A05 fix closes. The env-driven ``CORS_ALLOWED_ORIGINS`` loop must therefore drop
those forbidden values and, in production, any loopback origin so a stray env var
cannot re-open the hole.
"""

from __future__ import annotations

import pytest

from youtube_extension.main import _FORBIDDEN_ORIGINS, _is_loopback_origin


@pytest.mark.parametrize("origin", ["*", "null"])
def test_wildcard_and_null_are_forbidden(origin: str) -> None:
    # These are unsafe with allow_credentials=True and must never reach the
    # CORS allowlist, regardless of environment.
    assert origin in _FORBIDDEN_ORIGINS


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:8080", "http://127.0.0.1:3000", "http://[::1]:5173"],
)
def test_loopback_origins_detected(origin: str) -> None:
    assert _is_loopback_origin(origin) is True


@pytest.mark.parametrize("origin", ["https://uvai.io", "https://www.uvai.io"])
def test_public_origins_not_loopback(origin: str) -> None:
    assert _is_loopback_origin(origin) is False
