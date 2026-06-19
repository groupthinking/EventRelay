#!/usr/bin/env python3
"""
Verification script for Strategic Video Intelligence Workflow.
Tests the integration of PersonalityAgent and StrategyAgent into TranscriptActionWorkflow.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any

from youtube_extension.services.workflows.transcript_action_workflow import TranscriptActionWorkflow
from youtube_extension.services.agents.adapters.agent_orchestrator import AgentOrchestrator
# RobustYouTubeService is used via factory, but we need the metadata class for the mock
from src.shared.youtube import RobustYouTubeMetadata

# Mock YouTube Service to avoid real API calls and quota usage
class MockYouTubeService:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    
    async def get_video_metadata(self, video_url: str):
        from src.shared.youtube import RobustYouTubeMetadata
        return RobustYouTubeMetadata(
            video_id="test_vid_123",
            title="Strategic AI Implementation for Enterprises",
            description="A deep dive into deploying agentic workflows.",
            channel_id="channel_abc",
            channel_title="Enterprise AI Insights",
            published_at="2025-12-01T12:00:00Z",
            duration="PT10M",
            view_count=50000,
            like_count=1200,
            comment_count=45,
            thumbnail_urls={"default": "https://example.com/thumb.jpg"},
            tags=["AI", "Enterprise", "Agents"],
            category_id="27",
            default_language="en",
            default_audio_language="en",
            live_broadcast_content="none",
            transcript_available=True,
            source_api="mock_api",
            comments=[
                {"author": "User1", "text": "How do I deploy this on GCP?", "like_count": 5, "published_at": "2025-12-02T10:00:00Z"},
                {"author": "User2", "text": "Great insights, what about security?", "like_count": 10, "published_at": "2025-12-02T11:00:00Z"}
            ],
            channel_context={
                "channel_id": "channel_abc",
                "recent_videos": [
                    {"title": "Intro to Agents", "video_id": "vid001", "published_at": "2025-11-25T12:00:00Z"}
                ]
            }
        )
    
    async def get_transcript(self, video_id: str, language: str = "en"):
        return {
            "text": "In this video, we will discuss strategic AI implementation. First, understand the core principle. Second, deploy the agentic workflow. Third, optimize for scale.",
            "source": "mock_transcript",
            "segments": []
        }

async def verify_workflow():
    print("🚀 Starting Strategic Workflow Verification...")
    key = os.getenv("GEMINI_API_KEY")
    if key:
        print(f"🔑 GEMINI_API_KEY found in env: {key[:5]}...")
    else:
        print("❌ GEMINI_API_KEY NOT FOUND in env!")
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize workflow with mock factory
    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: MockYouTubeService()
    )
    
    video_url = "https://www.youtube.com/watch?v=test_vid_123"
    
    try:
        print(f"📦 Processing video: {video_url}")
        result = await workflow.run(video_url)
        
        print("\n✅ Workflow Execution Success!")
        
        # Check standard outputs
        outputs = result.get("outputs", {})
        print(f"\nAgents used: {result['orchestration_meta']['agents_used']}")
        
        if "transcript_action" in outputs:
            print("✅ TranscriptActionAgent output found.")
            
        # Check strategic outputs
        if "personality_agent" in outputs:
            print("✅ PersonalityAgent output found.")
            personality_map = outputs["personality_agent"]["data"].get("personality_map")
            print(f"   - Persona: {personality_map.get('creator_persona', {}).get('type')}")
        else:
            print("❌ PersonalityAgent output MISSING!")
            
        if "strategy_agent" in outputs:
            print("✅ StrategyAgent output found.")
            strategy_data = outputs["strategy_agent"]["data"]
            print(f"   - Core Principle: {strategy_data.get('strategic_analysis', {}).get('core_principle')}")
            if "a2ui_payload" in strategy_data:
                print("   - ✅ A2UI Payload generated.")
        else:
            print("❌ StrategyAgent output MISSING!")
            
        # Summary of results
        print("\n📝 Result Summary:")
        print(json.dumps(result, indent=2, default=str)[:1000] + "...")
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ Warning: GEMINI_API_KEY not set. Real LLM calls will fail.")
    
    asyncio.run(verify_workflow())
