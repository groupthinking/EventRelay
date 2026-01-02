#!/usr/bin/env python3
"""
Test Integrated MCP Servers
Tests the newly integrated MCP servers without external task routing issues
"""

import asyncio

# Add the parent directory to the path so we can import the coordinator
# REMOVED: sys.path.append removed
from mcp_ecosystem_coordinator import MCPEcosystemCoordinator


async def test_integrated_servers():
    """Test the integrated MCP servers functionality"""

    coordinator = MCPEcosystemCoordinator()

    try:
        print("🧪 TESTING INTEGRATED MCP SERVERS")
        print("=" * 50)

        # Test integrated servers status
        print("\n📊 Checking Integrated Servers Status:")
        integrated_status = await coordinator.get_integrated_servers_status()
        print(f"✅ Status: {integrated_status}")

        # Test video processor server
        print("\n🎥 Testing Video Processor Server:")
        video_request = {
            "action": "process_video",
            "video_id": "TTMYJAw5tiA",
            "analysis_type": "comprehensive"
        }
        video_response = await coordinator.dispatch_to_integrated_server("video_processor", video_request)
        print(f"📹 Response: {video_response}")

        # Test YouTube API proxy server
        print("\n📺 Testing YouTube API Proxy Server:")
        youtube_request = {
            "action": "fetch_youtube_data",
            "query": "AI tutorial videos",
            "max_results": 5
        }
        youtube_response = await coordinator.dispatch_to_integrated_server("youtube_proxy", youtube_request)
        print(f"📺 Response: {youtube_response}")

        # Test orchestrated video workflow
        print("\n🔄 Testing Orchestrated Video Workflow:")
        workflow_result = await coordinator.orchestrate_video_workflow("wXVvfFMTyzY")
        print(f"🔄 Workflow Result: {workflow_result}")

        # Test error handling
        print("\n❌ Testing Error Handling:")
        error_response = await coordinator.dispatch_to_integrated_server("non_existent_server", {"test": "data"})
        print(f"❌ Error Response: {error_response}")

        print("\n✅ All integrated server tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_integrated_servers())

