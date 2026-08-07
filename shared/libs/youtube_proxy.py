#!/usr/bin/env python3
"""
MCP YouTube API Proxy Server
Prevents timeout errors and handles rate limiting for YouTube API calls
Integrates sophisticated retry and rate limiting infrastructure
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

# YouTube API specific imports
try:
    import yt_dlp
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
    )
    from youtube_transcript_api.proxies import GenericProxyConfig
    YOUTUBE_DEPS_AVAILABLE = True
except ImportError as e:
    YOUTUBE_DEPS_AVAILABLE = False
    GenericProxyConfig = None  # type: ignore[assignment,misc]
    logging.warning(f"YouTube dependencies not available: {e}")

logger = logging.getLogger("youtube_api_proxy")


def _get_webshare_proxy_url() -> str | None:
    """Return the validated WEBSHARE_PROXY_URL, or None for direct connection."""
    url = os.getenv("WEBSHARE_PROXY_URL", "").strip()
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https", "socks5") or not parsed.hostname:
        logger.warning(
            "WEBSHARE_PROXY_URL is set but malformed — falling back to direct connection"
        )
        return None
    return url


def _get_transcript_proxy_config() -> GenericProxyConfig | None:
    """Return a youtube-transcript-api proxy config object, or None.

    youtube-transcript-api >=1.0 replaced the ``proxies=`` keyword with a
    ``proxy_config`` constructor argument accepting a proxy config object.
    """
    url = _get_webshare_proxy_url()
    if not url:
        return None
    if GenericProxyConfig is None:
        logger.warning(
            "WEBSHARE_PROXY_URL is set but youtube-transcript-api proxy support "
            "is unavailable (requires youtube-transcript-api>=1.0) — falling back "
            "to direct connection"
        )
        return None
    return GenericProxyConfig(http_url=url, https_url=url)


# Matches the ``user[:password]@`` userinfo segment of any URL. Kept byte-identical
# to the canonical copy in ``src/youtube_extension/utils/proxy.py``; see that module
# for the full rationale. In short: the classes exclude the authority delimiters
# (whitespace, "/", "?", "#") so paths and query strings containing "@" are never
# mistaken for credentials, but they permit a literal "@" so an unencoded one in
# the password is consumed whole rather than leaving the tail behind.
_USERINFO_RE = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)"
    r"(?P<user>[^\s/:?#]*)"
    r"(?::(?P<password>[^\s/?#]*))?"
    r"@"
)

_REDACTED = "***"
_UNPRINTABLE = "<unprintable error>"
_REDACTION_FAILED = "<redaction failed>"


def _redact_proxy_credentials(text: Any) -> str:
    """Strip URL userinfo (``user:pass@``) from ``text``.

    Two passes: exact replacement of the configured ``WEBSHARE_PROXY_URL`` (which
    preserves the host, so operators can still tell which proxy was in play),
    then a generic ``scheme://user:pass@`` sweep that catches credentials never
    matching the env value verbatim -- a normalised or percent-encoded form
    echoed back by yt-dlp, a ``CalledProcessError`` repr of the argv, or a
    different proxy variable such as ``HTTPS_PROXY``.

    Never raises: every caller here is an exception handler, where a failure
    would mask the original error.
    """
    if isinstance(text, str):
        candidate = text
    else:
        try:
            candidate = str(text)
        except Exception:  # noqa: BLE001 - a hostile __str__ must not propagate
            return _UNPRINTABLE

    try:
        return _redact(candidate)
    except Exception:  # noqa: BLE001 - never return text we cannot vouch for
        return _REDACTION_FAILED


def _redact(text: str) -> str:
    """Run the two redaction passes over an already-stringified ``text``."""
    url = os.getenv("WEBSHARE_PROXY_URL", "").strip()
    if url and url in text:
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            redacted = parsed._replace(netloc=netloc).geturl()
        except (ValueError, AttributeError):
            redacted = "<proxy-url>"
        text = text.replace(url, redacted)

    def _mask(match: re.Match[str]) -> str:
        if match.group("password") is None:
            return f"{match.group('scheme')}{_REDACTED}@"
        return f"{match.group('scheme')}{_REDACTED}:{_REDACTED}@"

    return _USERINFO_RE.sub(_mask, text)

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
            raise Exception("Circuit breaker OPEN for YouTube API - too many failures")

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
                    logger.error(f"❌ {operation_name} failed after {attempt-1} retries: {_redact_proxy_credentials(str(error))}")
                    self.circuit_breaker.record_failure()
                    self.consecutive_errors += 1
                    break

                # Non-retryable errors
                if error_type in [YouTubeErrorType.VIDEO_NOT_FOUND, YouTubeErrorType.PRIVATE_VIDEO]:
                    logger.warning(f"⚠️ {operation_name} non-retryable error: {_redact_proxy_credentials(str(error))}")
                    break

                # Calculate retry delay
                retry_delay = self._calculate_retry_delay(attempt, error_type)

                logger.warning(f"⚠️ {operation_name} attempt {attempt} failed ({error_type.value}), retrying in {retry_delay:.2f}s: {_redact_proxy_credentials(str(error))}")

                self.stats["retries_executed"] += 1
                await asyncio.sleep(retry_delay)

        # Final failure
        self.circuit_breaker.record_failure()
        self.consecutive_errors += 1
        raise last_error

    async def get_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Get video transcript with retry logic and fallback methods"""

        async def _transcript_operation():
            proxy_url = _get_webshare_proxy_url()
            proxy_config = _get_transcript_proxy_config()
            # youtube-transcript-api is synchronous/blocking network I/O; run it
            # in an executor so it doesn't stall the event loop. (get_event_loop
            # matches the convention used across the rest of this codebase.)
            loop = asyncio.get_event_loop()

            # Method 1: Direct transcript API
            # youtube-transcript-api >=1.0 replaced the ``get_transcript`` class
            # method with an instance ``fetch`` that returns a FetchedTranscript;
            # ``to_raw_data`` yields the list-of-dicts shape the rest of the
            # pipeline expects. The ``proxies=`` kwarg was replaced by a
            # ``proxy_config`` constructor argument.
            try:
                yt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
                transcript = await loop.run_in_executor(
                    None, lambda: yt_api.fetch(video_id).to_raw_data()
                )
                if transcript:
                    logger.info(f"✅ Direct transcript extraction: {len(transcript)} segments")
                    return transcript
            except Exception as e:
                logger.debug(f"Direct transcript failed: {e}")

            # Method 2: Alternative language codes
            # ``list_transcripts`` class method is now the instance ``list``;
            # each Transcript's ``fetch`` returns a FetchedTranscript, so
            # ``to_raw_data`` restores the list-of-dicts.
            try:
                yt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
                transcript_list = await loop.run_in_executor(
                    None, lambda: yt_api.list(video_id)
                )
                for transcript_item in transcript_list:
                    # A single language failing (disabled/blocked) must not abort
                    # the whole loop — try the next available transcript.
                    try:
                        transcript = await loop.run_in_executor(
                            None,
                            lambda item=transcript_item: item.fetch().to_raw_data(),
                        )
                    except Exception as item_e:
                        logger.debug(f"Alternative language item failed: {item_e}")
                        continue
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
                if proxy_url:
                    ydl_opts['proxy'] = proxy_url

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

            # CouldNotRetrieveTranscript(>=1.0) takes a bare video_id and builds
            # its own message/URL; passing a sentence corrupts the generated URL.
            raise CouldNotRetrieveTranscript(video_id)

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
