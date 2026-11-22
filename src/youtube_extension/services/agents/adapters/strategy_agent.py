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
from uuid import uuid4

from ...ai.hybrid_processor_service import (
    HybridConfig,
    HybridProcessorService,
    TaskType,
)
from ..base_agent import BaseAgent
from ..dto import AgentRequest, AgentResult
from ..registry import register

logger = logging.getLogger(__name__)

A2UI_PROTOCOL_VERSION = "1.0"
A2UI_BASIC_CATALOG_ID = (
    "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
)


def _strategy_surface(analysis: Any) -> dict[str, Any]:
    """Build one display-only A2UI surface; model values enter only literal Text fields."""

    def required_text(obj: Any, key: str) -> str:
        value = obj.get(key) if isinstance(obj, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"strategic_analysis requires nonempty text for {key}")
        return value.strip()

    principle = required_text(analysis, "core_principle")
    intent = required_text(analysis, "user_intent_analysis")
    optimization = analysis.get("action_optimization")
    better_way = required_text(optimization, "the_better_way")
    gain = required_text(optimization, "gain")

    def label(component_id: str, text: str) -> dict[str, str]:
        return {"id": component_id, "component": "Text", "text": text}

    return {
        "version": A2UI_PROTOCOL_VERSION,
        "createSurface": {
            "surfaceId": f"strategic-funnel-{uuid4().hex}",
            "catalogId": A2UI_BASIC_CATALOG_ID,
            "components": [
                {"id": "root", "component": "Column", "children": ["title", "stages", "better_way"]},
                label("title", f"Actionable funnel: {intent}"),
                {"id": "stages", "component": "List", "children": ["info", "application", "mastery"]},
                label("info", f"Info: {principle}"),
                label("application", f"Application: {better_way}"),
                label("mastery", f"Mastery check: {gain}"),
                {"id": "better_way", "component": "Card", "child": "better_way_text"},
                label("better_way_text", f"Better Way: {better_way}"),
            ],
        },
    }


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
            "Return only a JSON object with a 'strategic_analysis' object. "
            "Use nonempty text for 'core_principle' (what to learn), 'user_intent_analysis' (goal), "
            "and the two fields inside 'action_optimization': 'the_better_way' (an action to apply) "
            "and 'gain' (a concrete way to recognize mastery or assess the expected benefit). "
            "Do not generate UI components or an a2ui_payload; the application builds the interface.\n\n"
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
            strategy = json.loads(result.response)
        except json.JSONDecodeError as exc:
            raise ValueError("Strategy response must be valid JSON") from exc
        if not isinstance(strategy, dict) or set(strategy) != {"strategic_analysis"}:
            raise ValueError("Strategy response must contain only strategic_analysis")
        analysis = strategy["strategic_analysis"]
        return {"strategic_analysis": analysis, "a2ui_payload": [_strategy_surface(analysis)]}

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
