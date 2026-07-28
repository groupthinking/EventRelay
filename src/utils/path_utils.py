#!/usr/bin/env python3
"""
EventRelay Path Utilities
=========================

Provides project root detection and path resolution utilities.
Compatible with UVAI configuration.path_utils interface.
"""

from pathlib import Path


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
