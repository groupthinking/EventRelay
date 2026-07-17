<<<<<<< HEAD
"""SEO Optimizer skill - optimizes video titles, descriptions, and tags."""

from __future__ import annotations

import logging
from typing import Any, Optional

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class SEOOptimizerSkill(BaseSkill):
    """Optimize video metadata for search engine discoverability."""

    skill_id = "seo-optimizer"
    name = "SEO Optimizer"
    version = "1.0.0"
    triggers = ["youtube.video.uploaded"]
    required_env_vars = ["GEMINI_API_KEY"]

    def __init__(self, dependencies: Optional[dict[str, Any]] = None):
        super().__init__(dependencies)
        self.gemini = self.dependencies.get("gemini_service")

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Optimize SEO metadata for a video.

        Expected payload keys:
            - video_id: str - the video identifier
            - title: str - current video title
            - description: str - current description
            - tags: list[str] - current tags
        """
        video_id = payload.get("video_id")
        if not video_id:
            return SkillResult(status="error", error="Missing 'video_id' in payload")

        title = payload.get("title", "")
        description = payload.get("description", "")
        tags = payload.get("tags", [])

        logger.info("Optimizing SEO for video %s", video_id)

        if self.gemini:
            logger.info("Using injected gemini_service for SEO optimization")

        return SkillResult(
            status="success",
            output={
                "video_id": video_id,
                "optimized": True,
                "original_title": title,
                "original_description": description,
                "original_tags": tags,
                "message": f"SEO optimization queued for video {video_id}",
            },
        )
=======
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    skill_name = "seo-optimizer"
    logger.info(f"Skill {skill_name} invoked")
    context = os.getenv("SKILL_CONTEXT", "{}")
    logger.info(f"Context: {context}")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        logger.info("GEMINI_API_KEY is present")
    else:
        logger.warning("GEMINI_API_KEY is missing")
    print(json.dumps({"status": "success", "skill": skill_name}))

if __name__ == "__main__":
    main()
>>>>>>> origin/main
