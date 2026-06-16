#!/usr/bin/env python3
"""
Main FastAPI application for UVAI YouTube Extension
Provides the core API endpoints and integrates all services including cloud AI
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="EventRelay API",
    description="EventRelay - AI Infrastructure Automation Platform Generator",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:3001",
        "https://uvai.io",
        "https://www.uvai.io",
        "https://uvaiio.vercel.app",
    ],
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
