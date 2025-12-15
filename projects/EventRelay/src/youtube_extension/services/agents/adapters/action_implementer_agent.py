#!/usr/bin/env python3
"""
Action Implementer Agent Service
=================================

Extracted and refactored from development/agents/action_implementer.py
Provides actionable task generation and implementation planning with clean service interfaces.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..dto import AgentRequest, AgentResult
from ..registry import register
from ..base_agent import BaseAgent
from ..registry import register


@dataclass
class ActionPlan:
    """Structured action plan result"""
    primary_actions: List[Dict[str, Any]]
    supplementary_actions: List[Dict[str, Any]]
    learning_path: List[str]
    prerequisites: List[str]
    resources: List[Dict[str, Any]]
    estimated_total_time: str
    difficulty_progression: List[str]


@register
class ActionImplementerAgent(BaseAgent):
    name = "action_implementer"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Action Implementer Agent.

        Args:
            config: Configuration for action generation
        """
        self._action_templates = self._load_action_templates()

    def _load_action_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load action templates for different content types"""
        return {
            "tutorial": {
                "pattern": "follow_along",
                "action_types": ["practice", "implement", "experiment"],
                "difficulty_levels": ["beginner", "intermediate", "advanced"]
            },
            "educational": {
                "pattern": "learn_and_apply",
                "action_types": ["research", "study", "summarize", "test"],
                "difficulty_levels": ["beginner", "intermediate"]
            },
            "demonstration": {
                "pattern": "replicate_and_improve",
                "action_types": ["recreate", "modify", "enhance"],
                "difficulty_levels": ["intermediate", "advanced"]
            },
            "conceptual": {
                "pattern": "understand_and_explore",
                "action_types": ["research", "analyze", "discuss", "relate"],
                "difficulty_levels": ["beginner", "intermediate", "advanced"]
            }
        }

    async def run(self, req: AgentRequest) -> AgentResult:
        """
        Generate actionable tasks from video analysis.

        Args:
            req: AgentRequest with 'video_analysis' or 'video_data' in params

        Returns:
            AgentResult with action plan
        """
        start_time = asyncio.get_event_loop().time()

        # Validate input
        if "video_analysis" not in req.params and "video_data" not in req.params:
            return AgentResult(
                status="error",
                output={},
                logs=["Missing required video_analysis or video_data"],
            )

        try:
            # Extract analysis data
            if "video_analysis" in req.params:
                analysis = req.params["video_analysis"]
            else:
                # Create basic analysis from video_data
                video_data = req.params["video_data"]
                analysis = self._create_basic_analysis(video_data)

            # Determine content type
            content_type = self._determine_content_type(analysis)

            # Generate action plan
            action_plan = await self._generate_action_plan(analysis, content_type)

            processing_time = asyncio.get_event_loop().time() - start_time

            return AgentResult(
                status="ok",
                output={
                    "action_plan": action_plan,
                    "content_type": content_type,
                    "generation_method": "template_based"
                },
                logs=[f"Processing time: {processing_time:.2f}s"],
            )

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Action generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            return AgentResult(
                status="error",
                output={},
                logs=[error_msg, f"Processing time: {processing_time:.2f}s"],
            )

    def _create_basic_analysis(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic analysis from video metadata"""
        title = video_data.get("title", "")
        description = video_data.get("description", "")

        return {
            "title": title,
            "summary": description[:200] + "..." if len(description) > 200 else description,
            "key_points": self._extract_key_points_from_text(title + " " + description),
            "difficulty_level": "intermediate",
            "quality_score": 0.5
        }

    def _extract_key_points_from_text(self, text: str) -> List[str]:
        """Extract key points from text using simple heuristics"""
        # Simple keyword-based extraction
        keywords = ["learn", "build", "create", "develop", "implement", "tutorial", "guide", "how to"]
        key_points = []

        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                # Extract sentence containing keyword
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        key_points.append(sentence.strip())
                        break

        return key_points[:5]  # Limit to 5 key points

    def _determine_content_type(self, analysis: Dict[str, Any]) -> str:
        """Determine content type from analysis"""
        title = analysis.get("title", "").lower()
        summary = analysis.get("summary", "").lower()
        combined = title + " " + summary

        # Simple pattern matching
        if any(word in combined for word in ["tutorial", "how to", "step by step", "guide"]):
            return "tutorial"
        elif any(word in combined for word in ["demo", "demonstration", "example", "showcase"]):
            return "demonstration"
        elif any(word in combined for word in ["concept", "theory", "explanation", "understand"]):
            return "conceptual"
        else:
            return "educational"

    async def _generate_action_plan(self, analysis: Dict[str, Any], content_type: str) -> ActionPlan:
        """Generate comprehensive action plan based on analysis and content type"""

        template = self._action_templates.get(content_type, self._action_templates["educational"])

        # Generate primary actions
        primary_actions = self._generate_primary_actions(analysis, template)

        # Generate supplementary actions
        supplementary_actions = self._generate_supplementary_actions(analysis, template)

        # Create learning path
        learning_path = self._create_learning_path(primary_actions, supplementary_actions)

        # Identify prerequisites
        prerequisites = self._identify_prerequisites(analysis, content_type)

        # Gather resources
        resources = self._gather_resources(analysis, content_type)

        # Calculate total time
        estimated_total_time = self._calculate_total_time(primary_actions, supplementary_actions)

        # Create difficulty progression
        difficulty_progression = self._create_difficulty_progression(primary_actions)

        return ActionPlan(
            primary_actions=primary_actions,
            supplementary_actions=supplementary_actions,
            learning_path=learning_path,
            prerequisites=prerequisites,
            resources=resources,
            estimated_total_time=estimated_total_time,
            difficulty_progression=difficulty_progression
        )

    def _generate_primary_actions(self, analysis: Dict[str, Any], template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate primary actionable tasks"""
        actions = []
        title = analysis.get("title", "")
        key_points = analysis.get("key_points", [])

        # Generate main action from title
        main_action = {
            "id": "primary_001",
            "title": f"Complete: {title}",
            "description": f"Follow along with the video content and implement the main concepts",
            "priority": "high",
            "estimated_time": "30-60 minutes",
            "category": "implementation",
            "type": template["action_types"][0] if template["action_types"] else "practice",
            "difficulty": analysis.get("difficulty_level", "intermediate"),
            "prerequisites": [],
            "deliverables": ["Working implementation", "Understanding notes"]
        }
        actions.append(main_action)

        # Generate actions from key points
        for i, point in enumerate(key_points[:3]):  # Limit to 3 key points
            action = {
                "id": f"primary_{i+2:03d}",
                "title": f"Master: {point[:50]}...",
                "description": f"Deep dive into: {point}",
                "priority": "medium" if i > 0 else "high",
                "estimated_time": "15-30 minutes",
                "category": "learning",
                "type": template["action_types"][1] if len(template["action_types"]) > 1 else "study",
                "difficulty": analysis.get("difficulty_level", "intermediate"),
                "prerequisites": [main_action["id"]] if i > 0 else [],
                "deliverables": ["Summary notes", "Key insights"]
            }
            actions.append(action)

        return actions

    def _generate_supplementary_actions(self, analysis: Dict[str, Any], template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate supplementary learning actions"""
        actions = []

        # Research action
        research_action = {
            "id": "supp_001",
            "title": "Research related topics",
            "description": "Find additional resources and related content",
            "priority": "low",
            "estimated_time": "20-30 minutes",
            "category": "research",
            "type": "research",
            "difficulty": "beginner",
            "prerequisites": [],
            "deliverables": ["Resource list", "Related topics"]
        }
        actions.append(research_action)

        # Practice action
        practice_action = {
            "id": "supp_002",
            "title": "Create variations",
            "description": "Modify and extend the concepts learned",
            "priority": "medium",
            "estimated_time": "45-90 minutes",
            "category": "practice",
            "type": "experiment",
            "difficulty": analysis.get("difficulty_level", "intermediate"),
            "prerequisites": ["primary_001"],
            "deliverables": ["Custom implementation", "Experiment results"]
        }
        actions.append(practice_action)

        return actions

    def _create_learning_path(self, primary_actions: List[Dict[str, Any]], supplementary_actions: List[Dict[str, Any]]) -> List[str]:
        """Create ordered learning path"""
        path = []

        # Add primary actions in dependency order
        for action in sorted(primary_actions, key=lambda x: len(x.get("prerequisites", []))):
            path.append(action["id"])

        # Add supplementary actions
        for action in supplementary_actions:
            path.append(action["id"])

        return path

    def _identify_prerequisites(self, analysis: Dict[str, Any], content_type: str) -> List[str]:
        """Identify prerequisites for the content"""
        difficulty = analysis.get("difficulty_level", "intermediate")

        prereq_map = {
            "tutorial": {
                "beginner": ["Basic computer skills"],
                "intermediate": ["Fundamental programming concepts", "Development environment setup"],
                "advanced": ["Strong programming background", "Domain expertise"]
            },
            "educational": {
                "beginner": ["Basic subject knowledge"],
                "intermediate": ["Foundational concepts", "Related experience"],
                "advanced": ["Advanced background", "Specialized knowledge"]
            }
        }

        content_prereqs = prereq_map.get(content_type, prereq_map["educational"])
        return content_prereqs.get(difficulty, ["Basic knowledge"])

    def _gather_resources(self, analysis: Dict[str, Any], content_type: str) -> List[Dict[str, Any]]:
        """Gather relevant resources"""
        resources = [
            {
                "type": "documentation",
                "title": "Official documentation",
                "description": "Find relevant official docs",
                "priority": "high"
            },
            {
                "type": "community",
                "title": "Community forums",
                "description": "Join relevant communities for support",
                "priority": "medium"
            },
            {
                "type": "tools",
                "title": "Development tools",
                "description": "Set up necessary tools and environment",
                "priority": "high"
            }
        ]

        return resources

    def _calculate_total_time(self, primary_actions: List[Dict[str, Any]], supplementary_actions: List[Dict[str, Any]]) -> str:
        """Calculate estimated total time"""
        # Simple time estimation based on action count
        primary_time = len(primary_actions) * 30  # 30 min average per primary action
        supplementary_time = len(supplementary_actions) * 20  # 20 min average per supplementary action

        total_minutes = primary_time + supplementary_time
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _create_difficulty_progression(self, primary_actions: List[Dict[str, Any]]) -> List[str]:
        """Create difficulty progression path"""
        difficulties = ["beginner", "intermediate", "advanced"]
        progression = []

        for action in primary_actions:
            difficulty = action.get("difficulty", "intermediate")
            if difficulty not in progression:
                progression.append(difficulty)

        # Ensure logical order
        ordered_progression = []
        for diff in difficulties:
            if diff in progression:
                ordered_progression.append(diff)

        return ordered_progression

    def is_available(self) -> bool:
        """Check if agent is available for processing"""
        return True  # This agent doesn't depend on external services