"""SC2 — faithful transcript acquisition (+ STT fallback).

One transcript path: YouTube captions via youtube-transcript-api, with an
optional injected STT provider as the fallback when captions are absent. The 7
legacy VideoProcessor variants are not ported.
"""
from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable


class TranscriptUnavailable(RuntimeError):
    """No captions and no STT fallback could produce a transcript."""


@runtime_checkable
class SttProvider(Protocol):
    async def transcribe(self, video_id: str, language: str | None) -> str: """
Produce a transcript of the audio for the specified YouTube video.

Parameters:
    video_id (str): YouTube video identifier.
    language (str | None): Optional language code to guide transcription; if `None` the provider may auto-detect.

Returns:
    transcript (str): Complete transcription of the video's audio.
"""
...


@runtime_checkable
class TranscriptProvider(Protocol):
    async def fetch(self, video_id: str, language: str | None = None) -> str: """
Fetches a transcript for a YouTube video, preferring captions and falling back to an injected STT provider if captions cannot be obtained.

Parameters:
    video_id (str): YouTube video identifier.
    language (str | None): Optional language code to request captions in; if `None`, English ("en") is attempted.

Returns:
    transcript (str): The assembled transcript text from captions or from the STT provider.

Raises:
    TranscriptUnavailable: If caption retrieval fails and no STT provider is configured. Caption retrieval is bounded by a 30-second timeout.
"""
...


class YouTubeCaptionsProvider:
    """Captions-first transcript provider with optional STT fallback."""

    def __init__(self, stt: SttProvider | None = None) -> None:
        """
        Create a YouTubeCaptionsProvider configured with an optional speech-to-text fallback.
        
        Parameters:
            stt (SttProvider | None): Optional STT provider used when caption retrieval fails; if None, no STT fallback is available.
        """
        self._stt = stt

    async def fetch(self, video_id: str, language: str | None = None) -> str:
        """
        Fetch a transcript for a YouTube video, preferring captions and falling back to the configured STT provider if captions are unavailable.
        
        Parameters:
            video_id (str): YouTube video identifier (typically 11 characters).
            language (str | None): Optional BCP‑47 language code (e.g., "en"); when omitted, "en" is attempted.
        
        Returns:
            str: The assembled transcript text.
        
        Raises:
            TranscriptUnavailable: If captions cannot be obtained and no STT fallback is configured.
        """
        languages = [language] if language else ["en"]
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._fetch_captions, video_id, languages),
                timeout=30.0
            )
        except Exception as exc:  # noqa: BLE001 — any caption failure → fallback
            if self._stt is not None:
                return await self._stt.transcribe(video_id, language)
            raise TranscriptUnavailable(
                f"no captions for {video_id} and no STT fallback configured"
            ) from exc

    @staticmethod
    def _fetch_captions(video_id: str, languages: list[str]) -> str:
        # Imported here so the package imports without the optional dependency.
        """
        Fetches and concatenated captions for a YouTube video into a single trimmed transcript string.
        
        Parameters:
            video_id (str): YouTube video identifier.
            languages (list[str]): Ordered list of preferred language codes to try when fetching captions.
        
        Returns:
            str: Transcript text formed by joining caption segments with spaces and stripping leading/trailing whitespace.
        """
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetch = getattr(api, "fetch", None)
        if callable(fetch):  # youtube-transcript-api >= 1.0
            fetched = fetch(video_id, languages=languages)
            return " ".join(snippet.text for snippet in fetched).strip()
        # Legacy 0.6.x static API.
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return " ".join(item["text"] for item in data).strip()
