#!/usr/bin/env python3
"""
Personality Agent
Maps creator character, intent, and community personality.
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
class PersonalityAgent(BaseAgent):
    """Agent specialized in mapping persona, intent, and character."""
    name = "personality_agent"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        cfg = config or {}
        gemini_cfg = cfg.get("gemini_config") or self._build_gemini_config()
        self._hybrid_processor = cfg.get("hybrid_processor") or HybridProcessorService(HybridConfig(gemini=gemini_cfg))
        self._model = cfg.get("model") or "gemini-1.5-pro"

    async def run(self, req: AgentRequest) -> AgentResult:
        start_time = asyncio.get_event_loop().time()
        # video_metadata usually contains clip offsets, metadata contains YouTube info
        video_info = req.params.get("metadata") or {}
        video_metadata = req.params.get("video_metadata") or {}
        transcript = req.params.get("transcript")

        if not transcript and not video_info:
            return self._failure("Missing transcript or video metadata", start_time)

        try:
            # Map personality using Gemini
            persona_mapping = await self._map_personality(transcript, video_info)

            asyncio.get_event_loop().time() - start_time
            return AgentResult(
                status="ok",
                output={
                    "personality_map": persona_mapping,
                    "metadata": {
                        "model": self._model,
                        "video_id": video_metadata.get("video_id")
                    }
                },
                logs=[]
            )
        except Exception as exc:
            logger.error("PersonalityAgent failed: %s", exc, exc_info=True)
            return self._failure(str(exc), start_time)

    async def _map_personality(self, transcript: Optional[str], video_metadata: dict[str, Any]) -> dict[str, Any]:
        """Call Gemini to map the personality and intent."""
        comments = video_metadata.get("comments", [])
        channel_context = video_metadata.get("channel_context", {})

        prompt = (
            "You are a strategic personality analyst. Analyze the following video content and community interaction "
            "to map the creator's character, the underlying intent, and the community vibe.\n\n"
            "Produce a JSON object with the following keys:\n"
            "1. 'creator_persona': { 'type': str (e.g. Authority, Peer, Visionary), 'authority_level': str, 'communication_style': str }\n"
            "2. 'video_intent': { 'primary': str, 'secondary': str, 'likely_user_goal': str }\n"
            "3. 'community_sentiment': { 'vibe': str, 'common_themes': [str], 'intent_alignment': str }\n\n"
            f"Channel Context: {json.dumps(channel_context)}\n"
            f"Recent Comments: {json.dumps(comments[:10])}\n"
        )

        if transcript:
            prompt += f"\nTranscript Snippet: {transcript[:2000]}\n"

        result = await self._hybrid_processor.process(
            transcript if transcript else "Analyze video metadata for persona",
            prompt,
            task_type=TaskType.YOUTUBE_ANALYSIS,
            model_name=self._model,
            response_mime_type="application/json",
            video_metadata=video_metadata
        )

        if not result.success or not result.response:
            raise RuntimeError(f"Gemini personality mapping failed: {result.error}")

        return json.loads(result.response)

    def _failure(self, message: str, start_time: float) -> AgentResult:
        asyncio.get_event_loop().time() - start_time
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
