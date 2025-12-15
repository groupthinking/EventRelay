"""
Shared YouTube helpers reused across MCP servers and backend services.

This package centralises access to the robust YouTube service adapters so
callers from legacy modules (EventRelay, youtube_extension) can depend on a
single implementation.
"""

from src.youtube_extension.backend.services.youtube.adapters.robust import (
    RobustYouTubeService,
    RobustYouTubeMetadata,
    get_video_transcript_robust,
)
from src.youtube_extension.backend.services.youtube.adapters.innertube import (
    fetch_innertube_transcript,
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
    CaptionSegment,
)
from src.youtube_extension.backend.services.youtube.adapters.official_api import (
    RealYouTubeAPIService,
    YouTubeTranscriptSegment,
    YouTubeVideoMetadata,
    YouTubeSearchResult,
)

__all__ = [
    "RobustYouTubeService",
    "RobustYouTubeMetadata",
    "get_video_transcript_robust",
    "fetch_innertube_transcript",
    "InnertubeTranscriptError",
    "InnertubeTranscriptNotFound",
    "CaptionSegment",
    "RealYouTubeAPIService",
    "YouTubeTranscriptSegment",
    "YouTubeVideoMetadata",
    "YouTubeSearchResult",
]
