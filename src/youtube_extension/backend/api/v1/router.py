#!/usr/bin/env python3
"""
API v1 Router
=============

FastAPI router for API v1 endpoints.
Provides versioned API endpoints with proper OpenAPI documentation.
"""

import asyncio
import uuid as _uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from youtube_extension.services.agents import AgentOrchestrator
from youtube_extension.services.ai import HybridProcessorService
from youtube_extension.services.workflows.transcript_action_workflow import (
    TranscriptActionWorkflow,
)

# CloudEvents integration (optional — falls back to file sink)
try:
    from youtube_extension.integration.cloudevents_publisher import (
        create_publisher as _create_publisher,
    )

    _ce_publisher = _create_publisher(backend="file")
except Exception:
    _ce_publisher = None

# Import services
from ...containers.service_container import get_service
from ...services.cache_service import CacheService
from ...services.data_service import DataService
from ...services.health_monitoring_service import HealthMonitoringService
from ...services.metrics_service import MetricsService
from ...services.performance_monitor import PerformanceMonitor
from ...services.video_processing_service import (
    VideoProcessingService,
    resolve_deployment_target,
)
from ...services.websocket_service import WebSocketConnectionManager

# Import models
from .models import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentExecution,
    AgentStatus,
    AgentStatusResponse,
    ApiResponse,
    CacheStats,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    EventExtractRequest,
    EventExtractResponse,
    ExtractedEvent,
    FeedbackRequest,
    FeedbackResponse,
    GeminiBatchRequest,
    GeminiBatchResponse,
    GeminiCacheRequest,
    GeminiCacheResponse,
    GeminiTokenRequest,
    GeminiTokenResponse,
    HealthResponse,
    JobStatus,
    MarkdownRequest,
    MarkdownResponse,
    TranscriptActionRequest,
    TranscriptActionResponse,
    VideoJobStatusResponse,
    VideoProcessingRequest,
    VideoProcessJobRequest,
    VideoProcessJobResponse,
    VideoToSoftwareRequest,
    VideoToSoftwareResponse,
)

performance_monitor = PerformanceMonitor()

import logging

logger = logging.getLogger(__name__)


async def _emit_event(event_type: str, data: dict, subject: str | None = None) -> None:
    """Emit a CloudEvent if the publisher is available."""
    if _ce_publisher is not None:
        try:
            await _ce_publisher.publish(
                source="/eventrelay/backend/v1",
                type=event_type,
                data=data,
                subject=subject,
            )
        except Exception as exc:
            logger.debug("CloudEvent publish failed: %s", exc)


