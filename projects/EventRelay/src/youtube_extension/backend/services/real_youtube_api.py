#!/usr/bin/env python3
"""
Compatibility wrapper for the consolidated RealYouTubeAPIService.
"""

# Import from the actual implementation
from .youtube.adapters.official_api import (
    RealYouTubeAPIService,
    YouTubeVideoMetadata,
    YouTubeTranscriptSegment,
    YouTubeSearchResult,
    get_youtube_service,
    get_video_data,
)

__all__ = [
    "RealYouTubeAPIService",
    "YouTubeVideoMetadata",
    "YouTubeTranscriptSegment",
    "YouTubeSearchResult",
    "get_youtube_service",
    "get_video_data",
]
