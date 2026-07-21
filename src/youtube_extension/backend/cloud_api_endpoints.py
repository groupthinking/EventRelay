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
import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Optional, Union
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

# Import cloud services
from ..services.cloud import (
    get_cloud_tasks_service,
    get_firestore_service,
    get_vertex_ai_service,
)
from ..services.cloud.cloud_video_processor import get_cloud_video_processor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


# Well-known internal hostnames that must never receive an outbound callback.
_BLOCKED_CALLBACK_HOSTS = frozenset(
    {"localhost", "metadata", "metadata.google.internal"}
)


def _sanitize_log_value(value: Any) -> str:
    """Strip CR/LF from untrusted values before logging to prevent log injection."""
    return str(value).replace("\r", "").replace("\n", "")


def _is_blocked_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Return True unless the address is a globally routable public address.

    Rejecting every non-global destination (rather than enumerating unsafe
    ranges) also blocks addresses that Python reports as neither private nor
    global — e.g. shared CGNAT space (``100.64.0.0/10``) and deprecated IPv6
    site-local (``fec0::/10``) — which the enumerated form let through.
    Multicast and deprecated IPv6 site-local (``fec0::/10``, which some Python
    versions still report as global) are rejected explicitly.
    """
    return (
        ip.is_multicast
        or getattr(ip, "is_site_local", False)
        or not ip.is_global
    )


# Bounds for outbound callback dispatch: a hostname can resolve to many public
# addresses, so cap how many are attempted and the total wall-clock spent so a
# black-holing DNS answer cannot tie up a task worker far beyond one timeout.
_MAX_CALLBACK_ADDRESS_ATTEMPTS = 3
_CALLBACK_ATTEMPT_TIMEOUT = 10.0
_CALLBACK_TOTAL_TIMEOUT = 15.0


def _is_safe_callback_url(url: str, *, resolve: bool = True) -> bool:
    """Return True only for callback URLs safe for the server to POST to.

    Mitigates SSRF against the user-supplied Cloud Task callback:
      * requires an http(s) scheme with a hostname;
      * rejects well-known internal hostnames (trailing-dot / case normalized);
      * rejects loopback / private / link-local / reserved / multicast /
        unspecified IP literals;
      * when ``resolve`` is True, resolves the hostname via DNS and rejects if
        ANY resolved address is blocked — this defeats obfuscated IPv4
        encodings (decimal/hex/octal) and DNS names that map to internal
        addresses.

    ``resolve=False`` runs only the cheap, network-free checks; it is used for
    early request-time validation, while the full resolving check is run off
    the event loop immediately before the outbound request.
    """

    return _validated_callback_addresses(url, resolve=resolve) is not None


def _validated_callback_addresses(
    url: str, *, resolve: bool = True
) -> Optional[tuple[str, ...]]:
    """Validate a callback and return the exact public addresses it resolved to.

    A non-``None`` empty tuple means the URL passed the network-free validation.
    A resolving validation returns at least one numeric address; callers must use
    one of those addresses as the connection target instead of resolving the
    attacker-controlled hostname again.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return None

    hostname = parsed.hostname
    if parsed.scheme not in ("http", "https") or not hostname:
        return None

    if hostname.rstrip(".").lower() in _BLOCKED_CALLBACK_HOSTS:
        return None

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None:
        return None if _is_blocked_ip(ip) else (str(ip),)

    if not resolve:
        # Non-literal host clears the cheap gate; it is fully resolved and
        # re-validated before any outbound request is actually made.
        return ()

    try:
        addrinfos = socket.getaddrinfo(
            hostname,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except (socket.gaierror, UnicodeError, ValueError):
        # Unresolvable hostname — treat as unsafe.
        return None

    addresses = []
    for info in addrinfos:
        if info[0] not in (socket.AF_INET, socket.AF_INET6):
            continue
        resolved = str(info[4][0]).split("%", 1)[0]  # drop IPv6 scope/zone id
        try:
            resolved_ip = ipaddress.ip_address(resolved)
        except ValueError:
            return None
        if _is_blocked_ip(resolved_ip):
            return None
        normalized = str(resolved_ip)
        if normalized not in addresses:
            addresses.append(normalized)

    return tuple(addresses) if addresses else None


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
    metadata: Optional[dict[str, Any]] = None
    transcript: Optional[dict[str, Any]] = None
    ai_analysis: Optional[dict[str, Any]] = None
    processing_time: Optional[float] = None
    from_cache: bool = False
    error: Optional[str] = None


class CloudTaskPayload(BaseModel):
    """Payload for Cloud Tasks handler"""
    video_id: str
    video_url: str
    priority: int = 0
    callback_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class BatchCloudProcessingRequest(BaseModel):
    video_urls: list[str] = Field(..., description="List of YouTube video URLs")
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
    # Reject an unsafe callback URL up front (cheap, no DNS) so the caller gets
    # immediate feedback instead of a silently-dropped callback later. Raised
    # before the try/except below so it surfaces as 400, not 500.
    if request.callback_url and not _is_safe_callback_url(
        request.callback_url, resolve=False
    ):
        raise HTTPException(status_code=400, detail="Invalid callback_url")

    try:
        processor = get_cloud_video_processor()
        video_id = processor._extract_video_id(request.video_url)

        logger.info(
            "🎬 Cloud processing request: %s (async=%s, priority=%s)",
            _sanitize_log_value(request.video_url),
            request.async_processing,
            request.priority,
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
                error=result.error_message,
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
        "📝 Processing Cloud Task: %s (video_id=%s)",
        _sanitize_log_value(x_cloudtasks_taskname),
        _sanitize_log_value(payload.video_id),
    )

    try:
        processor = get_cloud_video_processor()

        # Process video synchronously
        result = await processor.process_video_sync(
            video_url=payload.video_url,
            force_refresh=False,
        )

        # Call callback URL if provided. Resolve and validate off the event loop,
        # then connect to that exact numeric address. The logical URL remains in
        # Host and TLS SNI so routing and certificate verification still target
        # the callback hostname without allowing connect-time DNS rebinding.
        if payload.callback_url and result.success:
            callback_addresses = await asyncio.to_thread(
                _validated_callback_addresses, payload.callback_url
            )
            if not callback_addresses:
                logger.warning(
                    "⚠️ Refusing to call unsafe callback URL: %s",
                    _sanitize_log_value(payload.callback_url),
                )
            else:
                try:
                    import httpx

                    callback_url = httpx.URL(payload.callback_url)
                    host_header = callback_url.netloc.decode("ascii")
                    loop = asyncio.get_running_loop()
                    deadline = loop.time() + _CALLBACK_TOTAL_TIMEOUT
                    sent = False
                    last_connect_error: Optional[Exception] = None
                    async with httpx.AsyncClient(follow_redirects=False) as client:
                        for address in callback_addresses[
                            :_MAX_CALLBACK_ADDRESS_ATTEMPTS
                        ]:
                            remaining = deadline - loop.time()
                            if remaining <= 0:
                                break
                            pinned_url = callback_url.copy_with(host=address)
                            try:
                                await client.post(
                                    pinned_url,
                                    json={
                                        "video_id": result.video_id,
                                        "status": "completed",
                                        "processing_time": result.processing_time,
                                    },
                                    headers={"Host": host_header},
                                    extensions={"sni_hostname": callback_url.host},
                                    timeout=min(_CALLBACK_ATTEMPT_TIMEOUT, remaining),
                                )
                                sent = True
                                break
                            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                                # httpx has not sent the request when connection
                                # establishment fails, so another already-validated
                                # address is safe to try without duplicating a POST.
                                last_connect_error = exc
                    if sent:
                        logger.info(
                            "✅ Callback sent to %s",
                            _sanitize_log_value(payload.callback_url),
                        )
                    elif last_connect_error is not None:
                        raise last_connect_error
                    else:
                        logger.warning(
                            "⚠️ Callback abandoned (attempt/deadline bound) for %s",
                            _sanitize_log_value(payload.callback_url),
                        )
                except Exception as e:
                    logger.warning(
                        "⚠️ Callback failed: %s", _sanitize_log_value(str(e))
                    )

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
        except Exception as state_error:
            logger.error(f"Failed to update error state: {state_error}")

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
            error_message=state.error_message,
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
            "error_message": state.error_message,
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

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return {
            "success": False,
            "error": str(e),
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
            await get_firestore_service()
            status["services"]["firestore"] = {
                "status": "operational",
                "enabled": True,
            }
        except Exception as e:
            status["services"]["firestore"] = {
                "status": "error",
                "error": str(e),
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
        except Exception as e:
            status["services"]["cloud_tasks"] = {
                "status": "error",
                "error": str(e),
            }
            status["overall_status"] = "degraded"

        # Check Vertex AI
        try:
            get_vertex_ai_service()
            status["services"]["vertex_ai"] = {
                "status": "operational",
                "enabled": True,
            }
        except Exception as e:
            status["services"]["vertex_ai"] = {
                "status": "error",
                "error": str(e),
            }
            status["overall_status"] = "degraded"

        return status

    except Exception as e:
        logger.error(f"Error getting cloud status: {e}")
        return {
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }



def setup_cloud_api_endpoints(app: FastAPI):
    """Setup cloud-native API endpoints for FastAPI app"""
    app.include_router(router)
    logger.info("🌐 Cloud-native API endpoints setup complete")
