## 2026-09-12 - Synchronous HTTP Request in Async Event Loop Optimization

*   **Identified Issue**: The `_transfer_via_webhook` method in `scripts/archive/video_transfer_pipeline.py` is defined as an `async def` coroutine but was using the synchronous `requests.post()` method. This is a common and critical performance anti-pattern. Because `requests.post` is blocking, it ties up the thread executing the asyncio event loop while waiting for the network response, stalling all other asynchronous operations that could run concurrently.
*   **Action Taken**: I replaced the blocking `requests.post()` call with an asynchronous `aiohttp.ClientSession().post()` block. This correctly yields execution back to the event loop during the network wait time.
*   **Measurement**: I simulated the behavior using synthetic benchmarks representing 10 concurrent webhook requests taking 0.5s each.
    *   **Baseline (Blocking)**: All 10 requests ran sequentially, taking **5.00s** total.
    *   **Optimized (Async)**: All 10 requests ran concurrently, taking **0.50s** total.
    *   **Result**: 10.0x performance improvement for concurrent requests.
## 2026-09-12 - Parallelizing Video Transcript Fetches
When executing API calls inside loops for transcript fetching via `YouTubeTranscriptApi`, the sequential execution introduces heavy N+1 bottlenecks. Modifying to `asyncio.create_task` combined with awaiting them allows for parallel execution which drastically reduces the operation cost if the primary fetch falls back or fails, reducing a 2.5s simulated operation down to 0.5s. Note that to preserve strict ordering prioritization, `asyncio.as_completed` should be avoided in favor of direct ordered loop evaluation.
