#!/usr/bin/env python3
"""
Cloud-Native API Endpoints
===========================

FastAPI endpoints for cloud-native deployment with:
- Vertex AI Agent Builder for reasoning
- Firestore for shared state
- Cloud Tasks for async processing
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import cloud services
from ..services.cloud import (
    get_firestore_service,
    get_cloud_tasks_service,
    get_vertex_ai_service,
    VideoProcessingTask,
)
from ..services.cloud.cloud_video_processor import get_cloud_video_processor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


def _client_safe_error(error_message: Optional[str]) -> Optional[str]:
    """Return a stable client-safe value for persisted processor failures.

    Older Firestore records may predate the write-side sanitizer, so every read
    boundary must treat stored error text as untrusted rather than echoing it.
    """
    return "Internal server error" if error_message else None


# Pydantic models for API requests/responses
class CloudVideoProcessingRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL or ID")
    priority: int = Field(0, description="Processing priority (higher = more urgent)", ge=0, le=10)
    async_processing: bool = Field(True, description="Use async processing via Cloud Tasks")
    callback_url: Optional[str] = Field(None, description="Callback URL for completion notification")


class CloudVideoAnalysisResponse(BaseModel):
    video_id: str
    video_url: str
    success: bool
    task_id: Optional[str] = None  # For async processing
    status: Optional[str] = None  # For sync processing
    metadata: Optional[Dict[str, Any]] = None
    transcript: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    from_cache: bool = False
    error: Optional[str] = None


class CloudTaskPayload(BaseModel):
    """Payload for Cloud Tasks handler"""
    video_id: str
    video_url: str
    priority: int = 0
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BatchCloudProcessingRequest(BaseModel):
    video_urls: List[str] = Field(..., description="List of YouTube video URLs")
    priority: int = Field(0, description="Processing priority", ge=0, le=10)


class VideoStatusResponse(BaseModel):
    video_id: str
    status: str
    current_stage: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None



@router.post("/api/v3/process-video", response_model=CloudVideoAnalysisResponse)
async def process_video_cloud(
    request: CloudVideoProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Process video using cloud-native architecture.

    - Async processing: Queues task in Cloud Tasks, returns immediately
    - Sync processing: Processes immediately, blocks until complete
    - State tracked in Firestore
    - AI reasoning via Vertex AI Agent Builder
    """
    try:
        processor = get_cloud_video_processor()
        video_id = processor._extract_video_id(request.video_url)

        logger.info(
            f"🎬 Cloud processing request: {request.video_url} "
            f"(async={request.async_processing}, priority={request.priority})"
        )

        if request.async_processing:
            # Async processing via Cloud Tasks
            task_id = await processor.process_video_async(
                video_url=request.video_url,
                priority=request.priority,
                callback_url=request.callback_url,
            )

            return CloudVideoAnalysisResponse(
                video_id=video_id,
                video_url=request.video_url,
                success=True,
                task_id=task_id,
                status='queued',
            )

        else:
            # Sync processing (blocking)
            result = await processor.process_video_sync(
                video_url=request.video_url,
                force_refresh=False,
            )

            return CloudVideoAnalysisResponse(
                video_id=result.video_id,
                video_url=result.video_url,
                success=result.success,
                status='completed' if result.success else 'failed',
                metadata=result.metadata,
                transcript=result.transcript,
                ai_analysis=result.ai_analysis,
                processing_time=result.processing_time,
                from_cache=result.from_cache,
                error=_client_safe_error(result.error_message),
            )

    except Exception as e:
        error_msg = f"Cloud processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # detail is a static string; error_msg (with the exception) is logged above only
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/v3/process-video-task")
async def process_video_task_handler(
    payload: CloudTaskPayload,
    request: Request,
    x_cloudtasks_taskname: Optional[str] = Header(None),
):
    """
    Handler for Cloud Tasks video processing tasks.

    This endpoint is called by Cloud Tasks to process queued videos.
    It should only be called by Cloud Tasks (verified via headers).
    """
    # Verify request is from Cloud Tasks
    if not x_cloudtasks_taskname:
        logger.warning("Unauthorized task handler access attempt")
        raise HTTPException(
            status_code=403,
            detail="Only Cloud Tasks can call this endpoint"
        )

    logger.info(
        f"📝 Processing Cloud Task: {x_cloudtasks_taskname} "
        f"(video_id={payload.video_id})"
    )

    try:
        processor = get_cloud_video_processor()

        # Process video synchronously
        result = await processor.process_video_sync(
            video_url=payload.video_url,
            force_refresh=False,
        )

        # Call callback URL if provided
        if payload.callback_url and result.success:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        payload.callback_url,
                        json={
                            'video_id': result.video_id,
                            'status': 'completed',
                            'processing_time': result.processing_time,
                        },
                        timeout=10.0
                    )
                logger.info(f"✅ Callback sent to {payload.callback_url}")
            except Exception as e:
                logger.warning(f"⚠️ Callback failed: {e}")

        return {
            "success": result.success,
            "video_id": result.video_id,
            "processing_time": result.processing_time,
            "task_name": x_cloudtasks_taskname,
        }

    except Exception as e:
        logger.error(f"Task processing failed: {e}", exc_info=True)

        # Update state with a static error message; raw exception is logged above only
        try:
            firestore_service = await get_firestore_service()
            await firestore_service.update_state(
                payload.video_id,
                status='failed',
                error_message="Task processing failed"
            )
        except Exception:
            logger.error("Failed to update error state", exc_info=True)

        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/v3/batch-process")
