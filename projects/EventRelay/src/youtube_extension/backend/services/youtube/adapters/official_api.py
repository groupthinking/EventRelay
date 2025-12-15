#!/usr/bin/env python3
"""
Real YouTube Data API v3 Integration Service
===========================================

Complete YouTube Data API integration with real video processing,
transcript extraction, and metadata retrieval.
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

from youtube_extension.utils import extract_video_id

# Fallback transcript retrieval
try:
    from .robust_youtube_service import get_video_transcript_robust
    HAS_ROBUST_TRANSCRIPT_FALLBACK = True
except Exception:
    HAS_ROBUST_TRANSCRIPT_FALLBACK = False

# Import our cost monitor (from services directory, not adapters)
from ...api_cost_monitor import cost_monitor, track_api_call, check_rate_limit_decorator

# YouTube Transcript API
try:
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        CouldNotRetrieveTranscript,
    )
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False
    logging.warning("youtube-transcript-api not available")

"""
Avoid network calls at import time. Presence of youtube_transcript_api sets
HAS_TRANSCRIPT_API; runtime health checks should be performed explicitly.
"""

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class YouTubeVideoMetadata:
    """Complete YouTube video metadata"""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: str
    duration: str
    view_count: int
    like_count: Optional[int]
    comment_count: Optional[int]
    thumbnail_urls: Dict[str, str]
    tags: List[str]
    category_id: str
    default_language: Optional[str]
    default_audio_language: Optional[str]
    live_broadcast_content: str
    privacy_status: str = "public"

@dataclass
class YouTubeTranscriptSegment:
    """Individual transcript segment"""
    text: str
    start: float
    duration: float
    
    @property
    def end(self) -> float:
        return self.start + self.duration

@dataclass
class YouTubeSearchResult:
    """YouTube search result"""
    video_id: str
    title: str
    description: str
    channel_title: str
    published_at: str
    thumbnail_url: str
    duration: str = None
    view_count: int = None

class RealYouTubeAPIService:
    """
    Complete YouTube Data API v3 integration service
    
    Features:
    - Real video metadata extraction using YouTube Data API v3
    - Transcript extraction with multiple fallbacks
    - Channel information and statistics
    - Search functionality with filters
    - Related videos discovery
    - Cost-aware API usage with quota management
    - Comprehensive error handling and fallbacks
    """
    
    def __init__(self, api_key: str = None):
        """Initialize YouTube API service"""
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY environment variable.")
        
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.quota_costs = {
            'videos': 1,
            'search': 100,
            'channels': 1,
            'playlistItems': 1,
            'commentThreads': 1,
            'captions': 200
        }
        
        # HTTP client for API calls
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={'User-Agent': 'UVAI-YouTube-Processor/1.0'}
        )
        
        logger.info("🎬 Real YouTube API Service initialized")
    
    @check_rate_limit_decorator('youtube')
    async def get_video_metadata(self, video_id_or_url: str) -> YouTubeVideoMetadata:
        """
        Get comprehensive video metadata using YouTube Data API v3
        
        Args:
            video_id_or_url: YouTube video ID or URL
            
        Returns:
            YouTubeVideoMetadata with complete video information
        """
        try:
            video_id = extract_video_id(video_id_or_url)
            
            # Track API usage
            await track_api_call(
                service="youtube",
                endpoint="videos",
                tokens=self.quota_costs['videos'],
                request_type="metadata",
                video_id=video_id
            )
            
            # Make API request
            url = f"{self.base_url}/videos"
            params = {
                'key': self.api_key,
                'id': video_id,
                'part': 'snippet,statistics,contentDetails,status',
                'fields': (
                    'items(id,snippet(title,description,channelId,channelTitle,'
                    'publishedAt,tags,categoryId,defaultLanguage,defaultAudioLanguage,'
                    'thumbnails),statistics(viewCount,likeCount,commentCount),'
                    'contentDetails(duration),status(privacyStatus,uploadStatus))'
                )
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                raise ValueError(f"Video not found: {video_id}")
            
            item = data['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item['contentDetails']
            status = item.get('status', {})
            
            # Parse thumbnails
            thumbnails = {}
            for quality, thumb_data in snippet.get('thumbnails', {}).items():
                thumbnails[quality] = thumb_data['url']
            
            metadata = YouTubeVideoMetadata(
                video_id=video_id,
                title=snippet['title'],
                description=snippet.get('description', ''),
                channel_id=snippet['channelId'],
                channel_title=snippet['channelTitle'],
                published_at=snippet['publishedAt'],
                duration=content_details['duration'],
                view_count=int(statistics.get('viewCount', 0)),
                like_count=int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else None,
                comment_count=int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else None,
                thumbnail_urls=thumbnails,
                tags=snippet.get('tags', []),
                category_id=snippet.get('categoryId', ''),
                default_language=snippet.get('defaultLanguage'),
                default_audio_language=snippet.get('defaultAudioLanguage'),
                live_broadcast_content=snippet.get('liveBroadcastContent', 'none'),
                privacy_status=status.get('privacyStatus', 'public')
            )
            
            logger.info(f"✅ Retrieved metadata for: {metadata.title} ({video_id})")
            return metadata
            
        except httpx.HTTPStatusError as e:
            error_msg = f"YouTube API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            
            await track_api_call(
                service="youtube",
                endpoint="videos",
                tokens=self.quota_costs['videos'],
                request_type="metadata",
                video_id=video_id,
                success=False,
                error_message=error_msg
            )
            
            raise Exception(error_msg)
        
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            raise
    
    async def get_video_transcript(self, video_id_or_url: str, language: str = 'en') -> List[YouTubeTranscriptSegment]:
        """
        Get video transcript with multiple fallback strategies
        
        Args:
            video_id_or_url: YouTube video ID or URL
            language: Preferred transcript language
            
        Returns:
            List of transcript segments with timing
        """
        if not HAS_TRANSCRIPT_API and not HAS_ROBUST_TRANSCRIPT_FALLBACK:
            logger.warning("No transcript providers available; returning empty transcript")
            return []
        
        try:
            video_id = extract_video_id(video_id_or_url)

            transcript_data = None
            if HAS_TRANSCRIPT_API:
                try:
                    yt_api = YouTubeTranscriptApi()
                    transcript_data = yt_api.fetch(video_id)
                    logger.info(f"✅ youtube-transcript-api fetched transcript for {video_id}")
                except (TranscriptsDisabled, NoTranscriptFound) as e:
                    logger.warning(f"❌ No transcripts available via youtube-transcript-api for {video_id}: {e}")
                except CouldNotRetrieveTranscript as e:
                    logger.error(f"❌ Could not retrieve transcript for {video_id}: {e}")
                except Exception as e:
                    logger.warning(f"youtube-transcript-api fetch failed for {video_id}: {e}")

            # Fallback via robust service if needed
            if (not transcript_data) and HAS_ROBUST_TRANSCRIPT_FALLBACK:
                try:
                    fallback = await get_video_transcript_robust(
                        video_id, language=language
                    )
                    if fallback.get('segments'):
                        transcript_data = [
                            {
                                'text': seg.get('text', ''),
                                'start': seg.get('start', 0.0),
                                'duration': seg.get('duration', 0.0),
                            }
                            for seg in fallback['segments']
                        ]
                        logger.info(f"🛟 Fallback transcript obtained via {fallback.get('source')} for {video_id}")
                    elif fallback.get('text'):
                        # Build a single segment if only text is available
                        transcript_data = [{'text': fallback['text'], 'start': 0.0, 'duration': 0.0}]
                        logger.info(f"🛟 Fallback transcript text obtained via {fallback.get('source')} for {video_id}")
                except Exception as e:
                    logger.warning(f"Fallback transcript retrieval failed: {e}")

            # If still nothing, return empty list
            if not transcript_data:
                return []
            
            # Convert to our format
            segments = []
            for entry in transcript_data:
                if isinstance(entry, dict):
                    text = entry.get('text', '').strip()
                    start = float(entry.get('start', 0.0))
                    duration = float(entry.get('duration', 0.0))
                else:
                    text = getattr(entry, 'text', '').strip()
                    start = float(getattr(entry, 'start', 0.0))
                    duration = float(getattr(entry, 'duration', 0.0))
                segments.append(YouTubeTranscriptSegment(text=text, start=start, duration=duration))
            
            # Track successful transcript retrieval
            await track_api_call(
                service="youtube",
                endpoint="transcript",
                tokens=len(segments),  # Use segment count as token count
                request_type="transcript",
                video_id=video_id
            )
            
            logger.info(f"✅ Retrieved {len(segments)} transcript segments for {video_id}")
            return segments
            
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            
            # Track failed transcript retrieval
            await track_api_call(
                service="youtube",
                endpoint="transcript",
                tokens=0,
                request_type="transcript",
                video_id=video_id,
                success=False,
                error_message=str(e)
            )
            
            return []
    
    @check_rate_limit_decorator('youtube')
    async def search_videos(self, 
                           query: str, 
                           max_results: int = 10,
                           order: str = 'relevance',
                           published_after: str = None,
                           duration: str = None,
                           video_type: str = None) -> List[YouTubeSearchResult]:
        """
        Search YouTube videos with filters
        
        Args:
            query: Search query
            max_results: Maximum results to return
            order: Sort order (relevance, date, rating, viewCount, title)
            published_after: RFC 3339 formatted date-time
            duration: Video duration (short, medium, long)
            video_type: Type of video (any, episode, movie)
            
        Returns:
            List of search results
        """
        try:
            # Track API usage
            await track_api_call(
                service="youtube",
                endpoint="search",
                tokens=self.quota_costs['search'],
                request_type="search"
            )
            
            url = f"{self.base_url}/search"
            params = {
                'key': self.api_key,
                'q': query,
                'part': 'snippet',
                'type': 'video',
                'maxResults': min(max_results, 50),  # API limit
                'order': order,
                'fields': (
                    'items(id(videoId),snippet(title,description,channelTitle,'
                    'publishedAt,thumbnails(high(url))))'
                )
            }
            
            if published_after:
                params['publishedAfter'] = published_after
            if duration:
                params['videoDuration'] = duration
            if video_type:
                params['videoType'] = video_type
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                result = YouTubeSearchResult(
                    video_id=item['id']['videoId'],
                    title=item['snippet']['title'],
                    description=item['snippet']['description'],
                    channel_title=item['snippet']['channelTitle'],
                    published_at=item['snippet']['publishedAt'],
                    thumbnail_url=item['snippet']['thumbnails']['high']['url']
                )
                results.append(result)
            
            logger.info(f"🔍 Found {len(results)} videos for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            raise
    
    @check_rate_limit_decorator('youtube')
    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information and statistics"""
        try:
            # Track API usage
            await track_api_call(
                service="youtube",
                endpoint="channels",
                tokens=self.quota_costs['channels'],
                request_type="channel_info"
            )
            
            url = f"{self.base_url}/channels"
            params = {
                'key': self.api_key,
                'id': channel_id,
                'part': 'snippet,statistics,brandingSettings',
                'fields': (
                    'items(snippet(title,description,thumbnails,publishedAt),'
                    'statistics(subscriberCount,videoCount,viewCount),'
                    'brandingSettings(channel(title,description)))'
                )
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                raise ValueError(f"Channel not found: {channel_id}")
            
            item = data['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            
            channel_info = {
                'channel_id': channel_id,
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': snippet['publishedAt'],
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0))
            }
            
            logger.info(f"📺 Retrieved info for channel: {channel_info['title']}")
            return channel_info
            
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            raise
    
    async def get_related_videos(self, video_id_or_url: str, max_results: int = 10) -> List[YouTubeSearchResult]:
        """Get videos related to the given video using channel and tags"""
        try:
            video_id = extract_video_id(video_id_or_url)
            metadata = await self.get_video_metadata(video_id)
            
            # Search using video title and channel for related content
            search_query = f"{metadata.title} {metadata.channel_title}"
            related_videos = await self.search_videos(
                query=search_query,
                max_results=max_results + 5  # Get extra to filter out original
            )
            
            # Filter out the original video and return requested count
            filtered_videos = [
                video for video in related_videos 
                if video.video_id != video_id
            ][:max_results]
            
            logger.info(f"🔗 Found {len(filtered_videos)} related videos for {video_id}")
            return filtered_videos
            
        except Exception as e:
            logger.error(f"Error getting related videos: {e}")
            return []
    
    async def get_comprehensive_video_data(self, video_id_or_url: str) -> Dict[str, Any]:
        """
        Get comprehensive video data combining metadata, transcript, and related info
        
        Returns:
            Complete video dataset for AI processing
        """
        try:
            video_id = extract_video_id(video_id_or_url)
            
            # Get metadata and transcript concurrently
            metadata_task = self.get_video_metadata(video_id)
            transcript_task = self.get_video_transcript(video_id)
            
            metadata, transcript = await asyncio.gather(
                metadata_task, 
                transcript_task,
                return_exceptions=True
            )
            
            if isinstance(metadata, Exception):
                raise metadata
            
            # Handle transcript errors gracefully
            if isinstance(transcript, Exception):
                logger.warning(f"Transcript error for {video_id}: {transcript}")
                transcript = []
            
            # Get channel info
            try:
                channel_info = await self.get_channel_info(metadata.channel_id)
            except Exception as e:
                logger.warning(f"Could not get channel info: {e}")
                channel_info = {}
            
            # Get related videos
            try:
                related_videos = await self.get_related_videos(video_id, max_results=5)
            except Exception as e:
                logger.warning(f"Could not get related videos: {e}")
                related_videos = []
            
            # Compile comprehensive data
            comprehensive_data = {
                'video_id': video_id,
                'metadata': asdict(metadata),
                'transcript': {
                    'segments': [asdict(segment) for segment in transcript],
                    'full_text': ' '.join([segment.text for segment in transcript]),
                    'duration_covered': max([segment.end for segment in transcript]) if transcript else 0,
                    'segment_count': len(transcript),
                    'has_transcript': len(transcript) > 0
                },
                'channel_info': channel_info,
                'related_videos': [asdict(video) for video in related_videos],
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'api_source': 'youtube_data_api_v3'
            }
            
            logger.info(f"✅ Compiled comprehensive data for {metadata.title}")
            logger.info(f"   - Transcript: {'✅' if transcript else '❌'} ({len(transcript)} segments)")
            logger.info(f"   - Channel: {'✅' if channel_info else '❌'}")
            logger.info(f"   - Related: {len(related_videos)} videos")
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive video data: {e}")
            raise
    
    async def validate_video_url(self, url: str) -> Tuple[bool, str, str]:
        """
        Validate YouTube URL and return video status
        
        Returns:
            (is_valid, video_id, error_message)
        """
        try:
            video_id = extract_video_id(url)
            
            # Try to get basic metadata to validate
            metadata = await self.get_video_metadata(video_id)
            
            if metadata.privacy_status == 'private':
                return False, video_id, "Video is private"
            elif metadata.privacy_status == 'unlisted':
                return True, video_id, "Video is unlisted but accessible"
            
            return True, video_id, "Video is public and accessible"
            
        except ValueError as e:
            return False, "", f"Invalid URL format: {e}"
        except Exception as e:
            return False, "", f"Video validation failed: {e}"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global service instance
youtube_service = None

def get_youtube_service() -> RealYouTubeAPIService:
    """Get or create YouTube API service instance"""
    global youtube_service
    if youtube_service is None:
        youtube_service = RealYouTubeAPIService()
    return youtube_service

async def get_video_data(video_url: str) -> Dict[str, Any]:
    """Convenience function to get comprehensive video data"""
    service = get_youtube_service()
    return await service.get_comprehensive_video_data(video_url)

if __name__ == "__main__":
    # Test the YouTube API service
    async def test_youtube_api():
        service = RealYouTubeAPIService()
        
        # Test with a real video
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Compliance-safe test video
        
        try:
            # Test URL validation
            is_valid, video_id, message = await service.validate_video_url(test_url)
            print(f"URL Validation: {is_valid} - {message}")
            
            if is_valid:
                # Get comprehensive data
                data = await service.get_comprehensive_video_data(test_url)
                print(f"\nVideo: {data['metadata']['title']}")
                print(f"Channel: {data['metadata']['channel_title']}")
                print(f"Views: {data['metadata']['view_count']:,}")
                print(f"Transcript: {data['transcript']['segment_count']} segments")
                print(f"Related videos: {len(data['related_videos'])}")
        
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await service.close()
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_youtube_api())
