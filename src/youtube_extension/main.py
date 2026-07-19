#!/usr/bin/env python3
"""
Main FastAPI application for UVAI YouTube Extension
Provides the core API endpoints and integrates all services including cloud AI
"""

import logging
import os
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            environment=os.getenv("ENVIRONMENT", os.getenv("VERCEL_ENV", "development")),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[StarletteIntegration(), FastApiIntegration()],
            # Do not attach request headers/cookies/body/user IP to events.
            # send_default_pii=True shipped user PII + auth headers to Sentry.
            # Opt in per-event via set_user() where genuinely needed instead.
            send_default_pii=os.getenv("SENTRY_SEND_PII", "false").lower() == "true",
            stream_gen_ai_spans=True,  # Enable for LLM monitoring (works for OpenAI-compatible including Grok/xAI via openai client)
        )
        logger.info("Sentry initialized for backend with AI monitoring")
    except Exception as exc:
        logger.warning("Sentry init skipped: %s", exc)

# Create FastAPI application
app = FastAPI(
    title="EventRelay API",
    description="EventRelay - AI Infrastructure Automation Platform Generator",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS.
#
# Security (OWASP A05 — Security Misconfiguration): because we send
# ``allow_credentials=True``, every allowed origin can make *credentialed*
# cross-origin requests. Shipping ``http://localhost:*`` origins to production
# would let a page served from an attacker-controlled localhost app issue
# credentialed calls against the production API, so localhost origins are only
# enabled outside production. Production origins can be extended without a code
# change via the ``CORS_ALLOWED_ORIGINS`` env var (comma-separated). In
# production, any localhost/loopback origin supplied that way is rejected so a
# stray env var cannot re-open the loopback bypass this control closes.
# Coalesce empty/whitespace values so an explicitly-empty ENVIRONMENT="" in a
# production deploy cannot silently fall through to the permissive dev origins.
_ENVIRONMENT = (
    (os.getenv("ENVIRONMENT") or "").strip()
    or (os.getenv("VERCEL_ENV") or "").strip()
    or "development"
).lower()
_IS_PRODUCTION = _ENVIRONMENT == "production"

_PRODUCTION_ORIGINS = [
    "https://uvai.io",
    "https://www.uvai.io",
    "https://uvaiio.vercel.app",
]
_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:3001",
]


def _is_loopback_origin(origin: str) -> bool:
    """True for http(s)://localhost / 127.0.0.1 / [::1] (any port)."""
    host = urlparse(origin).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"}


# Wildcard/credentialed CORS is invalid and dangerous: the CORS spec forbids
# `Access-Control-Allow-Origin: *` together with credentials, and Starlette
# would happily echo a literal "*" or "null" origin, effectively allowing
# credentialed cross-origin requests from any/opaque origin. Reject these
# values outright so a stray env var cannot open that hole.
_FORBIDDEN_ORIGINS = {"*", "null"}
_EXTRA_ORIGINS = []
for _origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(","):
    _origin = _origin.strip()
    if not _origin:
        continue
    if _origin in _FORBIDDEN_ORIGINS:
        logger.warning(
            "Ignoring forbidden wildcard origin %r from CORS_ALLOWED_ORIGINS "
            "(incompatible with allow_credentials=True)",
            _origin,
        )
        continue
    if _IS_PRODUCTION and _is_loopback_origin(_origin):
        logger.warning(
            "Ignoring loopback origin %r from CORS_ALLOWED_ORIGINS in production", _origin
        )
        continue
    _EXTRA_ORIGINS.append(_origin)

_allowed_origins = list(dict.fromkeys(
    _PRODUCTION_ORIGINS + _EXTRA_ORIGINS + ([] if _IS_PRODUCTION else _DEV_ORIGINS)
))
logger.info("CORS allow_origins configured for %s: %s", _ENVIRONMENT, _allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# SlowAPIMiddleware is what actually ENFORCES `default_limits`. Without it the
# limiter object is inert and every endpoint accepts unlimited traffic.
app.add_middleware(SlowAPIMiddleware)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# API key auth middleware
try:
    from .backend.middleware.api_key_auth import APIKeyAuthMiddleware as APIKeyMiddleware

    app.add_middleware(APIKeyMiddleware)
    logger.info("API key auth middleware loaded")
except ImportError as e:
    logger.warning(f"API key auth middleware not available: {e}")

# Include Cloud AI routes
try:
    from .backend.cloud_ai_routes import router as cloud_ai_router

    app.include_router(cloud_ai_router)
    logger.info("Cloud AI routes loaded successfully")
except ImportError as e:
    logger.warning(f"Cloud AI routes not available: {e}")

# Include Event Routes
try:
    from .backend.api.event_routes import router as event_router

    app.include_router(event_router)
    logger.info("Event routes loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load event routes: {e}")

# Include API v1 Router (production endpoints - transcript-action, health, etc.)
try:
    from .backend.api.v1.router import router as api_v1_router

    app.include_router(api_v1_router)
    logger.info("API v1 router loaded successfully")
except Exception as e:
    logger.error(f"Failed to load API v1 router: {type(e).__name__}: {e}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "uvai-youtube-extension"}


@app.post("/test-sentry")
async def test_sentry() -> None:
    """Deliberate Sentry smoke error. Requires X-API-Key (middleware) and ALLOW_SENTRY_SMOKE=1."""
    if os.getenv("ALLOW_SENTRY_SMOKE") != "1":
        raise HTTPException(status_code=404, detail="Not found")
    raise RuntimeError("sentry-smoke")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "UVAI YouTube Extension API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": [
            "YouTube video processing",
            "Cloud AI integration (Google, AWS, Azure, Apple)",
            "Multi-provider video analysis",
            "Batch processing support",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.youtube_extension.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
