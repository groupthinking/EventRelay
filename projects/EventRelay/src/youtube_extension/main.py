#!/usr/bin/env python3
"""
Main FastAPI application for UVAI YouTube Extension
Provides the core API endpoints and integrates all services including cloud AI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="EventRelay API",
    description="EventRelay - AI Infrastructure Automation Platform Generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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

# Include Generator routes (Revenue Pipeline)
try:
    from .backend.api.generator_routes import router as generator_router
    app.include_router(generator_router)
    logger.info("Generator routes loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load generator routes: {e}")


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
            "Batch processing support"
        ]
    }

# Video processing endpoint (placeholder)
@app.post("/api/v1/process-video")
async def process_video(video_url: str):
    """Process a YouTube video (placeholder implementation)"""
    try:
        # TODO: Implement actual video processing logic
        return {
            "status": "success",
            "video_url": video_url,
            "message": "Video processing initiated"
        }
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "src.youtube_extension.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
