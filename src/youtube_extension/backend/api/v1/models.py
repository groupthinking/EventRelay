#!/usr/bin/env python3
"""
API v1 Models
=============

Pydantic models for API v1 requests and responses.
Provides data validation and serialization for all API endpoints.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
import re


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    context: Optional[str] = Field("tooltip-assistant", description="Chat context")
    session_id: Optional[str] = Field("default", description="Session identifier")

    class Config:
        schema_extra = {
            "example": {
                "message": "How can I process a YouTube video?",
                "context": "tooltip-assistant",
                "session_id": "user123",
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    response: str = Field(..., description="AI assistant response")
    status: str = Field(..., description="Response status")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(..., description="Response timestamp")

    class Config:
        schema_extra = {
            "example": {
                "response": "I can help you process YouTube videos for analysis...",
                "status": "success",
                "session_id": "user123",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class VideoProcessingRequest(BaseModel):
    """Request model for video processing"""

    video_url: str = Field(..., description="YouTube video URL")
    options: Optional[Dict[str, Any]] = Field({}, description="Processing options")

    @validator("video_url")
    def validate_video_url(cls, value):
        """Validate YouTube URL format"""
        youtube_regex = re.compile(
            r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[a-zA-Z0-9_-]{11}"
        )
        if not youtube_regex.match(value):
            raise ValueError("Invalid YouTube URL format")
        return value

    class Config:
        schema_extra = {
            "example": {
                "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "options": {"quality": "high", "include_transcript": True},
            }
        }


class VideoProcessingResponse(BaseModel):
    """Response model for video processing"""

    result: Dict[str, Any] = Field(..., description="Processing results")
    status: str = Field(..., description="Processing status")
    progress: Optional[float] = Field(
        0.0, ge=0.0, le=100.0, description="Progress percentage"
    )
    timestamp: datetime = Field(..., description="Processing timestamp")

    class Config:
        schema_extra = {
            "example": {
                "result": {
                    "video_id": "jNQXAC9IVRw",
                    "title": "Sample Video",
                    "processed_data": "...",
                },
                "status": "success",
                "progress": 100.0,
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class MarkdownRequest(BaseModel):
    """Request model for markdown processing"""

    video_url: str = Field(..., description="YouTube video URL")
    force_regenerate: Optional[bool] = Field(
        False, description="Force cache regeneration"
    )

    @validator("video_url")
    def validate_video_url(cls, value):
        """Validate YouTube URL format"""
        youtube_regex = re.compile(
            r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[a-zA-Z0-9_-]{11}"
        )
        if not youtube_regex.match(value):
            raise ValueError("Invalid YouTube URL format")
        return value

    class Config:
        schema_extra = {
            "example": {
                "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "force_regenerate": False,
            }
        }


class MarkdownResponse(BaseModel):
    """Response model for markdown processing"""

    video_id: str = Field(..., description="YouTube video ID")
    video_url: str = Field(..., description="Original video URL")
    metadata: Dict[str, Any] = Field(..., description="Video metadata")
    markdown_content: str = Field(..., description="Generated markdown content")
    cached: bool = Field(..., description="Whether result was cached")
    save_path: str = Field(..., description="File save path")
    processing_time: str = Field(..., description="Processing duration")
    status: str = Field(..., description="Processing status")

    class Config:
        schema_extra = {
            "example": {
                "video_id": "jNQXAC9IVRw",
                "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "metadata": {"title": "Sample Video", "duration": "3:32"},
                "markdown_content": "# Sample Video Analysis\n\n...",
                "cached": False,
                "save_path": "/path/to/analysis.md",
                "processing_time": "15.3s",
                "status": "success",
            }
        }


class VideoToSoftwareRequest(BaseModel):
    """Request model for video-to-software conversion"""

    video_url: str = Field(..., description="YouTube video URL")
    project_type: str = Field("web", description="Project type (web, api, ml, mobile)")
    deployment_target: str = Field("vercel", description="Deployment platform")
    features: Optional[List[str]] = Field(
        [], description="Additional features to implement"
    )

    @validator("video_url")
    def validate_video_url(cls, value):
        """Validate YouTube URL format"""
        youtube_regex = re.compile(
            r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[a-zA-Z0-9_-]{11}"
        )
        if not youtube_regex.match(value):
            raise ValueError("Invalid YouTube URL format")
        return value

    @validator("project_type")
    def validate_project_type(cls, value):
        """Validate project type"""
        valid_types = ["web", "api", "ml", "mobile", "desktop"]
        if value not in valid_types:
            raise ValueError(f'Project type must be one of: {", ".join(valid_types)}')
        return value

    @validator("deployment_target")
    def validate_deployment_target(cls, value):
        """Validate deployment target"""
        valid_targets = [
            "vercel",
            "claude",
            "openai",
            "gemini",
            "lindy",
            "lindy.ai",
            "manus",
            "genspark",
            "genspark.ai",
            "github",
            "codex",
            "cursor",
            "github_pages",
        ]
        if value not in valid_targets:
            raise ValueError(
                f'Deployment target must be one of: {", ".join(valid_targets)}'
            )
        return value

    class Config:
        schema_extra = {
            "example": {
                "video_url": "https://www.youtube.com/watch?v=bMknfKXIFA8",
                "project_type": "web",
                "deployment_target": "vercel",
                "features": ["responsive_design", "dark_mode"],
            }
        }


class VideoToSoftwareResponse(BaseModel):
    """Response model for video-to-software conversion"""

    video_url: str = Field(..., description="Original video URL")
    project_name: str = Field(..., description="Generated project name")
    project_type: str = Field(..., description="Project type")
    deployment_target: str = Field(..., description="Deployment target")
    live_url: str = Field(..., description="Live deployment URL")
    github_repo: str = Field(..., description="GitHub repository URL")
    build_status: str = Field(..., description="Build status")
    processing_time: str = Field(..., description="Total processing time")
    features_implemented: List[str] = Field(..., description="Implemented features")
    video_analysis: Dict[str, Any] = Field(..., description="Video analysis results")
    code_generation: Dict[str, Any] = Field(..., description="Code generation details")
    deployment: Dict[str, Any] = Field(..., description="Deployment information")
    status: str = Field(..., description="Overall status")
    timestamp: datetime = Field(..., description="Completion timestamp")

    class Config:
        schema_extra = {
            "example": {
                "video_url": "https://www.youtube.com/watch?v=bMknfKXIFA8",
                "project_name": "sample-video-app",
                "project_type": "web",
                "deployment_target": "vercel",
                "live_url": "https://sample-video-app.vercel.app",
                "github_repo": "https://github.com/user/sample-video-app",
                "build_status": "completed",
                "processing_time": "45.2s",
                "features_implemented": ["responsive_design", "dark_mode"],
                "video_analysis": {"status": "success"},
                "code_generation": {"framework": "React"},
                "deployment": {"status": "success"},
                "status": "success",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Response model for health checks"""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: Optional[str] = Field(None, description="API version")
    components: Optional[Dict[str, Any]] = Field(
        {}, description="Component health details"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "2.0.0",
                "components": {"video_processor": "available", "cache": "healthy"},
            }
        }


