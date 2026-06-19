#!/usr/bin/env python3
"""
Test Tri-Model Consensus Tool
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.mcp_tools import get_tri_model_consensus_tool

async def test_consensus():
    """Test tri-model consensus for architecture decision"""
    print("=" * 70)
    print("TRI-MODEL CONSENSUS TEST: Grok + Claude + Gemini")
    print("=" * 70)
    print()

    tool = get_tri_model_consensus_tool()

    # Test prompt: architecture decision for a video app
    test_prompt = """
You are an expert software architect. Analyze this video concept and recommend the best technology stack:

VIDEO CONCEPT: "Building MCP Servers Tutorial - Complete Guide to Model Context Protocol"
DURATION: 15 minutes
TOPICS: Docker, MCP protocol, TypeScript, AI integration, server deployment

Recommend in JSON format:
{
    "app_type": "type of app to build",
    "framework": "primary framework",
    "tech_stack": ["list", "of", "technologies"],
    "features": ["key", "features", "to", "include"],
    "deployment": "deployment platform",
    "confidence": 0.0-1.0
}
"""

    print("📋 Test Prompt:")
    print(f"   Architecture decision for MCP servers tutorial video")
    print()
    print("🔮 Querying all three models...")
    print()

    result = await tool.get_consensus(
        prompt=test_prompt,
        task_type="architecture",
        require_all=False  # Don't fail if a model is unavailable
    )

    if result.get("status") == "success":
        print("✅ CONSENSUS ACHIEVED")
        print(f"   Models Queried: {result.get('models_queried')}/3")
        print(f"   Agreement Score: {result.get('agreement_score', 0):.2f}")
        print(f"   Consensus Confidence: {result.get('consensus_confidence', 0):.2f}")
        print(f"   Strategy Used: {result.get('strategy_used')}")
        print()

        print("🎯 Consensus Decision:")
        print(f"   {result.get('reasoning')}")
        print()

        print("📊 Individual Model Responses:")
        for response in result.get("model_responses", []):
            print(f"\n   [{response['model']}]")
            print(f"   Confidence: {response['confidence']:.2f}")
            print(f"   Latency: {response['latency_ms']}ms")
            print(f"   Response Preview: {response['response'][:200]}...")

        print()
        print("💡 Full Consensus Response:")
        print("-" * 70)
        print(result.get("consensus_response"))
        print("-" * 70)

    else:
        print(f"❌ CONSENSUS FAILED")
        print(f"   Error: {result.get('error')}")

    print()
    await tool.close()

if __name__ == "__main__":
    asyncio.run(test_consensus())