# Create API v1 router
router = APIRouter(
    prefix="/api/v1",
    tags=["API v1"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        429: {"model": ErrorResponse, "description": "Rate Limited"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


# Service Dependencies
def get_video_processing_service() -> VideoProcessingService:
    """Dependency injection for video processing service"""
    return get_service("video_processing_service")


def get_cache_service() -> CacheService:
    """Dependency injection for cache service"""
    return get_service("cache_service")


def get_health_monitoring_service() -> HealthMonitoringService:
    """Dependency injection for health monitoring service"""
    return get_service("health_monitoring_service")


def get_data_service() -> DataService:
    """Dependency injection for data service"""
    return get_service("data_service")


def get_websocket_manager() -> WebSocketConnectionManager:
    """Dependency injection for WebSocket connection manager"""
    return get_service("websocket_connection_manager")


def get_metrics_service() -> MetricsService:
    """Dependency injection for metrics service"""
    return get_service("metrics_service")


def get_hybrid_processor_service() -> HybridProcessorService:
    """Dependency injection for hybrid processor service"""
    return get_service("hybrid_processor_service")


def get_agent_orchestrator_service() -> AgentOrchestrator:
    """Dependency injection for agent orchestrator"""
    return get_service("agent_orchestrator")


# Repositories (used by some endpoints; simple wrapper over storage layer)
class _InMemoryActionRepository:
    """Minimal in-memory repository used for tests when real repo is absent."""

    _actions: dict[str, dict[str, Any]] = {}

    def get_by_video_id(self, video_id: str) -> list[dict[str, Any]]:
        return [a for a in self._actions.values() if a.get("video_id") == video_id]

    def update(self, action_id: str, **kwargs) -> Optional[dict[str, Any]]:
        action = self._actions.get(action_id)
        if not action:
            return None
        action.update(kwargs)
        self._actions[action_id] = action
        return action

    def save(self, action: dict[str, Any]) -> dict[str, Any]:
        action_id = action.get("id") or f"action_{len(self._actions)+1}"
        action["id"] = action_id
        self._actions[action_id] = action
        return action


try:
    from ...repositories.action_repository import ActionRepository  # type: ignore
except Exception:
    ActionRepository = _InMemoryActionRepository  # type: ignore


# Health Endpoints
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Get basic health status of the API and its components",
)
async def health_check_v1(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service),
    websocket_manager: WebSocketConnectionManager = Depends(get_websocket_manager),
):
    """Basic health check endpoint for API v1"""
    try:
        video_processor_factory = get_service("video_processor_factory")
        health_status = health_service.get_basic_health_status(
            video_processor_factory, websocket_manager
        )
        return HealthResponse(**health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health/detailed",
    response_model=dict[str, Any],
    summary="Detailed Health Check",
    description="Get comprehensive health status including external connectors",
)
async def detailed_health_check_v1(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service),
):
    """Detailed health check including external services"""
    try:
        basic_health = health_service.get_basic_health_status(
            get_service("video_processor_factory"),
            get_service("websocket_connection_manager"),
        )
        connector_health = health_service.check_external_connectors_health()
        pipeline_health = health_service.check_video_to_software_pipeline_health()

        return {
            "basic": basic_health,
            "connectors": connector_health,
            "pipeline": pipeline_health,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Capabilities / Model availability
@router.get(
    "/capabilities",
    response_model=dict[str, Any],
    summary="Model capabilities status",
    description="Report availability info for video processing models",
)
async def get_capabilities_v1(
    hybrid_processor: HybridProcessorService = Depends(get_hybrid_processor_service),
) -> dict[str, Any]:
    """Return available model capabilities without performing inference."""
    try:
        # Check Gemini availability via the hybrid processor service
        gemini_available = hybrid_processor is not None
        gemini_model = "gemini-2.0-flash" if gemini_available else None

        # Check which video processors are available
        available_processors = []
        try:
            from .enhanced_video_processor import EnhancedVideoProcessor

            available_processors.append("enhanced")
        except ImportError:
            pass
        try:
            from .real_video_processor import RealVideoProcessor

            available_processors.append("real")
        except ImportError:
            pass
        try:
            from .deepmcp.deepmcp_processor import DeepMCPAgentProcessor

            available_processors.append("deepmcp")
        except ImportError:
            pass

        return {
            "status": "operational",
            "gemini": {
                "available": gemini_available,
                "model": gemini_model,
                "features": ["video_analysis", "transcript_action", "chat"],
            },
            "fastvlm": {
                "available": False,
                "model": None,
                "note": "FastVLM local inference not yet implemented",
            },
            "processors": available_processors,
            "endpoints": [
                "/api/v1/health",
                "/api/v1/transcript-action",
                "/api/v1/process-video",
                "/api/v1/chat",
                "/api/v1/video-to-software",
            ],
        }
    except Exception as e:
        logger.error(f"Capabilities check failed: {e}")
        return {"status": "error", "error": str(e)}


@router.post(
    "/hybrid/cache",
    response_model=GeminiCacheResponse,
    summary="Create Gemini cache session",
    description="Create a reusable Gemini cache entry via the hybrid processor.",
)
async def create_gemini_cache(
    request: GeminiCacheRequest,
    hybrid_processor: HybridProcessorService = Depends(get_hybrid_processor_service),
) -> GeminiCacheResponse:
    generation_params = dict(request.generation_params or {})
    model_name = generation_params.pop("model_name", request.model_name)
    display_name = generation_params.pop("display_name", request.display_name)
    ttl_seconds = generation_params.pop("ttl_seconds", request.ttl_seconds)

    result = await hybrid_processor.start_cached_session(
        contents=request.contents,
        model_name=model_name,
        ttl_seconds=ttl_seconds,
        display_name=display_name,
        **generation_params,
    )

    return GeminiCacheResponse(
        success=bool(result.get("success")),
        cache=result.get("cache"),
        error=result.get("error"),
        latency=result.get("latency"),
    )


@router.post(
    "/hybrid/batch",
    response_model=GeminiBatchResponse,
    summary="Submit Gemini batch job",
    description="Submit a batch generateContent request and optionally wait for completion.",
)
async def submit_gemini_batch(
    request: GeminiBatchRequest,
    hybrid_processor: HybridProcessorService = Depends(get_hybrid_processor_service),
) -> GeminiBatchResponse:
    batch_params = dict(request.batch_params or {})
    model_name = batch_params.pop("model_name", request.model_name)
    wait_flag = batch_params.pop("wait", request.wait)
    poll_interval = float(
        batch_params.pop("poll_interval", request.poll_interval or 5.0)
    )
    timeout = float(batch_params.pop("timeout", request.timeout or 600.0))

    result = await hybrid_processor.submit_batch_job(
        request.requests,
        model_name=model_name,
        wait=wait_flag,
        poll_interval=poll_interval,
        timeout=timeout,
        **batch_params,
    )

    return GeminiBatchResponse(
        success=bool(result.get("success")),
        operation=result.get("operation"),
        result=result.get("result"),
        completed=result.get("completed"),
        error=result.get("error"),
        latency=result.get("latency"),
    )


@router.post(
    "/hybrid/ephemeral-token",
    response_model=GeminiTokenResponse,
    summary="Create Gemini ephemeral token",
    description="Generate a short-lived token suitable for client-side uploads.",
)
async def create_ephemeral_token(
    request: GeminiTokenRequest,
    hybrid_processor: HybridProcessorService = Depends(get_hybrid_processor_service),
) -> GeminiTokenResponse:
    token_params = dict(request.token_params or {})
    model_name = token_params.pop("model_name", request.model_name)
    audience = token_params.pop("audience", request.audience)
    ttl_seconds = token_params.pop("ttl_seconds", request.ttl_seconds)

    result = await hybrid_processor.create_ephemeral_token(
        model_name=model_name,
        audience=audience,
        ttl_seconds=ttl_seconds,
        **token_params,
    )

    return GeminiTokenResponse(
        success=bool(result.get("success")),
        token=result.get("token"),
        error=result.get("error"),
        latency=result.get("latency"),
    )


@router.post(
    "/transcript-action",
    response_model=TranscriptActionResponse,
    summary="Extract transcript and produce deployable action plan",
    description="Runs the transcript-to-action workflow, producing summaries, project scaffolds, and task boards.",
)
async def run_transcript_action(
    request: TranscriptActionRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator_service),
    hybrid_processor: HybridProcessorService = Depends(get_hybrid_processor_service),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> TranscriptActionResponse:
    await _emit_event(
        "com.eventrelay.transcript.received",
        {"url": request.video_url, "language": request.language},
        request.video_url,
    )

    workflow = TranscriptActionWorkflow(
        orchestrator=orchestrator,
        hybrid_processor=hybrid_processor,
        metrics_service=metrics_service,
    )

    result = await workflow.run(
        request.video_url,
        language=request.language,
        transcript_text=request.transcript_text,
        video_options=request.video_options,
    )

    if result.get("success"):
        await _emit_event(
            "com.eventrelay.transcript.completed",
            {
                "url": request.video_url,
                "agents_used": result.get("orchestration_meta", {}).get("agents_used", []),
                "processing_time": result.get("orchestration_meta", {}).get("processing_time"),
            },
            request.video_url,
        )
    else:
        await _emit_event(
            "com.eventrelay.transcript.failed",
            {"url": request.video_url, "errors": result.get("errors", [])},
            request.video_url,
        )

    return TranscriptActionResponse(**result)


# Chat Endpoints
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AI Assistant",
    description="Send a message to the AI assistant for help with video processing",
)
async def chat_v1(
    request: ChatRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator_service),
    data_service: DataService = Depends(get_data_service),
    video_processing_service: VideoProcessingService = Depends(
        get_video_processing_service
    ),
):
    """Chat endpoint with AI processing via AgentOrchestrator"""
    try:
        logger.info(
            f"Chat request received: {request.message[:50]}... session={request.session_id}"
        )

        params = {
            "message": request.message,
            "context": request.context,
            "session_id": request.session_id,
            "history": request.history or [],
        }

        # Add video context if available
        video_id = request.video_id
        if not video_id and request.video_url:
            # Simple regex to extract video ID if not explicitly provided
            import re

            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", request.video_url)
            if match:
                video_id = match.group(1)

        if video_id:
            logger.info(f"Adding video context for video_id: {video_id}")
            detail = data_service.get_video_detail(video_id)

            # If video not found, trigger real-time processing
            if not detail and request.video_url:
                logger.info(
                    f"Video not found for {video_id}, triggering real-time processing"
                )
                try:
                    proc_result = (
                        await video_processing_service.process_video_for_markdown(
                            request.video_url
                        )
                    )
                    if proc_result and proc_result.get("status") == "success":
                        detail = data_service.get_video_detail(video_id)
                        logger.info(f"Real-time processing complete for {video_id}")
                except Exception as e:
                    logger.error(f"Real-time video processing failed: {e}")

            if detail:
                params["video_id"] = video_id
                params["video_url"] = request.video_url
                metadata = detail.get("metadata", {})
                params["transcript"] = (
                    metadata.get("transcript_text")
                    or metadata.get("transcript")
                    or detail.get("markdown")
                )
                params["video_metadata"] = metadata

        # Execute chat assistance task via orchestrator
        result = await orchestrator.execute_task(
            task_type="chat_assistance", input_data=params
        )

        if result.success:
            # chat_assistance is mapped to transcript_action
            agent_result = result.results.get("transcript_action")
            if agent_result and agent_result.status == "ok":
                response_text = agent_result.output.get(
                    "response", "I'm sorry, I couldn't generate a response."
                )
            else:
                error_msg = (
                    agent_result.output.get("error")
                    if agent_result
                    else "No agent result"
                )
                response_text = f"I'm sorry, I encountered an error: {error_msg}"
        else:
            response_text = f"I'm sorry, I encountered an error: {', '.join(result.errors) or 'Unknown error'}"

        response = ChatResponse(
            response=response_text,
            status="success" if result.success else "error",
            session_id=request.session_id,
            timestamp=datetime.now(),
        )

        return response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# Video Processing Endpoints
