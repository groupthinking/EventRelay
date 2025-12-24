#!/usr/bin/env python3
"""
YouTube MCP Tool - Connects existing YouTube processing to MCP Agent Network
Wraps VideoProcessingService for agent consumption
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from youtube_extension.backend.video_processor_factory import get_video_processor

logger = logging.getLogger(__name__)

class YouTubeMCPTool:
    """
    MCP-compatible wrapper for YouTube video processing.
    Exposes video processing capabilities as MCP tools.
    """

    def __init__(self):
        # Get processor directly (factory pattern handles all deps)
        self.processor = None
        logger.info("✅ YouTube MCP Tool initialized")

    def _get_processor(self):
        """Lazy init processor"""
        if self.processor is None:
            self.processor = get_video_processor("auto")
        return self.processor

    async def close(self):
        """Clean up processor resources"""
        if self.processor and hasattr(self.processor, 'close'):
            await self.processor.close()
            self.processor = None

    async def process_video_markdown(self, video_url: str,
                                     extract_transcript: bool = True,
                                     analyze_content: bool = True) -> Dict[str, Any]:
        """
        Process video and generate markdown analysis.

        MCP Tool: process_video_markdown

        Args:
            video_url: YouTube video URL
            extract_transcript: Whether to extract transcript
            analyze_content: Whether to perform AI analysis

        Returns:
            Dict with video_id, metadata, markdown_content, transcript
        """
        try:
            logger.info(f"MCP Tool: process_video_markdown for {video_url}")

            processor = self._get_processor()
            result = await processor.process_video(video_url)

            # Extract data from result
            video_id = result.get("video_id", "unknown")
            metadata = result.get("metadata", {})

            # Generate markdown from result
            markdown_content = self._generate_markdown(result)

            # Extract transcript
            transcript = result.get("transcript", [])
            if isinstance(transcript, dict):
                transcript = transcript.get("segments", [])

            return {
                "status": "success",
                "video_id": video_id,
                "video_url": video_url,
                "metadata": metadata,
                "markdown_content": markdown_content,
                "transcript": transcript,
                "cached": False,
                "processing_time": result.get("processing_time", "0s")
            }

        except Exception as e:
            logger.error(f"MCP Tool error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "video_url": video_url
            }

    def _generate_markdown(self, result: Dict[str, Any]) -> str:
        """Generate markdown from processing result"""
        lines = []

        # Title
        metadata = result.get("metadata", {})
        title = metadata.get("title", "Video Analysis")
        lines.append(f"# {title}\n")

        # Metadata
        if metadata:
            lines.append("## Metadata")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # AI Analysis
        ai_analysis = result.get("ai_analysis", {})
        if ai_analysis:
            lines.append("## Analysis")
            for key, value in ai_analysis.items():
                lines.append(f"### {key}")
                if isinstance(value, list):
                    for item in value:
                        lines.append(f"- {item}")
                else:
                    lines.append(str(value))
                lines.append("")

        return "\n".join(lines)

    async def get_transcript(self, video_url: str) -> Dict[str, Any]:
        """
        Extract transcript from video.

        MCP Tool: get_transcript

        Args:
            video_url: YouTube video URL

        Returns:
            Dict with video_id, transcript segments
        """
        try:
            logger.info(f"MCP Tool: get_transcript for {video_url}")

            processor = self._get_processor()
            result = await processor.process_video(video_url)

            transcript = result.get("transcript", [])
            if isinstance(transcript, dict):
                transcript = transcript.get("segments", [])

            return {
                "status": "success",
                "video_id": result.get("video_id"),
                "video_url": video_url,
                "transcript": transcript,
                "language": result.get("metadata", {}).get("language", "en")
            }

        except Exception as e:
            logger.error(f"MCP Tool error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "video_url": video_url
            }

    async def analyze_video(self, video_url: str) -> Dict[str, Any]:
        """
        Perform AI analysis on video content.

        MCP Tool: analyze_video

        Args:
            video_url: YouTube video URL

        Returns:
            Dict with analysis results, topics, actions
        """
        try:
            logger.info(f"MCP Tool: analyze_video for {video_url}")

            processor = self._get_processor()
            result = await processor.process_video(video_url)

            ai_analysis = result.get("ai_analysis", {})

            return {
                "status": "success",
                "video_id": result.get("video_id"),
                "video_url": video_url,
                "metadata": result.get("metadata", {}),
                "analysis": {
                    "topics": ai_analysis.get("Related Topics", []),
                    "actions": ai_analysis.get("actions", []),
                    "summary": ai_analysis.get("summary", ""),
                    "technologies": ai_analysis.get("technologies", [])
                }
            }

        except Exception as e:
            logger.error(f"MCP Tool error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "video_url": video_url
            }

# Singleton instance
_tool = None

def get_youtube_tool() -> YouTubeMCPTool:
    """Get or create YouTube MCP Tool singleton"""
    global _tool
    if _tool is None:
        _tool = YouTubeMCPTool()
    return _tool

# MCP Tool registry for agent network
MCP_TOOLS = {
    "process_video_markdown": get_youtube_tool().process_video_markdown,
    "get_transcript": get_youtube_tool().get_transcript,
    "analyze_video": get_youtube_tool().analyze_video
}
