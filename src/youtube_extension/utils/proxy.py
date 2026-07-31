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
import re
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

_ALLOWED_SCHEMES = ("http", "https", "socks5", "socks5h")

# Matches the ``user[:password]@`` userinfo segment of any URL.
#
# The classes exclude whitespace, "/", "?" and "#" -- the delimiters that end a
# URL authority -- so a path, query, or fragment containing "@" (e.g.
# "https://example.com/a@b" or "https://example.com?e=a@b") is never mistaken
# for credentials, and a match can never span from one URL into the next.
#
# They deliberately *permit* a literal "@". Because the classes are greedy, the
# engine backtracks to the LAST "@" inside the authority, so an unencoded "@"
# in the password ("http://user:pa@ss@host") is consumed whole instead of the
# match stopping at the first separator and leaving the password tail behind.
#
# The user may be empty so credentials with no username ("http://:pass@host")
# are still redacted.
_USERINFO_RE = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)"
    r"(?P<user>[^\s/:?#]*)"
    r"(?::(?P<password>[^\s/?#]*))?"
    r"@"
)

_REDACTED = "***"

# Returned when the input cannot be stringified, or when redaction itself
# fails. Both are fail-closed: emitting a fixed placeholder is preferable to
# raising (which would mask the original error) or to returning text we cannot
# guarantee is clean (which could leak the credential we are trying to strip).
_UNPRINTABLE = "<unprintable error>"
_REDACTION_FAILED = "<redaction failed>"


def get_proxy_url() -> str | None:
    """Return the validated Webshare proxy URL, or None for direct connection.

    Never raises and never emits the URL (which carries credentials) into logs.
    ``urllib.parse`` raises ``ValueError`` for several malformed inputs — an
    unterminated IPv6 literal at parse time, a non-numeric or out-of-range port
    when ``.port`` is read — so both are contained here rather than escaping to
    callers that would log the exception alongside the offending URL.
    """
    url = os.getenv(_PROXY_ENV_VAR, "").strip()
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        valid = parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.hostname)
        if valid:
            parsed.port  # noqa: B018 - validates the port, raises ValueError if bad
    except ValueError:
        valid = False
    if not valid:
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


def redact_proxy_credentials(text: Any) -> str:
    """Strip URL userinfo (``user:pass@``) from ``text``.

    Two passes, because either alone is insufficient:

    1. Exact replacement of the configured ``WEBSHARE_PROXY_URL`` — preserves
       the host so operators can still tell *which* proxy was in play.
    2. A generic ``scheme://user:pass@`` sweep — catches credentials that never
       match the env value verbatim: yt-dlp echoing a normalised/percent-encoded
       form back on stderr, a ``CalledProcessError`` repr of the argv, or a
       different proxy variable (``HTTPS_PROXY`` and friends) entirely.

    Always returns a string and never raises; it is called from exception
    handlers, where a failure would mask the original error. If ``text`` cannot
    be stringified (a ``__str__`` that itself raises) or redaction fails, a
    fixed non-sensitive placeholder is returned instead.
    """
    if isinstance(text, str):
        candidate = text
    else:
        try:
            candidate = str(text)
        except Exception:  # noqa: BLE001 - a hostile __str__ must not propagate
            return _UNPRINTABLE

    try:
        return _redact(candidate)
    except Exception:  # noqa: BLE001 - never return text we cannot vouch for
        return _REDACTION_FAILED


def _redact(text: str) -> str:
    """Run the two redaction passes over an already-stringified ``text``."""
    url = os.getenv(_PROXY_ENV_VAR, "").strip()
    if url and url in text:
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            redacted = parsed._replace(netloc=netloc).geturl()
        except (ValueError, AttributeError):
            redacted = "<proxy-url>"
        text = text.replace(url, redacted)

    def _mask(match: re.Match[str]) -> str:
        if match.group("password") is None:
            return f"{match.group('scheme')}{_REDACTED}@"
        return f"{match.group('scheme')}{_REDACTED}:{_REDACTED}@"

    return _USERINFO_RE.sub(_mask, text)
