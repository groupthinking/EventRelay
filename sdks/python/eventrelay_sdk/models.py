from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptActionRequest(BaseModel):
    video_url: str
    language: Optional[str] = "en"
    transcript_text: Optional[str] = None
    video_options: Optional[dict[str, Any]] = None


class TranscriptActionResponse(BaseModel):
    success: bool
    video_url: str
    metadata: dict[str, Any]
    transcript: dict[str, Any]
    outputs: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    orchestration_meta: dict[str, Any]


class VideoProcessingRequest(BaseModel):
    video_url: str
    options: Optional[dict[str, Any]] = None


class VideoProcessingResponse(BaseModel):
    result: dict[str, Any]
    status: str
    progress: Optional[float] = 0.0
    timestamp: str


class VideoToSoftwareRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    video_url: str = Field(..., alias="url")
    project_type: Optional[str] = "web"
    deployment_target: Optional[str] = "vercel"
    features: Optional[list[str]] = None


class VideoToSoftwareResponse(BaseModel):
    video_url: str
    project_name: str
    project_type: str
    deployment_target: str
    live_url: str
    github_repo: str
    build_status: str
    processing_time: str
    features_implemented: list[str]
    video_analysis: dict[str, Any]
    code_generation: dict[str, Any]
    deployment: dict[str, Any]
    status: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: Optional[str] = None
    components: Optional[dict[str, Any]] = None
