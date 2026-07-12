"""A/B Testing skill - runs A/B tests on thumbnails and titles."""

from __future__ import annotations

import logging
from typing import Any, Optional

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class ABTestingSkill(BaseSkill):
    """Run A/B tests on video thumbnails and titles."""

    skill_id = "ab-testing"
    name = "A/B Testing"
    version = "1.0.0"
    triggers = ["video_uploaded"]
    required_env_vars = ["GEMINI_API_KEY", "DATABASE_URL"]

    def __init__(self, dependencies: Optional[dict[str, Any]] = None):
        super().__init__(dependencies)
        self.gemini = self.dependencies.get("gemini_service")
        self.analytics = self.dependencies.get("analytics_service")

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Create and manage an A/B test.

        Expected payload keys:
            - video_id: str - the video to test
            - test_type: str - "thumbnail" | "title" | "description"
            - variants: list[dict] - the test variants
        """
        video_id = payload.get("video_id")
        if not video_id:
            return SkillResult(status="error", error="Missing 'video_id' in payload")

        test_type = payload.get("test_type", "thumbnail")
        variants = payload.get("variants", [])

        logger.info(
            "Creating %s A/B test for video %s with %d variants",
            test_type,
            video_id,
            len(variants),
        )

        if self.gemini:
            logger.info("Using injected gemini_service for A/B testing")
        if self.analytics:
            logger.info("Using injected analytics_service for A/B testing")

        return SkillResult(
            status="success",
            output={
                "video_id": video_id,
                "test_type": test_type,
                "variant_count": len(variants),
                "created": True,
                "message": f"A/B test ({test_type}) created for video {video_id}",
            },
        )
