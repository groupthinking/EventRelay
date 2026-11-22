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

A2UI_PROTOCOL_VERSION = "1.0"
A2UI_BASIC_CATALOG_ID = (
    "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
)
A2UI_MESSAGE_TYPES = frozenset(
    {
        "createSurface",
        "updateComponents",
        "updateDataModel",
        "deleteSurface",
        "callRendererFunction",
        "agentFunctionResponse",
    }
)

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
            "2. 'a2ui_payload': A list of A2UI v1.0 agent-to-renderer messages that visualize the 3-stage funnel (Info, Application, Mastery).\n\n"
            "A2UI Payload Requirements:\n"
            "- Every message must set 'version' to '1.0'.\n"
            "- The first message must use 'createSurface' with surfaceId 'strategic-funnel' and catalogId "
            f"'{A2UI_BASIC_CATALOG_ID}'.\n"
            "- Put the initial Heading, List, and 'Better Way' Card component tree in createSurface.components, with root component id 'root'.\n"
            "- Later messages may use updateComponents or updateDataModel only after createSurface.\n"
            "- Do not emit legacy beginRendering, surfaceUpdate, or dataModelUpdate messages.\n\n"
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
            self._validate_a2ui_payload(strategy.get("a2ui_payload"))
            return strategy
        except json.JSONDecodeError:
            # Return raw response as fallback
            return {"strategic_analysis": {"raw": result.response}, "a2ui_payload": []}

    @staticmethod
    def _validate_a2ui_payload(payload: Any) -> None:
        """Reject legacy or malformed A2UI envelopes before they reach a renderer."""
        if not isinstance(payload, list) or not payload:
            raise ValueError("a2ui_payload must contain at least one A2UI v1.0 message")

        surface_created = False
        for index, message in enumerate(payload):
            if not isinstance(message, dict) or message.get("version") != A2UI_PROTOCOL_VERSION:
                raise ValueError(f"a2ui_payload[{index}] must declare version 1.0")

            kinds = A2UI_MESSAGE_TYPES.intersection(message)
            if len(kinds) != 1:
                raise ValueError(f"a2ui_payload[{index}] must contain exactly one v1.0 message")

            kind = next(iter(kinds))
            body = message[kind]
            if not isinstance(body, dict):
                raise ValueError(f"a2ui_payload[{index}].{kind} must be an object")

            if kind == "createSurface":
                if index != 0 or surface_created:
                    raise ValueError("createSurface must be the first and only surface creation")
                if body.get("surfaceId") != "strategic-funnel":
                    raise ValueError("createSurface must target strategic-funnel")
                if body.get("catalogId") != A2UI_BASIC_CATALOG_ID:
                    raise ValueError("createSurface must use the A2UI v1.0 basic catalog")
                surface_created = True
            elif not surface_created:
                raise ValueError("createSurface must precede all other A2UI messages")

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
