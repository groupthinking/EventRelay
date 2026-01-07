#!/usr/bin/env python3
"""
Production Video Test - Real video about producing/building something
Tests: video-ingest agent with relevant technical content
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents import get_agent_network, get_emitter

async def test_production_video():
    """Test with real production/technical video"""
    print("=" * 70)
    print("PRODUCTION VIDEO TEST - Video About Building/Producing")
    print("=" * 70)
    print()

    # Real production video provided by user
    test_video = "https://youtu.be/ButAp5rF69E"
    print(f"Video URL: {test_video}")
    print()

    # Get network
    network = get_agent_network()
    emitter = get_emitter()

    print("Testing video-ingest agent with production content...")
    print("-" * 70)

    try:
        # Emit start event
        await emitter.emit("pipeline.event", {
            "event": "production_test.started",
            "video_url": test_video
        })

        # Route to video-ingest agent
        result = await network.route_to_agent(
            "video-ingest",
            "process_video_markdown",
            {
                "video_url": test_video,
                "extract_transcript": True,
                "analyze_content": True
            }
        )

        print("RESULT:")
        print(f"  Status: {result.get('status')}")

        if result.get('status') == 'success':
            print(f"  ✅ Video ID: {result.get('video_id')}")
            print()

            # Show metadata
            metadata = result.get('metadata', {})
            if metadata:
                print("METADATA:")
                print(f"  Title: {metadata.get('title', 'N/A')}")
                print(f"  Channel: {metadata.get('channel', 'N/A')}")
                print(f"  Duration: {metadata.get('duration', 'N/A')}")
                print(f"  Category: {metadata.get('category', 'N/A')}")
                print()

            # Show transcript preview
            transcript = result.get('transcript')
            if transcript and len(transcript) > 0:
                print(f"TRANSCRIPT: {len(transcript)} segments")
                # Show first few meaningful segments
                for i, seg in enumerate(transcript[:5]):
                    text = seg.get('text', '') if isinstance(seg, dict) else str(seg)
                    if text and len(text.strip()) > 5:
                        print(f"  [{i+1}] {text[:80]}...")
                print()

            # Show markdown preview
            markdown = result.get('markdown_content', '')
            if markdown:
                lines = markdown.split('\n')
                print(f"MARKDOWN ANALYSIS ({len(markdown)} chars):")
                for line in lines[:20]:
                    if line.strip():
                        print(f"  {line}")
                print()

            # Analysis data for potential code generation
            analysis = result.get('analysis', {})
            if analysis:
                print("CONTENT ANALYSIS:")
                topics = analysis.get('topics', [])
                if topics:
                    print(f"  Topics: {', '.join(topics[:5])}")

                technologies = analysis.get('technologies', [])
                if technologies:
                    print(f"  Technologies: {', '.join(technologies[:5])}")
                print()

        else:
            error = result.get('error', 'Unknown error')
            print(f"  ✗ Error: {error}")
            print()

        # Emit complete event
        await emitter.emit("pipeline.event", {
            "event": "production_test.completed",
            "video_url": test_video,
            "success": result.get('status') == 'success'
        })

    except Exception as e:
        print(f"  ✗ Exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await emitter.close()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("This video is suitable for code generation pipeline")
    print("Next: Use this video for full pipeline test (ingest → architect → code-gen)")

if __name__ == "__main__":
    asyncio.run(test_production_video())
