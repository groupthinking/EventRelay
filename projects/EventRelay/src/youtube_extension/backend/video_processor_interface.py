#!/usr/bin/env python3
"""
Typed interface for video processors to enable safe consolidation.
Both `EnhancedVideoProcessor` and `RealVideoProcessor` should implement
`process_video(video_url: str) -> Dict[str, Any]`.
"""

from __future__ import annotations

from typing import Protocol, Dict, Any


class VideoProcessor(Protocol):
	async def process_video(self, video_url: str) -> Dict[str, Any]:
		...
