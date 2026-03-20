#!/usr/bin/env python3
"""
Example: Complete Video Analysis Workflow
-----------------------------------------
Demonstrates all advanced video analysis features:
1. Temporal event extraction
2. Structured output with schema
3. CloudEvents publishing to EventMesh/OpenWhisk

Usage:
    python examples/complete_workflow_example.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Run complete video analysis workflow."""

    video_url = "https://www.youtube.com/watch?v=i3FOFgimXn0" # How to video

    print("=" * 60)
    print("EventRelay Advanced Video Analysis Workflow")
    print("=" * 60)
    print()

    from src.integration.cloudevents_publisher import create_publisher
    from src.integration.temporal_video_analysis import TemporalVideoAnalyzer

    analyzer = TemporalVideoAnalyzer()

    # Extract tutorial steps
    print("Extracting tutorial steps...")
    steps = await analyzer.extract_tutorial_steps(
        video_url=video_url
    )

    print(f"✅ Extracted {len(steps)} steps")
    for step in steps:
        print(f" - [{step.get('timestamp', '00:00')}] Step {step.get('step_number', '?')}: {step.get('title', '')}")
        print(f"   Instruction: {step.get('instructions', '')}")

    # Extract events
    print("\nExtracting general events...")
    events = await analyzer.extract_temporal_events(
        video_url=video_url
    )

    print(f"✅ Extracted {len(events)} events")
    for evt in events:
        print(f" - [{evt.timestamp}] {evt.event_type}: {evt.description}")

    # Publish to EventMesh
    publisher = create_publisher(backend="file")
    for event in events[:3]:
        await publisher.publish(
            source="/video-analyzer",
            type=f"com.eventrelay.video.event.{event.event_type}",
            data={"timestamp": event.timestamp, "description": event.description}
        )

    await analyzer.close()
    await publisher.close()

    print("✅ Workflow complete!")


if __name__ == "__main__":
    asyncio.run(main())
