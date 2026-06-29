"""Transcript resource — run transcript-action workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..types import TranscriptActionRequest, TranscriptActionResponse

if TYPE_CHECKING:
    pass


class TranscriptResource:
    """Synchronous transcript resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def action(
        self,
        video_url: str,
        *,
        action: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> TranscriptActionResponse:
        """Run the transcript-action workflow for a YouTube video.

        Args:
            video_url: YouTube video URL.
            action: Specific action to perform on the transcript.
            options: Additional processing options.

        Returns:
            :class:`TranscriptActionResponse` with transcript and actions.
        """
        payload = TranscriptActionRequest(
            video_url=video_url,
            video_options=options or None,
        )
        response = self._client._post(
            "/api/v1/transcript-action",
            json=payload.model_dump(exclude_none=True),
        )
        return TranscriptActionResponse.model_validate(response)


class AsyncTranscriptResource:
    """Asynchronous transcript resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def action(
        self,
        video_url: str,
        *,
        action: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> TranscriptActionResponse:
        """Async version of :meth:`TranscriptResource.action`."""
        payload = TranscriptActionRequest(
            video_url=video_url,
            video_options=options or None,
        )
        response = await self._client._post(
            "/api/v1/transcript-action",
            json=payload.model_dump(exclude_none=True),
        )
        return TranscriptActionResponse.model_validate(response)
