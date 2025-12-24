"""
OpenAI Voice Agents Integration
-------------------------------
Supports both Speech-to-Speech (Realtime) and Chained architectures
for building voice-enabled AI agents.

Realtime API: gpt-4o-realtime-preview
Chained: gpt-4o-transcribe → gpt-4.1 → gpt-4o-mini-tts
"""

import os
import asyncio
import httpx
import base64
from typing import Optional, Literal, AsyncGenerator
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class SpeechResult:
    audio_data: bytes
    format: str = "mp3"


class OpenAIVoiceService:
    """
    OpenAI Voice Agents service supporting both architectures:
    
    1. Speech-to-Speech (Realtime): Low latency, natural conversation
       - Model: gpt-4o-realtime-preview
       - Best for: Interactive voice apps, natural interruptions
       
    2. Chained: High control, scriptable
       - Transcribe: gpt-4o-transcribe / gpt-4o-mini-transcribe
       - Process: gpt-4.1
       - Speak: gpt-4o-mini-tts
       - Best for: Strict responses, existing text agents
    """
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    # ============ Speech-to-Text (Transcription) ============
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        model: str = "gpt-4o-transcribe",
        language: Optional[str] = None,
        response_format: str = "json"
    ) -> TranscriptionResult:
        """
        Transcribe audio using OpenAI's latest transcription models.
        
        Models:
        - gpt-4o-transcribe: High accuracy
        - gpt-4o-mini-transcribe: Cost efficient
        """
        files = {
            "file": ("audio.wav", audio_data, "audio/wav"),
            "model": (None, model),
            "response_format": (None, response_format)
        }
        
        if language:
            files["language"] = (None, language)
        
        response = await self.client.post(
            f"{self.BASE_URL}/audio/transcriptions",
            files=files
        )
        response.raise_for_status()
        data = response.json()
        
        return TranscriptionResult(
            text=data.get("text", ""),
            language=data.get("language"),
            duration=data.get("duration")
        )
    
    # ============ Text-to-Speech ============
    
    async def text_to_speech(
        self,
        text: str,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3",
        speed: float = 1.0
    ) -> SpeechResult:
        """
        Convert text to speech using OpenAI's TTS models.
        
        Models:
        - gpt-4o-mini-tts: Latest, low latency
        - tts-1: Standard
        - tts-1-hd: High definition
        
        Voices: alloy, echo, fable, onyx, nova, shimmer
        """
        response = await self.client.post(
            f"{self.BASE_URL}/audio/speech",
            json={
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format,
                "speed": speed
            }
        )
        response.raise_for_status()
        
        return SpeechResult(
            audio_data=response.content,
            format=response_format
        )
    
    async def text_to_speech_streaming(
        self,
        text: str,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
        response_format: Literal["wav", "pcm"] = "pcm"
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream text-to-speech for lowest latency.
        Use pcm or wav format for streaming.
        """
        async with self.client.stream(
            "POST",
            f"{self.BASE_URL}/audio/speech",
            json={
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format
            }
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk
    
    # ============ Chained Pipeline ============
    
    async def voice_to_voice_chained(
        self,
        audio_data: bytes,
        system_prompt: str = "You are a helpful assistant.",
        transcription_model: str = "gpt-4o-transcribe",
        processing_model: str = "gpt-4.1",
        tts_model: str = "gpt-4o-mini-tts",
        voice: str = "alloy"
    ) -> tuple[str, SpeechResult]:
        """
        Complete chained voice-to-voice pipeline:
        1. Transcribe audio → text
        2. Process with GPT → response text
        3. Convert to speech → audio
        
        Returns: (response_text, audio_result)
        """
        # Step 1: Transcribe
        transcription = await self.transcribe_audio(audio_data, transcription_model)
        
        # Step 2: Process with GPT
        response_text = await self._generate_text_response(
            transcription.text,
            system_prompt,
            processing_model
        )
        
        # Step 3: Text to Speech
        audio = await self.text_to_speech(response_text, tts_model, voice)
        
        return response_text, audio
    
    async def _generate_text_response(
        self,
        user_message: str,
        system_prompt: str,
        model: str
    ) -> str:
        """Generate text response using GPT."""
        response = await self.client.post(
            f"{self.BASE_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    # ============ Utility Methods ============
    
    async def close(self):
        await self.client.aclose()


# Fallback integration for video analysis when Gemini fails
class OpenAIVideoFallback:
    """
    Fallback to OpenAI for video analysis when Gemini is unavailable.
    Uses GPT-4 Vision for frame analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    async def analyze_video_frames(
        self,
        frame_urls: list[str],
        prompt: str = "Analyze these video frames and describe what's happening"
    ) -> str:
        """Analyze video frames using GPT-4 Vision."""
        content = [{"type": "text", "text": prompt}]
        
        for url in frame_urls[:10]:  # Limit to 10 frames
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
        
        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 4096
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    async def close(self):
        await self.client.aclose()
