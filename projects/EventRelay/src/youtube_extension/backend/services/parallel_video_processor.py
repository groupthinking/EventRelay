#!/usr/bin/env python3
"""
Compatibility helpers for parallel video processing.

The real implementation is provided by the shared processor strategies. This
module simply exposes the registry entries that downstream code historically
imported from ``backend.services.parallel_video_processor``.
"""

from typing import Optional, Dict, Any

from src.youtube_extension.processors.strategies import (
    ProcessorStrategy,
    register_strategy,
    get_strategy,
)
from src.youtube_extension.processors.video_processor import VideoProcessor


class ParallelVideoProcessor(VideoProcessor):
    """
    Backwards-compatible wrapper that delegates to the shared `"parallel"`
    strategy while preserving the historical constructor signature.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs: Any):
        merged_config = dict(config or {})
        merged_config.update(kwargs)
        super().__init__(strategy="parallel", config=merged_config)


__all__ = [
    "ParallelVideoProcessor",
    "ProcessorStrategy",
    "register_strategy",
    "get_strategy",
]
