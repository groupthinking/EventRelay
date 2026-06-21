#!/usr/bin/env python3
"""
Strategy Agent
Generates actionable funnels and "Better Way" optimizations with A2UI support.
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional

from ...ai.hybrid_processor_service import (
    HybridConfig,
    HybridProcessorService,
    TaskType,
)
from ..base_agent import BaseAgent
from ..dto import AgentRequest, AgentResult
from ..registry import register

logger = logging.getLogger(__name__)

@register
class StrategyAgent(BaseAgent):
    """Agent specialized in strategic analysis and A2UI funnel generation."""
    name = "strategy_agent"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        cfg = config or {}
        gemini_cfg = cfg.get("gemini_config") or self._build_gemini_config()
        self._hybrid_processor = cfg.get("hybrid_processor") or HybridProcessorService(HybridConfig(gemini=gemini_cfg))
        self._model = cfg.get("model") or gemini_cfg.model_name

    async def run(self, req: AgentRequest) -> AgentResult:
        start_time = asyncio.get_event_loop().time()
        video_info = req.params.get("metadata") or {}
        video_metadata = req.params.get("video_metadata") or {}
        personality_map = req.params.get("personality_map") or {}
        transcript = req.params.get("transcript")

        if not transcript and not video_info:
            return self._failure("Missing transcript or video metadata", start_time)

        try:
            # Generate strategic analysis and A2UI payload
            strategy_data = await self._generate_strategy(transcript, video_info, personality_map)

            asyncio.get_event_loop().time() - start_time
            return AgentResult(
                status="ok",
                output={
                    "strategic_analysis": strategy_data.get("strategic_analysis"),
                    "a2ui_payload": strategy_data.get("a2ui_payload"),
                    "metadata": {
                        "model": self._model,
                        "video_id": video_metadata.get("video_id")
                    }
                },
                logs=[]
            )
        except Exception as exc:
            logger.error("StrategyAgent failed: %s", exc, exc_info=True)
            return self._failure(str(exc), start_time)

    async def _generate_strategy(self, transcript: Optional[str], video_metadata: dict[str, Any], personality_map: dict[str, Any]) -> dict[str, Any]:
        """Call Gemini to generate strategic analysis and A2UI payload."""

        prompt = (
            "You are a master strategist. Analyze the video data and personality mapping provided to generate a "
            "deep strategic analysis and an 'Actionable Funnel' for the user.\n\n"
            "Produce a JSON object with two main keys:\n"
            "1. 'strategic_analysis': { 'core_principle': str, 'user_intent_analysis': str, 'action_optimization': { 'the_better_way': str, 'gain': str } }\n"
            "2. 'a2ui_payload': A list of A2UI messages (beginRendering, surfaceUpdate) that visualize the 3-stage funnel (Info, Application, Mastery).\n\n"
            "A2UI Payload Requirements:\n"
            "- Use 'beginRendering' with surfaceId 'strategic-funnel'.\n"
            "- Use 'surfaceUpdate' with a Heading component and a List component for the funnel stages.\n"
            "- Include a 'Better Way' Card component.\n\n"
            f"Personality Map: {json.dumps(personality_map)}\n"
            f"Video Metadata: {json.dumps(video_metadata)}\n"
        )

        if transcript:
            prompt += f"\nTranscript Snippet: {transcript[:2000]}\n"

        result = await self._hybrid_processor.process(
            transcript if transcript else "Analyze video metadata for strategy",
            prompt,
            task_type=TaskType.YOUTUBE_ANALYSIS,
            model_name=self._model,
            response_mime_type="application/json",
            video_metadata=video_metadata
        )

        if not result.success or not result.response:
            raise RuntimeError(f"Gemini strategic analysis failed: {result.error}")

        try:
            return json.loads(result.response)
        except json.JSONDecodeError:
            # Return raw response as fallback
            return {"strategic_analysis": {"raw": result.response}, "a2ui_payload": []}

    def _failure(self, message: str, start_time: float) -> AgentResult:
        return AgentResult(
            status="error",
            output={},
            logs=[message]
        )

    @staticmethod
    def _build_gemini_config():
        from ...ai.gemini_service import GeminiConfig
        return GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GEMINI_LOCATION", "us-central1")
        )
