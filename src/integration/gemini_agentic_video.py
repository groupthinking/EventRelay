"""Gemini agentic video-understanding adapter.

This module isolates the Gemini Interactions API from EventRelay's existing
``generateContent`` integration.  It enables targeted, server-side inspection
of transcripts, frames, and audio without changing the production path until
benchmark evidence supports promotion.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Literal, Sequence

ProcessingMode = Literal["agentic", "static"]


@dataclass(frozen=True)
class VideoInput:
    """One video reference and its independently selected processing mode."""

    uri: str
    processing: ProcessingMode = "agentic"
    mime_type: str | None = None


@dataclass(frozen=True)
class AgenticVideoReceipt:
    """Stable execution receipt retained by EventRelay after analysis."""

    output_text: str
    total_tokens: int | None
    model: str
    sources: tuple[str, ...]
    processing_modes: tuple[ProcessingMode, ...]


class GeminiAgenticVideoService:
    """Run Gemini's Think -> Act -> Observe video-analysis loop."""

    DEFAULT_MODEL = "gemini-3.7-flash"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or os.getenv(
            "GEMINI_AGENTIC_VIDEO_MODEL", self.DEFAULT_MODEL
        )
        if client is not None:
            self._client = client
            return

        from google import genai

        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = (
            genai.Client(api_key=resolved_key) if resolved_key else genai.Client()
        )

    @staticmethod
    def build_input(videos: Sequence[VideoInput], prompt: str) -> list[dict[str, str]]:
        """Build the documented Interactions API input without materializing media."""
        if not videos:
            raise ValueError("At least one video reference is required")
        if not prompt.strip():
            raise ValueError("A non-empty analysis prompt is required")

        items: list[dict[str, str]] = []
        for video in videos:
            if not video.uri.strip():
                raise ValueError("Video URI must not be empty")
            item = {
                "type": "video",
                "uri": video.uri,
                "processing": video.processing,
            }
            if video.mime_type:
                item["mime_type"] = video.mime_type
            items.append(item)
        items.append({"type": "text", "text": prompt})
        return items

    async def analyze(
        self,
        videos: Sequence[VideoInput],
        prompt: str,
        *,
        model: str | None = None,
    ) -> AgenticVideoReceipt:
        """Analyze referenced media and return a durable, comparable receipt."""
        selected_model = model or self.model
        request_input = self.build_input(videos, prompt)
        response = await asyncio.to_thread(
            self._client.interactions.create,
            model=selected_model,
            input=request_input,
        )

        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", None)
        return AgenticVideoReceipt(
            output_text=str(getattr(response, "output_text", "")),
            total_tokens=int(total_tokens) if total_tokens is not None else None,
            model=selected_model,
            sources=tuple(video.uri for video in videos),
            processing_modes=tuple(video.processing for video in videos),
        )

