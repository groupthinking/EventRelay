#!/usr/bin/env python3
"""
BLUEPRINT GENERATOR AGENT
Generates a workflow DAG blueprint from video analysis.

The blueprint maps extracted concepts into a directed graph of implementation
steps — think of it as the "architectural floor plan" before any code is written.
It answers: "What needs to happen, in what order, and what depends on what?"
"""

import logging
from typing import Optional

from ..a2a_framework import BaseAgent

logger = logging.getLogger("blueprint_generator")


class BlueprintGenerator(BaseAgent):
    """Agent that generates structured workflow blueprints from video content.

    Takes video analysis output (transcript, events, key concepts) and produces
    a DAG-structured blueprint showing implementation phases, dependencies,
    and deliverables.
    """

    def __init__(self):
        super().__init__(
            "blueprint_generator",
            ["generate_blueprint", "map_workflow", "identify_dependencies"],
        )

        self.register_handler("generate_blueprint", self.handle_generate_blueprint)
        logger.info("📋 BLUEPRINT GENERATOR INITIALIZED")

    async def process_intent(self, intent: dict) -> dict:
        """Process blueprint generation intent."""
        action = intent.get("action")

        if action == "generate_blueprint":
            return await self.generate_blueprint(
                video_analysis=intent.get("video_analysis", {}),
                preferences=intent.get("preferences"),
            )
        return {"error": f"Unknown action: {action}"}

    async def generate_blueprint(
        self,
        video_analysis: dict,
        preferences: Optional[dict] = None,
    ) -> dict:
        """Generate a workflow blueprint from video analysis.

        Args:
            video_analysis: Output from the video-ingest stage containing
                           transcript, events, and content analysis.
            preferences: Optional user preferences (industry, complexity, etc.)
                        to customize the blueprint.

        Returns:
            Structured blueprint with phases, nodes, edges, and metadata.
        """
        preferences = preferences or {}
        video_id = video_analysis.get("video_id", "unknown")
        logger.info(f"📋 Generating blueprint for video: {video_id}")

        # Extract key concepts from video analysis
        transcript = video_analysis.get("transcript", "")
        events = video_analysis.get("events", [])
        content_analysis = video_analysis.get("content_analysis", {})
        topics = content_analysis.get("topics", [])
        actions = content_analysis.get("actions", [])

        # Build prompt context from preferences
        industry_context = ""
        if preferences.get("industry"):
            industry_context = (
                f"Target industry: {preferences['industry']}. "
                f"Tailor terminology and workflow patterns to this domain."
            )

        complexity = preferences.get("complexity", "moderate")

        # Structure the blueprint
        blueprint = {
            "video_id": video_id,
            "type": "workflow_blueprint",
            "metadata": {
                "source": "video_analysis",
                "industry": preferences.get("industry", "general"),
                "complexity": complexity,
                "generated_from": {
                    "topics_count": len(topics),
                    "actions_count": len(actions),
                    "events_count": len(events),
                    "transcript_length": len(transcript),
                },
            },
            "prompt_context": {
                "system": (
                    "You are an expert systems architect. Analyze the video content "
                    "and produce a structured workflow blueprint as a DAG. Each node "
                    "represents a discrete implementation step. Edges represent "
                    "dependencies. Group nodes into logical phases. "
                    f"{industry_context}"
                ),
                "user": (
                    f"Video topics: {topics}\n"
                    f"Extracted actions: {actions}\n"
                    f"Key events: {[e.get('summary', '') for e in events[:20]]}\n"
                    f"Complexity level: {complexity}\n\n"
                    "Generate a workflow blueprint with:\n"
                    "1. phases: ordered list of implementation phases\n"
                    "2. nodes: each with id, phase, title, description, effort_hours\n"
                    "3. edges: dependency links between nodes\n"
                    "4. critical_path: the longest dependency chain\n"
                    "5. parallel_opportunities: nodes that can execute concurrently"
                ),
            },
            "phases": [],
            "nodes": [],
            "edges": [],
            "critical_path": [],
            "parallel_opportunities": [],
        }

        # Derive initial structure from extracted data
        # (AI model fills in details when connected)
        if topics:
            for i, topic in enumerate(topics[:10]):
                topic_name = topic if isinstance(topic, str) else topic.get("name", f"Topic {i}")
                blueprint["nodes"].append({
                    "id": f"node_{i}",
                    "phase": f"phase_{i // 3}",
                    "title": topic_name,
                    "description": f"Implement: {topic_name}",
                    "effort_hours": 4,
                    "status": "pending",
                })

            # Create sequential edges as baseline
            for i in range(1, len(blueprint["nodes"])):
                blueprint["edges"].append({
                    "from": f"node_{i-1}",
                    "to": f"node_{i}",
                    "type": "depends_on",
                })

        return blueprint

    async def handle_generate_blueprint(self, message) -> dict:
        """Handle A2A blueprint generation request."""
        content = message.content
        return await self.generate_blueprint(
            video_analysis=content.get("video_analysis", {}),
            preferences=content.get("preferences"),
        )
