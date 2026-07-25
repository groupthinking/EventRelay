"""
Advanced Video Analysis API Routes
----------------------------------
Temporal analysis, structured output, and CloudEvents publishing endpoints.
"""

import logging
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.integration.cloudevents_publisher import create_publisher
from src.integration.temporal_video_analysis import TemporalVideoAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/video", tags=["video-analysis"])


# ============ Request Models ============

class TemporalSegmentRequest(BaseModel):
    """Request for analyzing a specific time segment."""
    video_url: str
    start_time: str = Field(..., description="Start timestamp (MM:SS or HH:MM:SS)")
    end_time: str = Field(..., description="End timestamp (MM:SS or HH:MM:SS)")
    focus: Optional[str] = Field(None, description="Focus area (code, speaker, slides)")


class TemporalEventsRequest(BaseModel):
    """Request for extracting timestamped events."""
    video_url: str
    event_types: Optional[List[str]] = Field(
        None,
        description="Event types to focus on (e.g., ['code_change', 'api_call'])"
    )
    publish_events: bool = Field(
        False,
        description="Publish extracted events to EventMesh as CloudEvents"
    )


class TemporalQuestionRequest(BaseModel):
    """Request for temporal question answering."""
    video_url: str
    question: str
    time_context: Optional[str] = Field(
        None,
        description="Temporal constraint (e.g., 'between 2:30 and 5:00')"
    )


class TimelineRequest(BaseModel):
    """Request for creating video timeline."""
    video_url: str
    granularity: str = Field(
        "medium",
        description="Timeline granularity: 'fine', 'medium', or 'coarse'"
    )


class SegmentComparisonRequest(BaseModel):
    """Request for comparing multiple segments."""
    video_url: str
    segments: List[Tuple[str, str]] = Field(
        ...,
        description="List of (start_time, end_time) tuples to compare"
    )
    comparison_focus: Optional[str] = Field(
        None,
        description="Aspect to compare (e.g., 'code quality', 'speaking style')"
    )


class TutorialStepsRequest(BaseModel):
    """Request for extracting tutorial steps."""
    video_url: str


class StructuredAnalysisRequest(BaseModel):
    """Request for analysis with structured JSON output schema."""
    video_url: str
    prompt: str
    schema: Dict = Field(
        ...,
        description="JSON schema for structured output",
        example={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["summary", "key_points"]
        }
    )
    publish_result: bool = Field(
        False,
        description="Publish result as CloudEvent"
    )


# ============ Temporal Analysis Endpoints ============

@router.post("/temporal/segment")
async def analyze_segment(request: TemporalSegmentRequest):
    """
    Analyze a specific time segment of a video.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "start_time": "2:30",
        "end_time": "5:45",
        "focus": "code"
    }
    ```
    """
    try:
        analyzer = TemporalVideoAnalyzer()
        result = await analyzer.analyze_segment(
            request.video_url,
            request.start_time,
            request.end_time,
            request.focus
        )
        await analyzer.close()

        return {
            "segment": {
                "start_time": request.start_time,
                "end_time": request.end_time,
                "focus": request.focus
            },
            "analysis": {
                "summary": result.summary,
                "key_events": result.key_events,
                "timestamps": result.timestamps
            }
        }
    except Exception as e:
        logger.error(f"Segment analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/temporal/events")
async def extract_temporal_events(request: TemporalEventsRequest):
    """
    Extract all timestamped events from a video.
    
    Optionally publishes events to EventMesh as CloudEvents.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "event_types": ["code_change", "api_call"],
        "publish_events": true
    }
    ```
    """
    try:
        analyzer = TemporalVideoAnalyzer()
        events = await analyzer.extract_temporal_events(
            request.video_url,
            request.event_types
        )
        await analyzer.close()

        # Convert to dict format
        events_data = [
            {
                "timestamp": evt.timestamp,
                "type": evt.event_type,
                "description": evt.description,
                "confidence": evt.confidence,
                "metadata": evt.metadata
            }
            for evt in events
        ]

        # Publish to EventMesh if requested
        published_ids = []
        if request.publish_events:
            publisher = create_publisher()
            for evt in events:
                event_id = await publisher.publish(
                    source="/video-analyzer/temporal",
                    type=f"com.eventrelay.video.event.{evt.event_type}",
                    data={
                        "timestamp": evt.timestamp,
                        "description": evt.description,
                        "confidence": evt.confidence,
                        "metadata": evt.metadata
                    },
                    subject=request.video_url
                )
                if event_id:
                    published_ids.append(event_id)
            await publisher.close()

        return {
            "video_url": request.video_url,
            "events_count": len(events),
            "events": events_data,
            "published": request.publish_events,
            "published_event_ids": published_ids
        }
    except Exception as e:
        logger.error(f"Event extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/temporal/question")
async def answer_temporal_question(request: TemporalQuestionRequest):
    """
    Answer a question about a video with temporal context.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "question": "What API is called?",
        "time_context": "between 2:30 and 5:00"
    }
    ```
    """
    try:
        analyzer = TemporalVideoAnalyzer()
        answer = await analyzer.temporal_question(
            request.video_url,
            request.question,
            request.time_context
        )
        await analyzer.close()

        return {
            "question": request.question,
            "time_context": request.time_context,
            "answer": answer
        }
    except Exception as e:
        logger.error(f"Temporal question failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/temporal/timeline")
