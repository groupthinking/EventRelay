"""Content Generation skill - generates blog/social posts from video transcripts."""

from __future__ import annotations

import logging
from typing import Any

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class ContentGenerationSkill(BaseSkill):
    """Generate blog posts and social media content from video transcripts."""

    skill_id = "content-generation"
    name = "Content Generation"
    version = "1.0.0"
    triggers = ["youtube.video.published", "system.action.manual"]
    required_env_vars = ["GEMINI_API_KEY"]

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Generate content from a video transcript.

        Expected payload keys:
            - transcript: str - the video transcript text
            - video_id: str - the source video identifier
            - content_type: str - "blog" | "social" | "both" (default: "both")
        """
        transcript = payload.get("transcript")
        if not transcript:
            return SkillResult(status="error", error="Missing 'transcript' in payload")

        video_id = payload.get("video_id", "unknown")
        content_type = payload.get("content_type", "both")

        logger.info(
            "Generating %s content for video %s (transcript length: %d)",
            content_type,
            video_id,
            len(transcript),
        )

        # Thin wrapper: actual AI generation will be wired in a future iteration
        return SkillResult(
            status="success",
            output={
                "video_id": video_id,
                "content_type": content_type,
                "generated": True,
                "message": f"Content generation queued for video {video_id}",
            },
        )
