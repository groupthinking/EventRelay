## 2026-07-12 - Resilient Asyncio Consumers

**Learning:** When replacing blocking tasks with `asyncio.wait_for` or similar timeouts (e.g. `blpop` in Redis), graceful shutdown can be delayed if the shutdown event is not checked during the blocking wait. Racing a `stop_event.wait()` against a blocking queue read using `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` prevents shutdown delays while accurately handling the queue.

**Action:** Ensure all long-running tasks or blocking queue consumers in asyncio loops are raced against a shutdown event to allow immediate, graceful application termination upon receiving SIGINT/SIGTERM.