async def create_timeline(request: TimelineRequest):
    """
    Create a detailed timeline of video content.
    
    Granularity options:
    - "fine": Every 5-10 seconds
    - "medium": Every 30-60 seconds (default)
    - "coarse": Major section boundaries only
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "granularity": "medium"
    }
    ```
    """
    try:
        if request.granularity not in ("fine", "medium", "coarse"):
            raise HTTPException(400, "Invalid granularity. Must be 'fine', 'medium', or 'coarse'")

        analyzer = TemporalVideoAnalyzer()
        timeline = await analyzer.create_timeline(
            request.video_url,
            request.granularity
        )
        await analyzer.close()

        return {
            "video_url": request.video_url,
            "granularity": request.granularity,
            "timeline": timeline
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Timeline creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/temporal/compare-segments")
async def compare_segments(request: SegmentComparisonRequest):
    """
    Compare multiple time segments within a video.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "segments": [["1:00", "2:00"], ["3:00", "4:00"]],
        "comparison_focus": "code quality"
    }
    ```
    """
    try:
        analyzer = TemporalVideoAnalyzer()
        comparison = await analyzer.compare_segments(
            request.video_url,
            request.segments,
            request.comparison_focus
        )
        await analyzer.close()

        return {
            "video_url": request.video_url,
            "segments_compared": len(request.segments),
            "comparison_focus": request.comparison_focus,
            "comparison": comparison
        }
    except Exception as e:
        logger.error(f"Segment comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/temporal/tutorial-steps")
async def extract_tutorial_steps(request: TutorialStepsRequest):
    """
    Extract step-by-step tutorial instructions with timestamps.
    Optimized for instructional/tutorial videos.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example"
    }
    ```
    """
    try:
        analyzer = TemporalVideoAnalyzer()
        steps = await analyzer.extract_tutorial_steps(request.video_url)
        await analyzer.close()

        return {
            "video_url": request.video_url,
            "steps_count": len(steps),
            "steps": steps
        }
    except Exception as e:
        logger.error(f"Tutorial extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Structured Output Endpoint ============

@router.post("/analyze/structured")
async def analyze_with_schema(request: StructuredAnalysisRequest):
    """
    Analyze video with structured JSON output conforming to provided schema.
    
    Uses Gemini's response_schema to enforce output structure.
    Optionally publishes result as a CloudEvent.
    
    Example:
    ```json
    {
        "video_url": "https://youtube.com/watch?v=example",
        "prompt": "Extract APIs and their endpoints",
        "schema": {
            "type": "object",
            "properties": {
                "apis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "endpoint": {"type": "string"},
                            "method": {"type": "string"}
                        }
                    }
                }
            }
        },
        "publish_result": true
    }
    ```
    """
    try:
        from src.youtube_extension.services.ai.gemini_service import (
            GeminiConfig,
            GeminiService,
        )

        config = GeminiConfig(
            response_schema=request.schema,
            response_mime_type="application/json"
        )

        service = GeminiService(config)

        # Construct prompt with video
        contents = [
            {"text": request.video_url},
            {"text": request.prompt}
        ]

        result = await service.generate_content_async(
            contents,
            response_schema=request.schema
        )

        # Parse structured result
        import json
        structured_result = json.loads(result.response) if isinstance(result.response, str) else result.response

        # Publish as CloudEvent if requested
        event_id = None
        if request.publish_result:
            publisher = create_publisher()
            event_id = await publisher.publish(
                source="/video-analyzer/structured",
                type="com.eventrelay.video.analyzed.structured",
                data=structured_result,
                subject=request.video_url,
                schema=json.dumps(request.schema)
            )
            await publisher.close()

        return {
            "video_url": request.video_url,
            "structured_result": structured_result,
            "schema": request.schema,
            "published": request.publish_result,
            "event_id": event_id
        }
    except Exception as e:
        logger.error(f"Structured analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ CloudEvents Publishing Endpoint ============

@router.post("/publish-event")
async def publish_video_event(
    source: str,
    event_type: str,
    data: Dict,
    subject: Optional[str] = None,
    backend: Optional[str] = None
):
    """
    Manually publish a video analysis event as a CloudEvent.
    
    Supports multiple backends:
    - pubsub: Google Cloud Pub/Sub
    - http: HTTP webhook
    - openwhisk: Apache OpenWhisk trigger
    - file: Local file (for testing)
    
    Example:
    ```json
    {
        "source": "/video-processor/gemini",
        "event_type": "com.eventrelay.video.processed",
        "data": {
            "video_url": "https://youtube.com/watch?v=example",
            "analysis": "..."
        },
        "subject": "https://youtube.com/watch?v=example",
        "backend": "pubsub"
    }
    ```
    """
    try:
        publisher = create_publisher(backend=backend)
        event_id = await publisher.publish(
            source=source,
            type=event_type,
            data=data,
            subject=subject
        )
        await publisher.close()

        return {
            "status": "published",
            "event_id": event_id,
            "backend": backend or "default"
        }
    except Exception as e:
        logger.error(f"Event publishing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
