#!/usr/bin/env python3
"""
Precision Extractor Agent
-------------------------
Specialized agent for high-precision extraction of physical entities (ingredients, tools, steps)
from video content by cross-referencing visual data with transcripts.
Addresses the "incorrect ingredients" bug found in YouTube comment analysis.
"""

import logging
import os
import json
from typing import Any, Optional, Dict, List
from google import genai
from google.genai import types

logger = logging.getLogger("precision_extractor")


class PrecisionExtractorAgent:
    """
    Agent focused on visual-to-text accuracy.
    Uses Gemini Multimodal to verify transcript claims against visual reality.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        )
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY required")

        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-2.0-flash"  # Standard Gemini 2.0 Flash model

    async def extract_precision_data(
        self, video_url: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract high-precision data by analyzing video frames directly.

        Args:
            video_url: The YouTube/File URI for the video.
            context: Optional context (e.g. "recipe", "mechanical repair", "code tutorial").
        """
        logger.info(f"🎯 Starting precision extraction for: {video_url}")

        prompt = f"""
        TASK: Extract high-precision data from this video.
        CONTEXT: {context if context else 'General high-fidelity extraction'}

        INSTRUCTIONS:
        1. Ignore the audio/transcript if it conflicts with visual evidence.
        2. Identify all physical objects, ingredients, tools, or specific brands shown.
        3. For each item, look for labels, text on screen, or specific quantities shown.
        4. List the exact steps shown visually, noting if they differ from common recipes or instructions.
        5. Provide a 'Visual Integrity Check': Note if anything mentioned in the video is visibly different (e.g., they say 'sugar' but the container says 'salt').

        OUTPUT FORMAT: JSON
        {{
            "physical_entities": [
                {{"item": "string", "quantity": "string", "brand": "string", "verification_source": "visual_label|size_estimation|context"}}
            ],
            "visual_steps": [
                {{"step_number": 1, "action": "string", "observed_detail": "string"}}
            ],
            "discrepancies": [
                {{"description": "string", "observed_on_screen": "string", "claimed_by_narrator": "string"}}
            ]
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_uri(file_uri=video_url, mime_type="video/*"),
                    types.Part.from_text(text=prompt),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            result = json.loads(response.text)
            logger.info("✅ Precision extraction complete.")
            return result

        except Exception as e:
            logger.error(f"❌ Precision extraction failed: {e}")
            return {
                "error": str(e),
                "physical_entities": [],
                "visual_steps": [],
                "discrepancies": [],
            }


if __name__ == "__main__":
    # Quick test
    import asyncio

    async def test():
        agent = PrecisionExtractorAgent()
        # Test with a known cooking video or similar if possible
        # For now, just a placeholder run
        # res = await agent.extract_precision_data("gs://bucket/video.mp4")
        # print(res)

    # asyncio.run(test())