class CacheStats(BaseModel):
    """Response model for cache statistics"""

    total_cached_videos: int = Field(..., description="Total cached videos")
    categories: Dict[str, Any] = Field(..., description="Cache by category")
    total_size_mb: float = Field(..., description="Total cache size in MB")
    oldest_cache: Optional[str] = Field(
        None, description="Oldest cache entry timestamp"
    )
    newest_cache: Optional[str] = Field(
        None, description="Newest cache entry timestamp"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_cached_videos": 42,
                "categories": {
                    "education": {"count": 15, "size_mb": 25.3},
                    "technology": {"count": 27, "size_mb": 41.7},
                },
                "total_size_mb": 67.0,
                "oldest_cache": "2024-01-01T10:00:00Z",
                "newest_cache": "2024-01-01T14:30:00Z",
            }
        }


class GeminiCacheRequest(BaseModel):
    """Request payload for Gemini cache creation"""

    contents: Union[str, Dict[str, Any], List[Any]] = Field(
        ..., description="Prompt or content payload to cache"
    )
    model_name: Optional[str] = Field(
        None, description="Specific model to use for caching"
    )
    ttl_seconds: int = Field(3600, ge=60, description="Cache time-to-live in seconds")
    display_name: Optional[str] = Field(
        None, description="Friendly name for the cache entry"
    )
    generation_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional Gemini parameters"
    )


class GeminiCacheResponse(BaseModel):
    """Response payload for Gemini cache creation"""

    success: bool
    cache: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency: Optional[float] = None


class GeminiBatchRequest(BaseModel):
    """Request payload for Gemini batch submission"""

    requests: List[Dict[str, Any]] = Field(
        ..., min_items=1, description="List of generateContent requests"
    )
    model_name: Optional[str] = Field(None, description="Optional model override")
    wait: bool = Field(False, description="Wait for completion before returning")
    poll_interval: Optional[float] = Field(
        5.0, ge=0.1, description="Polling interval when waiting"
    )
    timeout: Optional[float] = Field(
        600.0, ge=1.0, description="Maximum wait time in seconds"
    )
    batch_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional Gemini batch parameters"
    )


