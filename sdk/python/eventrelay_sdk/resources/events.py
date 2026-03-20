"""Events resource — extract structured events from transcripts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..types import EventExtractRequest, EventExtractResponse

if TYPE_CHECKING:
    pass


class EventsResource:
    """Synchronous events resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def extract(
        self,
        *,
        transcript: Optional[str] = None,
        job_id: Optional[str] = None,
        video_url: Optional[str] = None,
    ) -> EventExtractResponse:
        """Extract structured events from a transcript.

        Provide at least one of ``transcript``, ``job_id``, or ``video_url``.

        Args:
            transcript: Raw transcript text to extract events from.
            job_id: Job ID of a previously processed video whose transcript
                will be retrieved from the backend.
            video_url: YouTube URL — the backend will fetch the transcript.

        Returns:
            :class:`EventExtractResponse` containing a list of
            :class:`ExtractedEvent` objects.
        """
        payload = EventExtractRequest(
            transcript=transcript, job_id=job_id, video_url=video_url
        )
        response = self._client._post(
            "/api/v1/events/extract", json=payload.model_dump(exclude_none=True)
        )
        return EventExtractResponse.model_validate(response)


class AsyncEventsResource:
    """Asynchronous events resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def extract(
        self,
        *,
        transcript: Optional[str] = None,
        job_id: Optional[str] = None,
        video_url: Optional[str] = None,
    ) -> EventExtractResponse:
        """Async version of :meth:`EventsResource.extract`."""
        payload = EventExtractRequest(
            transcript=transcript, job_id=job_id, video_url=video_url
        )
        response = await self._client._post(
            "/api/v1/events/extract", json=payload.model_dump(exclude_none=True)
        )
        return EventExtractResponse.model_validate(response)
