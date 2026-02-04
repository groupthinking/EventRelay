#!/usr/bin/env python3
"""
Smart Collection Engine
-----------------------
Categorizes videos into logical collections (Research, Education, Leisure, etc.)
based on agent-generated analysis and metadata.
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger("smart_collections")


class CollectionCategory(Enum):
    RESEARCH = "Research"
    EDUCATION = "Education"
    LEISURE = "Leisure"
    TECHNICAL = "Technical"
    BUSINESS = "Business"
    MARKETING = "Marketing"
    ENTERTAINMENT = "Entertainment"
    FOOD = "Food & Cooking"
    UNCATEGORIZED = "Uncategorized"


class SmartCollectionEngine:
    """
    Engine to automatically assign videos to collections.
    """

    def __init__(self):
        # In a real app, this would interact with a database
        self.categories = [c.value for c in CollectionCategory]

    def categorize_video(
        self, analysis_result: Dict[str, Any], metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Determine which collection(s) a video belongs to.

        Args:
            analysis_result: The output from agents (Gemini, etc.)
            metadata: Video metadata (title, tags, description)
        """
        assigned_collections = []

        # 1. Check title/description for keywords
        text_context = (
            metadata.get("title", "") + " " + metadata.get("description", "")
        ).lower()
        tags = [t.lower() for t in metadata.get("tags", [])]

        if any(
            w in text_context
            for w in ["tutorial", "how to", "course", "learn", "lecture", "guide"]
        ):
            assigned_collections.append(CollectionCategory.EDUCATION.value)

        if any(
            w in text_context
            for w in [
                "research",
                "paper",
                "scientific",
                "study",
                "analysis",
                "physics",
                "quantum",
            ]
        ):
            assigned_collections.append(CollectionCategory.RESEARCH.value)

        if any(
            w in text_context
            for w in [
                "coding",
                "api",
                "python",
                "software",
                "dev",
                "next.js",
                "tailwind",
                "programming",
            ]
        ):
            assigned_collections.append(CollectionCategory.TECHNICAL.value)

        if any(
            w in text_context
            for w in ["recipe", "cooking", "food", "chef", "lasagna", "kitchen"]
        ):
            assigned_collections.append(CollectionCategory.FOOD.value)

        # 2. Check agent analysis for content classification
        # Assuming task_results['content_categorization'] exists in the logic
        task_results = analysis_result.get("task_results", {})
        categorization_task = task_results.get("content_categorization", {})
        agent_suggestion = categorization_task.get("content", "").lower()

        if "business" in agent_suggestion or "strategy" in agent_suggestion:
            if CollectionCategory.BUSINESS.value not in assigned_collections:
                assigned_collections.append(CollectionCategory.BUSINESS.value)

        if "entertainment" in agent_suggestion or "music" in agent_suggestion:
            assigned_collections.append(CollectionCategory.ENTERTAINMENT.value)

        # Default if nothing found logic
        if not assigned_collections:
            assigned_collections.append(CollectionCategory.UNCATEGORIZED.value)

        logger.info(f"📁 Video categorized into: {assigned_collections}")
        return assigned_collections

    def create_collection(self, name: str):
        """Placeholder for creating new dynamic collections"""
        pass


if __name__ == "__main__":
    # Test
    engine = SmartCollectionEngine()
    test_meta = {"title": "Advanced Python Tutorial", "tags": ["python", "coding"]}
    test_analysis = {
        "task_results": {
            "content_categorization": {
                "content": "This is a technical education video."
            }
        }
    }
    print(engine.categorize_video(test_analysis, test_meta))
