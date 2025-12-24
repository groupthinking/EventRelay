#!/usr/bin/env python3
"""
Real API Integration Endpoints
=============================

FastAPI endpoints that integrate real YouTube Data API, AI processing,
and cost monitoring instead of mock data.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import our real API services
from .services.real_video_processor import get_real_video_processor, process_video_real
from .services.real_youtube_api import get_youtube_service, get_video_data
from .services.real_ai_processor import get_ai_processor, analyze_video_with_ai
from .services.api_cost_monitor import cost_monitor

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class VideoProcessingRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL or ID")
    force_refresh: bool = Field(False, description="Skip cache and force fresh processing")
    include_related: bool = Field(True, description="Include related videos analysis")
    ai_analysis: bool = Field(True, description="Perform AI content analysis")

class VideoValidationRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL to validate")

class BatchProcessingRequest(BaseModel):
    video_urls: List[str] = Field(..., description="List of YouTube video URLs")
    max_concurrent: int = Field(3, description="Maximum concurrent processing tasks", ge=1, le=10)
    force_refresh: bool = Field(False, description="Skip cache for all videos")

class VideoAnalysisResponse(BaseModel):
    video_id: str
    video_url: str
    success: bool
    metadata: Optional[Dict[str, Any]] = None
    transcript: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    cost_breakdown: Optional[Dict[str, Any]] = None
    processing_time: float
    cached: bool = False
    error: Optional[str] = None

# Initialize real API services
def init_real_api_services():
    """Initialize real API services"""
    try:
        real_processor = get_real_video_processor()
        youtube_service = get_youtube_service()
        ai_processor = get_ai_processor()
        
        logger.info("✅ Real API services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize real API services: {e}")
        return False

# Real API Endpoints
def setup_real_api_endpoints(app: FastAPI):
    """Setup real API endpoints for FastAPI app"""
    
    @app.post("/api/v2/process-video", response_model=VideoAnalysisResponse)
    async def process_video_real_api(request: VideoProcessingRequest, background_tasks: BackgroundTasks):
        """
        Process video using real YouTube Data API and AI services
        
        This endpoint replaces mock data processing with:
        - Real YouTube Data API v3 integration
        - Multi-provider AI analysis (OpenAI/Anthropic/Gemini)
        - Real-time cost monitoring
        - Comprehensive error handling
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            logger.info(f"🎬 Real API processing request: {request.video_url}")
            
            # Get real video processor
            processor = get_real_video_processor()
            
            # Process video with real APIs
            result = await processor.process_video(
                video_url=request.video_url,
                force_refresh=request.force_refresh
            )
            
            # Track metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Format response
            response = VideoAnalysisResponse(
                video_id=result.get('video_id', ''),
                video_url=request.video_url,
                success=result.get('success', False),
                metadata=result.get('metadata'),
                transcript=result.get('transcript'),
                ai_analysis=result.get('ai_analysis'),
                cost_breakdown=result.get('cost_breakdown'),
                processing_time=processing_time,
                cached=result.get('cached', False),
                error=result.get('error')
            )
            
            logger.info(f"✅ Real API processing completed: {result.get('video_id')} - ${result.get('cost_breakdown', {}).get('total_cost', 0):.4f}")
            
            return response
            
        except Exception as e:
            error_msg = f"Real API processing failed: {str(e)}"
            logger.error(error_msg)
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "video_processing_failed",
                    "message": error_msg,
                    "video_url": request.video_url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    @app.post("/api/v2/validate-video")
    async def validate_video_url(request: VideoValidationRequest):
        """
        Validate YouTube video URL using real YouTube Data API
        """
        try:
            youtube_service = get_youtube_service()
            
            is_valid, video_id, message = await youtube_service.validate_video_url(request.video_url)
            
            return {
                "valid": is_valid,
                "video_id": video_id,
                "message": message,
                "video_url": request.video_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Validation failed: {str(e)}"
            )
    
    @app.post("/api/v2/batch-process")
    async def batch_process_videos(request: BatchProcessingRequest):
        """
        Process multiple videos concurrently with real APIs
        """
        try:
            if len(request.video_urls) > 20:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 20 videos allowed per batch request"
                )
            
            processor = get_real_video_processor()
            
            result = await processor.batch_process_videos(
                video_urls=request.video_urls,
                max_concurrent=request.max_concurrent
            )
            
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Batch processing failed: {str(e)}"
            )
    
    @app.get("/api/v2/videos/list")
    async def get_processed_videos_list():
        """
        Get list of processed videos from real processing cache
        """
        try:
            processor = get_real_video_processor()
            
            # Get cached processed videos
            cache_dir = processor.cache_dir
            processed_videos = []
            
            if cache_dir.exists():
                for cache_file in cache_dir.glob("*_processed.json"):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            video_data = json.load(f)
                        
                        processed_videos.append({
                            "id": video_data.get('video_id'),
                            "video_url": video_data.get('video_url'),
                            "title": video_data.get('metadata', {}).get('title', 'Unknown'),
                            "channel": video_data.get('metadata', {}).get('channel_title', 'Unknown'),
                            "duration": video_data.get('metadata', {}).get('duration', 'Unknown'),
                            "processed_at": video_data.get('timestamp'),
                            "has_transcript": video_data.get('transcript', {}).get('has_transcript', False),
                            "ai_analysis_success": video_data.get('ai_analysis', {}).get('success', False),
                            "total_cost": video_data.get('cost_breakdown', {}).get('total_cost', 0.0),
                            "analysis": video_data.get('ai_analysis', {}),
                            "createdAt": video_data.get('timestamp'),
                            "updatedAt": video_data.get('timestamp')
                        })
                    except Exception as e:
                        logger.warning(f"Error loading cached video {cache_file}: {e}")
            
            # Sort by processing timestamp
            processed_videos.sort(
                key=lambda x: x.get('processed_at', ''),
                reverse=True
            )
            
            return processed_videos
            
        except Exception as e:
            logger.error(f"Error getting processed videos list: {e}")
            return []
    
    @app.get("/api/v2/videos/{video_id}")
    async def get_video_analysis(video_id: str):
        """
        Get detailed analysis for a specific video
        """
        try:
            processor = get_real_video_processor()
            cache_path = processor._get_cache_path(video_id)
            
            if not cache_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Video analysis not found: {video_id}"
                )
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                video_data = json.load(f)
            
            return video_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving video analysis: {str(e)}"
            )
    
    @app.get("/api/v2/cost-dashboard")
    async def get_cost_dashboard():
        """
        Get real-time cost monitoring dashboard
        """
        try:
            dashboard = await cost_monitor.get_cost_dashboard()
            return dashboard
            
        except Exception as e:
            logger.error(f"Error getting cost dashboard: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @app.get("/api/v2/usage-analytics")
    async def get_usage_analytics(days: int = 7):
        """
        Get API usage analytics for the past N days
        """
        try:
            if days < 1 or days > 90:
                raise HTTPException(
                    status_code=400,
                    detail="Days must be between 1 and 90"
                )
            
            analytics = await cost_monitor.get_usage_analytics(days)
            return analytics
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @app.get("/api/v2/optimization-recommendations")
    async def get_optimization_recommendations():
        """
        Get AI-powered optimization recommendations for API usage
        """
        try:
            recommendations = await cost_monitor.optimize_api_usage()
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {e}")
            return {
                "error": str(e),
                "recommendations": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @app.get("/api/v2/service-status")
    async def get_service_status():
        """
        Get comprehensive service status including all real API integrations
        """
        try:
            # Get status from all services
            processor = get_real_video_processor()
            processor_status = await processor.get_processing_status()
            
            cost_dashboard = await cost_monitor.get_cost_dashboard()
            
            # Check API key availability
            api_keys_status = {
                "youtube_api": bool(os.getenv('YOUTUBE_API_KEY')),
                "openai_api": bool(os.getenv('OPENAI_API_KEY')),
                "anthropic_api": bool(os.getenv('ANTHROPIC_API_KEY')),
                "gemini_api": bool(os.getenv('GEMINI_API_KEY'))
            }
            
            return {
                "overall_status": "operational" if processor_status.get('service_status') == 'operational' else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processor": processor_status,
                "cost_monitoring": {
                    "status": "operational",
                    "today_cost": cost_dashboard.get('today_summary', {}).get('total_cost', 0.0),
                    "budget_remaining": cost_dashboard.get('today_summary', {}).get('budget_remaining', 0.0)
                },
                "api_keys": api_keys_status,
                "features": {
                    "real_youtube_api": True,
                    "multi_provider_ai": True,
                    "cost_monitoring": True,
                    "error_handling": True,
                    "caching": True,
                    "batch_processing": True
                },
                "version": "2.0.0-real-api-integration"
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @app.delete("/api/v2/cache/clear")
    async def clear_processing_cache():
        """
        Clear all video processing cache
        """
        try:
            processor = get_real_video_processor()
            
            # Clear cache directory
            import shutil
            if processor.cache_dir.exists():
                shutil.rmtree(processor.cache_dir)
                processor.cache_dir.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "message": "Processing cache cleared",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear cache: {str(e)}"
            )
    
    @app.post("/api/v2/search-videos")
    async def search_youtube_videos(
        query: str,
        max_results: int = 10,
        order: str = "relevance"
    ):
        """
        Search YouTube videos using real YouTube Data API
        """
        try:
            if max_results > 50:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 50 results allowed per search"
                )
            
            youtube_service = get_youtube_service()
            
            results = await youtube_service.search_videos(
                query=query,
                max_results=max_results,
                order=order
            )
            
            return {
                "query": query,
                "results": [
                    {
                        "video_id": result.video_id,
                        "title": result.title,
                        "description": result.description,
                        "channel_title": result.channel_title,
                        "published_at": result.published_at,
                        "thumbnail_url": result.thumbnail_url,
                        "video_url": f"https://www.youtube.com/watch?v={result.video_id}"
                    }
                    for result in results
                ],
                "total_results": len(results),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Search failed: {str(e)}"
            )
    
    logger.info("🚀 Real API endpoints setup complete")

# Initialize services when module is imported
SERVICES_INITIALIZED = init_real_api_services()

if __name__ == "__main__":
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="UVAI Real API Integration",
        description="Real YouTube Data API and AI processing integration",
        version="2.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup endpoints
    setup_real_api_endpoints(app)
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy" if SERVICES_INITIALIZED else "degraded",
            "services_initialized": SERVICES_INITIALIZED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0-real-api-integration"
        }
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)