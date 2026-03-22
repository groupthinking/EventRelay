"""

This module defines the structured output schema for video analysis that transforms
raw transcripts and visual cues into actionable, deterministic build instructions.

The BuildPlan is the primary artifact that flows from Stage 2 (Semantic Logic Parsing)
to Stage 3 (Code Generation), eliminating the need for loose text and template fallbacks.
"""

from enum import Enum
from typing import Any, Optional
BuildPlan — Structured instruction extraction for Stage 2 parsing.

Replaces loose text extraction with a deterministic, structured output
that Stage 3 (code generation) can consume directly.

Usage:
    from youtube_extension.backend.models.build_plan import BuildPlan, BuildStep

    # Gemini returns JSON matching this schema
    plan = BuildPlan.model_validate(gemini_response)
    for step in plan.steps:
        print(f"{step.action} → {step.target_file}")
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StepAction(str, Enum):
    """Action types a build step can perform."""
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    INSTALL_DEPENDENCY = "install_dependency"
    RUN_COMMAND = "run_command"
    CONFIGURE = "configure"
    DEPLOY = "deploy"


class BuildStep(BaseModel):
    """A single, atomic build step extracted from video analysis."""

    order: int = Field(..., description="1-based step order")
    action: StepAction = Field(..., description="What this step does")
    description: str = Field(..., description="Human-readable description of what happens")
    target_file: Optional[str] = Field(None, description="File path this step creates/modifies")
    code_content: Optional[str] = Field(None, description="Code snippet shown in the video (if visible)")
    dependencies: list[str] = Field(default_factory=list, description="Packages/tools this step requires")
    prerequisites: list[int] = Field(default_factory=list, description="Step order numbers that must complete first")


class BuildPlan(BaseModel):
    """
    Structured build plan extracted from video analysis (Stage 2 output).

    This is the contract between Stage 2 (parsing) and Stage 3 (code generation).
    Gemini's structured output mode should return JSON matching this schema.
    """

    video_id: str = Field(..., description="YouTube video ID")
    video_title: str = Field(..., description="Video title")
    project_type: str = Field(default="web", description="web | api | mobile | cli")
    framework: Optional[str] = Field(None, description="Primary framework (react, vue, fastapi, etc.)")
    technologies: list[str] = Field(default_factory=list, description="All technologies mentioned")
    steps: list[BuildStep] = Field(default_factory=list, description="Ordered build steps")
    summary: str = Field(default="", description="One-paragraph summary of what the video teaches")

    @property
    def file_steps(self) -> list[BuildStep]:
        """Steps that create or modify files."""
        return [s for s in self.steps if s.action in (StepAction.CREATE_FILE, StepAction.MODIFY_FILE)]

    @property
    def dependency_steps(self) -> list[BuildStep]:
        """Steps that install dependencies."""
        return [s for s in self.steps if s.action == StepAction.INSTALL_DEPENDENCY]

    def gemini_schema(self) -> dict:
        """Return the JSON Schema dict for Gemini structured output."""
        return self.model_json_schema()
