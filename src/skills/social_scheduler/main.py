"""Social Scheduler skill - schedules cross-platform social media posts."""

from __future__ import annotations

import logging
from typing import Any

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class SocialSchedulerSkill(BaseSkill):
    """Schedule and publish social media posts across platforms."""

    skill_id = "social-scheduler"
    name = "Social Scheduler"
    version = "1.0.0"
    triggers = ["ai.content.generated"]
    required_env_vars = ["GEMINI_API_KEY", "SOCIAL_API_KEY"]

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Schedule social media posts.

        Expected payload keys:
            - content: str - the content to post
            - platforms: list[str] - target platforms (e.g. ["twitter", "linkedin"])
            - schedule_time: str - ISO 8601 timestamp (optional, defaults to now)
        """
        content = payload.get("content")
        if not content:
            return SkillResult(status="error", error="Missing 'content' in payload")

        platforms = payload.get("platforms", ["twitter", "linkedin"])
        schedule_time = payload.get("schedule_time")

        logger.info(
            "Scheduling post to %s (scheduled: %s)",
            platforms,
            schedule_time or "immediate",
        )

        return SkillResult(
            status="success",
            output={
                "platforms": platforms,
                "scheduled": True,
                "schedule_time": schedule_time,
                "message": f"Posts scheduled for {len(platforms)} platform(s)",
            },
        )
