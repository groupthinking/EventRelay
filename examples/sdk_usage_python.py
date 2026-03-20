"""
Example: Using the EventRelay Python SDK

This example demonstrates how to use the EventRelay SDK to:
1. Process a YouTube video
2. Extract events from the transcript
3. Dispatch agents to handle events
4. Monitor agent execution
"""

import asyncio
import os
from typing import List

from eventrelay import EventRelay, AsyncEventRelay
from eventrelay.types import (
    VideoProcessJobRequest,
    EventExtractRequest,
    AgentDispatchRequest,
)


def sync_example():
    """Synchronous example using EventRelay SDK"""
    # Initialize client
    client = EventRelay(
        api_key=os.environ.get("EVENTRELAY_API_KEY"),
        base_url=os.environ.get("EVENTRELAY_API_URL", "https://api.uvai.io"),
    )

    # Step 1: Process a YouTube video
    print("📹 Processing video...")
    video_request = VideoProcessJobRequest(
        video_url="https://youtube.com/watch?v=auJzb1D-fag",
        language="en",
        options={"enable_cache": True},
    )

    job = client.videos.process(video_request)
    print(f"✅ Job created: {job.job_id}")

    # Step 2: Poll for completion
    print("⏳ Waiting for processing to complete...")
    status = client.videos.wait_for_completion(
        job_id=job.job_id,
        timeout=300,  # 5 minutes
        poll_interval=5,  # Check every 5 seconds
    )

    if status.status == "failed":
        print(f"❌ Processing failed: {status.error}")
        return

    print(f"✅ Processing complete!")
    print(f"   Transcript length: {len(status.transcript or '')} characters")

    # Step 3: Extract events
    print("\n🔍 Extracting events from transcript...")
    events = client.events.extract(
        EventExtractRequest(
            transcript=status.transcript,
            video_metadata=status.metadata,
        )
    )

    print(f"✅ Found {len(events.events)} events")
    for i, event in enumerate(events.events[:5], 1):  # Show first 5
        print(f"   {i}. {event.type}: {event.description}")

    # Step 4: Dispatch agents
    print("\n🤖 Dispatching agents...")
    agent_results = []

    for event in events.events[:3]:  # Dispatch for first 3 events
        agent = client.agents.dispatch(
            AgentDispatchRequest(
                event_type=event.type,
                payload=event.payload,
                priority=1,
            )
        )
        agent_results.append(agent)
        print(f"   ✅ Agent {agent.agent_id} dispatched: {agent.status}")

    # Step 5: Monitor agent execution
    print("\n📊 Monitoring agent execution...")
    for agent in agent_results:
        final_status = client.agents.wait_for_completion(
            agent_id=agent.agent_id,
            timeout=120,
        )
        print(f"   Agent {agent.agent_id}: {final_status.status}")

    print("\n🎉 All done!")


async def async_example():
    """Asynchronous example using AsyncEventRelay SDK"""
    # Initialize async client
    async with AsyncEventRelay(
        api_key=os.environ.get("EVENTRELAY_API_KEY"),
        base_url=os.environ.get("EVENTRELAY_API_URL", "https://api.uvai.io"),
    ) as client:
        # Process video asynchronously
        print("📹 Processing video (async)...")
        job = await client.videos.process(
            VideoProcessJobRequest(
                video_url="https://youtube.com/watch?v=auJzb1D-fag",
                language="en",
            )
        )

        # Wait for completion
        status = await client.videos.wait_for_completion(job_id=job.job_id)

        # Extract events
        events = await client.events.extract(
            EventExtractRequest(
                transcript=status.transcript,
                video_metadata=status.metadata,
            )
        )

        # Dispatch agents concurrently
        print(f"\n🤖 Dispatching {len(events.events[:3])} agents concurrently...")
        agent_tasks = [
            client.agents.dispatch(
                AgentDispatchRequest(
                    event_type=event.type,
                    payload=event.payload,
                )
            )
            for event in events.events[:3]
        ]

        agents = await asyncio.gather(*agent_tasks)

        # Monitor all agents concurrently
        print("\n📊 Monitoring agents concurrently...")
        status_tasks = [
            client.agents.wait_for_completion(agent_id=agent.agent_id)
            for agent in agents
        ]

        final_statuses = await asyncio.gather(*status_tasks)

        for status in final_statuses:
            print(f"   Agent {status.agent_id}: {status.status}")

        print("\n🎉 All done!")


def streaming_example():
    """Example using streaming API"""
    client = EventRelay(api_key=os.environ.get("EVENTRELAY_API_KEY"))

    print("💬 Streaming chat example...")

    # Stream chat responses
    for chunk in client.chat.stream(
        messages=[
            {"role": "user", "content": "Explain quantum computing in simple terms"}
        ]
    ):
        print(chunk.content, end="", flush=True)

    print("\n\n✅ Stream complete!")


def pagination_example():
    """Example using pagination"""
    client = EventRelay(api_key=os.environ.get("EVENTRELAY_API_KEY"))

    print("📄 Pagination example...")

    # Auto-paginate through all videos
    video_count = 0
    for video in client.videos.list():
        video_count += 1
        print(f"   {video_count}. {video.video_id}: {video.title}")

        # Stop after 10 for demo purposes
        if video_count >= 10:
            break

    print(f"\n✅ Listed {video_count} videos")


def error_handling_example():
    """Example with comprehensive error handling"""
    from eventrelay import APIError, RateLimitError, AuthenticationError

    client = EventRelay(api_key=os.environ.get("EVENTRELAY_API_KEY"))

    try:
        # This might fail for various reasons
        job = client.videos.process(
            VideoProcessJobRequest(video_url="https://youtube.com/watch?v=invalid")
        )

    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e.message}")
        print("   Please check your API key")

    except RateLimitError as e:
        print(f"❌ Rate limited: {e.message}")
        print(f"   Retry after {e.retry_after} seconds")

    except APIError as e:
        print(f"❌ API error ({e.status_code}): {e.message}")
        if e.detail:
            print(f"   Details: {e.detail}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    print("EventRelay SDK Examples\n" + "=" * 50 + "\n")

    # Check API key
    if not os.environ.get("EVENTRELAY_API_KEY"):
        print("❌ EVENTRELAY_API_KEY environment variable not set")
        print("   Set it with: export EVENTRELAY_API_KEY=your-key-here")
        exit(1)

    # Run examples
    print("\n1. Synchronous Example")
    print("-" * 50)
    sync_example()

    print("\n\n2. Asynchronous Example")
    print("-" * 50)
    asyncio.run(async_example())

    print("\n\n3. Streaming Example")
    print("-" * 50)
    streaming_example()

    print("\n\n4. Pagination Example")
    print("-" * 50)
    pagination_example()

    print("\n\n5. Error Handling Example")
    print("-" * 50)
    error_handling_example()
