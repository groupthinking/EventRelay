#!/usr/bin/env python3
"""
Gemini-Only Hybrid Processor Service
====================================

The previous implementation combined a local FastVLM backend with Gemini.
FastVLM support has been removed, so this module now provides a simplified
service that keeps the same public surface area while delegating all work to
Gemini. The routing engine and result structures remain to avoid breaking
imports elsewhere in the codebase.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image

from .gemini_service import GeminiConfig, GeminiResult, GeminiService


class ProcessingMode(Enum):
    """Processing mode roadmap retained for compatibility."""

    CLOUD_ONLY = "cloud"
    HYBRID_AUTO = "hybrid_auto"
    HYBRID_PARALLEL = "hybrid_parallel"
    HYBRID_FALLBACK = "hybrid_fallback"
    LOCAL_ONLY = "local"


class TaskType(Enum):
    """Task categorisation retained for existing routing heuristics."""

    YOUTUBE_ANALYSIS = "youtube_analysis"
    LONG_VIDEO_SUMMARY = "long_video_summary"
    COMPLEX_REASONING = "complex_reasoning"
    MULTIMODAL_SEARCH = "multimodal_search"
    BATCH_PROCESSING = "batch_processing"
    GENERAL_QA = "general_qa"
    IMAGE_DESCRIPTION = "image_description"
    VIDEO_UNDERSTANDING = "video_understanding"
    AUDIO_ANALYSIS = "audio_analysis"
    REAL_TIME_CAPTION = "real_time_caption"
    TECHNICAL_DOCUMENT = "technical_document"
    PRODUCT_DEMO = "product_demo"
    PRIVACY_SENSITIVE = "privacy_sensitive"
    LOW_LATENCY_QA = "low_latency_qa"


@dataclass
class HybridConfig:
    """Configuration for the simplified hybrid (Gemini-only) service."""

    gemini: GeminiConfig = None
    default_mode: ProcessingMode = ProcessingMode.CLOUD_ONLY
    routing_threshold: float = 0.7
    enable_caching: bool = True
    cache_ttl: int = 3600
    enable_metrics: bool = True
    model_routing: Dict[TaskType, str] = None

    def __post_init__(self) -> None:
        if self.gemini is None:
            self.gemini = GeminiConfig()
        if self.model_routing is None:
            self.model_routing = {
                TaskType.YOUTUBE_ANALYSIS: "gemini-3-pro-preview",
                TaskType.VIDEO_UNDERSTANDING: "gemini-3-pro-preview",
                TaskType.AUDIO_ANALYSIS: "gemini-1.5-pro",
                TaskType.COMPLEX_REASONING: "gemini-1.5-pro",
                TaskType.MULTIMODAL_SEARCH: "gemini-3-pro-preview",
                TaskType.BATCH_PROCESSING: "gemini-1.5-pro",
                TaskType.GENERAL_QA: "gemini-1.5-pro",
                TaskType.PRIVACY_SENSITIVE: "gemma-2-9b-it",
                TaskType.PRODUCT_DEMO: "veo-2",
            }


@dataclass
class RoutingDecision:
    """Routing decision result (still returned for API compatibility)."""

    mode: ProcessingMode
    confidence: float
    reason: str
    task_type: TaskType


@dataclass
class HybridResult:
    """Result from the hybrid processor (Gemini only)."""

    success: bool
    response: Optional[str]
    latency: float
    mode_used: ProcessingMode
    cloud_result: Optional[GeminiResult] = None
    routing_decision: Optional[RoutingDecision] = None
    from_cache: bool = False
    error: Optional[str] = None


TASK_ROUTING_RULES: Dict[TaskType, ProcessingMode] = {
    TaskType.REAL_TIME_CAPTION: ProcessingMode.CLOUD_ONLY,
    TaskType.TECHNICAL_DOCUMENT: ProcessingMode.CLOUD_ONLY,
    TaskType.PRODUCT_DEMO: ProcessingMode.CLOUD_ONLY,
    TaskType.PRIVACY_SENSITIVE: ProcessingMode.CLOUD_ONLY,
    TaskType.LOW_LATENCY_QA: ProcessingMode.CLOUD_ONLY,
    TaskType.YOUTUBE_ANALYSIS: ProcessingMode.CLOUD_ONLY,
    TaskType.LONG_VIDEO_SUMMARY: ProcessingMode.CLOUD_ONLY,
    TaskType.COMPLEX_REASONING: ProcessingMode.CLOUD_ONLY,
    TaskType.MULTIMODAL_SEARCH: ProcessingMode.CLOUD_ONLY,
    TaskType.BATCH_PROCESSING: ProcessingMode.CLOUD_ONLY,
    TaskType.GENERAL_QA: ProcessingMode.CLOUD_ONLY,
    TaskType.IMAGE_DESCRIPTION: ProcessingMode.CLOUD_ONLY,
    TaskType.VIDEO_UNDERSTANDING: ProcessingMode.CLOUD_ONLY,
    TaskType.AUDIO_ANALYSIS: ProcessingMode.CLOUD_ONLY,
}


class RoutingEngine:
    """Simple routing engine that now always selects Gemini."""

    def __init__(self, config: HybridConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RoutingEngine")

    def decide_routing(
        self,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
        task_type: Optional[TaskType] = None,
    ) -> RoutingDecision:
        """Decide routing strategy; currently always Gemini."""
        metadata = metadata or {}
        inferred_task = task_type or self._classify_task(prompt, metadata)
        reason = "Gemini selected (FastVLM disabled)"
        return RoutingDecision(
            mode=ProcessingMode.CLOUD_ONLY,
            confidence=0.9,
            reason=reason,
            task_type=inferred_task,
        )

    def _classify_task(self, prompt: str, metadata: Dict[str, Any]) -> TaskType:
        """Simple classifier retained from original implementation."""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ['private', 'confidential', 'sensitive', 'personal']):
            return TaskType.PRIVACY_SENSITIVE

        if any(word in prompt_lower for word in ['real-time', 'live', 'instant', 'quick']):
            return TaskType.REAL_TIME_CAPTION

        if any(word in prompt_lower for word in ['youtube', 'video summary', 'long video']):
            return TaskType.YOUTUBE_ANALYSIS

        if any(word in prompt_lower for word in ['analyze', 'complex', 'detailed analysis', 'reasoning']):
            return TaskType.COMPLEX_REASONING

        if any(word in prompt_lower for word in ['transcribe', 'audio', 'podcast', 'meeting recording']):
            return TaskType.AUDIO_ANALYSIS

        if any(word in prompt_lower for word in ['technical', 'documentation', 'code', 'diagram']):
            return TaskType.TECHNICAL_DOCUMENT

        return TaskType.GENERAL_QA


class HybridProcessorService:
    """
    Replacement hybrid processor that delegates all work to Gemini.
    The public API remains intact for callers that expect a hybrid service.
    """

    def __init__(self, config: Optional[HybridConfig] = None) -> None:
        self.config = config or HybridConfig()
        self.logger = logging.getLogger(__name__)

        self.gemini = GeminiService(self.config.gemini)
        self.router = RoutingEngine(self.config)

        self._cache: Optional[Dict[str, HybridResult]] = {} if self.config.enable_caching else None
        self.metrics = {
            "total_requests": 0,
            "cloud_requests": 0,
            "cache_hits": 0,
            "total_latency": 0.0,
            "errors": 0,
        }

        self.logger.info("Hybrid (Gemini-only) processor service initialized")
        self._log_status()

    def _log_status(self) -> None:
        gemini_info = self.gemini.get_model_info()
        self.logger.info(f"Gemini status: {gemini_info}")

    def _get_cache_key(self, input_data: Union[str, Path], prompt: str) -> str:
        return f"{hash(str(input_data))}_{hash(prompt)}"

    async def process(
        self,
        input_data: Union[str, Path, Image.Image],
        prompt: str,
        task_type: Optional[TaskType] = None,
        force_mode: Optional[ProcessingMode] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HybridResult:
        """Process an input using Gemini."""
        self.metrics["total_requests"] += 1
        start_time = time.time()
        metadata = metadata or {}

        cached_result = None
        cache_key = None
        if self._cache is not None and isinstance(input_data, (str, Path)):
            cache_key = self._get_cache_key(input_data, prompt)
            cached_result = self._cache.get(cache_key)
            if cached_result:
                self.metrics["cache_hits"] += 1
                result = cached_result
                result.from_cache = True
                return result

        try:
            routing_decision = RoutingDecision(
                mode=ProcessingMode.CLOUD_ONLY if force_mode is None else force_mode,
                confidence=0.9,
                reason="Gemini selected",
                task_type=task_type or TaskType.GENERAL_QA,
            )

            cloud_result = await self._call_gemini(
                input_data,
                prompt,
                routing_decision.task_type,
                **kwargs,
            )

            hybrid_result = HybridResult(
                success=cloud_result.success,
                response=cloud_result.response,
                latency=cloud_result.latency,
                mode_used=ProcessingMode.CLOUD_ONLY,
                cloud_result=cloud_result,
                routing_decision=routing_decision,
                error=cloud_result.error,
            )

            if self._cache is not None and cache_key and hybrid_result.success:
                self._cache[cache_key] = hybrid_result

            total_latency = time.time() - start_time
            hybrid_result.latency = total_latency
            self._update_metrics(total_latency)
            return hybrid_result

        except Exception as exc:
            self.metrics["errors"] += 1
            self.logger.error(f"Gemini processing failed: {exc}")
            return HybridResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                mode_used=ProcessingMode.CLOUD_ONLY,
                error=str(exc),
            )

    async def _call_gemini(
        self,
        input_data: Union[str, Path, Image.Image],
        prompt: str,
        task_type: Optional[TaskType],
        **kwargs,
    ) -> GeminiResult:
        """Route requests to Gemini helpers based on input type."""
        video_metadata = kwargs.get("video_metadata")
        forward_kwargs = {k: v for k, v in kwargs.items() if k != "video_metadata"}

        model_name = forward_kwargs.pop("model_name", None)
        if not model_name and task_type:
            model_name = self.config.model_routing.get(task_type)

        self.gemini.select_model(model_name)

        if isinstance(input_data, (str, Path)):
            input_str = str(input_data)
            lower_input = input_str.lower()

            if lower_input.startswith("http") and "youtube.com" in lower_input:
                return await self.gemini.process_youtube(
                    input_str,
                    prompt,
                    video_metadata=video_metadata,
                    **forward_kwargs,
                )

            if lower_input.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpg", ".mpeg", ".wmv", ".3gp")):
                return await self.gemini.process_video(
                    input_str,
                    prompt,
                    video_metadata=video_metadata,
                    **forward_kwargs,
                )

            if lower_input.endswith((".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")):
                return await self.gemini.process_audio(
                    input_str,
                    prompt,
                    **forward_kwargs,
                )

        return await self.gemini.process_image(input_data, prompt, **forward_kwargs)

    def _update_metrics(self, latency: float) -> None:
        self.metrics["cloud_requests"] += 1
        self.metrics["total_latency"] += latency

    def get_metrics(self) -> Dict[str, Any]:
        total_requests = self.metrics["total_requests"]
        avg_latency = self.metrics["total_latency"] / total_requests if total_requests else 0.0
        return {
            **self.metrics,
            "average_latency": avg_latency,
            "cache_hit_rate": (self.metrics["cache_hits"] / total_requests) if total_requests else 0.0,
            "error_rate": (self.metrics["errors"] / total_requests) if total_requests else 0.0,
            "gemini_available": self.gemini.is_available(),
        }

    def is_available(self) -> bool:
        return self.gemini.is_available()

    async def cleanup(self) -> None:
        await self.gemini.cleanup()
        if self._cache:
            self._cache.clear()
        self.logger.info("Hybrid processor service cleaned up")
