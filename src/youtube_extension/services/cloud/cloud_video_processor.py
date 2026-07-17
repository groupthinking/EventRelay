#!/usr/bin/env python3
"""
Cloud-Native Video Processor
=============================

Cloud-native video processor using:
- Vertex AI Agent Builder for AI reasoning
- Firestore for shared state
- Cloud Tasks for async processing
- Cloud Run for serverless scaling
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..cloud import (
    get_firestore_service,
    get_cloud_tasks_service,
    get_vertex_ai_service,
    VideoProcessingState,
    VideoProcessingTask,
)

logger = logging.getLogger(__name__)


@dataclass
class VideoProcessingResult:
    """Result of video processing"""
    video_id: str
    video_url: str
    success: bool
    metadata: Optional[Dict[str, Any]] = None
    transcript: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    from_cache: bool = False


class CloudNativeVideoProcessor:
    """
    Cloud-native video processor with:
    - Shared state via Firestore
    - Async processing via Cloud Tasks
    - AI reasoning via Vertex AI Agent Builder
    """

    def __init__(
        self,
        enable_queue: bool = True,
        enable_state: bool = True,
        enable_vertex_ai: bool = True,
    ):
        """
        Initialize cloud-native video processor.

        Args:
            enable_queue: Enable Cloud Tasks queue
            enable_state: Enable Firestore state management
            enable_vertex_ai: Enable Vertex AI Agent Builder
        """
        self.enable_queue = enable_queue
        self.enable_state = enable_state
        self.enable_vertex_ai = enable_vertex_ai

        logger.info(
            f"CloudNativeVideoProcessor initialized: "
            f"queue={enable_queue}, state={enable_state}, vertex_ai={enable_vertex_ai}"
        )

    async def process_video_async(
        self,
        video_url: str,
        priority: int = 0,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        Queue video for async processing via Cloud Tasks.

        Args:
            video_url: YouTube video URL
            priority: Processing priority (higher = more urgent)
            callback_url: Optional callback URL for completion notification

        Returns:
            Task ID
        """
        if not self.enable_queue:
            raise RuntimeError("Cloud Tasks queue not enabled")

        # Extract video ID
        video_id = self._extract_video_id(video_url)

        # Create state in Firestore
        if self.enable_state:
            firestore_service = await get_firestore_service()
            await firestore_service.create_state(video_id, video_url)
            logger.info(f"Created Firestore state for video: {video_id}")

        # Enqueue task
        tasks_service = get_cloud_tasks_service()
        task = VideoProcessingTask(
            video_id=video_id,
            video_url=video_url,
            priority=priority,
            callback_url=callback_url,
        )

        task_id = await tasks_service.enqueue_video_processing(task)
        logger.info(f"Enqueued video processing task: {task_id}")

        return task_id

    async def process_video_sync(
        self,
        video_url: str,
        force_refresh: bool = False,
    ) -> VideoProcessingResult:
        """
        Process video synchronously (blocking).

        Args:
            video_url: YouTube video URL
            force_refresh: Skip cache and reprocess

        Returns:
            VideoProcessingResult
        """
        start_time = datetime.now(timezone.utc)
        video_id = self._extract_video_id(video_url)

        try:
            # Check existing state
            if self.enable_state and not force_refresh:
                firestore_service = await get_firestore_service()
                state = await firestore_service.get_state(video_id)

                if state and state.status == 'completed':
                    logger.info(f"Using cached state for video: {video_id}")
                    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

                    return VideoProcessingResult(
                        video_id=video_id,
                        video_url=video_url,
                        success=True,
                        metadata=state.metadata,
                        transcript=state.transcript,
                        ai_analysis=state.ai_analysis,
                        processing_time=processing_time,
                        from_cache=True,
                    )

            # Create/update state
            if self.enable_state:
                firestore_service = await get_firestore_service()
                await firestore_service.create_state(video_id, video_url)
                await firestore_service.update_state(
                    video_id,
                    status='processing',
                    current_stage='metadata'
                )

            # Stage 1: Fetch metadata
            metadata = await self._fetch_metadata(video_url)
            if self.enable_state:
                await firestore_service.update_state(
                    video_id,
                    metadata=metadata,
                    current_stage='transcript'
                )

            # Stage 2: Extract transcript
            transcript = await self._extract_transcript(video_id)
            if self.enable_state:
                await firestore_service.update_state(
                    video_id,
                    transcript=transcript,
                    current_stage='analysis'
                )

            # Stage 3: AI analysis via Vertex AI
            ai_analysis = None
            if self.enable_vertex_ai:
                ai_analysis = await self._analyze_with_vertex_ai(
                    video_id,
                    metadata,
                    transcript
                )
                if self.enable_state:
                    await firestore_service.update_state(
                        video_id,
                        ai_analysis=ai_analysis,
                        current_stage='complete'
                    )

            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Update final state
            if self.enable_state:
                await firestore_service.update_state(
                    video_id,
                    status='completed',
                    processing_time=processing_time
                )

            logger.info(
                f"Successfully processed video: {video_id} "
                f"in {processing_time:.2f}s"
            )

            return VideoProcessingResult(
                video_id=video_id,
                video_url=video_url,
                success=True,
                metadata=metadata,
                transcript=transcript,
                ai_analysis=ai_analysis,
                processing_time=processing_time,
                from_cache=False,
            )

        except Exception as e:
            error_msg = f"Error processing video {video_id}: {str(e)}"
            logger.error(error_msg)

            # Update state with error
            if self.enable_state:
                firestore_service = await get_firestore_service()
                await firestore_service.update_state(
                    video_id,
                    status='failed',
                    error_message=error_msg
                )

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            return VideoProcessingResult(
                video_id=video_id,
                video_url=video_url,
                success=False,
                error_message=error_msg,
                processing_time=processing_time,
            )

    async def batch_process_async(
        self,
        video_urls: list[str],
        priority: int = 0,
    ) -> list[str]:
        """
        Queue multiple videos for async processing.

        Args:
            video_urls: List of YouTube video URLs
            priority: Processing priority

        Returns:
            List of task IDs
        """
        if not self.enable_queue:
            raise RuntimeError("Cloud Tasks queue not enabled")

        tasks_service = get_cloud_tasks_service()

        video_tasks = [
            VideoProcessingTask(
                video_id=self._extract_video_id(url),
                video_url=url,
                priority=priority,
            )
            for url in video_urls
        ]

        task_ids = await tasks_service.enqueue_batch(video_tasks)
        logger.info(f"Enqueued {len(task_ids)} video processing tasks")

        return task_ids

    async def get_processing_status(self, video_id: str) -> Optional[VideoProcessingState]:
        """
        Get current processing status for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoProcessingState or None
        """
        if not self.enable_state:
            raise RuntimeError("Firestore state not enabled")

        firestore_service = await get_firestore_service()
        return await firestore_service.get_state(video_id)

    def _extract_video_id(self, video_url: str) -> str:
        """Extract video ID from a YouTube URL.

        The host/path matching is case-insensitive so uppercase URLs such as
        ``HTTPS://YOUTUBE.COM/WATCH?V=...`` are handled here too. The
        API-boundary validator (``models._YOUTUBE_URL_REGEX``) is itself
        case-insensitive, so without this an uppercase URL would pass
        validation, fall through the ``else`` branch below, and return the
        whole URL as the "id" — breaking the downstream metadata fetch.
        """
        lowered = video_url.lower()
        if 'youtube.com/watch?v=' in lowered:
            return re.split(r'v=', video_url, flags=re.IGNORECASE)[1].split('&')[0]
        elif 'youtu.be/' in lowered:
            return re.split(r'youtu\.be/', video_url, flags=re.IGNORECASE)[1].split('?')[0]
        else:
            # Assume it's already an ID
            return video_url

    async def _fetch_metadata(self, video_url: str) -> Dict[str, Any]:
        """
        Fetch video metadata.

        This should integrate with real YouTube Data API.
        """
        # Placeholder - integrate with real implementation
        logger.info(f"Fetching metadata for: {video_url}")

        return {
            'title': 'Video Title',
            'channel': 'Channel Name',
            'duration': '10:30',
            'views': 1000,
            'description': 'Video description',
        }

    async def _extract_transcript(self, video_id: str) -> Dict[str, Any]:
        """
        Extract video transcript.

        This should integrate with YouTube Transcript API.
        """
        # Placeholder - integrate with real implementation
        logger.info(f"Extracting transcript for: {video_id}")

        return {
            'text': 'Full transcript text...',
            'language': 'en',
            'segments': [],
        }

    async def _analyze_with_vertex_ai(
        self,
        video_id: str,
        metadata: Dict[str, Any],
        transcript: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze video using Vertex AI Agent Builder.

        Args:
            video_id: YouTube video ID
            metadata: Video metadata
            transcript: Video transcript

        Returns:
            AI analysis results
        """
        if not self.enable_vertex_ai:
            return {}

        vertex_service = get_vertex_ai_service()

        # Analyze transcript
        response = await vertex_service.analyze_transcript(
            transcript=transcript.get('text', ''),
            video_metadata=metadata
        )

        logger.info(f"Completed Vertex AI analysis for video: {video_id}")

        return {
            'summary': response.text,
            'model': 'vertex-ai-agent-builder',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'usage': response.usage,
        }


# Singleton instance
_cloud_video_processor: Optional[CloudNativeVideoProcessor] = None


def get_cloud_video_processor() -> CloudNativeVideoProcessor:
    """Get or create singleton cloud video processor instance"""
    global _cloud_video_processor

    if _cloud_video_processor is None:
        _cloud_video_processor = CloudNativeVideoProcessor()

    return _cloud_video_processor
