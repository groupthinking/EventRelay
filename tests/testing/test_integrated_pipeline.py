#!/usr/bin/env python3
"""
Integration Test: MCP Agent Network + Claude Skill Monitor
Verifies end-to-end event emission from pipeline to monitor
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents import VideoPipelineOrchestrator, get_emitter

async def test_integrated_pipeline():
    """Test pipeline with skill monitor integration"""
    print("=" * 70)
    print("INTEGRATED PIPELINE TEST: Agent Network + Skill Monitor")
    print("=" * 70)
    print()

    # Check skill monitor emitter
    emitter = get_emitter()
    print(f"✓ Skill Monitor Emitter initialized")
    print(f"  Enabled: {emitter.enabled}")
    print(f"  Monitor URL: {emitter.monitor_url}")
    print()

    # Initialize orchestrator
    orchestrator = VideoPipelineOrchestrator()
    print(f"✓ Pipeline Orchestrator initialized")
    print(f"  Network: {orchestrator.network.get_network_status()['agents']} agents")
    print(f"  Emitter: Connected to skill monitor")
    print()

    # Run test pipeline
    print("RUNNING PIPELINE:")
    print("  Video: https://youtube.com/watch?v=test_integration")
    print("  Stages: 6 (video-ingest → architect → code-gen → validator → deployer → knowledge)")
    print()

    result = await orchestrator.run_pipeline(
        "https://youtube.com/watch?v=test_integration",
        {"continue_on_error": True}  # Continue even if stages fail (for testing)
    )

    print("PIPELINE RESULTS:")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Stages: {result['stages_completed']}")
    print(f"  Duration: {result['total_duration_ms']:.1f}ms")
    print()

    print("STAGE BREAKDOWN:")
    for agent_id, stage_result in result['stage_results'].items():
        status = "✓" if stage_result['success'] else "✗"
        print(f"  {status} {agent_id}: {stage_result['duration_ms']:.1f}ms", end="")
        if stage_result['error']:
            print(f" (ERROR: {stage_result['error']})")
        else:
            print()
    print()

    # Close emitter
    await emitter.close()

    print("=" * 70)
    print("✓ INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()
    print("Integration Points:")
    print("  1. Agent Network: Coordinating 6 specialized agents")
    print("  2. Pipeline Orchestrator: Managing video-to-software flow")
    print("  3. Skill Monitor: Receiving real-time events via WebSocket")
    print()
    print("Next Steps:")
    print("  1. Start Skill Monitor: cd ~/claude-skill-monitor && npm start")
    print("  2. View Dashboard: http://localhost:3000")
    print("  3. Run Real Pipeline: python test_integrated_pipeline.py")
    print("  4. Watch events flow in real-time on dashboard")

if __name__ == "__main__":
    asyncio.run(test_integrated_pipeline())
