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
    async def transcribe(self, video_id: str, language: str | None) -> str: ...


@runtime_checkable
class TranscriptProvider(Protocol):
    async def fetch(self, video_id: str, language: str | None = None) -> str: ...


class YouTubeCaptionsProvider:
    """Captions-first transcript provider with optional STT fallback."""

    def __init__(self, stt: SttProvider | None = None) -> None:
        self._stt = stt

    async def fetch(self, video_id: str, language: str | None = None) -> str:
        """Retrieve transcript for a YouTube video.

        Attempts to fetch captions via youtube-transcript-api. If caption
        fetching fails for any reason and an STT provider is configured,
        falls back to self._stt.transcribe.

        Args:
            video_id: YouTube video identifier (11 characters).
            language: Optional language code (e.g., "en"). Defaults to "en" if not provided.

        Returns:
            The video transcript as a string.

        Raises:
            TranscriptUnavailable: When captions are unavailable and no STT fallback is configured.
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
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetch = getattr(api, "fetch", None)
        if callable(fetch):  # youtube-transcript-api >= 1.0
            fetched = fetch(video_id, languages=languages)
            return " ".join(snippet.text for snippet in fetched).strip()
        # Legacy 0.6.x static API.
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return " ".join(item["text"] for item in data).strip()
