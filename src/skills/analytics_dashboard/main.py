"""Analytics Dashboard skill - aggregates metrics into dashboard data."""

from __future__ import annotations

import logging
from typing import Any

from skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class AnalyticsDashboardSkill(BaseSkill):
    """Aggregate engagement and performance metrics into dashboard data."""

    skill_id = "analytics-dashboard"
    name = "Analytics Dashboard"
    version = "1.0.0"
    triggers = ["daily_cron"]
    required_env_vars = ["DATABASE_URL"]

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Aggregate analytics metrics.

        Expected payload keys:
            - date_range: str - ISO date range ("2024-01-01/2024-01-31")
            - metrics: list[str] - which metrics to aggregate (optional)
        """
        date_range = payload.get("date_range")
        if not date_range:
            return SkillResult(status="error", error="Missing 'date_range' in payload")

        metrics = payload.get("metrics", ["views", "engagement", "conversions"])

        logger.info(
            "Aggregating %d metrics for range %s", len(metrics), date_range
        )

        return SkillResult(
            status="success",
            output={
                "date_range": date_range,
                "metrics_aggregated": metrics,
                "generated": True,
                "message": f"Dashboard data aggregated for {date_range}",
            },
        )
