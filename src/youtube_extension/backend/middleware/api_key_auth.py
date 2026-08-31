"""
API key authentication middleware (deny-by-default).

Security model
--------------
Every route requires a valid ``X-API-Key`` header EXCEPT an explicit, minimal
public allowlist (health, docs, openapi, root). This inverts the previous
opt-in allow-list, which left most endpoints — including all GET data
endpoints and destructive operations (e.g. ``DELETE /api/v1/cache``) —
unauthenticated.

Configuration
-------------
- ``EVENTRELAY_API_KEY`` set    -> every non-public route (all methods) requires it.
- ``EVENTRELAY_API_KEY`` unset  -> the app FAILS CLOSED (HTTP 503) on non-public
  routes, UNLESS ``ALLOW_UNAUTHENTICATED=1`` is set as an explicit local-dev
  opt-in (requests then pass through with a loud warning).

The key comparison uses :func:`hmac.compare_digest` (constant-time) to avoid a
timing side-channel.
"""

import hmac
import logging
import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Intentionally public, unauthenticated routes. Keep this list minimal.
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/health",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)

_TRUTHY = {"1", "true", "yes", "on"}

_UNAUTHORIZED_BODY = (
    b'{"error":"Authentication required",' b'"hint":"Send a valid X-API-Key header"}'
)
_MISCONFIGURED_BODY = (
    b'{"error":"Service unavailable",'
    b'"detail":"Server authentication is not configured. Set EVENTRELAY_API_KEY '
    b'(production) or ALLOW_UNAUTHENTICATED=1 (local development)."}'
)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Deny-by-default API key authentication."""

    def __init__(self, app, api_key: str | None = None) -> None:
        super().__init__(app)
        self.api_key = (
            api_key if api_key is not None else os.getenv("EVENTRELAY_API_KEY")
        )
        self.allow_unauthenticated = (
            os.getenv("ALLOW_UNAUTHENTICATED", "").strip().lower() in _TRUTHY
        )
        if self.api_key:
            logger.info("🔐 API key authentication enabled (deny-by-default).")
        elif self.allow_unauthenticated:
            logger.warning(
                "⚠️ EVENTRELAY_API_KEY is unset and ALLOW_UNAUTHENTICATED=1 — "
                "ALL endpoints are OPEN. Never use this configuration in production."
            )
        else:
            logger.error(
                "🚫 EVENTRELAY_API_KEY is unset — non-public endpoints will return "
                "HTTP 503. Set EVENTRELAY_API_KEY (production) or "
                "ALLOW_UNAUTHENTICATED=1 (local development)."
            )

    @staticmethod
    def _is_public(path: str) -> bool:
        # `/readyz` intentionally exposes only a boolean health signal so Cloud
        # Run can gate traffic on database readiness without storing an API key
        # in the probe. Do not make it a prefix: diagnostic children stay private.
        if path in {"/", "/readyz"}:
            return True
        return any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # CORS preflight and the public allowlist never require auth.
        if request.method == "OPTIONS" or self._is_public(path):
            return await call_next(request)

        # Local dev or test opt-in bypasses auth regardless of ambient API key.
        if self.allow_unauthenticated:
            return await call_next(request)

        # Fail closed when the server has no key configured.
        if not self.api_key:
            return Response(
                content=_MISCONFIGURED_BODY,
                status_code=503,
                media_type="application/json",
            )

        provided = request.headers.get("x-api-key", "")
        try:
            authed = hmac.compare_digest(provided, self.api_key)
        except (ValueError, TypeError):
            # A non-ASCII (Latin-1 decoded) or otherwise invalid header value
            # makes hmac.compare_digest raise; treat it as unauthorized (401)
            # rather than letting it surface as a 500.
            authed = False
        if not authed:
            return Response(
                content=_UNAUTHORIZED_BODY,
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
