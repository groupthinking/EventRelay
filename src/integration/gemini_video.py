"""
Gemini API - Video Analysis & Code Generation
----------------------------------------------
Uses Google's Gemini 2.5 Pro for advanced video understanding,
reasoning, and code generation with native YouTube URL support.

Provider: Google AI Platform
Models: gemini-2.5-pro (latest with video), gemini-2.0-flash (fast)
Endpoint: https://generativelanguage.googleapis.com/v1beta/models/
Project: gen-lang-client-0209671908
"""

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, cast

import httpx


@dataclass
class VideoAnalysisResult:
    """Result from Gemini video analysis."""

    summary: str
    key_events: list[dict] = field(default_factory=list)
    generated_code: Optional[str] = None
    transcript_segments: Optional[list[dict]] = None
    timestamps: Optional[list[dict]] = None
    apis_detected: Optional[list[dict]] = None
    build_plan: Optional[dict[str, Any]] = None


class GeminiVideoService:
    """
    Gemini 2.5 Pro service for advanced video analysis.

    Key capabilities:
    - Native YouTube URL support (preview)
    - Transcription with speaker detection
    - Visual OCR for on-screen text/code
    - Timestamping for events
    - Deep reasoning about video content

    Available Models:
    - gemini-2.5-pro: Latest with best reasoning
    - gemini-2.5-flash: Fast, cost-effective
    - gemini-2.0-flash-thinking-exp: Experimental thinking
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-2.5-pro"
    FALLBACK_MODEL = "gemini-2.0-flash"

    # API keys loaded from environment
    API_KEYS: list[str] = []

    def __init__(self, api_key: Optional[str] = None):
        # Load keys from environment
        env_keys = os.environ.get("GEMINI_API_KEYS", "")
        if env_keys:
            self.API_KEYS = [
                k.strip() for k in env_keys.split(",") if k.strip()
            ]

        # Fallback to single GEMINI_API_KEY
        single_key = api_key or os.environ.get("GEMINI_API_KEY")
        if single_key and single_key not in self.API_KEYS:
            self.API_KEYS.append(single_key)

        if not self.API_KEYS:
            raise ValueError("GEMINI_API_KEY or GEMINI_API_KEYS required")

        self.api_key = self.API_KEYS[0]
        # Longer timeout for video processing
        self.client = httpx.AsyncClient(timeout=180.0)
        self._key_index = 0

    def _rotate_key(self) -> None:
        """Rotate to next API key on rate limit."""
        self._key_index = (self._key_index + 1) % len(self.API_KEYS)
        self.api_key = self.API_KEYS[self._key_index]

    async def analyze_video(
        self,
        video_url: str,
        prompt: str = "Analyze this video and extract key events",
        model: Optional[str] = None,
        media_resolution: Literal["low", "high"] = "high",
        thinking_level: Literal["low", "high"] = "high",
    ) -> VideoAnalysisResult:
        """
        Analyze video content using Gemini's multimodal capabilities.

        Args:
            video_url: YouTube URL or file URI
            prompt: Analysis instructions
            model: Model to use (default: gemini-2.5-pro)
            media_resolution: 'low' (70 tokens/frame) or
                             'high' (280 tokens/frame).
                             Use 'high' for text-heavy videos.
            thinking_level: 'low' for simple tasks,
                            'high' for complex reasoning
        """
        model = model or self.DEFAULT_MODEL

        # Determine if YouTube URL - pass as plain text
        # (correct format per Google docs)
        is_youtube = "youtube.com" in video_url or "youtu.be" in video_url

        if is_youtube:
            # YouTube URLs are passed as plain text strings
            # NOT as file_data - per Google's documentation
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": video_url},
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192,
                },
            }
        else:
            # For uploaded files via File API,
            # use file_data with the returned URI
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "file_data": {
                                    "file_uri": video_url,
                                    "mime_type": "video/mp4",
                                }
                            },
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192,
                },
            }

        response = await self._make_request(model, payload)
        text = response["candidates"][0]["content"]["parts"][0]["text"]

        # Parse JSON response if possible
        try:
            parsed = json.loads(text)
            return VideoAnalysisResult(
                summary=parsed.get("summary", text),
                key_events=parsed.get("key_events", []),
                timestamps=parsed.get("timestamps", []),
                apis_detected=parsed.get("apis", []),
            )
        except json.JSONDecodeError:
            return VideoAnalysisResult(
                summary=text, key_events=self._extract_events(text)
            )

    async def generate_build_plan(
        self,
        video_url: str,
        transcript_excerpt: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Produce a structured BuildPlan JSON artifact directly from Gemini.

        The plan is consumed by downstream generators, so the schema is explicit
        and responseMimeType is set to application/json to avoid markdown fences.
        """
        model = self.DEFAULT_MODEL
        metadata = metadata or {}
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "prerequisites": {"type": "array", "items": {"type": "string"}},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {"type": "integer"},
                            "action": {"type": "string"},
                            "description": {"type": "string"},
                            "target_file": {"type": "string"},
                            "code": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "integer"}},
                            "prerequisites": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["step_number", "action", "description", "target_file"],
                    },
                },
            },
            "required": ["title", "summary", "steps"],
        }

        prompt = f"""
        You are deriving a deterministic build plan from a YouTube tutorial.
        Use only observable instructions from the video transcript and visuals.
        Output MUST be valid JSON that matches the provided schema.

        Video URL: {video_url}
        Title: {metadata.get('title', 'Unknown')}
        Transcript excerpt (optional): {transcript_excerpt[:1800]}

        Rules:
        - Keep steps ordered and numbered starting at 1.
        - Each step must include action type, target file, code snippet if visible, and dependencies.
        - Dependencies reference earlier step_number values.
        - Never include markdown fences or prose outside JSON.
        """

        payload = {
            "contents": [{"parts": [{"text": video_url}, {"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 4096,
            },
            "responseSchema": schema,
            "responseMimeType": "application/json",
        }

        response = await self._make_request(model, payload)
        raw_json = self._extract_json_content(response)
        try:
            return cast(dict[str, Any], json.loads(raw_json))
        except Exception:
            # Best-effort fallback to empty plan to avoid raising in pipelines
            return {
                "title": metadata.get("title", "Generated Build Plan"),
                "summary": "Plan could not be parsed from Gemini response.",
                "prerequisites": [],
                "steps": [],
            }

    async def _make_request(
        self, model: str, payload: dict, retries: int = 3
    ) -> dict:
        """Make API request with key rotation on failure."""
        last_error = None

        for _attempt in range(retries):
            try:
                response = await self.client.post(
                    f"{self.BASE_URL}/models/{model}:generateContent",
                    params={"key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                return cast(dict[Any, Any], response.json())
            except httpx.HTTPStatusError as e:
                last_error = e
                # Rate limit or overloaded
                if e.response.status_code in (429, 503):
                    self._rotate_key()
                    await asyncio.sleep(1)
                elif e.response.status_code in (400, 404):
                    # Model not found or bad request,
                    # try fallback with simpler payload
                    payload_copy = {
                        "contents": payload["contents"],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": 8192,
                        },
                    }

                    fallback_url = (
                        f"{self.BASE_URL}/models/"
                        f"{self.FALLBACK_MODEL}:generateContent"
                    )
                    response = await self.client.post(
                        fallback_url,
                        params={"key": self.api_key},
                        json=payload_copy,
                    )
                    response.raise_for_status()
                    return cast(dict[Any, Any], response.json())
                else:
                    raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("API request failed after retries")

    def _extract_json_content(self, response: dict[str, Any]) -> str:
        """
        Extract JSON content from Gemini response supporting both text and inlineData.
        """
        try:
            parts = response["candidates"][0]["content"].get("parts", [])
            for part in parts:
                if "text" in part and part["text"]:
                    return str(part["text"])
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("mimeType", "").endswith("json"):
                    data = inline.get("data")
                    if data:
                        return base64.b64decode(data).decode("utf-8")
        except Exception:
            pass
        return ""

    async def extract_technical_breakdown(
        self, video_url: str
    ) -> VideoAnalysisResult:
        """
        Extract technical breakdown from video including
        APIs, endpoints, and capabilities.
        Optimized for code tutorials and technical demos.
        """
        prompt = """
        Watch this video carefully.
        I need a comprehensive technical breakdown.

        Extract and return as JSON:
        {
            "summary": "Brief summary of what the video covers",
            "apis": [
                {
                    "name": "API name",
                    "endpoint": "URL or path",
                    "method": "GET/POST/etc",
                    "timestamp": "MM:SS"
                }
            ],
            "models": [
                {
                    "name": "Model name",
                    "provider": "Provider",
                    "capability": "What it does"
                }
            ],
            "capabilities": [
                {
                    "feature": "Feature name",
                    "description": "What it does",
                    "timestamp": "MM:SS"
                }
            ],
            "code_snippets": [
                {
                    "language": "python/js/etc",
                    "purpose": "What the code does",
                    "timestamp": "MM:SS"
                }
            ],
            "key_events": [
                {"event": "Description", "timestamp": "MM:SS"}
            ]
        }
        """

        return await self.analyze_video(
            video_url,
            prompt,
            # Critical for reading code on screen
            media_resolution="high",
            # Deep reasoning for technical content
            thinking_level="high",
        )

    async def extract_build_plan(
        self, video_url: str, response_schema: Optional[dict] = None
    ) -> dict:
        """
        Extract a structured BuildPlan from video content.

        This method implements Stage 2: Semantic Logic Parsing by transforming
        raw video transcripts and visual cues into structured, actionable
        instructions that Stage 3 (Code Generation) can consume deterministically.

        Args:
            video_url: YouTube URL or file URI
            response_schema: Optional custom JSON schema. If None, uses BuildPlan schema.

        Returns:
            Structured BuildPlan as a dict conforming to the schema
        """
        # Import schema function here to avoid circular dependencies
        from youtube_extension.backend.models.build_plan import (
            build_plan_to_gemini_schema,
        )

        schema = response_schema or build_plan_to_gemini_schema()

        prompt = """
        Analyze this video tutorial carefully and extract a structured build plan.

        Your task is to identify:
        1. The project being built (title, description, type)
        2. Technologies and frameworks used
        3. Step-by-step build instructions with dependencies
        4. Code snippets visible in the video
        5. Commands executed (npm install, etc.)
        6. Learning objectives and prerequisites

        For each build step:
        - Provide the exact action type (create_file, install_dependency, etc.)
        - Include the target file path if applicable
        - Extract any visible code snippets
        - Note dependencies between steps (e.g., "install tailwind" depends on "create react app")
        - Add relevant metadata (timestamps, component types, etc.)

        Be specific and actionable. The output will be used to automatically
        generate a working project, so accuracy and completeness are critical.

        Extract up to 20 steps if the video shows a complex build process.
        Order steps sequentially and mark dependencies clearly.
        """

        # Determine if YouTube URL
        is_youtube = "youtube.com" in video_url or "youtu.be" in video_url

        if is_youtube:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": video_url},
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,  # Lower temp for more consistent output
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                },
            }
        else:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "file_data": {
                                    "file_uri": video_url,
                                    "mime_type": "video/mp4",
                                }
                            },
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                },
            }

        response = await self._make_request(self.DEFAULT_MODEL, payload)
        text = response["candidates"][0]["content"]["parts"][0]["text"]

        # Parse JSON response
        try:
            import json

            build_plan = json.loads(text)
            return build_plan
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse BuildPlan JSON: {e}") from e

    async def generate_code_from_video(
        self, video_url: str, target_framework: str = "nextjs"
    ) -> str:
        """
        Generate production-ready application code based on
        video content.
        """

        prompt = f"""
        Analyze this video tutorial and generate production-ready
        {target_framework} code that implements what's shown.

        Include:
        1. Complete component structure with TypeScript
        2. API routes if applicable (Next.js App Router format)
        3. Full TypeScript types and interfaces
        4. Tailwind CSS styling
        5. Error handling and loading states
        6. Environment variable placeholders

        Output as a JSON object with files:
        {{
            "files": [
                {{"path": "src/app/page.tsx", "content": "..."}},
                {{"path": "src/app/api/route.ts", "content": "..."}}
            ]
        }}
        """

        result = await self.analyze_video(
            video_url, prompt, media_resolution="high", thinking_level="high"
        )
        return result.summary

    async def extract_transcript_with_timestamps(
        self, video_url: str
    ) -> list[dict]:
        """Extract timestamped transcript from video with speaker detection."""

        prompt = """Extract a detailed transcript from this video.

        Return as JSON:
        {
            "transcript": [
                {
                    "timestamp": "MM:SS",
                    "speaker": "Speaker name or Unknown",
                    "text": "What they said"
                }
            ],
            "total_duration": "MM:SS",
            "speakers_detected": ["List of speakers"]
        }
        """

        result = await self.analyze_video(
            video_url,
            prompt,
            media_resolution="low",
            thinking_level="low",
        )
        return result.transcript_segments or result.key_events

    async def answer_video_question(
        self, video_url: str, question: str
    ) -> str:
        """Answer a specific question based on video content."""

        prompt = f"""
        Watch this video and answer the following question
        based on both visual and audio evidence:

        Question: {question}

        Provide a detailed answer with timestamps when relevant.
        """

        result = await self.analyze_video(
            video_url, prompt, media_resolution="high", thinking_level="high"
        )
        return result.summary

    def _extract_events(self, text: str) -> list[dict]:
        """Parse events from analysis text."""
        events = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•", "1.", "2.", "3.")):
                # Remove bullet/number prefix
                event_text = line.lstrip("-*•0123456789.").strip()
                if event_text:
                    events.append({"event": event_text})
        return events

    async def close(self) -> None:
        await self.client.aclose()
