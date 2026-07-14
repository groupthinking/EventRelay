from __future__ import annotations

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


async def process(msg: dict) -> None:
    """Handle a single consumed message.

    No real task handler is wired up yet. Per the REAL_MODE_ONLY policy we must
    not fake success with a mock delay: raising here leaves the message
    unacknowledged (retained in the stream's pending list) rather than silently
    dropping real work behind a stub that immediately gets xack'ed.
    """
    logger.info(f"Received message (no handler implemented yet): {msg}")
    raise NotImplementedError(
        "Orchestrator task handler is not implemented; message left unacknowledged"
    )


async def ensure_consumer_group(
    redis_client: redis.Redis, stream_name: str, consumer_group: str
) -> None:
    """Ensure the Redis Streams consumer group exists.

    Only the "already exists" (BUSYGROUP) case is treated as success. Any other
    error — most importantly a transient ConnectionError while Redis is still
    starting up — is re-raised so the caller can retry. Swallowing those errors
    would leave the group uncreated while the consumer keeps looping, producing a
    permanent NOGROUP failure that never recovers and never consumes any tasks.
    """
    try:
        await redis_client.xgroup_create(
            stream_name, consumer_group, id='0', mkstream=True
        )
        logger.info(
            f"Created consumer group '{consumer_group}' for stream '{stream_name}'"
        )
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.debug(f"Consumer group '{consumer_group}' already exists")
        else:
            raise


async def main() -> None:
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

    def signal_handler() -> None:
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
            # Bounded timeouts so a hung/half-open connection surfaces as an
            # exception (which the loop handles) instead of blocking xreadgroup /
            # xack / xgroup_create indefinitely. socket_timeout must exceed the
            # 1s xreadgroup block below.
            redis_client = redis.from_url(
                redis_url,
                socket_connect_timeout=5,
                socket_timeout=10,
            )
            # Redact credentials from URL for safe logging
            safe_url = redact_url(redis_url)
            logger.info(f"✅ Orchestrator initialized, connecting to Redis at {safe_url} (Stream: {stream_name})")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            redis_client = None

    if redis_client is None:
        logger.info("✅ Orchestrator initialized and waiting for tasks (Mode: Standby)")

    # Whether the consumer group has been confirmed to exist. Created lazily inside
    # the loop so a transient failure at startup is retried instead of stranding the
    # consumer, and reset on any loop error so a lost connection or a missing group
    # (NOGROUP) triggers re-creation on the next iteration.
    group_ready = False

    # Main loop
    while not stop_event.is_set():
        try:
            if redis_client:
                if not group_ready:
                    await ensure_consumer_group(redis_client, stream_name, consumer_group)
                    group_ready = True

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
                    for _stream, messages in results:
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
            # Force the group to be re-ensured next iteration: the failure may be a
            # dropped connection or a missing group (NOGROUP) that needs re-creating.
            group_ready = False
            logger.error(f"Error in orchestrator loop: {e}")
            await asyncio.sleep(5)

    if redis_client:
        await redis_client.aclose()

    logger.info("👋 Orchestrator shutting down")

if __name__ == "__main__":
    asyncio.run(main())
