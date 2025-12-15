#!/usr/bin/env python3
"""
Refactored FastAPI Backend for YouTube Extension
==============================================

SERVICE-ORIENTED ARCHITECTURE
- Extracted business logic into dedicated services
- Implemented dependency injection for better testability
- Separated concerns for improved maintainability
- Added comprehensive error handling and monitoring

This refactored version maintains full backward compatibility
while providing a more modular and scalable architecture.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project paths for imports
project_root = Path(__file__).parent.parent
# REMOVED: sys.path.insert for project_root

# Import services and container
from backend.containers.service_container import get_service_container, get_service
from backend.services.video_processing_service import VideoProcessingService, resolve_deployment_target
from backend.services.cache_service import CacheService
from backend.services.health_monitoring_service import HealthMonitoringService
from backend.services.data_service import DataService
from backend.services.websocket_service import WebSocketService, WebSocketConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize service container
service_container = get_service_container()

# Pydantic Models (extracted from original main.py)
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "tooltip-assistant"
    session_id: Optional[str] = "default"

class VideoToSoftwareRequest(BaseModel):
    video_url: str
    project_type: str = "web"
    deployment_target: str = "vercel"
    features: Optional[List[str]] = []

class ChatResponse(BaseModel):
    response: str
    status: str
    session_id: str
    timestamp: datetime

class VideoProcessingRequest(BaseModel):
    video_url: str
    options: Optional[Dict[str, Any]] = {}

class VideoProcessingResponse(BaseModel):
    result: Dict[str, Any]
    status: str
    progress: Optional[float] = 0.0
    timestamp: datetime

class MarkdownRequest(BaseModel):
    video_url: str
    force_regenerate: Optional[bool] = False

class MarkdownResponse(BaseModel):
    video_id: str
    video_url: str
    metadata: Dict[str, Any]
    markdown_content: str
    cached: bool
    save_path: str
    processing_time: str
    status: str

# Service Dependencies
def get_video_processing_service() -> VideoProcessingService:
    """Dependency injection for video processing service"""
    return get_service('video_processing_service')

def get_cache_service() -> CacheService:
    """Dependency injection for cache service"""
    return get_service('cache_service')

def get_health_monitoring_service() -> HealthMonitoringService:
    """Dependency injection for health monitoring service"""
    return get_service('health_monitoring_service')

def get_data_service() -> DataService:
    """Dependency injection for data service"""
    return get_service('data_service')

def get_websocket_service() -> WebSocketService:
    """Dependency injection for WebSocket service"""
    return get_service('websocket_service')

def get_websocket_manager() -> WebSocketConnectionManager:
    """Dependency injection for WebSocket connection manager"""
    return get_service('websocket_connection_manager')

# Create FastAPI app
app = FastAPI(
    title="YouTube Extension API",
    description="Service-Oriented Backend API for YouTube Extension with MCP integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://youtube-extension-frontend.vercel.app",
        "https://youtube-extension-frontend-jxk2359s8-garvs-projects-5153e7c7.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoints
@app.get("/health")
async def health_check(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service),
    websocket_manager: WebSocketConnectionManager = Depends(get_websocket_manager)
):
    """Basic health check endpoint"""
    try:
        video_processor_factory = get_service('video_processor_factory')
        health_status = health_service.get_basic_health_status(
            video_processor_factory, websocket_manager
        )
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/connectors/health")
async def connectors_health(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service)
):
    """External connectors health check"""
    try:
        connector_health = health_service.check_external_connectors_health()
        return connector_health
    except Exception as e:
        logger.error(f"Connector health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service)
):
    """Prometheus-formatted metrics endpoint"""
    try:
        metrics_lines = health_service.get_metrics_prometheus_format()
        return JSONResponse(content="\n".join(metrics_lines), media_type="text/plain")
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chat Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    video_processing_service: VideoProcessingService = Depends(get_video_processing_service)
):
    """Handle chat requests with AI processing"""
    try:
        logger.info(f"Chat request received: {request.message[:50]}...")
        
        # Simple AI response (can be extended with dedicated chat service)
        processor = video_processing_service.get_video_processor()
        
        if processor:
            response_text = f"AI Assistant: I received your message: '{request.message}'. I'm here to help with video processing and analysis! Please provide a YouTube URL for video processing."
        else:
            response_text = f"AI Assistant: I received your message: '{request.message}'. (Video processor unavailable - please check configuration)"
        
        response = ChatResponse(
            response=response_text,
            status="success",
            session_id=request.session_id,
            timestamp=datetime.now()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Video Processing Endpoints
@app.post("/api/process-video-markdown", response_model=MarkdownResponse)
async def process_video_markdown(
    request: MarkdownRequest,
    video_processing_service: VideoProcessingService = Depends(get_video_processing_service),
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service)
):
    """Process video and return markdown-formatted learning guide"""
    # Rate limiting check
    if not health_service.rate_limit_check():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    health_service.increment_metric("requests_total")
    health_service.increment_metric("process_video_markdown_total")
    
    try:
        logger.info(f"Markdown processing request: {request.video_url}")
        
        if not request.video_url:
            raise HTTPException(status_code=400, detail="Video URL required")
        
        # Process video using service
        result = await video_processing_service.process_video_for_markdown(
            request.video_url, request.force_regenerate
        )
        
        # Update metrics
        if result['cached']:
            health_service.increment_metric("cached_total")
        health_service.increment_metric("success_total")
        
        return MarkdownResponse(**result)
        
    except HTTPException:
        health_service.increment_metric("error_total")
        raise
    except Exception as e:
        logger.error(f"Error in markdown processing: {e}")
        health_service.increment_metric("error_total")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-video", response_model=VideoProcessingResponse)
async def process_video_endpoint(
    request: VideoProcessingRequest,
    video_processing_service: VideoProcessingService = Depends(get_video_processing_service)
):
    """Basic video processing endpoint"""
    try:
        logger.info(f"Video processing request: {request.video_url}")
        
        if not request.video_url:
            raise HTTPException(status_code=400, detail="Video URL required")
        
        # Process video using service
        result = await video_processing_service.process_video_basic(
            request.video_url, request.options
        )
        
        return VideoProcessingResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in video processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video-to-software")
async def video_to_software_endpoint(
    request: VideoToSoftwareRequest,
    video_processing_service: VideoProcessingService = Depends(get_video_processing_service)
):
    """Convert YouTube video to deployed software"""
    try:
        logger.info(f"Video-to-software request: {request.video_url}")
        target_info = resolve_deployment_target(request.deployment_target)
        
        result = await video_processing_service.process_video_to_software(
            request.video_url,
            request.project_type,
            target_info["resolved"],
            request.features
        )

        result.setdefault("deployment", {})
        result["deployment"]["requested_target"] = target_info["requested"]
        result["deployment"]["resolved_target"] = target_info["resolved"]
        result["deployment"]["alias_applied"] = target_info.get("alias_applied", False)
        result["deployment_target"] = target_info["requested"]
        
        return result
        
    except Exception as e:
        logger.error(f"Video-to-software processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/video-to-software/health")
async def video_to_software_health(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service)
):
    """Check health of video-to-software pipeline"""
    try:
        pipeline_health = health_service.check_video_to_software_pipeline_health()
        return pipeline_health
    except Exception as e:
        logger.error(f"Pipeline health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Cache Management Endpoints
@app.get("/api/markdown/{video_id}")
async def get_markdown_analysis(
    video_id: str,
    format: str = "markdown",
    cache_service: CacheService = Depends(get_cache_service)
):
    """Get cached markdown analysis by video ID"""
    try:
        cache_info = cache_service.get_video_cache_info(video_id)
        
        if not cache_info:
            raise HTTPException(
                status_code=404, 
                detail=f"Markdown analysis not found for video ID: {video_id}"
            )
        
        return cache_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving markdown analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cache/{video_id}")
async def clear_video_cache(
    video_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """Clear cache for specific video"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        cache_service.clear_cache(video_url)
        
        return {
            "status": "success",
            "message": f"Cache cleared for video: {video_id}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cache")
