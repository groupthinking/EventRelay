from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, constr, validator
from enum import Enum
import uuid as _uuid


class VPVersion(str, Enum):
    v0 = "v0"


class TranscriptSegment(BaseModel):
    idx: int
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    text: str


class Transcript(BaseModel):
    language: Optional[str] = None
    full_text: str
    segments: List[TranscriptSegment] = Field(default_factory=list)


class Keyframe(BaseModel):
    t_s: float = Field(ge=0)
    image_path: Optional[str] = None
    desc: Optional[str] = None


class Requirement(BaseModel):
    id: str
    title: str
    detail: Optional[str] = None
    priority: Optional[str] = Field(default="normal")  # low|normal|high
    tags: List[str] = Field(default_factory=list)


class CodeSnippet(BaseModel):
    path_hint: Optional[str] = None
    lang: Optional[str] = None
    content: str


class ArtifactRef(BaseModel):
    kind: str  # e.g., "repo", "file", "url"
    path: Optional[str] = None  # repo/file path
    url: Optional[HttpUrl] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class Metrics(BaseModel):
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


class Provenance(BaseModel):
    created_at: datetime
    tool_versions: Dict[str, str] = Field(
        default_factory=dict
    )  # {"yt_api":"X", "mcp":"Y"}
    source_hash: Optional[str] = None
    notes: Optional[str] = None


class VideoPackV0(BaseModel):
    version: VPVersion = VPVersion.v0
    id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
    video_id: constr(strip_whitespace=True, min_length=3)
    source_url: Optional[HttpUrl] = None

    transcript: Transcript
    keyframes: List[Keyframe] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)
    requirements: List[Requirement] = Field(default_factory=list)
    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    artifacts: List[ArtifactRef] = Field(default_factory=list)

    metrics: Metrics = Field(default_factory=Metrics)
    provenance: Provenance

    @validator("keyframes", each_item=True)
    def _kf_has_desc_or_path(cls, keyframe_value):
        if not (keyframe_value.image_path or keyframe_value.desc):
            raise ValueError("keyframe requires image_path or desc")
        return keyframe_value
