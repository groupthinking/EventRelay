"""Video Pack identity: version + video_id → stable hash.

This is the immutable cite key for a YouTube video. Content extract
(Qwen / step 3) is a later versioned write, not a mutation of v0.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from youtube_extension.utils.video_utils import extract_video_id
from youtube_extension.videopack.schema import Provenance, Transcript, VideoPackV0
from youtube_extension.videopack.validate import validate_pack

if TYPE_CHECKING:
    from youtube_extension.videopack.store import VideoPackStore

IDENTITY_VERSION = "v0"


def identity_payload(video_id: str, version: str = IDENTITY_VERSION) -> dict[str, str]:
    return {"version": version, "video_id": video_id}


def identity_hash(video_id: str, version: str = IDENTITY_VERSION) -> str:
    encoded = json.dumps(
        identity_payload(video_id, version),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def resolve_video_id(url_or_id: str) -> str:
    return extract_video_id(url_or_id)


def build_identity_pack(
    video_id: str,
    source_url: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> VideoPackV0:
    created = created_at or datetime.now(timezone.utc)
    if source_url and source_url.startswith("http"):
        url = source_url
    else:
        url = f"https://www.youtube.com/watch?v={video_id}"
    pack = VideoPackV0(
        id=f"vp:{IDENTITY_VERSION}:{video_id}",
        video_id=video_id,
        source_url=url,
        transcript=Transcript(full_text=f"cite:youtube:{video_id}", segments=[]),
        provenance=Provenance(
            created_at=created,
            tool_versions={"videopack": IDENTITY_VERSION},
            source_hash=identity_hash(video_id, IDENTITY_VERSION),
            notes="Identity pack. Content extract is a later step.",
        ),
    )
    validate_pack(pack)
    return pack


def emit_video_pack(
    *,
    video_id: Optional[str] = None,
    video_url: Optional[str] = None,
    store: "VideoPackStore",
) -> VideoPackV0:
    resolved = video_id
    if not resolved and video_url:
        resolved = resolve_video_id(video_url)
    if not resolved:
        raise ValueError("Could not determine video_id")

    existing = store.get(resolved)
    if existing is not None:
        return existing

    pack = build_identity_pack(resolved, source_url=video_url)
    store.put(pack)
    return pack
