"""SC1 — input ingest & validation.

The one stage implemented in the skeleton, because it has no external
dependency and its acceptance test (valid->id, invalid->error) is unambiguous.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


class InvalidInput(ValueError):
    """Raised when a URL is not an acceptable YouTube video reference."""


_HOST_ALLOW = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(video_url: str) -> str:
    """Parse a YouTube URL and return its canonical 11-char video id.

    Raises InvalidInput for anything that is not a supported YouTube video URL.
    """
    if not video_url or not isinstance(video_url, str):
        raise InvalidInput("video_url is required")

    parsed = urlparse(video_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise InvalidInput("video_url must be an http(s) URL")
    host = (parsed.hostname or "").lower()
    if host not in _HOST_ALLOW:
        raise InvalidInput(f"unsupported host: {host or '(none)'}")

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/")
    elif parsed.path == "/watch":
        candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    elif parsed.path.startswith(("/embed/", "/shorts/", "/v/")):
        candidate = parsed.path.split("/", 2)[2]
    else:
        raise InvalidInput("could not locate a video id in the URL")

    candidate = candidate.split("&", 1)[0]
    if not _ID_RE.match(candidate):
        raise InvalidInput("video id is not a valid 11-character YouTube id")
    return candidate
