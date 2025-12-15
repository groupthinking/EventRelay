"""
YouTube API - Video Metadata & Transcripts
-------------------------------------------
Fetch video metadata, captions, and channel info from YouTube Data API v3.
"""

import os
import asyncio
import httpx
from typing import Optional
from dataclasses import dataclass
from youtube_transcript_api import YouTubeTranscriptApi


@dataclass
class VideoMetadata:
    """YouTube video metadata."""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: str
    duration: str
    view_count: int
    like_count: int
    tags: list[str]
    thumbnail_url: str


@dataclass
class TranscriptSegment:
    """Single transcript segment with timing."""
    text: str
    start: float
    duration: float


class YouTubeAPIService:
    """YouTube Data API v3 service for metadata and transcripts."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY required")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_video_metadata(self, video_id: str) -> VideoMetadata:
        """Fetch comprehensive video metadata."""
        
        response = await self.client.get(
            f"{self.BASE_URL}/videos",
            params={
                "key": self.api_key,
                "id": video_id,
                "part": "snippet,contentDetails,statistics"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("items"):
            raise ValueError(f"Video not found: {video_id}")
        
        item = data["items"][0]
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        
        return VideoMetadata(
            video_id=video_id,
            title=snippet["title"],
            description=snippet.get("description", ""),
            channel_id=snippet["channelId"],
            channel_title=snippet["channelTitle"],
            published_at=snippet["publishedAt"],
            duration=item["contentDetails"]["duration"],
            view_count=int(stats.get("viewCount", 0)),
            like_count=int(stats.get("likeCount", 0)),
            tags=snippet.get("tags", []),
            thumbnail_url=snippet["thumbnails"]["high"]["url"]
        )
    
    async def get_transcript(
        self,
        video_id: str,
        languages: list[str] = ["en"]
    ) -> list[TranscriptSegment]:
        """Fetch video transcript/captions."""
        
        # youtube_transcript_api is sync, run in executor
        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(
            None,
            lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        )
        
        return [
            TranscriptSegment(
                text=seg["text"],
                start=seg["start"],
                duration=seg["duration"]
            )
            for seg in transcript
        ]
    
    async def get_full_transcript_text(self, video_id: str) -> str:
        """Get transcript as single concatenated string."""
        segments = await self.get_transcript(video_id)
        return " ".join(seg.text for seg in segments)
    
    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance"
    ) -> list[dict]:
        """Search for videos by query."""
        
        response = await self.client.get(
            f"{self.BASE_URL}/search",
            params={
                "key": self.api_key,
                "q": query,
                "type": "video",
                "part": "snippet",
                "maxResults": max_results,
                "order": order
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return [
            {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "published_at": item["snippet"]["publishedAt"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
            }
            for item in data.get("items", [])
        ]
    
    async def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50
    ) -> list[dict]:
        """Get recent videos from a channel."""
        
        response = await self.client.get(
            f"{self.BASE_URL}/search",
            params={
                "key": self.api_key,
                "channelId": channel_id,
                "type": "video",
                "part": "snippet",
                "maxResults": max_results,
                "order": "date"
            }
        )
        response.raise_for_status()
        return response.json().get("items", [])
    
    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        import re
        patterns = [
            r'(?:v=|/v/|youtu\.be/)([^&?/]+)',
            r'(?:embed/)([^&?/]+)',
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Could not extract video ID from: {url}")
    
    async def close(self):
        await self.client.aclose()
