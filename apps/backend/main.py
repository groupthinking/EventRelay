"""Lean Vercel service for verified YouTube caption acquisition.

The workstation backend includes video, ML, cloud, and computer-vision extras
that exceed Vercel's function bundle limit.  This service intentionally exposes
only the production boundary used by the web workflow: health and evidence-
preserving YouTube caption acquisition.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import re
import time
from typing import Annotated, Any
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?$")


class CaptionTransportConfigurationError(RuntimeError):
    """Raised when a configured hosted caption transport is incomplete or invalid."""


def _caption_transport() -> tuple[Any | None, str]:
    """Return the configured transcript proxy and a non-sensitive transport name.

    Webshare's username/password form is preferred because its SDK integration
    automatically uses the rotating residential endpoint. ``WEBSHARE_PROXY_URL``
    remains supported for the repository's existing deployment contract and
    for other rotating HTTP(S) proxy providers.
    """

    username = os.getenv("WEBSHARE_PROXY_USERNAME", "").strip()
    password = os.getenv("WEBSHARE_PROXY_PASSWORD", "").strip()
    proxy_url = os.getenv("WEBSHARE_PROXY_URL", "").strip()

    if username or password:
        if not username or not password:
            raise CaptionTransportConfigurationError(
                "Both Webshare proxy credentials must be configured"
            )
        return (
            WebshareProxyConfig(
                proxy_username=username,
                proxy_password=password,
                filter_ip_locations=["us"],
            ),
            "webshare_residential",
        )

    if proxy_url:
        try:
            parsed = urlparse(proxy_url)
            port = parsed.port
        except ValueError as exc:
            raise CaptionTransportConfigurationError(
                "Caption proxy URL is invalid"
            ) from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not port:
            raise CaptionTransportConfigurationError(
                "Caption proxy URL must be an HTTP(S) URL with a host and port"
            )
        return (
            GenericProxyConfig(http_url=proxy_url, https_url=proxy_url),
            "rotating_residential_proxy",
        )

    return None, "direct"


def _caption_transport_readiness() -> dict[str, Any]:
    """Describe transport readiness without exposing proxy credentials."""

    try:
        _proxy_config, transport = _caption_transport()
    except CaptionTransportConfigurationError:
        return {
            "transport": "invalid_proxy_configuration",
            "ready": False,
            "required": True,
        }

    hosted = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
    ready = transport != "direct" or not hosted
    return {
        "transport": transport,
        "ready": ready,
        "required": hosted,
    }


def extract_youtube_video_id(value: str) -> str:
    """Return an allowlisted YouTube id without fetching the supplied URL."""

    try:
        parsed = urlparse(value)
    except ValueError as exc:
        raise ValueError("Invalid YouTube URL") from exc

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("YouTube URL must use http or https")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_YOUTUBE_HOSTS:
        raise ValueError("Only YouTube URLs are supported")
    if parsed.username or parsed.password or parsed.port not in {None, 80, 443}:
        raise ValueError("YouTube URL contains unsupported authority data")

    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/", 1)[0]
    elif parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    else:
        parts = [part for part in parsed.path.split("/") if part]
        candidate = (
            parts[1]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}
            else ""
        )

    if not VIDEO_ID_PATTERN.fullmatch(candidate):
        raise ValueError("YouTube URL does not contain a valid video id")
    return candidate


class TranscriptActionRequest(BaseModel):
    video_url: str = Field(min_length=10, max_length=2048)
    language: str = Field(default="en", min_length=2, max_length=12)

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, value: str) -> str:
        extract_youtube_video_id(value)
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if not LANGUAGE_PATTERN.fullmatch(value):
            raise ValueError("Invalid transcript language")
        return value


def _fetch_captions(video_id: str, language: str) -> list[dict[str, Any]]:
    languages = list(dict.fromkeys([language, language.split("-", 1)[0], "en"]))
    proxy_config, _transport = _caption_transport()
    api = YouTubeTranscriptApi(proxy_config=proxy_config)
    fetched = api.fetch(video_id, languages=languages)
    raw = fetched.to_raw_data()
    return [
        {
            "text": str(item.get("text") or "").strip(),
            "start": max(0.0, float(item.get("start") or 0.0)),
            "duration": max(0.0, float(item.get("duration") or 0.0)),
        }
        for item in raw
        if str(item.get("text") or "").strip()
    ]


def _require_api_key(provided: str | None) -> None:
    expected = os.getenv("EVENTRELAY_API_KEY", "").strip()
    if expected and not hmac.compare_digest(provided or "", expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(
    title="UVAI Caption Evidence Service",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, Any]:
    readiness = _caption_transport_readiness()
    return {
        "status": "healthy" if readiness["ready"] else "degraded",
        "service": "uvai-caption-evidence",
        "auth_mode": "api_key"
        if os.getenv("EVENTRELAY_API_KEY")
        else "service_binding",
        "video_path_ready": readiness["ready"],
        "caption_transport": readiness["transport"],
        "caption_transport_required": readiness["required"],
    }


@app.post("/api/v1/transcript-action")
async def transcript_action(
    payload: TranscriptActionRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> dict[str, Any]:
    _require_api_key(x_api_key)
    started = time.perf_counter()
    video_id = extract_youtube_video_id(payload.video_url)
    transport_readiness = _caption_transport_readiness()

    if not transport_readiness["ready"]:
        return {
            "success": False,
            "video_url": payload.video_url,
            "metadata": {
                "video_id": video_id,
                "caption_transport": transport_readiness["transport"],
            },
            "transcript": {
                "text": "",
                "segments": [],
                "source": "unavailable",
                "error": "Hosted caption transport is not configured.",
            },
            "outputs": {},
            "errors": [
                "A rotating residential caption transport is required in this environment."
            ],
            "orchestration_meta": {
                "processing_time": round(time.perf_counter() - started, 4),
                "agents_used": [],
            },
        }

    try:
        segments = await asyncio.wait_for(
            asyncio.to_thread(_fetch_captions, video_id, payload.language),
            timeout=20,
        )
    except (
        Exception
    ) as exc:  # provider failures are evidence failures, not fabricated text
        return {
            "success": False,
            "video_url": payload.video_url,
            "metadata": {
                "video_id": video_id,
                "caption_transport": transport_readiness["transport"],
            },
            "transcript": {
                "text": "",
                "segments": [],
                "source": "unavailable",
                "error": f"Caption acquisition failed: {type(exc).__name__}",
            },
            "outputs": {},
            "errors": ["Verified YouTube captions were unavailable."],
            "orchestration_meta": {
                "processing_time": round(time.perf_counter() - started, 4),
                "agents_used": [],
            },
        }

    transcript = " ".join(segment["text"] for segment in segments).strip()
    success = len(transcript) >= 40 and bool(segments)
    return {
        "success": success,
        "video_url": payload.video_url,
        "metadata": {
            "video_id": video_id,
            "caption_transport": transport_readiness["transport"],
        },
        "transcript": {
            "text": transcript if success else "",
            "segments": segments if success else [],
            "source": "youtube_transcript_api" if success else "unavailable",
        },
        "outputs": {},
        "errors": []
        if success
        else ["Verified YouTube captions were empty or too short."],
        "orchestration_meta": {
            "processing_time": round(time.perf_counter() - started, 4),
            "agents_used": ["caption-acquisition"] if success else [],
        },
    }