async def batch_process_videos_cloud(request: BatchCloudProcessingRequest):
    """
    Process multiple videos concurrently via Cloud Tasks.
    """
    try:
        if len(request.video_urls) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 videos allowed per batch request"
            )

        processor = get_cloud_video_processor()

        task_ids = await processor.batch_process_async(
            video_urls=request.video_urls,
            priority=request.priority,
        )

        return {
            "success": True,
            "queued_count": len(task_ids),
            "task_ids": task_ids,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in batch_process_videos_cloud: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/api/v3/videos/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """
    Get current processing status for a video from Firestore.
    """
    try:
        processor = get_cloud_video_processor()
        state = await processor.get_processing_status(video_id)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"No status found for video: {video_id}"
            )

        return VideoStatusResponse(
            video_id=state.video_id,
            status=state.status,
            current_stage=state.current_stage,
            created_at=state.created_at,
            updated_at=state.updated_at,
            processing_time=state.processing_time,
            error_message=_client_safe_error(state.error_message),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in get_video_status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/api/v3/videos/{video_id}/result")
async def get_video_result(video_id: str):
    """
    Get complete processing result for a video from Firestore.
    """
    try:
        processor = get_cloud_video_processor()
        state = await processor.get_processing_status(video_id)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"No result found for video: {video_id}"
            )

        return {
            "video_id": state.video_id,
            "video_url": state.video_url,
            "status": state.status,
            "current_stage": state.current_stage,
            "metadata": state.metadata,
            "transcript": state.transcript,
            "ai_analysis": state.ai_analysis,
            "processing_time": state.processing_time,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "error_message": _client_safe_error(state.error_message),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in get_video_result: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/api/v3/queue/stats")
async def get_queue_stats():
    """
    Get Cloud Tasks queue statistics.
    """
    try:
        tasks_service = get_cloud_tasks_service()
        stats = await tasks_service.get_queue_stats()

        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.error("Error getting queue stats", exc_info=True)
        return {
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@router.get("/api/v3/cloud-status")
async def get_cloud_status():
    """
    Get comprehensive cloud services status.
    """
    try:
        status = {
            "overall_status": "operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {},
        }

        # Check Firestore
        try:
            firestore_service = await get_firestore_service()
            status["services"]["firestore"] = {
                "status": "operational",
                "enabled": True,
            }
        except Exception:
            logger.error("firestore status check failed", exc_info=True)
            status["services"]["firestore"] = {
                "status": "error",
                "error": "Service unavailable",
            }
            status["overall_status"] = "degraded"

        # Check Cloud Tasks
        try:
            tasks_service = get_cloud_tasks_service()
            stats = await tasks_service.get_queue_stats()
            status["services"]["cloud_tasks"] = {
                "status": "operational",
                "enabled": True,
                "queue_stats": stats,
            }
        except Exception:
            logger.error("cloud_tasks status check failed", exc_info=True)
            status["services"]["cloud_tasks"] = {
                "status": "error",
                "error": "Service unavailable",
            }
            status["overall_status"] = "degraded"

        # Check Vertex AI
        try:
            vertex_service = get_vertex_ai_service()
            status["services"]["vertex_ai"] = {
                "status": "operational",
                "enabled": True,
            }
        except Exception:
            logger.error("vertex_ai status check failed", exc_info=True)
            status["services"]["vertex_ai"] = {
                "status": "error",
                "error": "Service unavailable",
            }
            status["overall_status"] = "degraded"

        return status

    except Exception:
        logger.error("Error getting cloud status", exc_info=True)
        return {
            "overall_status": "error",
            "error": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }



def setup_cloud_api_endpoints(app: FastAPI):
    """Setup cloud-native API endpoints for FastAPI app"""
    app.include_router(router)
    logger.info("🌐 Cloud-native API endpoints setup complete")
