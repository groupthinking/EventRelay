import json
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Any, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP_CLIENT = True
except ImportError:
    HAS_MCP_CLIENT = False

logger = logging.getLogger(__name__)

@dataclass
class VideoNotebook:
    """Class to hold video notebook data"""
    video_id: str
    title: str
    notebook_id: Optional[str] = None
    summary: Optional[str] = None
    podcast_audio_url: Optional[str] = None
    key_points: Optional[list[str]] = None

class NotebookLMProcessor:
    """
    Orchestrator for Google NotebookLM via MCP.
    Pipes video transcripts into NotebookLM for advanced RAG and audio generation.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = self.config.get("notebooklm_enabled", True)

        # Check if npx is available
        if not shutil.which("npx"):
            logger.warning("npx not found - NotebookLM Processor disabled")
            self.enabled = False

        if not HAS_MCP_CLIENT:
            logger.warning("mcp python package not found - NotebookLM Processor disabled")
            self.enabled = False

        self.server_params = None
        if self.enabled:
            self.server_params = StdioServerParameters(
                command="npx",
                args=["-y", "notebooklm-mcp@latest"],
                env=os.environ.copy()
            )

    async def process_video(self, video_id: str, transcript: str, title: str) -> VideoNotebook:
        """
        Process a video transcript with NotebookLM.

        Args:
            video_id: The YouTube Video ID
            transcript: The full text transcript
            title: The video title

        Returns:
            VideoNotebook object with results
        """
        if not self.enabled:
            logger.info("NotebookLM Processor is disabled, skipping")
            return VideoNotebook(video_id=video_id, title=title)

        logger.info(f"📓 Processing video {video_id} '{title}' with NotebookLM...")

        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 1. Create a dedicated notebook for this video
                    notebook_name = f"Video Analysis: {title[:50]}"

                    logger.info(f"📓 Creating notebook: {notebook_name}")
                    create_result = await session.call_tool("add_notebook", arguments={"name": notebook_name})
                    notebook_id = self._extract_notebook_id(create_result)

                    if not notebook_id:
                        logger.error("Failed to create notebook")
                        return VideoNotebook(video_id=video_id, title=title)

                    logger.info(f"✅ Notebook created: {notebook_id}")

                    # 2. Add Transcript as Source
                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]
                    logger.info(f"Available tools: {tool_names}")

                    source_added = False
                    if "add_source" in tool_names:
                        logger.info("Adding transcript source...")
                        await session.call_tool("add_source", arguments={
                            "notebook_id": notebook_id,
                            "content": transcript,
                            "title": "Full Transcript"
                        })
                        source_added = True

                    # 3. Generate Analysis
                    prompt_text = "Please provide a comprehensive summary of this video transcript, including 5 key takeaways and a sentiment analysis."

                    if not source_added:
                        # Context injection using triple quotes for safety
                        prompt_text = f"""Here is the transcript of a video titled '{title}':

{transcript}

{prompt_text}"""

                    logger.info("🤖 Generating analysis...")
                    analysis_result = await session.call_tool("ask_question", arguments={
                        "notebook_id": notebook_id,
                        "question": prompt_text
                    })

                    summary_text = self._extract_text(analysis_result)

                    return VideoNotebook(
                        video_id=video_id,
                        title=title,
                        notebook_id=notebook_id,
                        summary=summary_text,
                        key_points=[]
                    )

        except Exception as e:
            logger.error(f"❌ NotebookLM processing failed: {e}", exc_info=True)
            return VideoNotebook(video_id=video_id, title=title, summary=f"Processing failed: {e}")

    def _extract_notebook_id(self, result: Any) -> Optional[str]:
        """Helper to parse notebook ID from MCP result"""
        try:
            # Try parsing JSON from text content
            text = result.content[0].text
            # Look for ID in various structures
            if "id" in text:
                try:
                    data = json.loads(text)
                    return data.get("id") or data.get("notebook_id")
                except Exception:
                    pass
            # Fallback: simple string search if output is plain text
            return text.strip()
        except Exception:
            return None

    def _extract_text(self, result: Any) -> str:
        """Helper to extract text from MCP result"""
        try:
            return result.content[0].text
        except Exception:
            return ""
