import asyncio
import logging
import os
import signal
from urllib.parse import urlparse

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orchestrator")


def redact_url(url: str) -> str:
    """Redact credentials from URL for safe logging."""
    try:
        parsed = urlparse(url)
        if parsed.password or parsed.username:
            redacted = parsed._replace(netloc=f"{parsed.username or ''}:***@{parsed.hostname}:{parsed.port or ''}")
            return redacted.geturl()
        return url.split('@')[-1] if '@' in url else url
    except Exception:
        return "redis://***"


async def process(msg):
    """Placeholder processing function"""
    logger.info(f"Processing message: {msg}")
    # Simulate processing time
    await asyncio.sleep(0.1)


async def main():
    """
    Main Orchestrator Loop.

    In a full production environment, this service would consume messages from
    RabbitMQ or Redis to trigger video processing tasks asynchronously.

    Current Status: Implemented Redis Streams consumer with acknowledged delivery.
    """
    logger.info("🚀 Orchestrator Service Starting...")

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("🛑 Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Accept REDIS_URL as fallback for deployed environments
    redis_url = os.getenv("MESSAGE_QUEUE_URL") or os.getenv("REDIS_URL", "redis://localhost:6379")
    stream_name = os.getenv("ORCHESTRATOR_QUEUE_NAME", "orchestrator_tasks")
    consumer_group = os.getenv("ORCHESTRATOR_CONSUMER_GROUP", "orchestrator_workers")
    consumer_name = os.getenv("HOSTNAME", "orchestrator_1")
    redis_client = None

    if redis is not None:
        try:
            redis_client = redis.from_url(redis_url)
            # Redact credentials from URL for safe logging
            safe_url = redact_url(redis_url)
            logger.info(f"✅ Orchestrator initialized and connected to Redis at {safe_url} (Stream: {stream_name})")
            
            # Create consumer group if it doesn't exist (ignore if already exists)
            try:
                await redis_client.xgroup_create(stream_name, consumer_group, id='0', mkstream=True)
                logger.info(f"Created consumer group '{consumer_group}' for stream '{stream_name}'")
            except Exception as e:
                # Group already exists, which is fine
                logger.debug(f"Consumer group setup: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            redis_client = None

    if redis_client is None:
        logger.info("✅ Orchestrator initialized and waiting for tasks (Mode: Standby)")

    # Main loop
    while not stop_event.is_set():
        try:
            if redis_client:
                # Use Redis Streams with consumer groups for acknowledged delivery
                # Read with 1 second block timeout so we can check stop_event frequently
                results = await redis_client.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {stream_name: '>'},
                    count=1,
                    block=1000  # 1 second in milliseconds
                )
                
                if results:
                    for stream, messages in results:
                        for message_id, data in messages:
                            try:
                                # Process the message
                                await process(data)
                                # Acknowledge successful processing
                                await redis_client.xack(stream_name, consumer_group, message_id)
                                logger.debug(f"Acknowledged message {message_id}")
                            except Exception as proc_error:
                                logger.error(f"Failed to process message {message_id}: {proc_error}")
                                # Message remains unacknowledged and can be reclaimed
            else:
                # Heartbeat for standby mode
                await asyncio.sleep(60)
                logger.debug("❤️ Orchestrator heartbeat")

        except Exception as e:
            logger.error(f"Error in orchestrator loop: {e}")
            await asyncio.sleep(5)

    if redis_client:
        await redis_client.aclose()

    logger.info("👋 Orchestrator shutting down")

if __name__ == "__main__":
    asyncio.run(main())
