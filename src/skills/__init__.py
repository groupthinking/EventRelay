<<<<<<< HEAD
"""EventRelay GTM skills package."""
=======
"""GTM Skills package for EventRelay agent orchestration.

Skills provide go-to-market automation capabilities (content generation,
SEO optimization, social media scheduling, lead scoring, email campaigns,
analytics dashboards, and A/B testing) that extend EventRelay's video
pipeline into a full marketing automation platform.
"""

from skills.content_generation.main import ContentGenerationSkill
from skills.seo_optimizer.main import SEOOptimizerSkill
from skills.social_scheduler.main import SocialSchedulerSkill
from skills.lead_scorer.main import LeadScorerSkill
from skills.email_campaign.main import EmailCampaignSkill
from skills.analytics_dashboard.main import AnalyticsDashboardSkill
from skills.ab_testing.main import ABTestingSkill

__all__ = [
    "ContentGenerationSkill",
    "SEOOptimizerSkill",
    "SocialSchedulerSkill",
    "LeadScorerSkill",
    "EmailCampaignSkill",
    "AnalyticsDashboardSkill",
    "ABTestingSkill",
]
>>>>>>> origin/main
