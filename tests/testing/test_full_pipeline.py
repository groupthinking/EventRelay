#!/usr/bin/env python3
"""
Full Pipeline Test - video-ingest → architect → code-gen
Tests first 3 stages of video-to-software pipeline with real agents
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents import VideoPipelineOrchestrator

async def test_full_pipeline():
    """Test video → architecture → code generation pipeline"""
    print("=" * 70)
    print("FULL PIPELINE TEST: Video → Architecture → Code Generation")
    print("=" * 70)
    print()

    # Short tech video for testing
    test_video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"Test Video: {test_video}")
    print()

    # Initialize orchestrator
    orchestrator = VideoPipelineOrchestrator()

    # Run first 3 stages only (video-ingest, architect, code-gen)
    print("PIPELINE EXECUTION:")
    print("-" * 70)

    try:
        # Stage 1: Video Ingest
        print("\n[1/3] VIDEO INGEST...")
        result_1 = await orchestrator._execute_agent_stage("video-ingest")
        print(f"      Status: {'✅ SUCCESS' if result_1.success else '✗ FAILED'}")
        print(f"      Duration: {result_1.duration_ms:.1f}ms")
        if result_1.error:
            print(f"      Error: {result_1.error}")
            return

        # Store output for next stage
        orchestrator.pipeline_state["video-ingest_output"] = result_1.data
        orchestrator.pipeline_state["video_url"] = test_video

        # Show video metadata
        video_data = result_1.data
        if video_data.get("status") == "success":
            print(f"      Video ID: {video_data.get('video_id')}")
            print(f"      Title: {video_data.get('metadata', {}).get('title', 'N/A')[:60]}...")
            print(f"      Transcript: {len(video_data.get('transcript', []))} segments")

        # Stage 2: Architecture Determination
        print("\n[2/3] ARCHITECTURE DETERMINATION...")
        result_2 = await orchestrator._execute_agent_stage("architect")
        print(f"      Status: {'✅ SUCCESS' if result_2.success else '✗ FAILED'}")
        print(f"      Duration: {result_2.duration_ms:.1f}ms")
        if result_2.error:
            print(f"      Error: {result_2.error}")

        # Store output
        orchestrator.pipeline_state["architect_output"] = result_2.data

        # Show architecture
        arch_data = result_2.data
        if arch_data.get("status") == "success":
            arch = arch_data.get("architecture", {})
            print(f"      App Type: {arch.get('app_type', 'N/A')}")
            print(f"      Framework: {arch.get('framework', 'N/A')}")
            print(f"      Tech Stack: {', '.join(arch.get('tech_stack', [])[:3])}...")
            print(f"      Confidence: {arch.get('confidence', 0):.2f}")

        # Stage 3: Code Generation
        print("\n[3/3] CODE GENERATION...")
        result_3 = await orchestrator._execute_agent_stage("code-gen")
        print(f"      Status: {'✅ SUCCESS' if result_3.success else '✗ FAILED'}")
        print(f"      Duration: {result_3.duration_ms:.1f}ms")
        if result_3.error:
            print(f"      Error: {result_3.error}")

        # Show generated code
        code_data = result_3.data
        if code_data.get("status") == "success":
            print(f"      Files Generated: {code_data.get('files_generated', 0)}")
            print(f"      Project Path: {code_data.get('project_path', 'N/A')}")
            print(f"      Framework: {code_data.get('framework', 'N/A')}")
            print(f"      Entry Point: {code_data.get('entry_point', 'N/A')}")

            # List generated files
            files = code_data.get('files', {})
            if files:
                print(f"      Files:")
                for file_path in list(files.keys())[:8]:
                    print(f"        - {file_path}")
                if len(files) > 8:
                    print(f"        ... and {len(files) - 8} more")

    except Exception as e:
        print(f"\n✗ Pipeline Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)
    print("PIPELINE TEST COMPLETE")
    print("=" * 70)
    print()
    print("Results:")
    print(f"  Stage 1 (Video Ingest):     {'✅' if result_1.success else '✗'}")
    print(f"  Stage 2 (Architecture):     {'✅' if result_2.success else '✗'}")
    print(f"  Stage 3 (Code Generation):  {'✅' if result_3.success else '✗'}")
    print()
    print(f"Total Time: {(result_1.duration_ms + result_2.duration_ms + result_3.duration_ms):.1f}ms")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