async def clear_all_cache(
    cache_service: CacheService = Depends(get_cache_service)
):
    """Clear all cached results"""
    try:
        cache_service.clear_cache()
        
        return {
            "status": "success",
            "message": "All cache cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing all cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/stats")
async def get_cache_stats(
    cache_service: CacheService = Depends(get_cache_service)
):
    """Get cache statistics"""
    try:
        stats = cache_service.get_cache_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data Endpoints
@app.get("/results/learning_log")
async def get_learning_log(
    data_service: DataService = Depends(get_data_service)
):
    """Get learning log from enhanced analysis files"""
    try:
        learning_log = data_service.get_learning_log()
        return learning_log
    except Exception as e:
        logger.error(f"Error getting learning log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/videos")
async def get_videos_summary(
    data_service: DataService = Depends(get_data_service)
):
    """Get summary list of processed videos"""
    try:
        videos_summary = data_service.get_videos_summary()
        return videos_summary
    except Exception as e:
        logger.error(f"Error getting videos summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/videos/{video_id}")
async def get_video_detail(
    video_id: str,
    data_service: DataService = Depends(get_data_service)
):
    """Get detailed info for specific video"""
    try:
        video_detail = data_service.get_video_detail(video_id)
        
        if not video_detail:
            raise HTTPException(
                status_code=404, 
                detail=f"Video not found: {video_id}"
            )
        
        return video_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def post_feedback(
    payload: Dict[str, Any],
    data_service: DataService = Depends(get_data_service)
):
    """Accept and save feedback data"""
    try:
        success = data_service.save_feedback(payload)
        
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save feedback")
            
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_service: WebSocketService = Depends(get_websocket_service)
):
    """WebSocket endpoint for real-time communication"""
    await websocket_service.handle_websocket_connection(websocket)

# System Management Endpoints
@app.get("/system/status")
async def system_status():
    """Get comprehensive system status"""
    try:
        container_health = service_container.health_check()
        
        # Add additional system information
        system_info = {
            "system_status": container_health,
            "api_version": "2.0.0",
            "architecture": "service-oriented",
            "services_count": len(service_container.get_all_services()),
            "timestamp": datetime.now().isoformat()
        }
        
        return system_info
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/services")
async def list_services():
    """List all registered services"""
    try:
        services = service_container.get_all_services()
        return {
            "services": services,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with enhanced error details"""
    logger.error(f"Unhandled exception: {exc}")
    
    error_detail = {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url) if hasattr(request, 'url') else "unknown",
        "architecture": "service-oriented"
    }
    
    if hasattr(exc, '__class__'):
        error_detail["error_type"] = exc.__class__.__name__
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 Starting YouTube Extension API (Service-Oriented Architecture)")
    logger.info("✅ All services initialized via dependency injection")
    
    # Verify critical services
    try:
        video_service = get_service('video_processing_service')
        cache_service = get_service('cache_service')
        health_service = get_service('health_monitoring_service')
        
        logger.info("✅ Core services verified and ready")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("🛑 Shutting down YouTube Extension API")
    
    try:
        await service_container.shutdown()
        logger.info("✅ All services shutdown completed")
        
    except Exception as e:
        logger.warning(f"Service shutdown warning: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
