#!/usr/bin/env python3
"""
PERSONALITY AGENT
Maps character, intent, and personality from video content and community interaction.
"""

import logging

from ..a2a_framework import BaseAgent

logger = logging.getLogger("personality_agent")

class PersonalityAgent(BaseAgent):
    """Agent specialized in mapping persona, intent, and character"""

    def __init__(self):
        super().__init__("personality_agent", ["map_persona", "identify_intent", "analyze_character"])

    async def process_intent(self, intent: dict) -> dict:
        """Process personality analysis intent"""
        action = intent.get("action")

        if action == "map_personality":
            return await self.map_personality(intent.get("video_metadata"))
        else:
            return {"error": f"Unknown action: {action}"}

    async def map_personality(self, video_metadata: dict) -> dict:
        """Map the personality and intent of a video and its creator"""
        logger.info(f"🎭 Mapping personality for video: {video_metadata.get('video_id')}")

        # In a real implementation, this would call an LLM (Gemini 1.5 Pro)
        # with a prompt focused on character and intent mapping.

        # Prompt structure (conceptual):
        # "Analyze the creator's persona (Authority vs Peer), the tone (Instructional vs Narrative),
        # and the underlying intent of the video. Use comments to gauge community perception."

        # Mock result for now, to be integrated with LLM later
        return {
            "creator_persona": {
                "type": "Technical Authority",
                "authority_level": "High",
                "communication_style": "Structured and Professional",
                "background_context": video_metadata.get("channel_context", {}).get("recent_videos", [])
            },
            "video_intent": {
                "primary": "Skill Transfer",
                "secondary": "Problem Solving",
                "likely_user_goal": "Implement a specific solution after seeing a proof of concept"
            },
            "community_sentiment": {
                "vibe": "Collaborative and Curious",
                "common_themes": self._extract_comment_themes(video_metadata.get("comments", [])),
                "intent_alignment": "Users are seeking implementation details beyond the video content"
            }
        }

    def _extract_comment_themes(self, comments: list[dict]) -> list[str]:
        """Extract key themes from comments"""
        if not comments:
            return ["No comments provided"]

        # Simplistic keyword extraction as a placeholder
        themes = []
        full_text = " ".join([c.get("text", "").lower() for c in comments])

        if "how to" in full_text or "step" in full_text:
            themes.append("Implementation Request")
        if "amazing" in full_text or "thanks" in full_text:
            themes.append("Positive Reinforcement")
        if "error" in full_text or "failed" in full_text or "help" in full_text:
            themes.append("Troubleshooting Needed")

        return themes or ["General Engagement"]
