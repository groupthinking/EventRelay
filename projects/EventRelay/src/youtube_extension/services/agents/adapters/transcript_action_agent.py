#!/usr/bin/env python3
"""Transcript-to-action agent leveraging Gemini via the hybrid processor."""

from __future__ import annotations

import os
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from ..base_agent import BaseAgent
from ...ai.hybrid_processor_service import HybridProcessorService, HybridConfig, TaskType
from ...ai.gemini_service import GeminiResult, GeminiConfig

logger = logging.getLogger(__name__)


@dataclass
class PromptResult:
    """Container for parsed Gemini responses."""

    raw_text: str
    parsed: Optional[Dict[str, Any]]


from ..registry import register
from ..dto import AgentRequest, AgentResult

@register
class TranscriptActionAgent(BaseAgent):
    name = "transcript_action"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        hybrid_cfg = cfg.get("hybrid_config") or self._build_hybrid_config()
        self._hybrid_processor: HybridProcessorService = cfg.get("hybrid_processor") or HybridProcessorService(hybrid_cfg)
        self._summary_model = cfg.get("summary_model")
        self._project_model = cfg.get("project_model")
        self._task_model = cfg.get("task_model")
        self._language = cfg.get("language", "en")

    async def run(self, req: AgentRequest) -> AgentResult:
        start_time = asyncio.get_event_loop().time()
        transcript_text = req.params.get("transcript")
        metadata = req.params.get("metadata", {})
        video_metadata = req.params.get("video_metadata") or {}

        if not transcript_text:
            return self._failure("Missing transcript text", start_time)

        try:
            summary = await self._generate_summary(transcript_text, metadata, video_metadata)
            if not summary.parsed:
                logger.debug("Summary JSON parsing failed; falling back to raw text")

            scaffold = await self._generate_project_scaffold(transcript_text, metadata, video_metadata)
            tasks = await self._generate_task_board(transcript_text, metadata, video_metadata)

            total_time = asyncio.get_event_loop().time() - start_time
            return AgentResult(
                status="ok",
                output={
                    "summary": summary.parsed or {"raw": summary.raw_text},
                    "project_scaffold": scaffold.parsed or {"raw": scaffold.raw_text},
                    "task_board": tasks.parsed or {"raw": tasks.raw_text},
                    "metadata": metadata,
                    "processing_notes": {
                        "summary_model": self._summary_model or self._default_model(TaskType.COMPLEX_REASONING),
                        "project_model": self._project_model or self._default_model(TaskType.BATCH_PROCESSING),
                        "task_model": self._task_model or self._default_model(TaskType.BATCH_PROCESSING),
                        "language": self._language,
                        "clip_window": self._clip_window_notes(video_metadata),
                    },
                },
                logs=[],
            )
        except Exception as exc:
            logger.error("TranscriptActionAgent failed: %s", exc, exc_info=True)
            return self._failure(str(exc), start_time)

    async def _generate_summary(
        self,
        transcript: str,
        metadata: Dict[str, Any],
        video_metadata: Dict[str, Any],
    ) -> PromptResult:
        clip_hint = self._build_prompt_clip_context(metadata, video_metadata)
        prompt = (
            "You are a technical product lead. Given the transcript below, produce a JSON object with keys"
            " 'executive_summary', 'target_audience', 'key_objectives', 'risks', and 'next_milestones'."
            " Each value should be concise and actionable."
        )
        if clip_hint:
            prompt += f" Focus on {clip_hint}."
        return await self._invoke_gemini(prompt, transcript, self._summary_model, fail_message="summary generation")

    async def _generate_project_scaffold(
        self,
        transcript: str,
        metadata: Dict[str, Any],
        video_metadata: Dict[str, Any],
    ) -> PromptResult:
        context = metadata.get("title") or metadata.get("video_id") or "the referenced content"
        clip_hint = self._build_prompt_clip_context(metadata, video_metadata)
        prompt = (
            f"Create a deployment-ready project scaffold for {context}. Return JSON with keys"
            " 'repository_structure' (list of directories/files with purposes),"
            " 'core_modules' (list with name, responsibility, api_notes),"
            " and 'integration_points' (list describing external services/APIs)."
            " Base your recommendations strictly on the transcript insights."
        )
        if clip_hint:
            prompt += f" Anchor recommendations to {clip_hint}."
        return await self._invoke_gemini(prompt, transcript, self._project_model, fail_message="project scaffold generation")

    async def _generate_task_board(
        self,
        transcript: str,
        metadata: Dict[str, Any],
        video_metadata: Dict[str, Any],
    ) -> PromptResult:
        clip_hint = self._build_prompt_clip_context(metadata, video_metadata)
        prompt = (
            "Return a JSON Kanban board with columns 'Backlog', 'In Progress', 'Blocked', 'Review', 'Done'."
            " Each column should contain items with 'title', 'owner_role', 'dependencies', 'estimate_days',"
            " and 'definition_of_done'. Use transcript-driven priorities."
        )
        if clip_hint:
            prompt += f" Prioritise work relevant to {clip_hint}."
        return await self._invoke_gemini(prompt, transcript, self._task_model, fail_message="task board generation")

    async def _invoke_gemini(
        self,
        prompt: str,
        transcript: str,
        model_override: Optional[str],
        *,
        fail_message: str,
    ) -> PromptResult:
        model_name = model_override or self._default_model(TaskType.COMPLEX_REASONING)
        self._hybrid_processor.gemini.select_model(model_name)
        result: GeminiResult = await self._hybrid_processor.gemini.process_text(
            prompt,
            input_text=transcript,
            response_mime_type="application/json",
        )
        if not result.success or not result.response:
            raise RuntimeError(f"Gemini {fail_message} failed: {result.error}")

        parsed = self._safe_parse_json(result.response)
        return PromptResult(raw_text=result.response, parsed=parsed)

    def _default_model(self, task_type: TaskType) -> str:
        return self._hybrid_processor.config.model_routing.get(task_type, self._hybrid_processor.config.gemini.model_name)

    @staticmethod
    def _safe_parse_json(payload: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _clip_window_notes(video_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not video_metadata:
            return None
        if not any(key in video_metadata for key in ("start_offset", "end_offset", "fps")):
            return None
        return {
            key: value
            for key, value in video_metadata.items()
            if key in {"start_offset", "end_offset", "fps"}
        }

    def _build_prompt_clip_context(
        self,
        metadata: Dict[str, Any],
        video_metadata: Dict[str, Any],
    ) -> str:
        if not video_metadata:
            return ""

        start = self._format_offset(video_metadata.get("start_offset"))
        end = self._format_offset(video_metadata.get("end_offset"))
        fps = video_metadata.get("fps")

        segments = []
        if start or end:
            if start and end:
                segments.append(f"the clip from {start} to {end}")
            elif start:
                segments.append(f"the clip starting at {start}")
            elif end:
                segments.append(f"the clip ending at {end}")

        if fps:
            segments.append(f"sampled at {fps} FPS")

        return ", ".join(segments)

    @staticmethod
    def _format_offset(value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            seconds = float(value)
        elif isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned.endswith("s"):
                cleaned = cleaned[:-1]
            try:
                seconds = float(cleaned)
            except ValueError:
                return None
        else:
            return None

        if seconds < 0:
            return None

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".rstrip("0").rstrip(".")
        return f"{minutes:02d}:{secs:06.3f}".rstrip("0").rstrip(".")

    def _failure(self, message: str, start_time: float) -> AgentResult:
        elapsed = asyncio.get_event_loop().time() - start_time
        return AgentResult(
            success=False,
            data={},
            errors=[message],
            processing_time=elapsed,
            agent_name=self.name,
            timestamp=datetime.now(),
        )

    @staticmethod
    def _build_hybrid_config() -> HybridConfig:
        gemini_cfg = GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GEMINI_LOCATION", "us-central1"),
        )
        return HybridConfig(gemini=gemini_cfg)
