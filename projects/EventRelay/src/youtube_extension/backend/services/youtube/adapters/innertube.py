"""Innertube transcript retrieval utilities."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from html import unescape
from typing import Iterable, List, Optional
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

_API_KEY_PATTERN = re.compile(r'"INNERTUBE_API_KEY":"(?P<key>[^"]+)"')
_ANDROID_HEADERS = {
    "user-agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 10)",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "accept-encoding": "identity",
}


class InnertubeTranscriptError(RuntimeError):
    """Base error for Innertube transcript failures."""


class InnertubeTranscriptNotFound(InnertubeTranscriptError):
    """Raised when no caption tracks are available for the requested language."""


@dataclass
class CaptionSegment:
    """Normalized caption segment."""

    text: str
    start: float
    duration: float


async def fetch_innertube_transcript(
    video_id: str,
    language: str = "en",
    client: Optional[httpx.AsyncClient] = None,
) -> List[CaptionSegment]:
    """Retrieve captions via the Innertube player endpoint.

    Args:
        video_id: YouTube video identifier.
        language: Desired caption language (ISO code).
        client: Optional shared ``httpx.AsyncClient``.

    Returns:
        Ordered list of ``CaptionSegment`` entries.

    Raises:
        InnertubeTranscriptError: On fetch or parsing issues.
        InnertubeTranscriptNotFound: When captions exist but not in the requested language.
    """

    if not video_id:
        raise ValueError("video_id is required for Innertube transcript fetch")

    close_client = False
    session = client
    if session is None:
        session = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        html = await _fetch_watch_page(session, video_id)
        api_key = _extract_api_key(html)
        if not api_key:
            raise InnertubeTranscriptError("INNERTUBE_API_KEY not found in watch page")

        player_response = await _fetch_player_response(session, video_id, api_key)
        caption_url = _select_caption_track(player_response, language)
        if not caption_url:
            raise InnertubeTranscriptNotFound(
                f"No captions available for language '{language}'"
            )

        xml_text = await _fetch_caption_xml(session, caption_url)
        segments = parse_transcript_xml(xml_text)
        if not segments:
            raise InnertubeTranscriptError("Caption XML parsed but contained no segments")

        logger.info(
            "🎞️ Innertube transcript fetched for %s (%d segments)",
            video_id,
            len(segments),
        )
        return segments
    except InnertubeTranscriptError:
        raise
    except Exception as exc:  # noqa: BLE001 - log unexpected errors
        raise InnertubeTranscriptError(str(exc)) from exc
    finally:
        if close_client:
            await session.aclose()


async def _fetch_watch_page(client: httpx.AsyncClient, video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    response = await client.get(url, headers=_ANDROID_HEADERS)
    response.raise_for_status()
    return response.text


def _extract_api_key(html: str) -> Optional[str]:
    match = _API_KEY_PATTERN.search(html)
    return match.group("key") if match else None


async def _fetch_player_response(
    client: httpx.AsyncClient, video_id: str, api_key: str
) -> dict:
    endpoint = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.38",
                "hl": "en",
                "gl": "US",
            }
        },
        "videoId": video_id,
    }

    response = await client.post(
        endpoint,
        headers={"content-type": "application/json", **_ANDROID_HEADERS},
        content=json.dumps(payload),
    )
    response.raise_for_status()
    return response.json()


def _select_caption_track(player_response: dict, language: str) -> Optional[str]:
    tracks = (
        player_response.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )

    if not tracks:
        return None

    track = next((t for t in tracks if t.get("languageCode") == language), None)
    if track is None:
        track = tracks[0]

    base_url = track.get("baseUrl")
    if not base_url:
        return None

    return re.sub(r"&fmt=\w+$", "", base_url)


async def _fetch_caption_xml(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url, headers={**_ANDROID_HEADERS, "accept": "application/xml"})
    response.raise_for_status()
    return response.text


def parse_transcript_xml(xml_text: str) -> List[CaptionSegment]:
    """Convert YouTube XML transcript into ``CaptionSegment`` entries."""

    if not xml_text.strip():
        return []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:  # pragma: no cover - invalid XML is rare
        logger.warning("Failed to parse caption XML: %s", exc)
        return []

    segments: List[CaptionSegment] = []
    for node in root.findall("text"):
        raw_text = node.text or ""
        text = _normalize_caption_text(raw_text)
        start = _safe_float(node.attrib.get("start"))
        duration = _safe_float(node.attrib.get("dur"))
        segments.append(CaptionSegment(text=text, start=start, duration=duration))

    return segments


def _normalize_caption_text(text: str) -> str:
    return unescape(text.replace("\n", " ").strip())


def _safe_float(value: Optional[str]) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def sync_fetch_innertube_transcript(video_id: str, language: str = "en") -> List[CaptionSegment]:
    """Synchronous helper for contexts without an event loop."""

    return asyncio.run(fetch_innertube_transcript(video_id, language))


__all__ = [
    "CaptionSegment",
    "InnertubeTranscriptError",
    "InnertubeTranscriptNotFound",
    "fetch_innertube_transcript",
    "parse_transcript_xml",
    "sync_fetch_innertube_transcript",
]