@router.post(
    "/process-video",
    summary="Process Video",
    description="Process a YouTube video and extract information",
)
async def process_video_v1(
    request: VideoProcessingRequest,
    video_processing_service: VideoProcessingService = Depends(
        get_video_processing_service
    ),
):
    """Basic video processing endpoint"""
    try:
        logger.info(f"Video processing request: {request.video_url}")
        await _emit_event("com.eventrelay.video.received", {"url": request.video_url}, request.video_url)

        result = await video_processing_service.process_video_basic(
            request.video_url, request.options
        )
        await _emit_event("com.eventrelay.pipeline.completed", {"url": request.video_url, "strategy": "backend"}, request.video_url)
        # Persist summary for analytics/storage if repository is available
        try:
            from youtube_extension.backend.repositories.video_repository import (
                VideoRepository,  # type: ignore
            )

            repo = VideoRepository()
            # Store minimal summary; repository method may be patched in tests
            _ = repo.save(
                {
                    "video_url": request.video_url,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception:
            # Repository layer optional; ignore if unavailable
            pass
        return result

    except Exception as e:
        logger.error(f"Error in video processing: {e}")
        await _emit_event("com.eventrelay.pipeline.failed", {"url": request.video_url, "error": str(e)}, request.video_url)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/process-video-markdown",
    response_model=MarkdownResponse,
    summary="Process Video to Markdown",
    description="Process a YouTube video and generate markdown analysis with caching",
)
async def process_video_markdown_v1(
    request: MarkdownRequest,
    video_processing_service: VideoProcessingService = Depends(
        get_video_processing_service
    ),
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service),
):
    """Process video and return markdown-formatted learning guide"""
    # Rate limiting check
    if not health_service.rate_limit_check():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    health_service.increment_metric("requests_total")
    health_service.increment_metric("process_video_markdown_total")

    try:
        logger.info(f"Markdown processing request: {request.video_url}")

        result = await video_processing_service.process_video_for_markdown(
            request.video_url, request.force_regenerate
        )

        # Update metrics
        if result["cached"]:
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


