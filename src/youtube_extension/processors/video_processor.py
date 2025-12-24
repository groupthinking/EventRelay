#!/usr/bin/env python3
"""
Unified Video Processor
=======================

This module provides a unified interface for video processing, using a
strategy pattern to select the appropriate processing method based on
the provided options.
"""

from typing import Dict, Any, List, Optional
from .strategies import get_strategy, ProcessorStrategy

class VideoProcessor:
    """
    A unified video processor that uses a strategy pattern to delegate
    the actual processing to a specific strategy.
    """
    def __init__(self, strategy: str = "enhanced", config: Optional[Dict[str, Any]] = None):
        """
        Initialize the video processor with a specific strategy.

        Args:
            strategy: The name of the strategy to use (e.g., "enhanced", "optimized", "parallel").
            config: A configuration dictionary for the strategy.
        """
        self.strategy: ProcessorStrategy = get_strategy(strategy)(config=config)

    async def process_video(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a single video using the selected strategy.
        """
        return await self.strategy.process_video(video_url, options)

    async def process_batch(self, video_urls: List[str], options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Process a batch of videos using the selected strategy.
        """
        return await self.strategy.process_batch(video_urls, options)

# Default processor instance
default_processor = VideoProcessor()
