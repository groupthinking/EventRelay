"""Regression tests for the CORS origin allowlist guard in ``youtube_extension.main``.

Because the API is served with ``allow_credentials=True``, a wildcard (``*``) or
``null`` origin in the allowlist causes Starlette to reflect *any* request origin
with credentials — the exact credentialed cross-origin bypass the OWASP A05 fix
closes. ``_is_concrete_origin`` must reject those (and any non-http(s) or
host-less value) so a stray ``CORS_ALLOWED_ORIGINS`` entry cannot re-open it.
"""

from __future__ import annotations

import pytest

from youtube_extension.main import _is_concrete_origin, _is_loopback_origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://uvai.io",
        "http://localhost:3000",
        "https://evil.com",  # concrete, even if untrusted — scheme+host check only
    ],
)
def test_concrete_origins_accepted(origin: str) -> None:
    assert _is_concrete_origin(origin) is True


@pytest.mark.parametrize(
    "origin",
    [
        "*",            # wildcard — unsafe with credentials
        "null",         # sandboxed-origin literal
        "",             # empty
        "uvai.io",      # missing scheme
        "ftp://uvai.io",  # non-http(s) scheme
        "https://",     # scheme without host
    ],
)
def test_non_concrete_origins_rejected(origin: str) -> None:
    assert _is_concrete_origin(origin) is False


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:8080", "http://127.0.0.1:3000", "http://[::1]:5173"],
)
def test_loopback_origins_detected(origin: str) -> None:
    assert _is_loopback_origin(origin) is True
