#!/usr/bin/env python3
"""
Compatibility layer for Innertube transcript helpers.

The authoritative implementation lives in
``src.youtube_extension.backend.services.youtube.adapters.innertube``. This
module re-exports the public API so legacy imports keep functioning while the
shared adapters remain the single source of truth.
"""

from src.shared.youtube import (
    fetch_innertube_transcript,
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
    CaptionSegment,
)

__all__ = [
    "fetch_innertube_transcript",
    "InnertubeTranscriptError",
    "InnertubeTranscriptNotFound",
    "CaptionSegment",
]
