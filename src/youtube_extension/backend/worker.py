#!/usr/bin/env python3
"""
UVAI Backend Worker
=========================

Consumes video processing events from Pub/Sub and invokes the video processing service.
Designed to run as a standalone service.
"""

import os
import json
import logging
import asyncio
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
from youtube_extension.backend.containers.service_container import get_service_container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "uvai-730bb")
SUBSCRIPTION_ID = os.getenv("PUBSUB_SUBSCRIPTION_ID", "uvai-backend-worker")

def process_message(message):
    """
    Callback for handling Pub/Sub messages.
    """
    logger.info(f"Received message: {message.message_id}")
    
    try:
        data = json.loads(message.data.decode("utf-8"))
        video_url = data.get("video_url")
        options = data.get("options", {})
        
        if not video_url:
            logger.warning("Message missing video_url, acking to drop.")
            message.ack()
            return

        logger.info(f"Processing video: {video_url}")

        # Run async processing in a new event loop for this thread
        # Note: In a production pull-subscriber, we might want to manage the loop differently
        # or use an async-compatible client library if available. 
        # For simplicity here, we run safe.
        asyncio.run(run_processing(video_url, options))
        
        message.ack()
        logger.info(f"Message {message.message_id} acknowledged.")

    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        # Build-in retry via nack
        message.nack()

async def run_processing(video_url, options):
    """
    Async wrapper to call the service.
    """
    container = get_service_container()
    service = container.get_service("video_processing_service")
    
    try:
        result = await service.process_video_basic(video_url, options)
        logger.info(f"Processing complete for {video_url}. Status: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"Service processing error: {e}")
        raise e

def main():
    logger.info(f"Starting worker for subscription: projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_ID}")
    
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_message)
    logger.info(f"Listening for messages on {subscription_path}...")

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result()
        except TimeoutError:
            streaming_pull_future.cancel()  # Trigger the shutdown.
            streaming_pull_future.result()  # Block until the shutdown is complete.
        except Exception as e:
            logger.error(f"Subscriber failure: {e}")
            streaming_pull_future.cancel()
            streaming_pull_future.result()

if __name__ == "__main__":
    main()
