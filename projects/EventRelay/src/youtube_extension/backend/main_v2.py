#!/usr/bin/env python3
"""
Production-Ready FastAPI Backend for YouTube Extension
====================================================

SERVICE-ORIENTED ARCHITECTURE WITH API VERSIONING
- Modular service-based architecture with dependency injection
- API versioning for backward compatibility and future expansion
- Comprehensive OpenAPI documentation and validation
- Production-grade error handling, logging, and monitoring
- Zero breaking changes to existing API contracts

Version: 2.0.0
Architecture: Service-Oriented with IoC Container
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.utils import get_openapi

# Path setup for imports
project_root = Path(__file__).parent.parent

# Import services and container
from .containers.service_container import get_service_container
from .services.websocket_service import WebSocketService
from .services.database_optimizer import initialize_database_optimization, shutdown_database_optimization
from ..processors.video_processor import default_processor as video_processor

# Import API routers
from .api.v1.router import router as v1_router

# Import integrations router
try:
    from integrations.routes import router as integrations_router
except ImportError:
    integrations_router = None

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('youtube_extension_api.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# Load environment variables from project .env for local/dev use
# This ensures keys like GEMINI_API_KEY/GOOGLE_API_KEY are available
# even when uvicorn is not started with --env-file.
# -------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=False)
        logging.getLogger(__name__).info(f"Loaded environment from {env_path}")
except Exception as _env_err:  # noqa: F841 - best-effort only
    # Do not fail startup if dotenv is unavailable; env can come from OS
    pass

# -------------------------------------------------------------
# FastVLM Gemini Hybrid Integration
# Using proper package imports instead of sys.path manipulation
# The hybrid module is available as a sibling package
# -------------------------------------------------------------

# Initialize service container
service_container = get_service_container()

# Create FastAPI application
app = FastAPI(
    title="YouTube Extension API",
    description="""
    ## Service-Oriented Backend API for YouTube Extension
    
    **Architecture Features:**
    - 🏗️ **Service-Oriented Architecture** with dependency injection
    - 📋 **API Versioning** for backward compatibility  
    - 🔄 **Real-time WebSocket** communication
    - 📊 **Comprehensive Monitoring** and health checks
    - 🚀 **Production-ready** with proper error handling
    
    **Core Capabilities:**
    - **Video Processing**: AI-powered analysis of YouTube videos
    - **Markdown Generation**: Automated learning guides and summaries
    - **Video-to-Software**: Convert videos into deployable applications
    - **Caching System**: Intelligent caching for improved performance
    - **Real-time Communication**: WebSocket support for live updates
    
    **API Versions:**
    - **v1**: Current stable API with all core features
    - **Legacy**: Backward compatibility with original endpoints
    
    **MCP Integration:**
    - Multi-modal Content Processing with agent orchestration
    - Support for multiple LLM providers (Gemini, Claude, GPT-4)
    - Real-time video analysis and action generation
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "YouTube Extension API",
        "url": "https://github.com/uvai/youtube-extension",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Enhanced CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Development environments
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative dev server
        "http://localhost:3001",  # Additional dev port
        
        # Production environments
        "https://youtube-extension-frontend.vercel.app",
        "https://youtube-extension-frontend-jxk2359s8-garvs-projects-5153e7c7.vercel.app",
        
        # Vercel preview deployments
        "https://*.vercel.app",
        
        # Additional production domains
        "https://uvai.platform",
        "https://api.uvai.platform",
        "https://uvai.io",
        "https://www.uvai.io",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security headers middleware
from .middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=True,  # Enable HSTS in production with HTTPS
    hsts_max_age=31536000,  # 1 year
)

# Rate limiting middleware
from .middleware.rate_limiting import RateLimitMiddleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,  # Configurable via environment
    burst_size=20,
    exempt_paths=["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/health"],
)

# Include API version routers
app.include_router(v1_router)

# Include integrations router if available
if integrations_router:
    app.include_router(integrations_router)

