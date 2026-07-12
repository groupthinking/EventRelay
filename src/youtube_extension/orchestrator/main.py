import asyncio
import logging
import os
import signal

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

    Current Status: Implemented Redis consumer with fallback to Standby mode.
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

    redis_url = os.getenv("MESSAGE_QUEUE_URL", "redis://localhost:6379")
    queue_name = os.getenv("ORCHESTRATOR_QUEUE_NAME", "orchestrator_tasks")
    redis_client = None

    if redis is not None:
        try:
            # We don't verify connection on initialization as blpop will fail if invalid
            redis_client = redis.from_url(redis_url)
            logger.info(f"✅ Orchestrator initialized and connected to Redis at {redis_url} (Queue: {queue_name})")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            redis_client = None

    if redis_client is None:
        logger.info("✅ Orchestrator initialized and waiting for tasks (Mode: Standby)")

    # Main loop
    while not stop_event.is_set():
        try:
            if redis_client:
                # Use blpop with a timeout of 1 second so we can check stop_event frequently
                result = await redis_client.blpop(queue_name, timeout=1)
                if result:
                    _, msg = result
                    await process(msg)
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