class GeminiBatchResponse(BaseModel):
    """Response payload for Gemini batch submission"""

    success: bool
    operation: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    completed: Optional[bool] = None
    error: Optional[str] = None
    latency: Optional[float] = None


class GeminiTokenRequest(BaseModel):
    """Request payload for Gemini ephemeral token creation"""

    model_name: Optional[str] = Field(
        None, description="Model alias to scope the token"
    )
    audience: Optional[str] = Field(None, description="Audience claim for the token")
    ttl_seconds: Optional[int] = Field(
        None, ge=60, description="Token time-to-live in seconds"
    )
    token_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional token parameters"
    )


class GeminiTokenResponse(BaseModel):
    """Response payload for Gemini ephemeral token creation"""

    success: bool
    token: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency: Optional[float] = None


class VideoClipOptions(BaseModel):
    """Optional video clipping and sampling controls for Gemini processing."""

    start_seconds: Optional[float] = Field(
        None,
        ge=0.0,
        description="Start offset (seconds) when requesting Gemini video processing",
    )
    end_seconds: Optional[float] = Field(
        None,
        gt=0.0,
        description="End offset (seconds); must be greater than start_seconds when provided",
    )
    fps: Optional[float] = Field(
        None,
        gt=0.0,
        le=30.0,
        description="Sampling rate for Gemini video frames; defaults to API standard when omitted",
    )

    @validator("end_seconds")
    def _validate_offsets(cls, value, values):  # noqa: D401 - short helper
        """Ensure the end offset is after the start offset."""
        start = values.get("start_seconds")
        if value is not None and start is not None and value <= start:
            raise ValueError("end_seconds must be greater than start_seconds")
        return value


class TranscriptActionRequest(BaseModel):
    """Request model for transcript-to-action workflow"""

    video_url: str = Field(..., description="YouTube video URL")
    language: Optional[str] = Field("en", description="Preferred transcript language")
    transcript_text: Optional[str] = Field(
        None, description="Optional pre-fetched transcript text"
    )
    video_options: Optional[VideoClipOptions] = Field(
        None,
        description="Optional Gemini video metadata controls (clip window, fps, resolution)",
    )


class TranscriptActionResponse(BaseModel):
    """Response model for transcript-to-action workflow"""

    success: bool
    video_url: str
    metadata: Dict[str, Any]
    transcript: Dict[str, Any]
    outputs: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    orchestration_meta: Dict[str, Any]


class FeedbackRequest(BaseModel):
    """Request model for feedback submission"""

    video_id: Optional[str] = Field(None, description="Related video ID")
    feedback_type: str = Field(..., description="Type of feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5)")
    comment: Optional[str] = Field(
        None, max_length=1000, description="Feedback comment"
    )
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field({}, description="Additional metadata")

    @validator("feedback_type")
    def validate_feedback_type(cls, value):
        """Validate feedback type"""
        valid_types = [
            "quality",
            "accuracy",
            "speed",
            "feature_request",
            "bug_report",
            "general",
        ]
        if value not in valid_types:
            raise ValueError(f'Feedback type must be one of: {", ".join(valid_types)}')
        return value

    class Config:
        schema_extra = {
            "example": {
                "video_id": "jNQXAC9IVRw",
                "feedback_type": "quality",
                "rating": 5,
                "comment": "Excellent video analysis results!",
                "user_id": "user123",
                "metadata": {"source": "web_interface"},
            }
        }


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    status: str = Field(..., description="Submission status")
    message: Optional[str] = Field(None, description="Response message")
    feedback_id: Optional[str] = Field(None, description="Feedback identifier")
    timestamp: datetime = Field(..., description="Submission timestamp")

    class Config:
        schema_extra = {
            "example": {
                "status": "ok",
                "message": "Thank you for your feedback!",
                "feedback_id": "fb123456",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    error_type: Optional[str] = Field(None, description="Error type/category")
    timestamp: datetime = Field(..., description="Error timestamp")
    path: Optional[str] = Field(None, description="Request path")

    class Config:
        schema_extra = {
            "example": {
                "error": "Validation error",
                "detail": "Invalid YouTube URL format",
                "error_type": "validation_error",
                "timestamp": "2024-01-01T12:00:00Z",
                "path": "/api/v1/process-video",
            }
        }
