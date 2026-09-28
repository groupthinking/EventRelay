"""Upstash REST Video Pack store — same keys as apps/web video-pack-store.ts."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from youtube_extension.videopack.credentials import UpstashRestCredentials
from youtube_extension.videopack.identity import identity_hash
from youtube_extension.videopack.schema import VideoPackV0

logger = logging.getLogger(__name__)

VIDEO_PACK_STORE_VERSION = "v0"
VIDEO_PACK_STORE_PREFIX = f"er:videopack:{VIDEO_PACK_STORE_VERSION}:"


def pack_store_key(source_hash: str) -> str:
    return f"{VIDEO_PACK_STORE_PREFIX}{source_hash}"


class UpstashRestVideoPackStore:
    """Read/write VideoPack rows in Upstash using the web app's key schema."""

    def __init__(self, credentials: UpstashRestCredentials) -> None:
        self._credentials = credentials

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._credentials.token}"}

    def _pipeline(self, *command: str) -> Any:
        url = self._credentials.url
        headers = {**self._headers(), "Content-Type": "application/json"}
        body = json.dumps(list(command))
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            response = client.post(url, headers=headers, content=body)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                if first.get("error"):
                    raise RuntimeError(str(first["error"]))
                return first.get("result")
        return payload

    def _get_raw(self, source_hash: str) -> Any:
        try:
            return self._pipeline("GET", pack_store_key(source_hash))
        except httpx.HTTPError as exc:
            logger.error(
                "Upstash video pack GET failed for hash=%s: %s",
                source_hash[:8],
                exc,
                exc_info=True,
            )
            raise

    @staticmethod
    def _decode_record(raw: Any) -> Optional[dict[str, Any]]:
        decoded: Any = raw
        for _ in range(2):
            if decoded is None:
                return None
            if isinstance(decoded, str):
                try:
                    decoded = json.loads(decoded)
                except json.JSONDecodeError:
                    return None
                continue
            break
        if not isinstance(decoded, dict):
            return None
        return decoded

    @staticmethod
    def _pack_from_record(record: dict[str, Any]) -> Optional[VideoPackV0]:
        if record.get("state") != "ready":
            return None
        pack = record.get("pack")
        if not isinstance(pack, dict):
            return None
        try:
            return VideoPackV0.model_validate(pack)
        except Exception as exc:
            logger.warning("Invalid ready pack in Upstash record: %s", exc)
            return None

    def get(self, video_id: str) -> Optional[VideoPackV0]:
        source_hash = identity_hash(video_id)
        raw = self._get_raw(source_hash)
        record = self._decode_record(raw)
        if not record:
            return None
        return self._pack_from_record(record)

    def put(self, pack: VideoPackV0) -> None:
        source_hash = pack.provenance.source_hash
        record = {
            "state": "ready",
            "pack": pack.model_dump(mode="json"),
        }
        encoded = json.dumps(record, separators=(",", ":"), sort_keys=True)
        try:
            self._pipeline("SET", pack_store_key(source_hash), encoded)
        except httpx.HTTPError as exc:
            logger.error(
                "Upstash video pack SET failed for video_id=%s: %s",
                pack.video_id,
                exc,
                exc_info=True,
            )
            raise
