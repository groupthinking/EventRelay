"""Videos resource — process YouTube videos and manage the video library."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..types import VideoJobStatusResponse, VideoProcessJobRequest, VideoProcessJobResponse

if TYPE_CHECKING:
    import httpx


class VideosResource:
    """Synchronous videos resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def process(
        self,
        video_url: str,
        *,
        language: str = "en",
        options: Optional[dict[str, Any]] = None,
    ) -> VideoProcessJobResponse:
        """Submit a YouTube video for async processing.

        Args:
            video_url: Full YouTube video URL.
            language: Transcript language code (default ``"en"``).
            options: Optional processing overrides.

        Returns:
            :class:`VideoProcessJobResponse` containing the ``job_id``.
        """
        payload = VideoProcessJobRequest(
            video_url=video_url, language=language, options=options or {}
        )
        response = self._client._post(
            "/api/v1/videos/process", json=payload.model_dump()
        )
        return VideoProcessJobResponse.model_validate(response)

    def get_status(self, *, job_id: str) -> VideoJobStatusResponse:
        """Poll processing status for a given job.

        Args:
            job_id: The ``job_id`` returned by :meth:`process`.

        Returns:
            :class:`VideoJobStatusResponse` with current status and progress.
        """
        response = self._client._get(f"/api/v1/videos/{job_id}/status")
        return VideoJobStatusResponse.model_validate(response)

    def list(self) -> list[dict[str, Any]]:
        """List all processed videos in the library."""
        return self._client._get("/api/v1/videos")  # type: ignore[return-value]

    def retrieve(self, video_id: str) -> dict[str, Any]:
        """Retrieve metadata for a single video.

        Args:
            video_id: YouTube video ID (11-character string).
        """
        return self._client._get(f"/api/v1/videos/{video_id}")  # type: ignore[return-value]

    def delete(self, video_id: str) -> dict[str, Any]:
        """Remove a processed video from the cache.

        Args:
            video_id: YouTube video ID.
        """
        return self._client._delete(f"/api/v1/cache/{video_id}")  # type: ignore[return-value]


class AsyncVideosResource:
    """Asynchronous videos resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def process(
        self,
        video_url: str,
        *,
        language: str = "en",
        options: Optional[dict[str, Any]] = None,
    ) -> VideoProcessJobResponse:
        """Async version of :meth:`VideosResource.process`."""
        payload = VideoProcessJobRequest(
            video_url=video_url, language=language, options=options or {}
        )
        response = await self._client._post(
            "/api/v1/videos/process", json=payload.model_dump()
        )
        return VideoProcessJobResponse.model_validate(response)

    async def get_status(self, *, job_id: str) -> VideoJobStatusResponse:
        """Async version of :meth:`VideosResource.get_status`."""
        response = await self._client._get(f"/api/v1/videos/{job_id}/status")
        return VideoJobStatusResponse.model_validate(response)

    async def list(self) -> list[dict[str, Any]]:
        """Async version of :meth:`VideosResource.list`."""
        return await self._client._get("/api/v1/videos")  # type: ignore[return-value]

    async def retrieve(self, video_id: str) -> dict[str, Any]:
        """Async version of :meth:`VideosResource.retrieve`."""
        return await self._client._get(f"/api/v1/videos/{video_id}")  # type: ignore[return-value]

    async def delete(self, video_id: str) -> dict[str, Any]:
        """Async version of :meth:`VideosResource.delete`."""
        return await self._client._delete(f"/api/v1/cache/{video_id}")  # type: ignore[return-value]
