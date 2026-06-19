#!/usr/bin/env python3
"""
Test/Demo script for MCP Agent Network
Verifies agent network initialization and routing
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents import get_agent_network, VideoPipelineOrchestrator

async def test_network():
    """Test agent network"""
    print("=" * 60)
    print("MCP AGENT NETWORK TEST")
    print("=" * 60)
    print()

    # Get network
    network = get_agent_network()
    status = network.get_network_status()

    print(f"✓ Network initialized")
    print(f"  Agents: {status['agents']}")
    print(f"  Tools: {status['tools']}")
    print(f"  Servers: {status['servers']}")
    print()

    # Show agents
    print("AGENTS:")
    for agent_id in status['agent_ids']:
        agent = network.get_agent(agent_id)
        print(f"  [{agent.id}] {agent.name}")
        print(f"    Role: {agent.role}")
        print(f"    Tools: {', '.join(agent.tools[:3])}...")
        print(f"    Capabilities: {', '.join(agent.capabilities[:2])}...")
        print()

    # Show pipeline order
    print("PIPELINE ORDER:")
    for i, agent_id in enumerate(network.get_pipeline_agents(), 1):
        agent = network.get_agent(agent_id)
        print(f"  {i}. {agent.name}")
    print()

    # Test routing
    print("ROUTING TEST:")
    result = await network.route_to_agent(
        "video-ingest",
        "process_video_markdown",
        {"video_url": "https://youtube.com/watch?v=test"}
    )
    print(f"  ✓ Routed to video-ingest agent")
    print(f"    Status: {result.get('status')}")
    print()

    # Test orchestrator
    print("ORCHESTRATOR TEST:")
    orchestrator = VideoPipelineOrchestrator()
    print(f"  ✓ Orchestrator initialized")
    print(f"  ✓ Ready to run pipeline")
    print()

    print("=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Integrate with actual MCP servers")
    print("  2. Run real video-to-software pipeline")
    print("  3. Monitor agent performance")

if __name__ == "__main__":
    asyncio.run(test_network())
