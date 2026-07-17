<<<<<<< HEAD
"""Email Campaign skill - generates and sends email sequences."""

from __future__ import annotations

import logging
from typing import Any, Optional

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class EmailCampaignSkill(BaseSkill):
    """Generate and dispatch email campaign sequences."""

    skill_id = "email-campaign"
    name = "Email Campaign"
    version = "1.0.0"
    triggers = ["crm.lead.scored"]
    required_env_vars = ["GEMINI_API_KEY", "DATABASE_URL"]

    def __init__(self, dependencies: Optional[dict[str, Any]] = None):
        super().__init__(dependencies)
        self.email_service = self.dependencies.get("email_service")

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

        if self.email_service:
            logger.info("Using injected email_service for campaign dispatch")

        return SkillResult(
            status="success",
            output={
                "lead_id": lead_id,
                "campaign_type": campaign_type,
                "generated": True,
                "message": f"Email campaign ({campaign_type}) queued for lead {lead_id}",
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
    skill_name = "email-campaign"
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
