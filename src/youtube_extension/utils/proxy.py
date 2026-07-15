"""
Proxy Utilities
===============

Central helpers for routing YouTube traffic (yt-dlp, youtube-transcript-api)
through a Webshare residential proxy configured via ``WEBSHARE_PROXY_URL``.

When the environment variable is unset or malformed, all helpers return
``None`` so callers gracefully fall back to direct connections.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Any

try:  # pragma: no cover - optional dependency
    from youtube_transcript_api.proxies import GenericProxyConfig

    HAS_PROXY_CONFIG = True
except ImportError:  # pragma: no cover - import guard
    GenericProxyConfig = None  # type: ignore[assignment,misc]
    HAS_PROXY_CONFIG = False

logger = logging.getLogger(__name__)

_PROXY_ENV_VAR = "WEBSHARE_PROXY_URL"


def get_proxy_url() -> str | None:
    """Return the validated Webshare proxy URL, or None for direct connection."""
    url = os.getenv(_PROXY_ENV_VAR, "").strip()
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https", "socks5") or not parsed.hostname:
        logger.warning(
            "%s is set but malformed — falling back to direct connection",
            _PROXY_ENV_VAR,
        )
        return None
    return url


def get_proxy_dict() -> dict[str, str] | None:
    """Return a requests-style proxies dict covering http and https, or None."""
    url = get_proxy_url()
    if not url:
        return None
    return {"http": url, "https": url}


def get_transcript_proxy_config() -> Any | None:
    """Return a youtube-transcript-api proxy config object, or None."""
    url = get_proxy_url()
    if not url:
        return None
    if not HAS_PROXY_CONFIG:
        logger.warning(
            "%s is set but youtube-transcript-api proxy support is unavailable "
            "(requires youtube-transcript-api>=1.0) — falling back to direct connection",
            _PROXY_ENV_VAR,
        )
        return None
    return GenericProxyConfig(http_url=url, https_url=url)


def redact_proxy_credentials(text: str) -> str:
    """Strip user:pass credentials of the configured proxy URL from text."""
    url = os.getenv(_PROXY_ENV_VAR, "").strip()
    if not url or url not in text:
        return text
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        redacted = parsed._replace(netloc=netloc).geturl()
    except (ValueError, AttributeError):
        redacted = "<proxy-url>"
    return text.replace(url, redacted)
