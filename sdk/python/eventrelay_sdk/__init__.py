"""
EventRelay Python SDK
=====================

Type-safe Python client for the EventRelay API.
Auto-generated via Stainless from openapi/eventrelay.openapi.json.

Usage::

    from eventrelay_sdk import EventRelayClient

    client = EventRelayClient(api_key="...", base_url="http://localhost:8000")
    job = client.videos.process(video_url="https://www.youtube.com/watch?v=auJzb1D-fag")
"""

from __future__ import annotations

from .client import AsyncEventRelayClient, EventRelayClient
from .types import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentStatusResponse,
    ChatRequest,
    ChatResponse,
    EventExtractRequest,
    EventExtractResponse,
    HealthResponse,
    TranscriptActionRequest,
    TranscriptActionResponse,
    VideoJobStatusResponse,
    VideoProcessJobRequest,
    VideoProcessJobResponse,
)

__all__ = [
    "EventRelayClient",
    "AsyncEventRelayClient",
    # Request / Response types
    "VideoProcessJobRequest",
    "VideoProcessJobResponse",
    "VideoJobStatusResponse",
    "EventExtractRequest",
    "EventExtractResponse",
    "AgentDispatchRequest",
    "AgentDispatchResponse",
    "AgentStatusResponse",
    "TranscriptActionRequest",
    "TranscriptActionResponse",
    "ChatRequest",
    "ChatResponse",
    "HealthResponse",
]

__version__ = "0.1.0"
