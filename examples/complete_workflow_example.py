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
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Run complete video analysis workflow."""
    
    video_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("=" * 60)
    print("EventRelay Advanced Video Analysis Workflow")
    print("=" * 60)
    print()
    
    from src.integration.temporal_video_analysis import TemporalVideoAnalyzer
    from src.integration.cloudevents_publisher import create_publisher
    
    analyzer = TemporalVideoAnalyzer()
    
    # Extract events
    events = await analyzer.extract_temporal_events(
        video_url=video_url,
        event_types=["code_change", "api_call"]
    )
    
    print(f"✅ Extracted {len(events)} events")
    
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
