#!/usr/bin/env python3
"""
Compatibility wrapper for the consolidated robust YouTube service.

The shared implementation lives under ``src.shared.youtube``. This module keeps
legacy import paths functioning while ensuring all logic routes through the
centralised adapters.
"""

from src.shared.youtube import (
    RobustYouTubeService as _RobustYouTubeService,
    RobustYouTubeMetadata,
    get_video_transcript_robust,
    fetch_innertube_transcript,
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
)

RobustYouTubeService = _RobustYouTubeService

__all__ = [
    "RobustYouTubeService",
    "RobustYouTubeMetadata",
    "get_video_transcript_robust",
    "fetch_innertube_transcript",
    "InnertubeTranscriptError",
    "InnertubeTranscriptNotFound",
]
