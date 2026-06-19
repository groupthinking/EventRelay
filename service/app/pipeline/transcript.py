"""SC2 — faithful transcript acquisition (+ STT fallback).

Interface only in the skeleton. Port exactly ONE transcript implementation from
the legacy tree here (see PORTING_PARAMETERS SC2) — not the 7 VideoProcessor
variants. STT fallback is a second function behind the same return type.
"""
from __future__ import annotations


async def fetch_transcript(video_id: str, language: str | None = None) -> str:
    """
    Obtain a word-for-word transcript for the specified video.
    
    Parameters:
        video_id (str): Identifier of the video to transcribe.
        language (str | None): Optional BCP-47 language hint used when selecting captions or configuring STT.
    
    Returns:
        str: Exact caption text when captions are available; otherwise an STT-generated transcript in the same string shape.
    
    Raises:
        NotImplementedError: SC2 transcript acquisition has not been ported yet (see docs/PORTING_PARAMETERS.md).
    """
    raise NotImplementedError(
        "SC2 transcript acquisition not yet ported — see docs/PORTING_PARAMETERS.md"
    )
