#!/usr/bin/env python3
"""
Main FastAPI application for UVAI YouTube Extension
Provides the core API endpoints and integrates all services including cloud AI
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        "https://event-relay-web.vercel.app",
        "https://eventrelay-production.up.railway.app",
        "https://uvai.io",
        "https://www.uvai.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
