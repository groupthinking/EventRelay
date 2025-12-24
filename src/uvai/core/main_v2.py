"""
Thin wrapper exposing the canonical ASGI app under the `uvai.core` namespace.
Run with: uvicorn uvai.core.main_v2:app --reload
"""

from __future__ import annotations

try:
    from youtube_extension.backend.main_v2 import app as app  # noqa: F401
except Exception as import_error:
    raise RuntimeError(f"Failed to import canonical app: {import_error}")
