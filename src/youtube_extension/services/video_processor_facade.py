"""Single entry point for video processing backends (Phase 6 consolidation hook)."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class VideoProcessorBackend(Protocol):
    async def process_video(self, video_url: str) -> dict[str, Any]: ...


class VideoProcessorFacade:
    """Routes processing to the configured backend without duplicating orchestration."""

    def __init__(self, backend: VideoProcessorBackend) -> None:
        self._backend = backend

    async def process(self, video_url: str) -> dict[str, Any]:
        logger.info("VideoProcessorFacade dispatch for %s", video_url)
        return await self._backend.process_video(video_url)
