#!/usr/bin/env python3
"""
LAUNCH PLAN GENERATOR AGENT
Generates a go-to-market (GTM) launch plan from video analysis.

Think of this as the "business layer" — it bridges the gap between
"I watched a video about X" and "Here's how I bring X to market."
Uses Google Search grounding for market-aware content when available.
"""

import logging
from typing import Optional

from ..a2a_framework import BaseAgent

logger = logging.getLogger("launch_plan_generator")


class LaunchPlanGenerator(BaseAgent):
    """Agent that generates structured launch plans from video content.

    Takes video analysis output and produces a GTM strategy with target
    audience, channels, timeline, and success metrics. Optionally uses
    Google Search grounding for competitive awareness.
    """

    def __init__(self):
        super().__init__(
            "launch_plan_generator",
            ["generate_launch_plan", "market_analysis", "gtm_strategy"],
        )

        self.register_handler("generate_launch_plan", self.handle_generate_launch_plan)
        logger.info("🚀 LAUNCH PLAN GENERATOR INITIALIZED")

    async def process_intent(self, intent: dict) -> dict:
        """Process launch plan generation intent."""
        action = intent.get("action")

        if action == "generate_launch_plan":
            return await self.generate_launch_plan(
                video_analysis=intent.get("video_analysis", {}),
                preferences=intent.get("preferences"),
            )
        return {"error": f"Unknown action: {action}"}

    async def generate_launch_plan(
        self,
        video_analysis: dict,
        preferences: Optional[dict] = None,
    ) -> dict:
        """Generate a GTM launch plan from video analysis.

        Args:
            video_analysis: Output from the video-ingest stage.
            preferences: User preferences (industry, target_audience, tone, etc.)

        Returns:
            Structured launch plan with market positioning, channels, timeline,
            and success metrics.
        """
        preferences = preferences or {}
        video_id = video_analysis.get("video_id", "unknown")
        logger.info(f"🚀 Generating launch plan for video: {video_id}")

        transcript = video_analysis.get("transcript", "")
        content_analysis = video_analysis.get("content_analysis", {})
        topics = content_analysis.get("topics", [])
        actions = content_analysis.get("actions", [])

        # Build preference-aware context
        industry = preferences.get("industry", "technology")
        target_audience = preferences.get("target_audience", "")
        business_model = preferences.get("business_model", "SaaS")
        tone = preferences.get("tone", "professional")

        launch_plan = {
            "video_id": video_id,
            "type": "launch_plan",
            "metadata": {
                "source": "video_analysis",
                "industry": industry,
                "business_model": business_model,
                "grounding": "google_search",  # Indicates search grounding is requested
            },
            "prompt_context": {
                "system": (
                    "You are a GTM strategist. Analyze the video content and generate "
                    "a launch plan. Use Google Search grounding to validate market "
                    "assumptions and identify competitors. "
                    f"Industry: {industry}. Business model: {business_model}. "
                    f"Tone: {tone}."
                ),
                "user": (
                    f"Video topics: {topics}\n"
                    f"Key actions: {actions}\n"
                    f"Target audience: {target_audience}\n\n"
                    "Generate a launch plan with:\n"
                    "1. value_proposition: one-line pitch\n"
                    "2. target_segments: 2-3 customer segments with pain points\n"
                    "3. competitive_landscape: known alternatives and differentiators\n"
                    "4. channels: ranked go-to-market channels\n"
                    "5. timeline: 90-day launch timeline with milestones\n"
                    "6. success_metrics: measurable KPIs for launch\n"
                    "7. risks: top 3 risks with mitigation strategies"
                ),
                "tools": [
                    {"googleSearch": {}},  # Google Search grounding tool
                ],
            },
            "value_proposition": "",
            "target_segments": [],
            "competitive_landscape": {
                "alternatives": [],
                "differentiators": [],
            },
            "channels": [],
            "timeline": {
                "phases": [
                    {
                        "name": "Pre-launch",
                        "duration_days": 30,
                        "milestones": [
                            "Define MVP scope",
                            "Set up landing page",
                            "Build waitlist",
                        ],
                    },
                    {
                        "name": "Soft Launch",
                        "duration_days": 30,
                        "milestones": [
                            "Beta release to waitlist",
                            "Collect feedback",
                            "Iterate on core features",
                        ],
                    },
                    {
                        "name": "General Availability",
                        "duration_days": 30,
                        "milestones": [
                            "Public launch",
                            "Content marketing push",
                            "First revenue milestone",
                        ],
                    },
                ],
            },
            "success_metrics": [],
            "risks": [],
        }

        # Pre-populate segments from video topics
        for topic in topics[:3]:
            topic_name = topic if isinstance(topic, str) else topic.get("name", "")
            if topic_name:
                launch_plan["target_segments"].append({
                    "segment": f"{topic_name} practitioners",
                    "pain_point": f"Need better tooling for {topic_name}",
                    "size_estimate": "Unknown — requires search grounding",
                })

        return launch_plan

    async def handle_generate_launch_plan(self, message) -> dict:
        """Handle A2A launch plan generation request."""
        content = message.content
        return await self.generate_launch_plan(
            video_analysis=content.get("video_analysis", {}),
            preferences=content.get("preferences"),
        )
