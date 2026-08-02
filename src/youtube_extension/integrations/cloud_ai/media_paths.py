"""
Safe resolution of local media paths for cloud AI providers.

Every provider in this package exposes ``analyze_image(image_url, ...)`` and
dispatches on the string's prefix. The remote schemes each provider recognises
differ, and *anything else* used to be treated as a local filesystem path and
opened verbatim. That final branch would happily read ``/etc/passwd`` or
``../../secrets.env`` if a caller supplied it. The recognised remote schemes,
per provider, are:

* ``aws_rekognition``: ``s3://`` and ``http(s)://``.
* ``azure_vision``: ``http(s)://`` only (``s3://`` falls through to the local
  branch and is now rejected unless it names a real in-root path).
* ``google_cloud``: ``http(s)://`` only (same ``s3://`` caveat as Azure).

This module centralises the guard so all three providers share one policy:

* Local reads are **opt-in**. With ``CLOUD_AI_MEDIA_ROOT`` unset, every local
  path is rejected, so only each provider's recognised remote schemes above
  remain usable. This is the production posture; the local branch is a
  development convenience.
* When a root *is* configured, a candidate path is fully resolved
  (``Path.resolve()`` follows symlinks) and must live inside the equally
  resolved root. That covers symlink escapes, not just lexical ``..`` segments.
* Rejection raises :class:`UnsafeMediaPathError` rather than returning empty
  bytes, so failures are loud.

Callers should read from the returned resolved path rather than the original
caller-supplied string: the returned path is the one that was validated, which
narrows (though does not eliminate) the check-to-open race.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .exceptions import ConfigurationError, UnsafeMediaPathError

logger = logging.getLogger(__name__)

#: Environment variable naming the directory local media may be read from.
#: Unset (the default) disables local reads entirely.
MEDIA_ROOT_ENV_VAR = "CLOUD_AI_MEDIA_ROOT"

__all__ = [
    "MEDIA_ROOT_ENV_VAR",
    "get_media_root",
    "resolve_local_media_path",
]


def get_media_root() -> Path | None:
    """Return the configured media root, or ``None`` when local reads are off.

    A relative value is resolved against the process working directory. The
    root is resolved with symlinks followed so that containment checks compare
    real paths on both sides.

    The resolved value must be an existing directory. Rejecting a root that
    points at a regular file (e.g. ``CLOUD_AI_MEDIA_ROOT=/etc/passwd``) or at a
    non-existent path is what keeps the guard fail-closed: without this check,
    ``resolve_local_media_path`` would treat that single file as "inside" the
    root via ``is_relative_to`` and hand it straight to the caller.

    Raises:
        ConfigurationError: if the variable is set to a value that cannot be
            resolved, or that does not resolve to an existing directory.
    """
    raw = os.environ.get(MEDIA_ROOT_ENV_VAR)
    if raw is None or not raw.strip():
        return None

    try:
        root = Path(raw.strip()).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        # RuntimeError covers symlink loops on older resolvers; OSError covers
        # unreadable path components and platform-specific failures.
        raise ConfigurationError(
            f"{MEDIA_ROOT_ENV_VAR} is not a resolvable directory path",
            missing_config=MEDIA_ROOT_ENV_VAR,
        ) from exc

    if not root.is_dir():
        raise ConfigurationError(
            f"{MEDIA_ROOT_ENV_VAR} must point to an existing directory",
            missing_config=MEDIA_ROOT_ENV_VAR,
        )

    return root


def resolve_local_media_path(candidate: str, provider: str | None = None) -> Path:
    """Validate a caller-supplied local media path and return its real path.

    Args:
        candidate: The path exactly as supplied by the caller.
        provider: Provider name, attached to raised errors for context.

    Returns:
        The fully resolved path, guaranteed to sit inside the configured root.

    Raises:
        UnsafeMediaPathError: if local reads are disabled, the path escapes the
            configured root (lexically or via symlink), or it resolves to
            something that is not a regular file.
        ConfigurationError: if ``CLOUD_AI_MEDIA_ROOT`` is set but unusable.
    """
    if not candidate or not candidate.strip():
        raise UnsafeMediaPathError(
            "Local media path is empty",
            provider=provider,
            requested_path=candidate,
        )

    root = get_media_root()
    if root is None:
        raise UnsafeMediaPathError(
            "Local media reads are disabled. Use an s3:// or https:// source, "
            f"or set {MEDIA_ROOT_ENV_VAR} to the directory local media may be "
            "read from.",
            provider=provider,
            requested_path=candidate,
        )

    try:
        resolved = Path(candidate).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise UnsafeMediaPathError(
            "Local media path could not be resolved",
            provider=provider,
            requested_path=candidate,
        ) from exc

    if not resolved.is_relative_to(root):
        # Log the resolution server-side for forensics; keep it out of the
        # exception so the path is not echoed back to an untrusted caller.
        logger.warning(
            "Rejected local media path outside %s: %r resolved to %s",
            MEDIA_ROOT_ENV_VAR,
            candidate,
            resolved,
        )
        raise UnsafeMediaPathError(
            "Local media path is outside the permitted media root",
            provider=provider,
            requested_path=candidate,
        )

    # ``resolve()`` follows symlinks, so a link inside the root that points out
    # of it has already been rejected above. What remains is to refuse
    # non-regular files: a FIFO or character device placed inside the root
    # would otherwise block a worker thread indefinitely on read.
    if resolved.exists() and not resolved.is_file():
        raise UnsafeMediaPathError(
            "Local media path is not a regular file",
            provider=provider,
            requested_path=candidate,
        )

    return resolved
