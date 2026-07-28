#!/usr/bin/env python3
"""
EventRelay Path Utilities
=========================

Provides project root detection and path resolution utilities.
Compatible with UVAI configuration.path_utils interface.
"""

<<<<<<< HEAD
from pathlib import Path
=======
import os
from pathlib import Path
from typing import Union

PathLike = Union[str, "os.PathLike[str]"]


def select_writable_dir(preferred: PathLike, fallback: PathLike) -> Path:
    """Return a directory that is actually writable, preferring ``preferred``.

    ``preferred`` is chosen only when it *already exists* and is a writable
    directory. It is never created — this avoids materializing developer- or
    machine-specific trees (e.g. ``/Users/garvey/...``) in foreign environments
    such as CI runners or root containers, where a plain ``mkdir`` would
    otherwise succeed. Existence alone is insufficient because an existing but
    read-only directory passes ``exists()``/``mkdir(exist_ok=True)`` yet still
    raises ``PermissionError`` on the first real write.

    When ``preferred`` is unusable, ``fallback`` is created (parents included)
    and returned, guaranteeing the caller a writable location.

    Args:
        preferred: The legacy/default directory to reuse when viable.
        fallback: The runtime directory to create and use otherwise.

    Returns:
        Path: A writable directory.
    """
    candidate = Path(preferred)
    if candidate.is_dir() and os.access(candidate, os.W_OK):
        return candidate
    runtime = Path(fallback)
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


def select_readable_file(preferred: PathLike, fallback: PathLike) -> Path:
    """Return a readable config file, preferring ``preferred``.

    ``preferred`` is chosen only when it exists as a readable file — a bare
    ``exists()`` check is not enough, since an existing but unreadable file (or
    a directory at that path) would be selected and then fail to open, silently
    discarding a perfectly good ``fallback``. When ``preferred`` is unusable the
    ``fallback`` path is returned as-is (its readability is decided by the
    caller's own load logic).

    Args:
        preferred: The legacy/default file to reuse when readable.
        fallback: The runtime file path to fall back to.

    Returns:
        Path: The selected file path.
    """
    candidate = Path(preferred)
    if candidate.is_file() and os.access(candidate, os.R_OK):
        return candidate
    return Path(fallback)
>>>>>>> origin/main


def get_project_root() -> Path:
    """
    Get EventRelay project root directory.

    Returns:
        Path: Absolute path to EventRelay project root
    """
    # This file is in: EventRelay/src/utils/path_utils.py
    # Project root is 2 levels up
    return Path(__file__).parent.parent.parent


def resolve_path(*parts: str) -> Path:
    """
    Resolve path relative to project root.

    Args:
        *parts: Path components to join

    Returns:
        Path: Absolute path resolved from project root

    Examples:
        >>> resolve_path('logs', 'app.log')
        PosixPath('/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/logs/app.log')

        >>> resolve_path('temp', 'packaged_projects')
        PosixPath('/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/temp/packaged_projects')
    """
    return get_project_root().joinpath(*parts)


if __name__ == "__main__":
    # Test utilities
    print(f"Project Root: {get_project_root()}")
    print(f"Logs Path: {resolve_path('logs', 'test.log')}")
    print(f"Temp Path: {resolve_path('temp', 'packaged_projects')}")
