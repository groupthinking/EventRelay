"""SC2 — faithful transcript acquisition (+ STT fallback).

Interface only in the skeleton. Port exactly ONE transcript implementation from
the legacy tree here (see PORTING_PARAMETERS SC2) — not the 7 VideoProcessor
variants. STT fallback is a second function behind the same return type.
"""
from __future__ import annotations


async def fetch_transcript(video_id: str, language: str | None = None) -> str:
    """Return a word-for-word transcript for the given video id.

    Acceptance test (SC2): captioned video -> exact caption text; caption-less
    video -> STT transcript; both return the same `str` shape.
    """
    raise NotImplementedError(
        "SC2 transcript acquisition not yet ported — see docs/PORTING_PARAMETERS.md"
    )
