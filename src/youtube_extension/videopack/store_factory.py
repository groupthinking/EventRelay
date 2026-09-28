"""Select the canonical Video Pack store for this process."""

from __future__ import annotations

import logging
from pathlib import Path

from youtube_extension.videopack.credentials import (
    filesystem_store_explicitly_allowed,
    is_production_runtime,
    resolve_upstash_redis_credentials,
)
from youtube_extension.videopack.store import VideoPackStore
from youtube_extension.videopack.upstash_rest_store import UpstashRestVideoPackStore

logger = logging.getLogger(__name__)

_DEFAULT_FS_ROOT = Path("storage/video_packs")

def get_video_pack_store(
    *,
    filesystem_root: Path | None = None,
) -> VideoPackStore | UpstashRestVideoPackStore:
    """
    Production uses Upstash REST only (same keys as apps/web).
    Filesystem storage is opt-in for local dev via VIDEO_PACK_FILESYSTEM_STORE=1.
    """
    creds = resolve_upstash_redis_credentials()
    if creds:
        return UpstashRestVideoPackStore(creds)

    if is_production_runtime():
        raise RuntimeError(
            "Durable video pack storage is not configured in production. "
            "Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN "
            "(or KV_REST_API_URL + KV_REST_API_TOKEN)."
        )

    if filesystem_store_explicitly_allowed():
        root = filesystem_root or _DEFAULT_FS_ROOT
        logger.warning(
            "Using filesystem Video Pack store at %s (dev-only; not canonical in prod)",
            root,
        )
        return VideoPackStore(root)

    raise RuntimeError(
        "Video Pack store unavailable: configure Upstash REST credentials or set "
        "VIDEO_PACK_FILESYSTEM_STORE=1 for explicit local filesystem dev mode."
    )
