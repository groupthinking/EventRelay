#!/usr/bin/env python3
"""
Robust YouTube Service with Multiple API Fallbacks
=================================================

A comprehensive YouTube service that tries multiple approaches:
1. Direct YouTube Data API v3 (most reliable)
2. PyTube (alternative for metadata)
3. YouTube Transcript API (for transcripts)
4. YouTube Search Python (for search)
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import httpx
from urllib.parse import urlparse, parse_qs

# Import our cost monitor
try:
    from .api_cost_monitor import cost_monitor, track_api_call, check_rate_limit_decorator
except ImportError:  # pragma: no cover - fallback for refactored layout
    from ...api_cost_monitor import (  # type: ignore
        check_rate_limit_decorator,
        cost_monitor,
        track_api_call,
    )
from .innertube import (
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
    fetch_innertube_transcript,
)

# Try to import alternative libraries
try:
    from pytube import YouTube as PyTubeYouTube
    HAS_PYTube = True
except ImportError:
    HAS_PYTube = False
    PyTubeYouTube = None

try:
    from youtubesearchpython import VideosSearch, Transcript
    HAS_YOUTUBE_SEARCH = True
except ImportError:
    HAS_YOUTUBE_SEARCH = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False

logger = logging.getLogger(__name__)

@dataclass
class RobustYouTubeMetadata:
    """Complete YouTube video metadata with fallbacks"""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: str
    duration: str
    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    thumbnail_urls: Dict[str, str]
    tags: List[str]
    category_id: str
    default_language: Optional[str]
    default_audio_language: Optional[str]
    live_broadcast_content: str
    transcript_available: bool = False
    transcript_segments: int = 0
    source_api: str = "unknown"

class RobustYouTubeService:
    """
    Robust YouTube service with multiple fallback APIs
    """

    def __init__(self, api_key: Optional[str] = None):
        self.youtube_api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def get_video_metadata(self, video_url: str) -> RobustYouTubeMetadata:
        """
        Get video metadata using multiple fallback approaches
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {video_url}")

        # Try YouTube Data API v3 first (most reliable)
        try:
            return await self._get_metadata_youtube_api(video_id)
        except Exception as e:
            logger.warning(f"YouTube API v3 failed: {e}")

        # Fallback to PyTube
        if HAS_PYTube:
            try:
                return await self._get_metadata_pytube(video_url)
            except Exception as e:
                logger.warning(f"PyTube fallback failed: {e}")

        # Fallback to YouTube Search Python
        if HAS_YOUTUBE_SEARCH:
            try:
                return await self._get_metadata_search_api(video_id)
            except Exception as e:
                logger.warning(f"YouTube Search fallback failed: {e}")

        raise Exception("All YouTube metadata APIs failed")

    async def _get_metadata_youtube_api(self, video_id: str) -> RobustYouTubeMetadata:
        """Get metadata using YouTube Data API v3"""
        if not self.youtube_api_key:
            raise Exception("YouTube API key required")

        url = f"{self.base_url}/videos"
        params = {
            'id': video_id,
            'key': self.youtube_api_key,
            'part': 'snippet,statistics,contentDetails,status',
            'fields': 'items(id,snippet(title,description,channelId,channelTitle,publishedAt,tags,categoryId,defaultLanguage,defaultAudioLanguage,thumbnails),statistics(viewCount,likeCount,commentCount),contentDetails(duration),status(privacyStatus,uploadStatus))'
        }

        if not self.session:
            self.session = httpx.AsyncClient(timeout=30.0)

        response = await self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        if not data.get('items'):
            raise Exception(f"Video not found: {video_id}")

        item = data['items'][0]
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})

        # Check for transcript availability
        transcript_available, transcript_segments = await self._check_transcript_availability(video_id)

        return RobustYouTubeMetadata(
            video_id=video_id,
            title=snippet['title'],
            description=snippet['description'],
            channel_id=snippet['channelId'],
            channel_title=snippet['channelTitle'],
            published_at=snippet['publishedAt'],
            duration=content_details.get('duration', 'PT0S'),
            view_count=int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else None,
            like_count=int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else None,
            comment_count=int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else None,
            thumbnail_urls={
                quality: thumb['url']
                for quality, thumb in snippet.get('thumbnails', {}).items()
                if 'url' in thumb
            },
            tags=snippet.get('tags', []),
            category_id=snippet.get('categoryId', '0'),
            default_language=snippet.get('defaultLanguage'),
            default_audio_language=snippet.get('defaultAudioLanguage'),
            live_broadcast_content='none',
            transcript_available=transcript_available,
            transcript_segments=transcript_segments,
            source_api='youtube_data_api_v3'
        )

    async def _get_metadata_pytube(self, video_url: str) -> RobustYouTubeMetadata:
        """Fallback metadata using PyTube"""
        def _get_pytube_metadata():
            yt = PyTubeYouTube(video_url)
            return {
                'title': yt.title,
                'description': yt.description,
                'channel_title': yt.author,
                'publish_date': yt.publish_date.isoformat() if yt.publish_date else None,
                'length': yt.length,
                'views': yt.views,
                'thumbnail_url': yt.thumbnail_url
            }

        metadata = await asyncio.get_event_loop().run_in_executor(None, _get_pytube_metadata)

        # Extract video ID
        video_id = self._extract_video_id(video_url)

        return RobustYouTubeMetadata(
            video_id=video_id,
            title=metadata['title'] or 'Unknown Title',
            description=metadata['description'] or '',
            channel_id='unknown',
            channel_title=metadata['channel_title'] or 'Unknown Channel',
            published_at=metadata['publish_date'] or datetime.now(timezone.utc).isoformat(),
            duration=f"PT{metadata['length'] or 0}S",
            view_count=metadata['views'],
            like_count=None,
            comment_count=None,
            thumbnail_urls={'default': metadata['thumbnail_url']} if metadata['thumbnail_url'] else {},
            tags=[],
            category_id='0',
            default_language=None,
            default_audio_language=None,
            live_broadcast_content='none',
            transcript_available=False,
            transcript_segments=0,
            source_api='pytube'
        )

    async def _get_metadata_search_api(self, video_id: str) -> RobustYouTubeMetadata:
        """Fallback metadata using YouTube Search Python"""
        search = VideosSearch(video_id, limit=1)

        results = await asyncio.get_event_loop().run_in_executor(None, search.result)
        if not results.get('result'):
            raise Exception("No search results found")

        video = results['result'][0]

        return RobustYouTubeMetadata(
            video_id=video_id,
            title=video.get('title', 'Unknown Title'),
            description=video.get('descriptionSnippet', [{}])[0].get('text', ''),
            channel_id='unknown',
            channel_title=video.get('channel', {}).get('name', 'Unknown Channel'),
            published_at=video.get('publishedTime') or datetime.now(timezone.utc).isoformat(),
            duration=video.get('duration', 'PT0S'),
            view_count=int(video.get('viewCount', {}).get('text', '0').replace(',', '')) if video.get('viewCount') else None,
            like_count=None,
            comment_count=None,
            thumbnail_urls={
                'default': video.get('thumbnails', [{}])[0].get('url', '')
            },
            tags=[],
            category_id='0',
            default_language=None,
            default_audio_language=None,
            live_broadcast_content='none',
            transcript_available=False,
            transcript_segments=0,
            source_api='youtube_search_python'
        )

    async def _check_transcript_availability(self, video_id: str) -> Tuple[bool, int]:
        """Check if transcript is available and count segments"""
        try:
            if HAS_TRANSCRIPT_API:
                # Use high-level API to list and fetch transcripts
                try:
                    yt_api = YouTubeTranscriptApi()
                    transcript = yt_api.fetch(video_id)
                except Exception:
                    # If object API fails, try module-level list() as fallback pattern
                    try:
                        list_api = YouTubeTranscriptApi.list(video_id)
                        transcript = list_api
                    except Exception:
                        transcript = []
                return True, len(transcript)
            elif HAS_YOUTUBE_SEARCH:
                transcript_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: Transcript.get(video_id)
                )
                segments = transcript_data.get('segments', [])
                return True, len(segments)
        except Exception as e:
            logger.debug(f"Transcript availability check failed: {e}")

        return False, 0

    async def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """Get video transcript using multiple fallback approaches"""
        # Try YouTube Transcript API first
        if HAS_TRANSCRIPT_API:
            try:
                segments_data = []
                transcript_text_parts = []

                try:
                    yt_api = YouTubeTranscriptApi()
                    transcript = yt_api.fetch(video_id)
                except Exception:
                    try:
                        transcript = YouTubeTranscriptApi.list(video_id)
                    except Exception:
                        transcript = []

                for segment in transcript:
                    # API returns dicts with keys text,start,duration
                    text = segment.get('text', '') if isinstance(segment, dict) else getattr(segment, 'text', '')
                    start = segment.get('start', 0) if isinstance(segment, dict) else getattr(segment, 'start', 0)
                    duration = segment.get('duration', 0) if isinstance(segment, dict) else getattr(segment, 'duration', 0)

                    segments_data.append({'text': text, 'start': start, 'duration': duration})
                    transcript_text_parts.append(text)

                transcript_text = " ".join(transcript_text_parts)

                return {
                    'text': transcript_text,
                    'source': 'youtube_transcript_api',
                    'confidence': 0.9,
                    'segments': segments_data,
                    'processing_time': datetime.now().isoformat()
                }
            except Exception as e:
                logger.warning(f"YouTube Transcript API failed: {e}")

        # Try Innertube Android fallback
        try:
            if self.session is None:
                self.session = httpx.AsyncClient(timeout=30.0)
            innertube_segments = await fetch_innertube_transcript(
                video_id, language=language, client=self.session
            )
            if innertube_segments:
                transcript_text = " ".join(seg.text for seg in innertube_segments if seg.text)
                return {
                    'text': transcript_text,
                    'source': 'innertube_android',
                    'confidence': 0.75,
                    'segments': [
                        {
                            'text': seg.text,
                            'start': seg.start,
                            'duration': seg.duration,
                        }
                        for seg in innertube_segments
                    ],
                    'processing_time': datetime.now().isoformat(),
                }
        except InnertubeTranscriptNotFound as e:
            logger.info(f"Innertube captions not available for {video_id}: {e}")
        except InnertubeTranscriptError as e:
            logger.debug(f"Innertube transcript fallback failed for {video_id}: {e}")

        # Try YouTube Search Python
        if HAS_YOUTUBE_SEARCH:
            try:
                transcript_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: Transcript.get(video_id)
                )

                if transcript_data.get('segments'):
                    transcript_text = " ".join([
                        segment.get('text', '')
                        for segment in transcript_data['segments']
                    ])

                    return {
                        'text': transcript_text,
                        'source': 'youtube_search_python',
                        'confidence': 0.8,
                        'segments': transcript_data['segments'],
                        'processing_time': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"YouTube Search transcript failed: {e}")

        return {
            'text': '',
            'source': 'unavailable',
            'confidence': 0.0,
            'error': 'No transcript APIs available or working',
            'processing_time': datetime.now().isoformat()
        }

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        if len(url) == 11:
            return url

        return None

