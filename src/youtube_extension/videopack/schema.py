from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, constr, validator


class VPVersion(str, Enum):
    v0 = "v0"


class TranscriptSegment(BaseModel):
    idx: int
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    text: str


class Transcript(BaseModel):
    language: str | None = None
    full_text: str
    segments: list[TranscriptSegment] = Field(default_factory=list)


class Keyframe(BaseModel):
    t_s: float = Field(ge=0)
    image_path: str | None = None
    desc: str | None = None


class Requirement(BaseModel):
    id: str
    title: str
    detail: str | None = None
    priority: str | None = Field(default="normal")  # low|normal|high
    tags: list[str] = Field(default_factory=list)


class CodeSnippet(BaseModel):
    path_hint: str | None = None
    lang: str | None = None
    content: str


class Chapter(BaseModel):
    title: str
    start_s: float = Field(ge=0)
    end_s: float | None = None
    summary: str | None = None


class CodeCue(BaseModel):
    t_s: float = Field(ge=0, description="Timestamp in video where code is shown/discussed")
    language: str | None = None
    snippet: str | None = None
    description: str | None = None
    framework: str | None = None


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
    title: str
    description: str | None = None
    category: str | None = Field(default="learn")  # setup|build|deploy|learn|research|configure
    estimated_minutes: int | None = None
    priority: str | None = Field(default="normal")  # low|normal|high
    dependencies: list[str] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    kind: str  # e.g., "repo", "file", "url"
    path: str | None = None  # repo/file path
    url: HttpUrl | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class Metrics(BaseModel):
    cost_usd: float | None = None
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class Provenance(BaseModel):
    created_at: datetime
    tool_versions: dict[str, str] = Field(
        default_factory=dict
    )  # {"yt_api":"X", "mcp":"Y"}
    source_hash: str | None = None
    notes: str | None = None


class VideoPackV0(BaseModel):
    version: VPVersion = VPVersion.v0
    id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
    video_id: constr(strip_whitespace=True, min_length=3)
    source_url: HttpUrl | None = None

    transcript: Transcript
    chapters: list[Chapter] = Field(default_factory=list)
    keyframes: list[Keyframe] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    code_snippets: list[CodeSnippet] = Field(default_factory=list)
    code_cues: list[CodeCue] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)

    metrics: Metrics = Field(default_factory=Metrics)
    provenance: Provenance

    @validator("keyframes", each_item=True)
    def _kf_has_desc_or_path(cls, keyframe_value):
        if not (keyframe_value.image_path or keyframe_value.desc):
            raise ValueError("keyframe requires image_path or desc")
        return keyframe_value
