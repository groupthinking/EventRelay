import asyncio
import logging
import os
import json
import redis.asyncio as redis
import signal

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orchestrator")

async def main():
    """
    Main Orchestrator Loop.

    In a full production environment, this service would consume messages from
    RabbitMQ or Redis to trigger video processing tasks asynchronously.

    Current Status: Placeholder for future async worker implementation.
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

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    queue_name = os.getenv("ORCHESTRATOR_QUEUE", "orchestrator:tasks")

    try:
        redis_client = redis.from_url(redis_url)
        # Test connection
        await redis_client.ping()
        logger.info(f"✅ Connected to Redis at {redis_url}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        redis_client = None

    if redis_client:
        logger.info(f"✅ Orchestrator initialized and waiting for tasks on '{queue_name}' (Mode: Active)")
    else:
        logger.warning("⚠️ Orchestrator initialized without Redis (Mode: Standby)")

    # Main loop
    while not stop_event.is_set():
        try:
            if redis_client:
                # Wait for messages using BLPOP or stop_event using wait()
                # BLPOP blocks, so we wrap it in an asyncio.Task and wait for either it or stop_event
                blpop_task = asyncio.create_task(redis_client.blpop([queue_name], timeout=60))
                stop_task = asyncio.create_task(stop_event.wait())

                done, pending = await asyncio.wait(
                    [blpop_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                if stop_task in done:
                    break

                # Await or get the result to properly raise connection exceptions
                # so the outer except block catches it and sleeps
                task_data = blpop_task.result() if not blpop_task.cancelled() else None

                if task_data:
                    _, message = task_data
                    try:
                        parsed_msg = json.loads(message)
                        logger.info(f"📥 Received task: {parsed_msg}")
                        # Future: route to specific agent or task processor
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ Received invalid JSON task: {message}")
                else:
                    # BLPOP timed out, use this as a heartbeat
                    logger.debug("❤️ Orchestrator heartbeat")
            else:
                # Fallback to simple heartbeat if Redis is unavailable
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=60)
                except asyncio.TimeoutError:
                    logger.debug("❤️ Orchestrator heartbeat")

        except Exception as e:
            logger.error(f"Error in orchestrator loop: {e}")
            await asyncio.sleep(5)

    if redis_client:
        await redis_client.close()

    logger.info("👋 Orchestrator shutting down")

if __name__ == "__main__":
    asyncio.run(main())
