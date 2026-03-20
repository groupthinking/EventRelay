#!/usr/bin/env python3
"""
Cloud Services Example
======================

Example usage of cloud-native services.
"""

import asyncio
import os
from youtube_extension.services.cloud import (
    get_firestore_service,
    get_cloud_tasks_service,
    get_vertex_ai_service,
    VideoProcessingTask,
)
from youtube_extension.services.cloud.cloud_video_processor import (
    get_cloud_video_processor
)


async def example_firestore():
    """Example: Using Firestore for state management"""
    print("\n=== Firestore State Example ===\n")

    # Get service
    firestore_service = await get_firestore_service()

    # Create state
    print("Creating state for video...")
    state = await firestore_service.create_state(
        video_id="test123",
        video_url="https://youtube.com/watch?v=test123"
    )
    print(f"✅ Created: {state.video_id} - {state.status}")

    # Update state
    print("\nUpdating state...")
    state = await firestore_service.update_state(
        video_id="test123",
        status="processing",
        current_stage="transcript",
        metadata={"title": "Test Video"}
    )
    print(f"✅ Updated: {state.current_stage}")

    # Get state
    print("\nGetting state...")
    state = await firestore_service.get_state("test123")
    print(f"✅ Retrieved: {state.status} - {state.current_stage}")

    # List states
    print("\nListing states...")
    states = await firestore_service.list_states(status="processing", limit=10)
    print(f"✅ Found {len(states)} processing videos")

    # Cleanup
    await firestore_service.delete_state("test123")
    print("\n✅ Cleaned up test state")


async def example_cloud_tasks():
    """Example: Using Cloud Tasks for async processing"""
    print("\n=== Cloud Tasks Queue Example ===\n")

    # Get service
    tasks_service = get_cloud_tasks_service()

    # Create task
    task = VideoProcessingTask(
        video_id="test456",
        video_url="https://youtube.com/watch?v=test456",
        priority=5
    )

    # Enqueue task
    print("Enqueuing video processing task...")
    task_id = await tasks_service.enqueue_video_processing(task)
    print(f"✅ Task enqueued: {task_id}")

    # Get queue stats
    print("\nGetting queue stats...")
    stats = await tasks_service.get_queue_stats()
    print(f"✅ Queue: {stats['name']}")
    print(f"   State: {stats['state']}")
    print(f"   Tasks: {stats['tasks_count']}")


async def example_vertex_ai():
    """Example: Using Vertex AI for reasoning"""
    print("\n=== Vertex AI Agent Example ===\n")

    # Get service
    vertex_service = get_vertex_ai_service()

    # Process text
    print("Processing text with Vertex AI...")
    response = await vertex_service.process_text(
        prompt="Summarize the key points about cloud-native architecture in 3 bullet points."
    )
    print(f"✅ Response:\n{response.text}\n")
    print(f"   Usage: {response.usage}")

    # Generate embeddings
    print("\nGenerating embeddings...")
    texts = [
        "Cloud-native architecture uses microservices",
        "Vertex AI provides agent reasoning",
        "Firestore manages shared state"
    ]
    embeddings = await vertex_service.generate_embeddings(texts)
    print(f"✅ Generated {len(embeddings)} embeddings")
    print(f"   Dimension: {len(embeddings[0])}")


async def example_video_processor():
    """Example: Using cloud video processor"""
    print("\n=== Cloud Video Processor Example ===\n")

    # Get processor
    processor = get_cloud_video_processor()

    # Process video asynchronously
    print("Enqueuing video for async processing...")
    task_id = await processor.process_video_async(
        video_url="https://youtube.com/watch?v=test789",
        priority=7
    )
    print(f"✅ Task ID: {task_id}")

    # Check status
    print("\nChecking processing status...")
    status = await processor.get_processing_status("test789")
    if status:
        print(f"✅ Status: {status.status} - {status.current_stage}")
    else:
        print("⚠️  No status found (expected for example)")

    # Process video synchronously (for testing)
    # Note: This will fail without real YouTube API credentials
    # print("\nProcessing video synchronously...")
    # result = await processor.process_video_sync(
    #     video_url="https://youtube.com/watch?v=dQw4w9WgXcQ"
    # )
    # print(f"✅ Result: {result.success}")


async def example_batch_processing():
    """Example: Batch processing multiple videos"""
    print("\n=== Batch Processing Example ===\n")

    processor = get_cloud_video_processor()

    video_urls = [
        "https://youtube.com/watch?v=video1",
        "https://youtube.com/watch?v=video2",
        "https://youtube.com/watch?v=video3",
    ]

    print(f"Enqueuing {len(video_urls)} videos for batch processing...")
    task_ids = await processor.batch_process_async(
        video_urls=video_urls,
        priority=3
    )
    print(f"✅ Enqueued {len(task_ids)} tasks")
    for i, task_id in enumerate(task_ids, 1):
        print(f"   {i}. {task_id}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Cloud Services Examples")
    print("=" * 60)

    try:
        # Run examples
        await example_firestore()
        await example_cloud_tasks()
        await example_vertex_ai()
        await example_video_processor()
        await example_batch_processing()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        print("Make sure you have:")
        print("1. Set GOOGLE_CLOUD_PROJECT environment variable")
        print("2. Run infrastructure/cloudrun/setup.sh")
        print("3. Configured authentication (gcloud auth application-default login)")


if __name__ == "__main__":
    # Check configuration
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        print("\n⚠️  Warning: GOOGLE_CLOUD_PROJECT not set")
        print("Set it with: export GOOGLE_CLOUD_PROJECT='your-project-id'\n")

    asyncio.run(main())