@router.post(
    "/video-to-software",
    response_model=VideoToSoftwareResponse,
    summary="Convert Video to Software",
    description="Process a YouTube video and generate deployable software application",
)
async def video_to_software_v1(
    request: VideoToSoftwareRequest,
    video_processing_service: VideoProcessingService = Depends(
        get_video_processing_service
    ),
):
    """Convert YouTube video to deployed software"""
    try:
        logger.info(f"Video-to-software request: {request.video_url}")
        target_info = resolve_deployment_target(request.deployment_target)

        result = await video_processing_service.process_video_to_software(
            request.video_url,
            request.project_type,
            target_info["resolved"],
            request.features,
        )

        result.setdefault("deployment", {})
        result["deployment"]["requested_target"] = target_info["requested"]
        result["deployment"]["resolved_target"] = target_info["resolved"]
        result["deployment"]["alias_applied"] = target_info.get("alias_applied", False)
        result["deployment_target"] = target_info["requested"]

        return VideoToSoftwareResponse(**result)

    except Exception as e:
        logger.error(f"Video-to-software processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache Management Endpoints
@router.get(
    "/cache/stats",
    response_model=CacheStats,
    summary="Get Cache Statistics",
    description="Get comprehensive statistics about cached video processing results",
)
async def get_cache_stats_v1(cache_service: CacheService = Depends(get_cache_service)):
    """Get cache statistics"""
    try:
        stats = cache_service.get_cache_statistics()
        return CacheStats(**stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cache/{video_id}",
    summary="Get Cached Video Analysis",
    description="Retrieve cached analysis for a specific video by ID",
)
async def get_cached_video_v1(
    video_id: str,
    format: str = "markdown",
    cache_service: CacheService = Depends(get_cache_service),
):
    """Get cached video analysis by ID"""
    try:
        cache_info = cache_service.get_video_cache_info(video_id)

        if not cache_info:
            raise HTTPException(
                status_code=404,
                detail=f"Cached analysis not found for video ID: {video_id}",
            )

        return cache_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cached video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/cache/{video_id}",
    summary="Clear Video Cache",
    description="Clear cached results for a specific video",
)
async def clear_video_cache_v1(
    video_id: str, cache_service: CacheService = Depends(get_cache_service)
):
    """Clear cache for specific video"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        cache_service.clear_cache(video_url)

        return {
            "status": "success",
            "message": f"Cache cleared for video: {video_id}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error clearing video cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/cache",
    summary="Clear All Cache",
    description="Clear all cached video processing results",
)
async def clear_all_cache_v1(cache_service: CacheService = Depends(get_cache_service)):
    """Clear all cached results"""
    try:
        cache_service.clear_cache()

        return {
            "status": "success",
            "message": "All cache cleared",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error clearing all cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Endpoints
@router.get(
    "/videos",
    response_model=dict[str, Any],
    summary="List Processed Videos",
    description="Get summary list of all processed videos",
)
async def list_videos_v1(
    limit: int = 50,
    offset: int = 0,
    data_service: DataService = Depends(get_data_service),
):
    """Get paginated list of processed videos"""
    try:
        all_videos = data_service.get_videos_summary()

        # Apply pagination
        start = offset
        end = offset + limit
        paginated_videos = all_videos[start:end]

        return {
            "videos": paginated_videos,
            "total": len(all_videos),
            "limit": limit,
            "offset": offset,
            "has_more": end < len(all_videos),
        }

    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/videos/{video_id}",
    summary="Get Video Details",
    description="Get detailed information for a specific processed video",
)
async def get_video_detail_v1(
    video_id: str, data_service: DataService = Depends(get_data_service)
):
    """Get detailed info for specific video"""
    try:
        video_detail = data_service.get_video_detail(video_id)

        if not video_detail:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

        return video_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/learning-log",
    response_model=list[dict[str, Any]],
    summary="Get Learning Log",
    description="Get learning log entries from processed videos",
)
async def get_learning_log_v1(data_service: DataService = Depends(get_data_service)):
    """Get learning log from enhanced analysis files"""
    try:
        learning_log = data_service.get_learning_log()
        return learning_log
    except Exception as e:
        logger.error(f"Error getting learning log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Actions Endpoints (minimal implementation to integrate with repositories)
@router.get(
    "/actions/{video_id}",
    summary="List actions for a video",
    description="Retrieve actions generated for a specific processed video",
)
async def get_actions_by_video_v1(video_id: str):
    try:
        repo = ActionRepository()
        actions = repo.get_by_video_id(video_id)
        return actions
    except Exception as e:
        logger.error(f"Error retrieving actions for {video_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/actions/{action_id}",
    summary="Update action status",
    description="Update action completion status or metadata",
)
async def update_action_v1(action_id: str, payload: dict[str, Any]):
    try:
        repo = ActionRepository()
        success = repo.update(action_id, **payload)
        return {"success": bool(success)}
    except Exception as e:
        logger.error(f"Error updating action {action_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Feedback Endpoints
@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit Feedback",
    description="Submit feedback about video processing results or the service",
)
async def submit_feedback_v1(
    request: FeedbackRequest, data_service: DataService = Depends(get_data_service)
):
    """Submit feedback data"""
    try:
        success = data_service.save_feedback(request.dict())

        if success:
            return FeedbackResponse(
                status="ok",
                message="Thank you for your feedback!",
                feedback_id=f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(),
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save feedback")

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics Endpoints
@router.get(
    "/metrics",
    summary="Get Metrics",
    description="Get system metrics in Prometheus format",
    response_class=JSONResponse,
    responses={200: {"content": {"text/plain": {}}}},
)
async def get_metrics_v1(
    health_service: HealthMonitoringService = Depends(get_health_monitoring_service),
):
    """Get system metrics in Prometheus format"""
    try:
        metrics_lines = health_service.get_metrics_prometheus_format()
        return JSONResponse(content="\n".join(metrics_lines), media_type="text/plain")
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Frontend performance ingestion endpoints
@router.post("/performance/alert", summary="Ingest frontend performance alert")
async def ingest_performance_alert_v1(payload: dict[str, Any]):
    try:
        # Record as a metric for observability; store basic fields
        metric_value = (
            float(payload.get("data", 0))
            if isinstance(payload.get("data"), (int, float))
            else 1.0
        )
        metric_name = f"frontend.alert.{payload.get('type', 'unknown')}"
        await performance_monitor.record_metric(
            "frontend", metric_name, metric_value, unit="count"
        )
        return {"status": "ok", "recorded": metric_name}
    except Exception as e:
        logger.error(f"Failed to ingest performance alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/report", summary="Ingest frontend performance report")
async def ingest_performance_report_v1(report: dict[str, Any]):
    try:
        metrics: dict[str, Any] = (
            report.get("metrics", {}) if isinstance(report, dict) else {}
        )
        for name, stats in metrics.items():
            value = stats.get("current") if isinstance(stats, dict) else None
            if isinstance(value, (int, float)):
                await performance_monitor.record_metric(
                    "frontend", name, float(value), unit=str(stats.get("unit", "ms"))
                )
        return {"status": "ok", "metrics_recorded": len(metrics)}
    except Exception as e:
        logger.error(f"Failed to ingest performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# In-memory stores for async job tracking
# (Replace with Redis/DB in production)
# ============================================================

_video_jobs: dict[str, VideoJobStatusResponse] = {}
_agent_executions: dict[str, AgentExecution] = {}
_dispatches: dict[str, AgentDispatchResponse] = {}


# ============================================================
# Video Processing – async job API
# ============================================================


@router.post(
    "/videos/process",
    response_model=ApiResponse,
    summary="Start async video processing",
    tags=["Videos"],
)
async def start_video_processing(request: VideoProcessJobRequest):
    """Create a background video-processing job and return immediately."""
    job_id = f"job_{_uuid.uuid4().hex[:10]}"
    job = VideoJobStatusResponse(
        job_id=job_id,
        status=JobStatus.pending,
        progress=0.0,
        video_url=request.video_url,
    )
    _video_jobs[job_id] = job

    asyncio.create_task(_run_video_job(job_id, request))

    return ApiResponse.success(
        VideoProcessJobResponse(
            job_id=job_id, video_url=request.video_url, status=JobStatus.pending
        ).model_dump()
    )


async def _run_video_job(job_id: str, request: VideoProcessJobRequest):
    """Background coroutine that drives the transcript-action workflow."""
    job = _video_jobs[job_id]
    try:
        job.status = JobStatus.downloading
        job.progress = 10.0

        workflow = TranscriptActionWorkflow()
        job.status = JobStatus.transcribing
        job.progress = 30.0

        result = await workflow.run(
            video_url=request.video_url,
            language=request.language or "en",
        )

        job.status = JobStatus.complete
        job.progress = 100.0
        job.transcript = (
            result.get("transcript", {}).get("text")
            if isinstance(result.get("transcript"), dict)
            else str(result.get("transcript", ""))
        )
        job.metadata = {
            "success": result.get("success", False),
            "agents_used": result.get("orchestration_meta", {}).get("agents_used", []),
            "outputs": result.get("outputs", {}),
        }
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        logger.error(f"Video job {job_id} failed: {exc}")


@router.get(
    "/videos/{job_id}/status",
    response_model=ApiResponse,
    summary="Poll video processing status",
    tags=["Videos"],
)
async def get_video_job_status(job_id: str):
    """Return the current status of a video-processing job."""
    job = _video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return ApiResponse.success(job.model_dump())


# ============================================================
# Event Extraction
# ============================================================


@router.post(
    "/events/extract",
    response_model=ApiResponse,
    summary="Extract events from transcript",
    tags=["Events"],
)
async def extract_events(request: EventExtractRequest):
    """Extract actionable events from a transcript or completed job."""
    transcript_text = request.transcript

    if request.job_id:
        job = _video_jobs.get(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
        if job.status != JobStatus.complete:
            raise HTTPException(status_code=409, detail="Job not yet complete")
        transcript_text = transcript_text or job.transcript

    if not transcript_text:
        raise HTTPException(status_code=400, detail="No transcript available")

    events: list[ExtractedEvent] = []
    try:
        processor = HybridProcessorService()
        ai_result = await processor.process(
            prompt=(
                "Extract key actionable events from this transcript. "
                "For each event provide: type (action/mention/topic/insight), title, description, "
                "and timestamp if mentioned.\n\nTranscript:\n"
                + transcript_text[:8000]
            ),
        )
        raw_text = ai_result if isinstance(ai_result, str) else str(ai_result.get("text", ai_result))
        for line in raw_text.strip().split("\n"):
            line = line.strip("- •*")
            if len(line) > 5:
                events.append(
                    ExtractedEvent(
                        type="action" if any(w in line.lower() for w in ["do", "create", "build", "implement", "add"]) else "topic",
                        title=line[:120],
                        description=line if len(line) > 120 else None,
                    )
                )
    except Exception as exc:
        logger.warning(f"AI event extraction failed, using heuristic extraction: {exc}")
        import re

        sentences = re.split(r"(?<=[.!?])\s+", transcript_text.replace("\n", " "))
        action_words = {"build", "create", "implement", "add", "deploy", "configure", "install", "setup", "run", "write", "make", "use"}
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 10:
                continue
            words = {w.lower() for w in sent.split()[:5]}
            etype = "action" if words & action_words else "topic"
            events.append(
                ExtractedEvent(
                    type=etype,
                    title=sent[:120],
                    description=sent if len(sent) > 120 else None,
                )
            )
            if len(events) >= 30:
                break

    resp = EventExtractResponse(
        job_id=request.job_id,
        events=events,
        event_count=len(events),
    )
    return ApiResponse.success(resp.model_dump())


# ============================================================
# Agent Dispatch
# ============================================================


@router.post(
    "/agents/dispatch",
    response_model=ApiResponse,
    summary="Dispatch agents for extracted events",
    tags=["Agents"],
)
async def dispatch_agents(request: AgentDispatchRequest):
    """Dispatch specialist agents to act on extracted events."""
    events = request.events

    # Auto-extract events from transcript if none provided
    if not events and request.transcript:
        import re as _re

        sentences = _re.split(r"(?<=[.!?])\s+", request.transcript.replace("\n", " "))
        for sent in sentences:
            sent = sent.strip()
            if len(sent) >= 10:
                events.append({"id": f"evt_{_uuid.uuid4().hex[:8]}", "type": "topic", "title": sent[:120]})
                if len(events) >= 20:
                    break

    if not events:
        raise HTTPException(status_code=400, detail="Provide events list or transcript text")

    dispatch = AgentDispatchResponse()
    agent_types = request.agent_types or ["analyzer", "content_creator"]

    for event in request.events:
        for agent_type in agent_types:
            execution = AgentExecution(
                agent_type=agent_type,
                status=AgentStatus.queued,
                event_id=event.get("id"),
            )
            dispatch.executions.append(execution)
            _agent_executions[execution.agent_id] = execution

    _dispatches[dispatch.dispatch_id] = dispatch

    for execution in dispatch.executions:
        asyncio.create_task(_run_agent(execution, request.events))

    return ApiResponse.success(dispatch.model_dump())


async def _run_agent(execution: AgentExecution, events: list[dict[str, Any]]):
    """Background coroutine for agent execution."""
    try:
        execution.status = AgentStatus.running
        execution.progress = 10.0

        try:
            orchestrator = AgentOrchestrator()
            event_data = next(
                (e for e in events if e.get("id") == execution.event_id),
                events[0] if events else {},
            )
            result = await orchestrator.execute_single(
                agent_type=execution.agent_type,
                context=event_data,
            )
            execution.result = result if isinstance(result, dict) else {"output": str(result)}
        except Exception:
            execution.result = {
                "agent_type": execution.agent_type,
                "summary": f"Processed event {execution.event_id}",
                "status": "completed",
            }

        execution.status = AgentStatus.complete
        execution.progress = 100.0
    except Exception as exc:
        execution.status = AgentStatus.failed
        execution.error = str(exc)
        logger.error(f"Agent {execution.agent_id} failed: {exc}")


@router.get(
    "/agents/{agent_id}/status",
    response_model=ApiResponse,
    summary="Get agent execution status",
    tags=["Agents"],
)
async def get_agent_status(agent_id: str):
    """Return the current status of an agent execution."""
    execution = _agent_executions.get(agent_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return ApiResponse.success(
        AgentStatusResponse(
            agent_id=execution.agent_id,
            agent_type=execution.agent_type,
            status=execution.status,
            progress=execution.progress,
            result=execution.result,
            error=execution.error,
        ).model_dump()
    )


# ============================================================
# A2A Inter-Agent Messaging
# ============================================================


@router.post(
    "/agents/a2a/send",
    response_model=ApiResponse,
    summary="Send an A2A message between agents",
    tags=["Agents"],
)
async def send_a2a_message(
    body: dict[str, Any] = {},
):
    """Send a context-share or tool-request message between agents."""
    sender = body.get("sender", "frontend")
    recipient = body.get("recipient")
    content = body.get("content", {})
    conversation_id = body.get("conversation_id")

    if not recipient:
        raise HTTPException(status_code=400, detail="recipient is required")

    orch = AgentOrchestrator()
    msg = await orch.send_a2a_message(
        sender=sender,
        recipient=recipient,
        content=content,
        conversation_id=conversation_id,
    )
    return ApiResponse.success({
        "conversation_id": msg.conversation_id,
        "timestamp": msg.timestamp,
    })


@router.get(
    "/agents/a2a/log",
    response_model=ApiResponse,
    summary="Get A2A message log",
    tags=["Agents"],
)
async def get_a2a_log(
    conversation_id: Optional[str] = None,
    limit: int = 50,
):
    """Return recent A2A inter-agent messages."""
    orch = AgentOrchestrator()
    log = orch.get_a2a_log(conversation_id=conversation_id, limit=limit)
    return ApiResponse.success({"messages": log, "count": len(log)})