# Convenience functions
async def get_video_metadata_robust(video_url: str, api_key: Optional[str] = None) -> RobustYouTubeMetadata:
    """Get video metadata with robust fallbacks"""
    async with RobustYouTubeService(api_key) as service:
        return await service.get_video_metadata(video_url)

async def get_video_transcript_robust(
    video_id: str, api_key: Optional[str] = None, language: str = "en"
) -> Dict[str, Any]:
    """Get video transcript with robust fallbacks"""
    async with RobustYouTubeService(api_key) as service:
        return await service.get_transcript(video_id, language=language)

if __name__ == "__main__":
    async def test_robust_service():
        video_url = "https://www.youtube.com/watch?v=4v7tJ55rzs4"

        print(f"🔍 Testing robust YouTube service with: {video_url}")

        try:
            metadata = await get_video_metadata_robust(video_url)
            print("✅ Metadata retrieved successfully!")
            print(f"Title: {metadata.title}")
            print(f"Channel: {metadata.channel_title}")
            print(f"Views: {metadata.view_count:,}")
            print(f"Duration: {metadata.duration}")
            print(f"Transcript Available: {metadata.transcript_available}")
            print(f"Source API: {metadata.source_api}")

            # Try to get transcript
            transcript = await get_video_transcript_robust(metadata.video_id)
            print(f"Transcript status: {transcript.get('source')}")
            if transcript.get('text'):
                print(f"Transcript: {len(transcript['text'])} characters")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_robust_service())
