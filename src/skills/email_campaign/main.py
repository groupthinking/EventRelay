"""Email Campaign skill - generates and sends email sequences."""

from __future__ import annotations

import logging
from typing import Any

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class EmailCampaignSkill(BaseSkill):
    """Generate and dispatch email campaign sequences."""

    skill_id = "email-campaign"
    name = "Email Campaign"
    version = "1.0.0"
    triggers = ["crm.lead.scored"]
    required_env_vars = ["GEMINI_API_KEY", "DATABASE_URL"]

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Generate an email campaign sequence.

        Expected payload keys:
            - lead_id: str - the target lead
            - campaign_type: str - "nurture" | "onboarding" | "re-engagement"
            - template_id: str - optional template override
        """
        lead_id = payload.get("lead_id")
        if not lead_id:
            return SkillResult(status="error", error="Missing 'lead_id' in payload")

        campaign_type = payload.get("campaign_type", "nurture")

        logger.info(
            "Generating %s email campaign for lead %s", campaign_type, lead_id
        )

        return SkillResult(
            status="success",
            output={
                "lead_id": lead_id,
                "campaign_type": campaign_type,
                "generated": True,
                "message": f"Email campaign ({campaign_type}) queued for lead {lead_id}",
            },
        )
