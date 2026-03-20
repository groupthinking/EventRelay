#!/usr/bin/env python3
"""
Cloud Tasks Queue Service
==========================

Manages async video processing queue using Google Cloud Tasks.
Enables non-blocking video processing with retry logic and concurrency control.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

try:
    from google.cloud import tasks_v2
    from google.protobuf import timestamp_pb2
    CLOUD_TASKS_AVAILABLE = True
except ImportError:
    tasks_v2 = None
    timestamp_pb2 = None
    CLOUD_TASKS_AVAILABLE = False
    logging.warning("Cloud Tasks not available - install: pip install google-cloud-tasks")


logger = logging.getLogger(__name__)


@dataclass
class TaskConfig:
    """Configuration for a Cloud Tasks task"""
    task_name: Optional[str] = None
    schedule_time: Optional[datetime] = None  # When to execute (None = immediate)
    max_retry_count: int = 3
    max_retry_duration: timedelta = timedelta(hours=1)
    min_backoff: timedelta = timedelta(seconds=10)
    max_backoff: timedelta = timedelta(seconds=300)


@dataclass
class VideoProcessingTask:
    """Video processing task payload"""
    video_id: str
    video_url: str
    priority: int = 0  # Higher = more urgent
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert to JSON payload"""
        return json.dumps({
            'video_id': self.video_id,
            'video_url': self.video_url,
            'priority': self.priority,
            'callback_url': self.callback_url,
            'metadata': self.metadata or {},
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'VideoProcessingTask':
        """Create from JSON payload"""
        data = json.loads(json_str)
        return cls(**data)


class CloudTasksQueueService:
    """
    Service for managing video processing tasks via Cloud Tasks.

    Provides:
    - Async task queuing with Cloud Tasks
    - Automatic retry with exponential backoff
    - Priority-based task ordering
    - Task status tracking
    - Concurrency control
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        queue_name: str = "video-processing-queue",
        service_url: Optional[str] = None,
    ):
        """
        Initialize Cloud Tasks queue service.

        Args:
            project_id: GCP project ID (defaults to env GOOGLE_CLOUD_PROJECT)
            location: GCP region for queue
            queue_name: Name of the Cloud Tasks queue
            service_url: URL of the Cloud Run service that will process tasks
        """
        if not CLOUD_TASKS_AVAILABLE:
            raise ImportError(
                "Cloud Tasks not available. Install: pip install google-cloud-tasks"
            )

        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location
        self.queue_name = queue_name
        self.service_url = service_url or os.getenv('CLOUD_RUN_SERVICE_URL')

        if not self.service_url:
            logger.warning(
                "No service URL configured. Set CLOUD_RUN_SERVICE_URL or pass service_url parameter."
            )

        # Initialize Cloud Tasks client
        self.client: Optional[tasks_v2.CloudTasksClient] = None

        logger.info(
            f"CloudTasksQueueService initialized: "
            f"project={self.project_id}, location={self.location}, queue={self.queue_name}"
        )

    def initialize(self) -> None:
        """Initialize Cloud Tasks client"""
        if not self.client:
            self.client = tasks_v2.CloudTasksClient()
            logger.info("Cloud Tasks client initialized")

    def close(self) -> None:
        """Close Cloud Tasks client connection"""
        if self.client:
            self.client.transport.close()
            self.client = None
            logger.info("Cloud Tasks client closed")

    def _get_queue_path(self) -> str:
        """Get full queue path"""
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        return self.client.queue_path(
            self.project_id,
            self.location,
            self.queue_name
        )

    async def enqueue_video_processing(
        self,
        video_task: VideoProcessingTask,
        task_config: Optional[TaskConfig] = None,
    ) -> str:
        """
        Enqueue a video for processing.

        Args:
            video_task: Video processing task
            task_config: Task configuration (retry, scheduling, etc.)

        Returns:
            Task name/ID
        """
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        if not self.service_url:
            raise ValueError("Service URL not configured. Cannot enqueue tasks.")

        config = task_config or TaskConfig()

        # Build task
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{self.service_url}/api/v3/process-video-task",
                headers={
                    "Content-Type": "application/json",
                },
                body=video_task.to_json().encode(),
            )
        )

        # Set task name if provided
        if config.task_name:
            task.name = self.client.task_path(
                self.project_id,
                self.location,
                self.queue_name,
                config.task_name
            )

        # Set schedule time if provided
        if config.schedule_time:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(config.schedule_time)
            task.schedule_time = timestamp

        # Create task
        queue_path = self._get_queue_path()
        response = self.client.create_task(
            request=tasks_v2.CreateTaskRequest(
                parent=queue_path,
                task=task,
            )
        )

        task_id = response.name.split('/')[-1]
        logger.info(
            f"Enqueued video processing task: {task_id} "
            f"(video_id={video_task.video_id}, priority={video_task.priority})"
        )

        return task_id

    async def enqueue_batch(
        self,
        video_tasks: list[VideoProcessingTask],
        task_config: Optional[TaskConfig] = None,
    ) -> list[str]:
        """
        Enqueue multiple videos for processing.

        Args:
            video_tasks: List of video processing tasks
            task_config: Task configuration for all tasks

        Returns:
            List of task IDs
        """
        task_ids = []

        for video_task in video_tasks:
            try:
                task_id = await self.enqueue_video_processing(video_task, task_config)
                task_ids.append(task_id)
            except Exception as e:
                logger.error(f"Failed to enqueue task for {video_task.video_id}: {e}")

        logger.info(f"Enqueued {len(task_ids)}/{len(video_tasks)} tasks successfully")
        return task_ids

    async def create_queue_if_not_exists(self) -> None:
        """
        Create the Cloud Tasks queue if it doesn't exist.

        This should be called during deployment/setup.
        """
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        try:
            # Try to get the queue
            queue_path = self._get_queue_path()
            self.client.get_queue(name=queue_path)
            logger.info(f"Queue already exists: {queue_path}")

        except Exception:
            # Queue doesn't exist, create it
            parent = f"projects/{self.project_id}/locations/{self.location}"

            queue = tasks_v2.Queue(
                name=self._get_queue_path(),
                rate_limits=tasks_v2.RateLimits(
                    max_dispatches_per_second=100,  # Max 100 tasks/second
                    max_concurrent_dispatches=50,   # Max 50 concurrent tasks
                ),
                retry_config=tasks_v2.RetryConfig(
                    max_attempts=3,
                    max_retry_duration=timedelta(hours=1),
                    min_backoff=timedelta(seconds=10),
                    max_backoff=timedelta(seconds=300),
                    max_doublings=3,
                ),
            )

            self.client.create_queue(
                request=tasks_v2.CreateQueueRequest(
                    parent=parent,
                    queue=queue,
                )
            )
            logger.info(f"Created queue: {self._get_queue_path()}")

    async def pause_queue(self) -> None:
        """Pause the queue (stop processing tasks)"""
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        queue_path = self._get_queue_path()
        self.client.pause_queue(name=queue_path)
        logger.info(f"Paused queue: {queue_path}")

    async def resume_queue(self) -> None:
        """Resume the queue (start processing tasks)"""
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        queue_path = self._get_queue_path()
        self.client.resume_queue(name=queue_path)
        logger.info(f"Resumed queue: {queue_path}")

    async def purge_queue(self) -> None:
        """Purge all tasks from the queue"""
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        queue_path = self._get_queue_path()
        self.client.purge_queue(name=queue_path)
        logger.info(f"Purged queue: {queue_path}")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dict with queue stats (tasks count, dispatches, etc.)
        """
        if not self.client:
            raise RuntimeError("Cloud Tasks client not initialized. Call initialize() first.")

        queue_path = self._get_queue_path()
        queue = self.client.get_queue(name=queue_path)

        return {
            'name': queue.name,
            'state': queue.state.name,
            'tasks_count': queue.stats.tasks_count if queue.stats else 0,
            'oldest_task_age': queue.stats.oldest_estimated_arrival_time if queue.stats else None,
            'rate_limits': {
                'max_dispatches_per_second': queue.rate_limits.max_dispatches_per_second,
                'max_concurrent_dispatches': queue.rate_limits.max_concurrent_dispatches,
            } if queue.rate_limits else None,
        }


# Singleton instance
_cloud_tasks_service: Optional[CloudTasksQueueService] = None


def get_cloud_tasks_service() -> CloudTasksQueueService:
    """Get or create singleton Cloud Tasks service instance"""
    global _cloud_tasks_service

    if _cloud_tasks_service is None:
        _cloud_tasks_service = CloudTasksQueueService()
        _cloud_tasks_service.initialize()

    return _cloud_tasks_service


def cleanup_cloud_tasks_service() -> None:
    """Cleanup singleton Cloud Tasks service instance"""
    global _cloud_tasks_service

    if _cloud_tasks_service is not None:
        _cloud_tasks_service.close()
        _cloud_tasks_service = None
