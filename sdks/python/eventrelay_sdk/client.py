from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel

from .models import (
    HealthResponse,
    TranscriptActionRequest,
    TranscriptActionResponse,
    VideoProcessingRequest,
    VideoProcessingResponse,
    VideoToSoftwareRequest,
    VideoToSoftwareResponse,
)


class EventRelayClient:
    """Small typed client for the EventRelay API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EventRelayClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, json: Optional[dict] = None) -> dict:
        response = self._client.request(method, path, json=json)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse(model: type[BaseModel], payload: dict) -> BaseModel:
        return model.model_validate(payload)

    def health(self) -> HealthResponse:
        data = self._request("GET", "/api/v1/health")
        return self._parse(HealthResponse, data)

    def transcript_action(
        self, request: TranscriptActionRequest
    ) -> TranscriptActionResponse:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        data = self._request("POST", "/api/v1/transcript-action", json=payload)
        return self._parse(TranscriptActionResponse, data)

    def video_to_software(
        self, request: VideoToSoftwareRequest
    ) -> VideoToSoftwareResponse:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        data = self._request("POST", "/api/v1/video-to-software", json=payload)
        return self._parse(VideoToSoftwareResponse, data)

    def process_video(
        self, request: VideoProcessingRequest
    ) -> VideoProcessingResponse:
        payload = request.model_dump(by_alias=True, exclude_none=True)
        data = self._request("POST", "/api/v1/process-video", json=payload)
        return self._parse(VideoProcessingResponse, data)
