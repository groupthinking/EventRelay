#!/usr/bin/env python3
"""
Video Master Agent Service
===========================

Extracted and refactored from development/agents/gemini_video_master_agent.py
Provides comprehensive video processing using Google AI (Gemini) with clean service interfaces.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..base_agent import BaseAgent, AgentResult

# Google AI imports
try:
    import google.generativeai as genai
    from google.generativeai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google AI not available - install: pip install google-generativeai")


@dataclass
class VideoAnalysisResult:
    """Structured result from video analysis"""
    title: str
    summary: str
    key_points: List[str]
    actions: List[Dict[str, Any]]
    difficulty_level: str
    estimated_duration: str
    quality_score: float


from ..registry import register
from ..dto import AgentRequest, AgentResult

@register
class VideoMasterAgent(BaseAgent):
    name = "video_master"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Video Master Agent.

        Args:
            config: Configuration including API keys and settings
        """
        cfg = config or {}
        self._gemini_client = None
        self._setup_gemini()

    def _setup_gemini(self):
        """Setup Gemini AI client"""
        if not GEMINI_AVAILABLE:
            self.logger.error("Gemini AI not available")
            return

        api_key = self.get_config("gemini_api_key") or self.get_config("GOOGLE_AI_API_KEY")
        if not api_key:
            self.logger.error("No Gemini API key provided")
            return

        try:
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel('gemini-pro')
            self.logger.info("Gemini AI client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup Gemini client: {e}")

    async def run(self, req: AgentRequest) -> AgentResult:
        """
        Process video data using Gemini AI.

        Args:
            req: AgentRequest with 'video_data' and 'transcript' in params

        Returns:
            AgentResult with video analysis
        """
        start_time = asyncio.get_event_loop().time()
        errors = self.validate_input(req.params, ["video_data", "transcript"])

        if errors:
            return AgentResult(
                status="error",
                output={},
                logs=errors,
            )

        if not self._gemini_client:
            return AgentResult(
                status="error",
                output={},
                logs=["Gemini client not available"],
            )

        try:
            video_data = req.params["video_data"]
            transcript = req.params["transcript"]

            # Create analysis prompt
            prompt = self._create_analysis_prompt(video_data, transcript)

            # Call Gemini API
            response = await self._call_gemini_async(prompt)

            # Parse response
            analysis_result = self._parse_gemini_response(response)

            processing_time = asyncio.get_event_loop().time() - start_time

            return AgentResult(
                status="ok",
                output={
                    "video_analysis": analysis_result,
                    "raw_response": response,
                    "model_used": "gemini-pro"
                },
                logs=[f"Processing time: {processing_time:.2f}s"],
            )

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Video analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            return AgentResult(
                status="error",
                output={},
                logs=[error_msg, f"Processing time: {processing_time:.2f}s"],
            )

    def _create_analysis_prompt(self, video_data: Dict[str, Any], transcript: List[Dict[str, Any]]) -> str:
        """Create comprehensive analysis prompt for Gemini"""
        transcript_text = self._format_transcript(transcript)

        prompt = f"""
        Analyze this YouTube video comprehensively and provide a structured response.

        VIDEO METADATA:
        - Title: {video_data.get('title', 'N/A')}
        - Duration: {video_data.get('duration', 'N/A')} seconds
        - Description: {video_data.get('description', 'N/A')[:500]}...

        TRANSCRIPT:
        {transcript_text[:3000]}...

        Please provide a JSON response with the following structure:
        {{
            "title": "Cleaned video title",
            "summary": "Comprehensive 2-3 sentence summary",
            "key_points": ["point1", "point2", "point3"],
            "actions": [
                {{
                    "title": "Actionable task title",
                    "description": "Detailed description",
                    "priority": "high|medium|low",
                    "estimated_time": "time estimate",
                    "category": "Any concise topical category (e.g. 'react basics', 'python automation', 'design systems')"
                }}
            ],
            "difficulty_level": "beginner|intermediate|advanced",
            "estimated_duration": "time to complete learning",
            "quality_score": 0.0-1.0
        }}

        Focus on extracting actionable insights and practical next steps across any domain.
        Absolutely avoid classifying or recommending pure music/performance videos; if the content is primarily music,
        flag it as "unsupported_music_content" in the summary and do not provide actions.
        """
        return prompt

    def _format_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """Format transcript for analysis"""
        if not transcript:
            return "No transcript available"

        formatted = []
        for entry in transcript[:50]:  # Limit to first 50 entries
            if isinstance(entry, dict):
                text = entry.get('text', '')
                start = entry.get('start', 0)
                formatted.append(f"[{start:.1f}s] {text}")
            else:
                formatted.append(str(entry))

        return "\n".join(formatted)

    async def _call_gemini_async(self, prompt: str) -> str:
        """Call Gemini API asynchronously"""
        loop = asyncio.get_event_loop()

        def _sync_call():
            try:
                response = self._gemini_client.generate_content(prompt)
                return response.text
            except Exception as e:
                self.logger.error(f"Gemini API call failed: {e}")
                raise

        # Run in executor to avoid blocking
        return await loop.run_in_executor(None, _sync_call)

    def _parse_gemini_response(self, response: str) -> VideoAnalysisResult:
        """Parse Gemini response into structured result"""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Assume entire response is JSON
                json_str = response.strip()

            data = json.loads(json_str)

            return VideoAnalysisResult(
                title=data.get("title", "Unknown"),
                summary=data.get("summary", "No summary available"),
                key_points=data.get("key_points", []),
                actions=data.get("actions", []),
                difficulty_level=data.get("difficulty_level", "intermediate"),
                estimated_duration=data.get("estimated_duration", "Unknown"),
                quality_score=float(data.get("quality_score", 0.5))
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Failed to parse Gemini response as JSON: {e}")

            # Fallback to basic parsing
            return VideoAnalysisResult(
                title="Video Analysis",
                summary=response[:200] + "..." if len(response) > 200 else response,
                key_points=["Analysis completed with fallback parsing"],
                actions=[{
                    "title": "Review video analysis",
                    "description": "Manual review required due to parsing issues",
                    "priority": "medium",
                    "estimated_time": "5-10 minutes",
                    "category": "review"
                }],
                difficulty_level="intermediate",
                estimated_duration="Variable",
                quality_score=0.3
            )

    def is_available(self) -> bool:
        """Check if agent is available for processing"""
        return GEMINI_AVAILABLE and self._gemini_client is not None
