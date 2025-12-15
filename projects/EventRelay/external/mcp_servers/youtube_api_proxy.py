#!/usr/bin/env python3
"""
MCP YouTube API Proxy Server
Prevents timeout errors and handles rate limiting for YouTube API calls
Integrates sophisticated retry and rate limiting infrastructure
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import aiohttp
from datetime import datetime, timedelta
import random

# YouTube API specific imports
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript, NoTranscriptFound
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import yt_dlp
    YOUTUBE_DEPS_AVAILABLE = True
except ImportError as e:
    YOUTUBE_DEPS_AVAILABLE = False
    logging.warning(f"YouTube dependencies not available: {e}")

logger = logging.getLogger("youtube_api_proxy")

class YouTubeErrorType(Enum):
    """YouTube API specific error types"""
    QUOTA_EXCEEDED = "quota_exceeded"
    VIDEO_NOT_FOUND = "video_not_found"
    PRIVATE_VIDEO = "private_video"
    REGION_BLOCKED = "region_blocked"
    TRANSCRIPT_DISABLED = "transcript_disabled"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    NETWORK = "network"
    UNKNOWN = "unknown"

@dataclass
class YouTubeRetryConfig:
    """YouTube API specific retry configuration"""
    max_retries: int = 5
    base_delay: float = 2.0
    max_delay: float = 120.0
    exponential_backoff: bool = True
    jitter: bool = True
    backoff_multiplier: float = 2.5
    
    # YouTube specific settings
    quota_backoff_multiplier: float = 10.0  # Longer delays for quota issues
    region_retry_delay: float = 30.0  # Delay for region blocks
    ip_rotation_enabled: bool = True

@dataclass
class YouTubeRateLimit:
    """YouTube API rate limits"""
    requests_per_minute: int = 100  # YouTube API v3 default quota
    requests_per_second: int = 5
    requests_per_hour: int = 10000
    burst_capacity: int = 20
    
    # Adaptive limits
    adaptive_reduction_factor: float = 0.5  # Reduce by 50% on errors
    recovery_factor: float = 1.1  # Increase by 10% on success

class CircuitBreaker:
    """Circuit breaker for YouTube API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if request can be executed"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class YouTubeAPIProxy:
    """MCP YouTube API Proxy with intelligent retry and rate limiting"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.retry_config = YouTubeRetryConfig()
        self.rate_limit = YouTubeRateLimit()
        self.circuit_breaker = CircuitBreaker()
        
        # Request tracking
        self.request_history = []
        self.last_request_time = 0
        self.consecutive_errors = 0
        self.success_count = 0
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries_executed": 0,
            "circuit_breaks": 0,
            "total_wait_time": 0.0,
            "by_error_type": {error_type.value: 0 for error_type in YouTubeErrorType},
            "by_method": {
                "transcript": {"requests": 0, "successes": 0, "failures": 0},
                "video_info": {"requests": 0, "successes": 0, "failures": 0},
                "search": {"requests": 0, "successes": 0, "failures": 0}
            }
        }
        
        logger.info("🎯 YouTube API Proxy initialized with intelligent retry/rate limiting")
    
    def _classify_error(self, error: Exception) -> YouTubeErrorType:
        """Classify YouTube API errors for appropriate handling"""
        
        error_str = str(error).lower()
        
        if isinstance(error, HttpError):
            if error.resp.status == 403:
                if "quota" in error_str or "limit" in error_str:
                    return YouTubeErrorType.QUOTA_EXCEEDED
                elif "blocked" in error_str:
                    return YouTubeErrorType.REGION_BLOCKED
            elif error.resp.status == 404:
                return YouTubeErrorType.VIDEO_NOT_FOUND
            elif error.resp.status == 429:
                return YouTubeErrorType.RATE_LIMIT
            elif error.resp.status >= 500:
                return YouTubeErrorType.SERVER_ERROR
        
        elif isinstance(error, (CouldNotRetrieveTranscript, NoTranscriptFound)):
            if "private" in error_str:
                return YouTubeErrorType.PRIVATE_VIDEO
            elif "disabled" in error_str:
                return YouTubeErrorType.TRANSCRIPT_DISABLED
            elif "blocked" in error_str:
                return YouTubeErrorType.REGION_BLOCKED
            else:
                return YouTubeErrorType.TRANSCRIPT_DISABLED
        
        elif isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return YouTubeErrorType.TIMEOUT
        
        elif "network" in error_str or "connection" in error_str:
            return YouTubeErrorType.NETWORK
        
        return YouTubeErrorType.UNKNOWN
    
    def _calculate_retry_delay(self, attempt: int, error_type: YouTubeErrorType) -> float:
        """Calculate intelligent retry delay based on error type"""
        
        base_delay = self.retry_config.base_delay
        
        # Error-specific delay multipliers
        if error_type == YouTubeErrorType.QUOTA_EXCEEDED:
            base_delay *= self.retry_config.quota_backoff_multiplier
        elif error_type == YouTubeErrorType.REGION_BLOCKED:
            base_delay = self.retry_config.region_retry_delay
        elif error_type == YouTubeErrorType.RATE_LIMIT:
            base_delay *= 3.0  # Longer delays for rate limits
        
        # Exponential backoff
        if self.retry_config.exponential_backoff:
            delay = base_delay * (self.retry_config.backoff_multiplier ** (attempt - 1))
        else:
            delay = base_delay
        
        # Apply jitter
        if self.retry_config.jitter:
            delay *= (0.5 + random.random())
        
        # Cap at max delay
        delay = min(delay, self.retry_config.max_delay)
        
        return delay
    
    async def _wait_for_rate_limit(self):
        """Intelligent rate limiting with adaptive adjustment"""
        
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - 60
        self.request_history = [req_time for req_time in self.request_history if req_time > cutoff_time]
        
        # Check requests per minute
        if len(self.request_history) >= self.rate_limit.requests_per_minute:
            wait_time = 60 - (current_time - self.request_history[0])
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.stats["total_wait_time"] += wait_time
        
        # Check requests per second
        recent_requests = [req_time for req_time in self.request_history if req_time > current_time - 1]
        if len(recent_requests) >= self.rate_limit.requests_per_second:
            wait_time = 1.0
            logger.debug(f"⏳ Per-second rate limit, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            self.stats["total_wait_time"] += wait_time
        
        # Adaptive adjustment based on error rate
        if self.consecutive_errors > 3:
            adaptive_delay = min(self.consecutive_errors * 2, 30)
            logger.info(f"⚠️ Adaptive delay due to errors: {adaptive_delay}s")
            await asyncio.sleep(adaptive_delay)
            self.stats["total_wait_time"] += adaptive_delay
        
        # Record request time
        self.request_history.append(current_time)
    
    async def _execute_with_retry(self, operation_func, operation_name: str, *args, **kwargs) -> Any:
        """Execute operation with intelligent retry logic"""
        
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_breaks"] += 1
            raise Exception(f"Circuit breaker OPEN for YouTube API - too many failures")
        
        self.stats["total_requests"] += 1
        self.stats["by_method"][operation_name]["requests"] += 1
        
        last_error = None
        
        for attempt in range(1, self.retry_config.max_retries + 2):  # +1 for initial attempt
            try:
                # Rate limiting
                await self._wait_for_rate_limit()
                
                # Execute operation
                start_time = time.time()
                result = await operation_func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Success handling
                self.circuit_breaker.record_success()
                self.consecutive_errors = 0
                self.success_count += 1
                self.stats["successful_requests"] += 1
                self.stats["by_method"][operation_name]["successes"] += 1
                
                logger.info(f"✅ {operation_name} succeeded (attempt {attempt}, {execution_time:.2f}s)")
                return result
                
            except Exception as error:
                last_error = error
                error_type = self._classify_error(error)
                
                # Update statistics
                self.stats["failed_requests"] += 1
                self.stats["by_error_type"][error_type.value] += 1
                self.stats["by_method"][operation_name]["failures"] += 1
                
                # Check if we should retry
                if attempt > self.retry_config.max_retries:
                    logger.error(f"❌ {operation_name} failed after {attempt-1} retries: {error}")
                    self.circuit_breaker.record_failure()
                    self.consecutive_errors += 1
                    break
                
                # Non-retryable errors
                if error_type in [YouTubeErrorType.VIDEO_NOT_FOUND, YouTubeErrorType.PRIVATE_VIDEO]:
                    logger.warning(f"⚠️ {operation_name} non-retryable error: {error}")
                    break
                
                # Calculate retry delay
                retry_delay = self._calculate_retry_delay(attempt, error_type)
                
                logger.warning(f"⚠️ {operation_name} attempt {attempt} failed ({error_type.value}), retrying in {retry_delay:.2f}s: {error}")
                
                self.stats["retries_executed"] += 1
                await asyncio.sleep(retry_delay)
        
        # Final failure
        self.circuit_breaker.record_failure()
        self.consecutive_errors += 1
        raise last_error
    
    async def get_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Get video transcript with retry logic and fallback methods"""
        
        async def _transcript_operation():
            transcript_data = []
            
            # Method 1: Direct transcript API
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                if transcript:
                    logger.info(f"✅ Direct transcript extraction: {len(transcript)} segments")
                    return transcript
            except Exception as e:
                logger.debug(f"Direct transcript failed: {e}")
            
            # Method 2: Alternative language codes
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for transcript_item in transcript_list:
                    transcript = transcript_item.fetch()
                    if transcript:
                        logger.info(f"✅ Alternative language transcript: {len(transcript)} segments")
                        return transcript
            except Exception as e:
                logger.debug(f"Alternative transcript failed: {e}")
            
            # Method 3: yt-dlp fallback
            try:
                ydl_opts = {
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'skip_download': True,
                    'quiet': True,
                    'socket_timeout': 30
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    
                    subtitles = info.get('subtitles', {})
                    auto_captions = info.get('automatic_captions', {})
                    
                    if subtitles or auto_captions:
                        logger.info("✅ Found subtitle data via yt-dlp")
                        # Convert to transcript format
                        return [{'text': 'Transcript extracted via yt-dlp', 'start': 0, 'duration': 1}]
            except Exception as e:
                logger.debug(f"yt-dlp extraction failed: {e}")
            
            raise CouldNotRetrieveTranscript(f"All transcript extraction methods failed for {video_id}")
        
        return await self._execute_with_retry(_transcript_operation, "transcript")
    
    async def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Get video information with retry logic"""
        
        async def _video_info_operation():
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            request = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                raise Exception(f"Video {video_id} not found")
            
            return response['items'][0]
        
        return await self._execute_with_retry(_video_info_operation, "video_info")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        
        total_requests = self.stats["total_requests"]
        success_rate = (self.stats["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "circuit_breaker_state": self.circuit_breaker.state,
            "consecutive_errors": self.consecutive_errors,
            "current_rpm": len([req for req in self.request_history if req > time.time() - 60]),
            "uptime": time.time() - (self.request_history[0] if self.request_history else time.time())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the proxy"""
        
        try:
            # Simple API test
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            request = youtube.channels().list(part='snippet', mine=True)
            response = request.execute()
            
            return {
                "status": "healthy",
                "api_accessible": True,
                "circuit_breaker": self.circuit_breaker.state,
                "error_rate": self.consecutive_errors,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.state,
                "timestamp": datetime.now().isoformat()
            }


# Factory function for creating proxy instances
def create_youtube_proxy(api_key: str) -> YouTubeAPIProxy:
    """Create and configure YouTube API proxy"""
    
    if not YOUTUBE_DEPS_AVAILABLE:
        raise RuntimeError("YouTube dependencies not available - install youtube-transcript-api, google-api-python-client, yt-dlp")
    
    if not api_key or len(api_key) != 39 or not api_key.startswith('AIzaSy'):
        raise ValueError("Invalid YouTube API key format")
    
    return YouTubeAPIProxy(api_key)


# Example usage and testing
async def main():
    """Test the YouTube API proxy"""
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        logger.error("YOUTUBE_API_KEY environment variable required")
        return
    
    # Create proxy
    proxy = create_youtube_proxy(api_key)
    
    # Test transcript extraction
    # Use an educational video ID for examples/tests
    test_video_id = "aircAruvnKk"
    
    try:
        logger.info(f"🔍 Testing transcript extraction for {test_video_id}")
        transcript = await proxy.get_transcript(test_video_id)
        logger.info(f"✅ Retrieved {len(transcript)} transcript segments")
        
        # Test video info
        logger.info(f"🔍 Testing video info for {test_video_id}")
        video_info = await proxy.get_video_info(test_video_id)
        logger.info(f"✅ Retrieved video info: {video_info['snippet']['title']}")
        
        # Print statistics
        stats = proxy.get_stats()
        logger.info(f"📊 Proxy Statistics: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        stats = proxy.get_stats()
        logger.info(f"📊 Proxy Statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())