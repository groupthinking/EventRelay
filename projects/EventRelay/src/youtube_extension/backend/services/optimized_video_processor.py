#!/usr/bin/env python3
"""
Compatibility wrappers for optimized video processing strategies.

The concrete implementations live in ``src.youtube_extension.processors``
modules. This shim keeps legacy imports operational while centralising the real
logic inside the modern strategy registry.
"""

from typing import Optional, Dict, Any

from src.youtube_extension.processors.strategies import (
    OptimizedStrategy,
    ProcessorStrategy,
    get_strategy,
)
from src.youtube_extension.processors.video_processor import VideoProcessor


class OptimizedVideoProcessor(VideoProcessor):
    """
    Legacy-compatible facade that maps to the unified strategy-backed
    ``VideoProcessor``. Consumers can continue instantiating this class while
    all behaviour routes through the `"optimized"` strategy.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(strategy="optimized", config=config)


__all__ = [
    "OptimizedVideoProcessor",
    "OptimizedStrategy",
    "ProcessorStrategy",
    "VideoProcessor",
    "get_strategy",
]
