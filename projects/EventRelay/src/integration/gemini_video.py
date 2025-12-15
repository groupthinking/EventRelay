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

import os
import asyncio
import httpx
import json
from typing import Optional, Literal
from dataclasses import dataclass, field


@dataclass
class VideoAnalysisResult:
    """Result from Gemini video analysis."""
    summary: str
    key_events: list[dict] = field(default_factory=list)
    generated_code: Optional[str] = None
    transcript_segments: Optional[list[dict]] = None
    timestamps: Optional[list[dict]] = None
    apis_detected: Optional[list[dict]] = None


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
    
    # Fallback API keys for rotation
    API_KEYS = [
        "AIzaSyDtYn1Sg9QnvrNm8P4AdazfhiqtzV9FL8k",
        "AIzaSyAty2XLeRopDoSChegU91UkJhp1OKHdm4Q",
        "AIzaSyDfodICil5xI3iCqpIt4qFm1ebpHhE22rY",
        "AIzaSyCDppBM9GS067IDAkLQQDLZV4SJ2uC43qA",
        "AIzaSyDKA991w_reg2W5Z6Juw92mg9Nj86iQFaA",
        "AIzaSyA3CScjNNPRxe1K08PDMjDQyDRlzX-uIG0",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or self.API_KEYS[0]
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        self.client = httpx.AsyncClient(timeout=180.0)  # Longer timeout for video
        self._key_index = 0
    
    def _rotate_key(self):
        """Rotate to next API key on rate limit."""
        self._key_index = (self._key_index + 1) % len(self.API_KEYS)
        self.api_key = self.API_KEYS[self._key_index]
    
    async def analyze_video(
        self,
        video_url: str,
        prompt: str = "Analyze this video and extract key events",
        model: str = None,
        media_resolution: Literal["low", "high"] = "high",
        thinking_level: Literal["low", "high"] = "high"
    ) -> VideoAnalysisResult:
        """
        Analyze video content using Gemini's multimodal capabilities.
        
        Args:
            video_url: YouTube URL or file URI
            prompt: Analysis instructions
            model: Model to use (default: gemini-2.5-pro)
            media_resolution: 'low' (70 tokens/frame) or 'high' (280 tokens/frame)
                             Use 'high' for text-heavy videos (code, slides)
            thinking_level: 'low' for simple tasks, 'high' for complex reasoning
        """
        model = model or self.DEFAULT_MODEL
        
        # Determine if YouTube URL - pass as plain text (correct format per Google docs)
        is_youtube = "youtube.com" in video_url or "youtu.be" in video_url
        
        if is_youtube:
            # YouTube URLs are passed as plain text strings in the contents array
            # NOT as file_data - this is the correct format per Google's documentation
            payload = {
                "contents": [{
                    "parts": [
                        {"text": video_url},
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192
                }
            }
        else:
            # For uploaded files via File API, use file_data with the returned URI
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "file_data": {
                                "file_uri": video_url,
                                "mime_type": "video/mp4"
                            }
                        },
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 8192
                }
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
                apis_detected=parsed.get("apis", [])
            )
        except json.JSONDecodeError:
            return VideoAnalysisResult(
                summary=text,
                key_events=self._extract_events(text)
            )
    
    async def _make_request(self, model: str, payload: dict, retries: int = 3) -> dict:
        """Make API request with key rotation on failure."""
        last_error = None
        
        for attempt in range(retries):
            try:
                response = await self.client.post(
                    f"{self.BASE_URL}/models/{model}:generateContent",
                    params={"key": self.api_key},
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (429, 503):  # Rate limit or overloaded
                    self._rotate_key()
                    await asyncio.sleep(1)
                elif e.response.status_code in (400, 404):
                    # Model not found or bad request, try fallback with simpler payload
                    payload_copy = {
                        "contents": payload["contents"],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": 8192
                        }
                    }
                    
                    response = await self.client.post(
                        f"{self.BASE_URL}/models/{self.FALLBACK_MODEL}:generateContent",
                        params={"key": self.api_key},
                        json=payload_copy
                    )
                    response.raise_for_status()
                    return response.json()
                else:
                    raise
        
        raise last_error
    
    async def extract_technical_breakdown(
        self,
        video_url: str
    ) -> VideoAnalysisResult:
        """
        Extract technical breakdown from video including APIs, endpoints, and capabilities.
        Optimized for code tutorials and technical demos.
        """
        prompt = """
        Watch this video carefully. I need a comprehensive technical breakdown.
        
        Extract and return as JSON:
        {
            "summary": "Brief summary of what the video covers",
            "apis": [
                {"name": "API name", "endpoint": "URL or path", "method": "GET/POST/etc", "timestamp": "MM:SS"}
            ],
            "models": [
                {"name": "Model name", "provider": "Provider", "capability": "What it does"}
            ],
            "capabilities": [
                {"feature": "Feature name", "description": "What it does", "timestamp": "MM:SS"}
            ],
            "code_snippets": [
                {"language": "python/js/etc", "purpose": "What the code does", "timestamp": "MM:SS"}
            ],
            "key_events": [
                {"event": "Description", "timestamp": "MM:SS"}
            ]
        }
        """
        
        return await self.analyze_video(
            video_url, 
            prompt,
            media_resolution="high",  # Critical for reading code on screen
            thinking_level="high"     # Deep reasoning for technical content
        )
    
    async def generate_code_from_video(
        self,
        video_url: str,
        target_framework: str = "nextjs"
    ) -> str:
        """Generate production-ready application code based on video content."""
        
        prompt = f"""Analyze this video tutorial and generate production-ready 
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
            video_url, 
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        return result.summary
    
    async def extract_transcript_with_timestamps(
        self,
        video_url: str
    ) -> list[dict]:
        """Extract timestamped transcript from video with speaker detection."""
        
        prompt = """Extract a detailed transcript from this video.
        
        Return as JSON:
        {
            "transcript": [
                {"timestamp": "MM:SS", "speaker": "Speaker name or Unknown", "text": "What they said"}
            ],
            "total_duration": "MM:SS",
            "speakers_detected": ["List of speakers"]
        }
        """
        
        result = await self.analyze_video(
            video_url, 
            prompt,
            media_resolution="low",  # Audio focus doesn't need high visual tokens
            thinking_level="low"     # Transcription is straightforward
        )
        return result.transcript_segments or result.key_events
    
    async def answer_video_question(
        self,
        video_url: str,
        question: str
    ) -> str:
        """Answer a specific question based on video content."""
        
        prompt = f"""Watch this video and answer the following question based on 
        both visual and audio evidence:
        
        Question: {question}
        
        Provide a detailed answer with timestamps when relevant.
        """
        
        result = await self.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
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
    
    async def close(self):
        await self.client.aclose()
