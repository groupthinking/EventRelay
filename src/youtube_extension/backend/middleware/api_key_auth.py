"""
Optional API key authentication middleware.
When EVENTRELAY_API_KEY is set, requires X-API-Key header on mutation endpoints.
When not set, all requests pass through (development mode).
"""
import logging
import os

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

PROTECTED_PREFIXES = ["/api/v1/video-to-software", "/api/v1/process-video", "/api/v1/transcript-action"]
EXEMPT_METHODS = {"GET", "OPTIONS", "HEAD"}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str | None = None):
        super().__init__(app)
        self.api_key = api_key or os.getenv("EVENTRELAY_API_KEY")
        if self.api_key:
            logger.info("🔐 API key authentication enabled for pipeline endpoints")
        else:
            logger.warning("⚠️ No EVENTRELAY_API_KEY set — pipeline endpoints are unauthenticated")

    async def dispatch(self, request: Request, call_next):
        if not self.api_key:
            return await call_next(request)

        if request.method in EXEMPT_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
            provided_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            if provided_key != self.api_key:
                return Response(
                    content='{"error": "Invalid or missing API key", "hint": "Set X-API-Key header"}',
                    status_code=401,
                    media_type="application/json",
                )

        return await call_next(request)
