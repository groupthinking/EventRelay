#!/usr/bin/env python3
"""
Firestore State Service
=======================

Manages shared state across pipeline stages using Google Cloud Firestore.
Replaces in-memory caching for cloud-native, scalable deployment.
"""

import asyncio
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1 import AsyncClient
    FIRESTORE_AVAILABLE = True
except ImportError:
    firestore = None
    AsyncClient = None
    FIRESTORE_AVAILABLE = False
    logging.warning("Firestore not available - install: pip install google-cloud-firestore")


logger = logging.getLogger(__name__)

# Size of the worker pool that drains expired documents in cleanup_old_states().
# Cleanup can match an unbounded number of documents, so deletes are pulled from
# a shared iterator by this many workers rather than dispatched all at once.
# Both controls are configurable so operators can tune cleanup independently of
# an application deployment; invalid numeric values fail fast during startup.
CLEANUP_DELETE_CONCURRENCY = max(
    1, int(os.getenv("CLEANUP_DELETE_CONCURRENCY", "16"))
)
CLEANUP_DELETE_TIMEOUT_SECONDS = max(
    0.001, float(os.getenv("CLEANUP_DELETE_TIMEOUT_SECONDS", "30"))
)


@dataclass
class VideoProcessingState:
    """State container for video processing pipeline"""
    video_id: str
    video_url: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    current_stage: str  # 'metadata', 'transcript', 'analysis', 'complete'
    metadata: Optional[dict[str, Any]] = None
    transcript: Optional[dict[str, Any]] = None
    ai_analysis: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    processing_time: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Firestore storage"""
        data = asdict(self)
        # Ensure timestamps are properly formatted
        if not data.get('created_at'):
            data['created_at'] = datetime.now(timezone.utc).isoformat()
        data['updated_at'] = datetime.now(timezone.utc).isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'VideoProcessingState':
        """Create from Firestore dictionary"""
        return cls(**data)


class FirestoreStateService:
    """
    Service for managing video processing state in Firestore.

    Provides:
    - Shared state across Cloud Run instances
    - Persistent pipeline state tracking
    - Concurrent access control
    - State history and recovery
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = "video_processing_state",
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """
        Initialize Firestore state service.

        Args:
            project_id: GCP project ID (defaults to env GOOGLE_CLOUD_PROJECT)
            collection_name: Firestore collection name
            enable_cache: Enable local caching for recent states
            cache_ttl: Cache TTL in seconds
        """
        if not FIRESTORE_AVAILABLE:
            raise ImportError(
                "Firestore not available. Install: pip install google-cloud-firestore"
            )

        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.collection_name = collection_name
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl

        # Initialize Firestore client
        self.db: Optional[AsyncClient] = None
        self._local_cache: dict[str, VideoProcessingState] = {}
        self._cache_timestamps: dict[str, datetime] = {}

        logger.info(
            f"FirestoreStateService initialized: "
            f"project={self.project_id}, collection={self.collection_name}"
        )

    async def initialize(self) -> None:
        """Initialize async Firestore client"""
        if not self.db:
            self.db = firestore.AsyncClient(project=self.project_id)
            logger.info("Firestore async client initialized")

    async def close(self) -> None:
        """Close Firestore client connection"""
        if self.db:
            await self.db.close()
            self.db = None
            logger.info("Firestore client closed")

    def _get_collection(self):
        """Get Firestore collection reference"""
        if not self.db:
            raise RuntimeError("Firestore client not initialized. Call initialize() first.")
        return self.db.collection(self.collection_name)

    def _is_cache_valid(self, video_id: str) -> bool:
        """Check if local cache entry is still valid"""
        if not self.enable_cache or video_id not in self._cache_timestamps:
            return False

        age = (datetime.now(timezone.utc) - self._cache_timestamps[video_id]).total_seconds()
        return age < self.cache_ttl

    async def create_state(self, video_id: str, video_url: str) -> VideoProcessingState:
        """
        Create new processing state for a video.

        Args:
            video_id: YouTube video ID
            video_url: Full YouTube URL

        Returns:
            VideoProcessingState: New state object
        """
        state = VideoProcessingState(
            video_id=video_id,
            video_url=video_url,
            status='pending',
            current_stage='metadata',
            created_at=datetime.now(timezone.utc).isoformat()
        )

        # Save to Firestore
        collection = self._get_collection()
        await collection.document(video_id).set(state.to_dict())

        # Update local cache
        if self.enable_cache:
            self._local_cache[video_id] = state
            self._cache_timestamps[video_id] = datetime.now(timezone.utc)

        logger.info(f"Created processing state for video: {video_id}")
        return state

    async def get_state(self, video_id: str) -> Optional[VideoProcessingState]:
        """
        Get current processing state for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoProcessingState or None if not found
        """
        # Check local cache first
        if self._is_cache_valid(video_id):
            logger.debug(f"Cache hit for video state: {video_id}")
            return self._local_cache[video_id]

        # Fetch from Firestore
        collection = self._get_collection()
        doc = await collection.document(video_id).get()

        if not doc.exists:
            logger.warning(f"No state found for video: {video_id}")
            return None

        state = VideoProcessingState.from_dict(doc.to_dict())

        # Update cache
        if self.enable_cache:
            self._local_cache[video_id] = state
            self._cache_timestamps[video_id] = datetime.now(timezone.utc)

        logger.debug(f"Retrieved state for video: {video_id}")
        return state

    async def update_state(
        self,
        video_id: str,
        status: Optional[str] = None,
        current_stage: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        transcript: Optional[dict[str, Any]] = None,
        ai_analysis: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> VideoProcessingState:
        """
        Update processing state for a video.

        Args:
            video_id: YouTube video ID
            status: New status
            current_stage: New pipeline stage
            metadata: Video metadata
            transcript: Video transcript data
            ai_analysis: AI analysis results
            error_message: Error message if failed
            processing_time: Total processing time

        Returns:
            Updated VideoProcessingState
        """
        # Get current state
        state = await self.get_state(video_id)
        if not state:
            raise ValueError(f"No state found for video: {video_id}")

        # Update fields
        if status is not None:
            state.status = status
        if current_stage is not None:
            state.current_stage = current_stage
        if metadata is not None:
            state.metadata = metadata
        if transcript is not None:
            state.transcript = transcript
        if ai_analysis is not None:
            state.ai_analysis = ai_analysis
        if error_message is not None:
            state.error_message = error_message
        if processing_time is not None:
            state.processing_time = processing_time

        # Save to Firestore
        collection = self._get_collection()
        await collection.document(video_id).update(state.to_dict())

        # Update cache
        if self.enable_cache:
            self._local_cache[video_id] = state
            self._cache_timestamps[video_id] = datetime.now(timezone.utc)

        logger.info(
            f"Updated state for video {video_id}: "
            f"status={status}, stage={current_stage}"
        )
        return state

    async def delete_state(self, video_id: str) -> None:
        """
        Delete processing state for a video.

        Args:
            video_id: YouTube video ID
        """
        collection = self._get_collection()
        await collection.document(video_id).delete()

        # Remove from cache
        self._local_cache.pop(video_id, None)
        self._cache_timestamps.pop(video_id, None)

        logger.info(f"Deleted state for video: {video_id}")

    async def list_states(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[VideoProcessingState]:
        """
        List processing states with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of VideoProcessingState objects
        """
        collection = self._get_collection()
        query = collection

        if status:
            query = query.where('status', '==', status)

        query = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)

        docs = await query.get()
        states = [VideoProcessingState.from_dict(doc.to_dict()) for doc in docs]

        logger.info(f"Listed {len(states)} states (status={status}, limit={limit})")
        return states

    async def cleanup_old_states(self, days: int = 7) -> int:
        """
        Clean up old processing states.

        Args:
            days: Delete states older than this many days

        Returns:
            Number of states deleted
        """
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        collection = self._get_collection()

        # Query old states
        query = collection.where('created_at', '<', cutoff_date)
        docs = await query.get()

        if not docs:
            logger.info(f"Cleaned up 0 old states (>{days} days)")
            return 0

        # Delete with a fixed pool of workers pulling from a shared iterator.
        # Deleting sequentially made cleanup latency scale with the size of the
        # expired backlog. The pool overlaps up to CLEANUP_DELETE_CONCURRENCY
        # deletes at a time while keeping *both* the in-flight RPCs and the
        # number of pending task objects bounded -- gather() over every document
        # would allocate one task per document up front, which is unsafe for a
        # query whose result set has no limit. Failures are tallied rather than
        # raised so one bad delete cannot abandon the rest of the backlog.
        pending = iter(docs)
        succeeded = 0
        failures: list[Exception] = []

        async def _delete_worker() -> None:
            nonlocal succeeded
            while True:
                try:
                    doc = next(pending)
                except StopIteration:
                    return
                try:
                    await doc.reference.delete(timeout=CLEANUP_DELETE_TIMEOUT_SECONDS)
                    succeeded += 1
                except Exception as exc:  # noqa: BLE001 - tallied and logged below
                    failures.append(exc)

        await asyncio.gather(
            *(
                _delete_worker()
                for _ in range(min(CLEANUP_DELETE_CONCURRENCY, len(docs)))
            )
        )

        count = succeeded

        if failures:
            logger.warning(
                f"Failed to delete {len(failures)} of {len(docs)} old states; "
                f"first error: {failures[0]!r}"
            )

        logger.info(f"Cleaned up {count} old states (>{days} days)")
        return count


# Singleton instance
_firestore_service: Optional[FirestoreStateService] = None


async def get_firestore_service() -> FirestoreStateService:
    """Get or create singleton Firestore service instance"""
    global _firestore_service

    if _firestore_service is None:
        _firestore_service = FirestoreStateService()
        await _firestore_service.initialize()

    return _firestore_service


async def cleanup_firestore_service() -> None:
    """Cleanup singleton Firestore service instance"""
    global _firestore_service

    if _firestore_service is not None:
        await _firestore_service.close()
        _firestore_service = None
