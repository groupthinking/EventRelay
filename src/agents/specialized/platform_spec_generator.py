#!/usr/bin/env python3
"""
PLATFORM SPEC GENERATOR AGENT
Generates a technical platform specification from video analysis.

This is the "architecture blueprint" companion to the launch plan — while the
launch plan answers "how do we bring this to market," the platform spec answers
"what do we actually need to build?" Think of it as a system design document
that an engineering team can pick up and start implementing from.
"""

import logging
from typing import Optional

from ..a2a_framework import BaseAgent

logger = logging.getLogger("platform_spec_generator")


class PlatformSpecGenerator(BaseAgent):
    """Agent that generates platform architecture specifications.

    Takes video analysis output and produces a technical specification
    covering system architecture, API design, data models, infrastructure,
    and non-functional requirements.
    """

    def __init__(self):
        super().__init__(
            "platform_spec_generator",
            ["generate_platform_spec", "system_design", "api_design"],
        )

        self.register_handler("generate_platform_spec", self.handle_generate_spec)
        logger.info("⚙️ PLATFORM SPEC GENERATOR INITIALIZED")

    async def process_intent(self, intent: dict) -> dict:
        """Process platform spec generation intent."""
        action = intent.get("action")

        if action == "generate_platform_spec":
            return await self.generate_platform_spec(
                video_analysis=intent.get("video_analysis", {}),
                architecture=intent.get("architecture"),
                preferences=intent.get("preferences"),
            )
        return {"error": f"Unknown action: {action}"}

    async def generate_platform_spec(
        self,
        video_analysis: dict,
        architecture: Optional[dict] = None,
        preferences: Optional[dict] = None,
    ) -> dict:
        """Generate a platform specification from video analysis.

        Args:
            video_analysis: Output from the video-ingest stage.
            architecture: Optional output from the architect stage (if available).
            preferences: User preferences (industry, complexity, etc.)

        Returns:
            Structured platform spec with system design, API endpoints,
            data models, and infrastructure requirements.
        """
        preferences = preferences or {}
        architecture = architecture or {}
        video_id = video_analysis.get("video_id", "unknown")
        logger.info(f"⚙️ Generating platform spec for video: {video_id}")

        content_analysis = video_analysis.get("content_analysis", {})
        topics = content_analysis.get("topics", [])
        actions = content_analysis.get("actions", [])

        complexity = preferences.get("complexity", "moderate")
        industry = preferences.get("industry", "technology")

        # Map complexity to architectural decisions
        complexity_map = {
            "simple": {
                "architecture_style": "Monolith",
                "database": "SQLite/PostgreSQL",
                "hosting": "Single server / PaaS",
                "scaling": "Vertical",
            },
            "moderate": {
                "architecture_style": "Modular monolith",
                "database": "PostgreSQL + Redis",
                "hosting": "Container-based (Docker/Cloud Run)",
                "scaling": "Horizontal with load balancer",
            },
            "complex": {
                "architecture_style": "Microservices",
                "database": "PostgreSQL + Redis + Vector DB",
                "hosting": "Kubernetes",
                "scaling": "Auto-scaling with service mesh",
            },
        }

        arch_defaults = complexity_map.get(complexity, complexity_map["moderate"])

        platform_spec = {
            "video_id": video_id,
            "type": "platform_spec",
            "metadata": {
                "source": "video_analysis",
                "complexity": complexity,
                "industry": industry,
                "grounding": "google_search",
            },
            "prompt_context": {
                "system": (
                    "You are a senior platform architect. Analyze the video content "
                    "and generate a detailed technical platform specification. Use "
                    "Google Search grounding to reference current best practices "
                    "and technology choices. "
                    f"Complexity: {complexity}. Industry: {industry}."
                ),
                "user": (
                    f"Video topics: {topics}\n"
                    f"Key actions: {actions}\n"
                    f"Existing architecture hints: {architecture}\n\n"
                    "Generate a platform spec with:\n"
                    "1. system_overview: high-level architecture description\n"
                    "2. components: list of services/modules with responsibilities\n"
                    "3. api_endpoints: key REST/GraphQL endpoints\n"
                    "4. data_models: core entities and relationships\n"
                    "5. infrastructure: hosting, CI/CD, monitoring\n"
                    "6. non_functional: performance, security, scalability targets\n"
                    "7. tech_stack: recommended technologies with rationale"
                ),
                "tools": [
                    {"googleSearch": {}},
                ],
            },
            "system_overview": {
                "architecture_style": arch_defaults["architecture_style"],
                "description": "",
            },
            "components": [],
            "api_endpoints": [],
            "data_models": [],
            "infrastructure": {
                "database": arch_defaults["database"],
                "hosting": arch_defaults["hosting"],
                "scaling_strategy": arch_defaults["scaling"],
                "ci_cd": "GitHub Actions",
                "monitoring": "OpenTelemetry + Grafana",
            },
            "non_functional": {
                "performance": {
                    "p95_latency_ms": 200,
                    "throughput_rps": 100,
                },
                "security": {
                    "auth": "OAuth 2.0 / JWT",
                    "encryption": "TLS 1.3 + AES-256 at rest",
                    "compliance": [],
                },
                "scalability": {
                    "strategy": arch_defaults["scaling"],
                    "target_users": "10K concurrent",
                },
            },
            "tech_stack": {
                "backend": "Python/FastAPI" if industry != "fintech" else "Go/Gin",
                "frontend": "Next.js/React",
                "database": arch_defaults["database"],
                "message_queue": "Redis Streams" if complexity != "complex" else "Kafka",
                "rationale": {},
            },
        }

        # Derive components from topics
        for i, topic in enumerate(topics[:8]):
            topic_name = topic if isinstance(topic, str) else topic.get("name", f"Component {i}")
            platform_spec["components"].append({
                "name": topic_name.replace(" ", "_").lower(),
                "type": "service" if complexity == "complex" else "module",
                "responsibility": f"Handle {topic_name} logic",
                "dependencies": [],
            })

        return platform_spec

    async def handle_generate_spec(self, message) -> dict:
        """Handle A2A platform spec generation request."""
        content = message.content
        return await self.generate_platform_spec(
            video_analysis=content.get("video_analysis", {}),
            architecture=content.get("architecture"),
            preferences=content.get("preferences"),
        )