# Root redirect to documentation
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation"""
    return RedirectResponse(url="/docs")

# Legacy API endpoints for backward compatibility
@app.get("/health")
async def legacy_health():
    """Legacy health endpoint - redirects to v1"""
    return RedirectResponse(url="/api/v1/health", status_code=308)

@app.post("/api/chat")
async def legacy_chat(request: dict):
    """Legacy chat endpoint - redirects to v1 with data preservation"""
    from fastapi import Request
    # For now, maintain the existing implementation for backward compatibility
    try:
        from backend.api.v1.models import ChatRequest, ChatResponse
        from backend.containers.service_container import get_service
        
        # Convert legacy request to new format
        chat_request = ChatRequest(**request)
        video_processing_service = get_service('video_processing_service')
        
        processor = video_processing_service.get_video_processor()
        
        if processor:
            response_text = f"AI Assistant: I received your message: '{chat_request.message}'. I'm here to help with video processing and analysis!"
        else:
            response_text = f"AI Assistant: I received your message: '{chat_request.message}'. (Video processor unavailable)"
        
        return {
            "response": response_text,
            "status": "success",
            "session_id": chat_request.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Legacy chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-video-markdown")
async def legacy_process_video_markdown(request: dict):
    """Legacy markdown processing endpoint"""
    try:
        from backend.api.v1.models import MarkdownRequest
        from backend.containers.service_container import get_service
        
        # Convert to new format
        markdown_request = MarkdownRequest(**request)
        video_processing_service = get_service('video_processing_service')
        health_service = get_service('health_monitoring_service')
        
        # Rate limiting
        if not health_service.rate_limit_check():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        health_service.increment_metric("requests_total")
        
        # Process video
        result = await video_processing_service.process_video_for_markdown(
            markdown_request.video_url, 
            markdown_request.force_regenerate
        )
        
        health_service.increment_metric("success_total")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Legacy markdown processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-video")
async def legacy_process_video(request: dict):
    """Legacy video processing endpoint"""
    try:
        from backend.api.v1.models import VideoProcessingRequest
        from backend.containers.service_container import get_service
        
        # Convert to new format
        video_request = VideoProcessingRequest(**request)
        video_processing_service = get_service('video_processing_service')
        
        # Process video
        result = await video_processing_service.process_video_basic(
            video_request.video_url,
            video_request.options
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Legacy video processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Other legacy endpoints with redirects
@app.get("/metrics")
async def legacy_metrics():
    """Legacy metrics endpoint"""
    return RedirectResponse(url="/api/v1/metrics", status_code=308)

@app.get("/connectors/health")
async def legacy_connectors_health():
    """Legacy connector health endpoint"""
    return RedirectResponse(url="/api/v1/health/detailed", status_code=308)

@app.delete("/api/cache/{video_id}")
async def legacy_clear_video_cache(video_id: str):
    """Legacy cache clearing endpoint"""
    return RedirectResponse(url=f"/api/v1/cache/{video_id}", status_code=308)

@app.get("/api/cache/stats")
async def legacy_cache_stats():
    """Legacy cache stats endpoint"""
    return RedirectResponse(url="/api/v1/cache/stats", status_code=308)

# WebSocket endpoint (no versioning needed for WebSocket)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    websocket_service: WebSocketService = service_container.get_service('websocket_service')
    await websocket_service.handle_websocket_connection(websocket)

# System management endpoints
@app.get("/system/info")
async def system_info():
    """Get comprehensive system information"""
    try:
        container_health = service_container.health_check()
        
        system_info = {
            "api_version": "2.0.0",
            "architecture": "service-oriented",
            "features": {
                "api_versioning": True,
                "dependency_injection": True,
                "websocket_support": True,
                "comprehensive_monitoring": True,
                "backward_compatibility": True
            },
            "services": {
                "total_registered": len(service_container.get_all_services()),
                "health_status": container_health["container"]
            },
            "api_endpoints": {
                "v1_endpoints": len(v1_router.routes),
                "legacy_endpoints": "maintained for backward compatibility",
                "websocket": "real-time communication enabled"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return system_info
        
    except Exception as e:
        logger.error(f"System info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced OpenAPI schema generation
def custom_openapi():
    """Generate enhanced OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="YouTube Extension API",
        version="2.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://uvai.io/logo.png"
    }
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.uvai.io",
            "description": "Production server"
        }
    ]
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    # Add custom tags
    openapi_schema["tags"] = [
        {
            "name": "API v1",
            "description": "Version 1 of the API - current stable release"
        },
        {
            "name": "Health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "Video Processing",
            "description": "Core video processing and analysis endpoints"
        },
        {
            "name": "Cache Management",
            "description": "Cache control and statistics endpoints"
        },
        {
            "name": "Data & Analytics",
            "description": "Data retrieval and analytics endpoints"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError with proper logging"""
    logger.error(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url) if hasattr(request, 'url') else "unknown"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with enhanced error details"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    error_detail = {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url) if hasattr(request, 'url') else "unknown",
        "version": "2.0.0",
        "architecture": "service-oriented"
    }
    
    if hasattr(exc, '__class__'):
        error_detail["error_type"] = exc.__class__.__name__
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 Starting YouTube Extension API v2.0.0")
    logger.info("📐 Architecture: Service-Oriented with Dependency Injection")
    logger.info("📋 API Versioning: v1 available at /api/v1/")
    logger.info("⚡ WebSocket: Real-time communication enabled at /ws")
    logger.info("📊 Documentation: Available at /docs and /redoc")
    
    try:
        # Verify critical services
        video_service = service_container.get_service('video_processing_service')
        cache_service = service_container.get_service('cache_service')
        health_service = service_container.get_service('health_monitoring_service')
        data_service = service_container.get_service('data_service')
        websocket_service = service_container.get_service('websocket_service')
        
        logger.info("✅ All critical services initialized and verified")
        # Initialize database optimization (connection pool and minimal schema for SQLite)
        await initialize_database_optimization()
        # Start parallel video processor for availability
        try:
            await parallel_processor.start()
        except Exception as e:
            logger.warning(f"Parallel processor not started: {e}")
        logger.info("🎯 API is ready to handle requests")
        
        # Log configuration summary
        config_summary = {
            # Pull from container configuration; HealthMonitoringService no longer exposes _rate_limit_rps
            "rate_limiting": getattr(service_container, "_config", {}).get("rate_limit_rps"),
            "cache_directory": cache_service.cache_dir,
            "websocket_connections": 0,
            "api_endpoints": len(app.routes)
        }
        logger.info(f"⚙️  Configuration: {config_summary}")
        
    except Exception as e:
        logger.error(f"❌ Critical service initialization failed: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("🛑 Shutting down YouTube Extension API")
    
    try:
        await service_container.shutdown()
        # Stop parallel processor and shutdown DB optimization
        try:
            await parallel_processor.stop()
        except Exception:
            pass
        try:
            await shutdown_database_optimization()
        except Exception:
            pass
        logger.info("✅ Graceful shutdown completed")
        
    except Exception as e:
        logger.warning(f"⚠️  Shutdown warning: {e}")

# Development server runner
if __name__ == "__main__":
    import uvicorn
    
    logger.info("🔧 Starting development server...")
    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )