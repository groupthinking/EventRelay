#!/usr/bin/env python3
"""
Real Video Processor Service
===========================

Integrated video processing service that combines YouTube Data API, AI processing,
and cost monitoring to provide complete real video analysis.
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from youtube_extension.utils import extract_video_id

from .api_cost_monitor import cost_monitor
from .real_ai_processor import (
    analyze_video_with_ai,
    get_ai_processor,
)

# Import our real API services
from .real_youtube_api import get_youtube_service

# Configure logging
logger = logging.getLogger(__name__)

# Cached results older than this are treated as misses.
_CACHE_TTL_SECONDS = 86400  # 24 hours

class RealVideoProcessor:
    """
    Complete real video processing service

    Combines:
    - YouTube Data API v3 for metadata and transcripts
    - Multi-provider AI processing (OpenAI/Anthropic/Gemini)
    - Cost monitoring and optimization
    - Comprehensive error handling and fallbacks
    - Result caching and storage
    """

    def __init__(self):
        """Initialize the real video processor"""
        self.youtube_service = get_youtube_service()
        self.ai_processor = get_ai_processor()

        # Cache directory for processed results
        self.cache_dir = Path("youtube_processed_videos/real_processing")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Processing configuration
        self.enable_caching = os.getenv('FALLBACK_TO_CACHE', 'true').lower() == 'true'
        self.max_retry_attempts = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))

        logger.info("🚀 Real Video Processor initialized")

    def _get_cache_key(self, video_url: str) -> str:
        """Generate cache key for video URL"""
        return hashlib.sha256(video_url.encode()).hexdigest()[:12]

    def _get_cache_path(self, video_id: str) -> Path:
        """Get cache file path for video"""
        return self.cache_dir / f"{video_id}_processed.json"

    @staticmethod
    def _read_cache_file(cache_path: Path) -> Optional[tuple[dict[str, Any], float]]:
        """Read and parse a cache entry.

        Blocking: performs ``open``/``fstat``/``json.load``. Always run this off
        the event loop. Keeping the whole sequence in a single call also avoids a
        stat/read race across separate thread hops.

        The age is taken from ``fstat`` on the already-open descriptor rather than
        from a separate ``stat`` on the path, so the timestamp always describes the
        exact bytes being parsed even if the path is republished concurrently.

        Returns ``(payload, cache_age_seconds)`` for a fresh entry, else ``None``.
        """
        try:
            handle = open(cache_path, encoding='utf-8')
        except FileNotFoundError:
            return None

        with handle as f:
            cache_age = datetime.now().timestamp() - os.fstat(f.fileno()).st_mtime
            # Deliberately the positive form, mirroring the original
            # ``cache_age < 86400`` guard: a non-finite timestamp compares False
            # here and falls through to a miss, exactly as it did before.
            if cache_age < _CACHE_TTL_SECONDS:
                return json.load(f), cache_age

        return None

    @staticmethod
    def _write_cache_file(cache_path: Path, payload: dict[str, Any]) -> None:
        """Serialize ``payload`` to ``cache_path``.

        Blocking: performs ``open``/``json.dump``/``replace``. Always run off the
        event loop.

        Publishes atomically. Serializing straight into ``cache_path`` would
        truncate it up front, so a concurrent reader could observe an empty or
        half-written entry. Writing to a sibling temp file and ``os.replace``-ing
        it into position means readers only ever see a complete entry; the temp
        file shares the cache directory so the rename stays on one filesystem.
        """
        fd, tmp_name = tempfile.mkstemp(
            dir=cache_path.parent, prefix=f'.{cache_path.name}.', suffix='.tmp'
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_name, cache_path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp_name)
            raise

    @staticmethod
    def _count_cached_files(cache_dir: Path) -> int:
        """Count published cache entries under ``cache_dir``.

        Blocking: performs a ``stat`` plus a full directory walk. Always run
        this off the event loop. It is reached from the status endpoint, so an
        inline walk stalls every concurrently-served request for as long as the
        scan takes — which grows with the number of cached videos.

        The existence check and the walk stay in a single call so the directory
        cannot disappear between them, mirroring ``_read_cache_file``. The count
        is accumulated lazily rather than materializing the whole listing, since
        only the total is ever used.
        """
        if not cache_dir.exists():
            return 0
        return sum(1 for _ in cache_dir.glob("*_processed.json"))

    async def _load_from_cache(self, video_id: str) -> Optional[dict[str, Any]]:
        """Load processed result from cache if available"""
        if not self.enable_caching:
            return None

        try:
            cache_path = self._get_cache_path(video_id)
            entry = await asyncio.to_thread(self._read_cache_file, cache_path)
            if entry is None:
                return None

            cached_result, cache_age = entry
            cached_result['cached'] = True
            cached_result['cache_age_hours'] = round(cache_age / 3600, 2)

            logger.info(f"📁 Using cached result for {video_id} (age: {cached_result['cache_age_hours']}h)")
            return cached_result

        except Exception as e:
            logger.warning(f"Error loading cache: {e}")

        return None

    async def _save_to_cache(self, video_id: str, result: dict[str, Any]):
        """Save processed result to cache"""
        if not self.enable_caching:
            return

        try:
            cache_path = self._get_cache_path(video_id)

            # Remove cache-specific fields before saving
            clean_result = {k: v for k, v in result.items() if k not in ['cached', 'cache_age_hours']}

            await asyncio.to_thread(self._write_cache_file, cache_path, clean_result)

            logger.debug(f"💾 Saved result to cache: {cache_path}")

        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")

    async def process_video(self, video_url: str, force_refresh: bool = False) -> dict[str, Any]:
        """
        Process a video with complete real API integration

        Args:
            video_url: YouTube video URL or ID
            force_refresh: Skip cache and force fresh processing

        Returns:
            Complete video processing result with AI analysis
        """
        start_time = datetime.now(timezone.utc)
        processing_steps = []
        total_cost = 0.0

        try:
            # Extract video ID
            video_id = extract_video_id(video_url)

            processing_steps.append({
                'step': 'video_id_extraction',
                'status': 'completed',
                'result': video_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_result = await self._load_from_cache(video_id)
                if cached_result:
                    return cached_result

            # Step 1: Get comprehensive YouTube data
            logger.info(f"🎬 Processing video: {video_id}")

            try:
                youtube_data = await self.youtube_service.get_comprehensive_video_data(video_url)
                processing_steps.append({
                    'step': 'youtube_data_extraction',
                    'status': 'completed',
                    'metadata': {
                        'title': youtube_data['metadata']['title'],
                        'duration': youtube_data['metadata']['duration'],
                        'has_transcript': youtube_data['transcript']['has_transcript'],
                        'transcript_segments': youtube_data['transcript']['segment_count']
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

            except Exception as e:
                error_msg = f"YouTube data extraction failed: {e}"
                logger.error(error_msg)
                processing_steps.append({
                    'step': 'youtube_data_extraction',
                    'status': 'failed',
                    'error': error_msg,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

                # Return minimal result if YouTube API fails
                return {
                    'video_id': video_id,
                    'video_url': video_url,
                    'success': False,
                    'error': error_msg,
                    'processing_steps': processing_steps,
                    'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds(),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'cost_breakdown': {'total_cost': 0.0},
                    'cached': False
                }

            # Step 2: AI Analysis
            logger.info(f"🤖 Running AI analysis for {video_id}")

            try:
                ai_analysis = await analyze_video_with_ai(youtube_data)
                total_cost += ai_analysis.get('total_cost', 0.0)

                processing_steps.append({
                    'step': 'ai_analysis',
                    'status': 'completed' if ai_analysis.get('success') else 'partial',
                    'providers_used': ai_analysis.get('processing_providers', []),
                    'analyses_completed': len([k for k in ['content_analysis', 'summary', 'actions', 'categorization']
                                             if ai_analysis.get(k) is not None]),
                    'cost': ai_analysis.get('total_cost', 0.0),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

            except Exception as e:
                error_msg = f"AI analysis failed: {e}"
                logger.error(error_msg)
                processing_steps.append({
                    'step': 'ai_analysis',
                    'status': 'failed',
                    'error': error_msg,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

                # Continue with YouTube data only
                ai_analysis = {
                    'success': False,
                    'error': error_msg,
                    'total_cost': 0.0,
                    'processing_providers': []
                }

            # Step 3: Compile comprehensive result
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Get cost monitoring data
            cost_dashboard = await cost_monitor.get_cost_dashboard()

            comprehensive_result = {
                # Video identification
                'video_id': video_id,
                'video_url': video_url,
                'success': True,

                # Core data
                'metadata': youtube_data['metadata'],
                'transcript': youtube_data['transcript'],
                'channel_info': youtube_data.get('channel_info', {}),
                'related_videos': youtube_data.get('related_videos', []),

                # AI Analysis results
                'ai_analysis': ai_analysis,

                # Processing metadata
                'processing_steps': processing_steps,
                'processing_time': processing_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),

                # Cost information
                'cost_breakdown': {
                    'total_cost': total_cost,
                    'youtube_api_quota': len(processing_steps),  # Rough estimate
                    'ai_processing_cost': ai_analysis.get('total_cost', 0.0),
                    'providers_used': ai_analysis.get('processing_providers', []),
                    'budget_remaining': cost_dashboard.get('today_summary', {}).get('budget_remaining', 0.0)
                },

                # Cache information
                'cached': False,
                'save_path': str(self._get_cache_path(video_id)),

                # Quality indicators
                'quality_metrics': {
                    'has_metadata': bool(youtube_data.get('metadata')),
                    'has_transcript': youtube_data['transcript']['has_transcript'],
                    'transcript_quality': 'high' if youtube_data['transcript']['segment_count'] > 50 else 'medium' if youtube_data['transcript']['segment_count'] > 10 else 'low',
                    'ai_analysis_success': ai_analysis.get('success', False),
                    'processing_success_rate': len([s for s in processing_steps if s['status'] == 'completed']) / len(processing_steps) if processing_steps else 0
                }
            }

            # Save to cache
            await self._save_to_cache(video_id, comprehensive_result)

            # Log success
            logger.info(f"✅ Video processing complete for {video_id}")
            logger.info(f"   - Processing time: {processing_time:.2f}s")
            logger.info(f"   - Total cost: ${total_cost:.4f}")
            logger.info(f"   - AI providers: {', '.join(ai_analysis.get('processing_providers', []))}")
            logger.info(f"   - Transcript: {'✅' if youtube_data['transcript']['has_transcript'] else '❌'}")
            logger.info(f"   - AI analysis: {'✅' if ai_analysis.get('success') else '❌'}")

            return comprehensive_result

        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Video processing failed: {str(e)}"
            logger.error(error_msg)

            processing_steps.append({
                'step': 'processing_error',
                'status': 'failed',
                'error': error_msg,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            return {
                'video_id': video_id if 'video_id' in locals() else 'unknown',
                'video_url': video_url,
                'success': False,
                'error': error_msg,
                'processing_steps': processing_steps,
                'processing_time': processing_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cost_breakdown': {'total_cost': total_cost},
                'cached': False
            }

    async def validate_and_process(self, video_url: str) -> dict[str, Any]:
        """
        Validate video URL and process if valid

        Returns:
            Validation result and processing data
        """
        try:
            # Validate URL first
            is_valid, video_id, message = await self.youtube_service.validate_video_url(video_url)

            if not is_valid:
                return {
                    'valid': False,
                    'video_id': video_id,
                    'error': message,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

            # Process if valid
            result = await self.process_video(video_url)
            result['valid'] = True
            result['validation_message'] = message

            return result

        except Exception as e:
            return {
                'valid': False,
                'video_id': '',
                'error': f"Validation failed: {str(e)}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def batch_process_videos(self, video_urls: list[str], max_concurrent: int = 3) -> dict[str, Any]:
        """
        Process multiple videos concurrently with cost and rate limit management

        Args:
            video_urls: List of YouTube video URLs
            max_concurrent: Maximum concurrent processing tasks

        Returns:
            Batch processing results
        """
        start_time = datetime.now(timezone.utc)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(url: str) -> tuple[str, dict[str, Any]]:
            async with semaphore:
                try:
                    result = await self.process_video(url)
                    return url, result
                except Exception as e:
                    return url, {
                        'success': False,
                        'error': str(e),
                        'video_url': url,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

        # Process all videos
        tasks = [process_single(url) for url in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Compile batch results
        successful_results = []
        failed_results = []
        total_cost = 0.0

        for result in results:
            if isinstance(result, Exception):
                failed_results.append({
                    'video_url': 'unknown',
                    'error': str(result),
                    'success': False
                })
                continue

            url, video_result = result
            if video_result.get('success'):
                successful_results.append(video_result)
                total_cost += video_result.get('cost_breakdown', {}).get('total_cost', 0.0)
            else:
                failed_results.append(video_result)

        batch_result = {
            'batch_processing': True,
            'total_videos': len(video_urls),
            'successful': len(successful_results),
            'failed': len(failed_results),
            'success_rate': len(successful_results) / len(video_urls) * 100,
            'total_cost': total_cost,
            'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'results': successful_results,
            'errors': failed_results
        }

        logger.info(f"🎯 Batch processing complete: {len(successful_results)}/{len(video_urls)} successful")
        logger.info(f"   - Total cost: ${total_cost:.4f}")
        logger.info(f"   - Processing time: {batch_result['processing_time']:.2f}s")

        return batch_result

    async def get_processing_status(self) -> dict[str, Any]:
        """Get current processing status and statistics"""
        try:
            cost_dashboard = await cost_monitor.get_cost_dashboard()

            # Count cached files (off the event loop; the walk is unbounded)
            cached_files = await asyncio.to_thread(
                self._count_cached_files, self.cache_dir
            )

            return {
                'service_status': 'operational',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cache': {
                    'enabled': self.enable_caching,
                    'cached_videos': cached_files,
                    'cache_directory': str(self.cache_dir)
                },
                'api_status': {
                    'youtube_service': 'operational' if self.youtube_service else 'unavailable',
                    'ai_processor': 'operational' if self.ai_processor else 'unavailable',
                    'cost_monitor': 'operational' if cost_monitor else 'unavailable'
                },
                'cost_monitoring': cost_dashboard,
                'configuration': {
                    'max_retry_attempts': self.max_retry_attempts,
                    'enable_caching': self.enable_caching
                }
            }

        except Exception as e:
            return {
                'service_status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def close(self):
        """Clean up resources"""
        try:
            if self.youtube_service:
                await self.youtube_service.close()
            logger.info("🔌 Real Video Processor closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Global service instance
real_video_processor = None

def get_real_video_processor() -> RealVideoProcessor:
    """Get or create real video processor instance"""
    global real_video_processor
    if real_video_processor is None:
        real_video_processor = RealVideoProcessor()
    return real_video_processor

# Convenience functions
async def process_video_real(video_url: str, force_refresh: bool = False) -> dict[str, Any]:
    """Process a video using real APIs"""
    processor = get_real_video_processor()
    return await processor.process_video(video_url, force_refresh)

async def validate_and_process_video(video_url: str) -> dict[str, Any]:
    """Validate and process a video"""
    processor = get_real_video_processor()
    return await processor.validate_and_process(video_url)

if __name__ == "__main__":
    # Test the real video processor
    async def test_real_processor():
        processor = RealVideoProcessor()

        # Test with a real video (non-music, compliance-safe)
        test_url = "https://www.youtube.com/watch?v=b1mjQIiH7r4"

        try:
            print("🧪 Testing Real Video Processor")

            # Test validation and processing
            result = await processor.validate_and_process(test_url)

            if result.get('valid') and result.get('success'):
                print("✅ Processing successful!")
                print(f"   Video: {result['metadata']['title']}")
                print(f"   Duration: {result['metadata']['duration']}")
                print(f"   Transcript: {'Yes' if result['transcript']['has_transcript'] else 'No'}")
                print(f"   AI Analysis: {'Yes' if result['ai_analysis']['success'] else 'No'}")
                print(f"   Cost: ${result['cost_breakdown']['total_cost']:.4f}")
                print(f"   Processing time: {result['processing_time']:.2f}s")
            else:
                print(f"❌ Processing failed: {result.get('error')}")

            # Test status
            status = await processor.get_processing_status()
            print(f"\n📊 Service Status: {status['service_status']}")
            print(f"   Cached videos: {status['cache']['cached_videos']}")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            await processor.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_real_processor())
