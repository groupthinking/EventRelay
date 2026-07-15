<<<<<<< HEAD
#!/usr/bin/env python3
"""Thin GTM skill wrapper."""

import json
import sys
from typing import Any

SKILL_ID = "content-generation"


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the skill wrapper with a JSON-serializable payload."""
    return {
        "status": "success",
        "skill": SKILL_ID,
        "payload": payload,
    }


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    request = json.loads(raw) if raw else {}
    print(json.dumps(run(request)))
=======
"""Content Generation skill - generates blog/social posts from video transcripts."""

from __future__ import annotations

import logging
from typing import Any, Optional

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class ContentGenerationSkill(BaseSkill):
    """Generate blog posts and social media content from video transcripts."""

    skill_id = "content-generation"
    name = "Content Generation"
    version = "1.0.0"
    triggers = ["youtube.video.published"]
    required_env_vars = ["GEMINI_API_KEY"]

    def __init__(self, dependencies: Optional[dict[str, Any]] = None):
        super().__init__(dependencies)
        self.gemini = self.dependencies.get("gemini_service")
        self.db = self.dependencies.get("database_service")

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

        if self.gemini:
            logger.info("Using injected gemini_service for generation")
            # In a real implementation, we would call self.gemini.process_text(...) here

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
>>>>>>> origin/main
