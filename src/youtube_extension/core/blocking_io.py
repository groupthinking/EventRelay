"""Dedicated executor for blocking file/OS I/O offloads.

Every ``asyncio.to_thread(...)`` / ``run_in_executor(None, ...)`` call in the
process shares asyncio's *default* executor, whose worker count is bounded
(``min(32, cpu_count + 4)``). A work item that blocks indefinitely — e.g. an
``open()``/``read()`` against an NFS/FUSE-backed mount — leaks that worker slot
permanently: cancelling the awaiting coroutine releases the *caller* but never
interrupts the *thread*. Enough concurrent stalls exhaust the shared pool and
every ``to_thread`` user in the process stops making progress, including
unrelated subsystems.

This module isolates that blast radius. ``run_blocking(...)`` routes offloads
onto a dedicated, explicitly-sized :class:`~concurrent.futures.ThreadPoolExecutor`
so a pile-up of stalled I/O can exhaust *this* pool only, never the default one
the rest of the process depends on. It also provides one place to attach a
caller-side deadline and saturation observability.

Deliberately **not** attempted here: cancelling a stuck worker thread. CPython
offers no safe way to interrupt a thread parked in a syscall, so a caller-side
timeout bounds the coroutine, not the thread. Isolation is the containment.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar

from youtube_extension.core.env_config import positive_int_env

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Small by design: this pool exists to be expendable. If it is too small for a
# workload the symptom is queueing (visible via the saturation warning below),
# not process-wide starvation.
_DEFAULT_MAX_WORKERS = 8
_MAX_WORKERS_CEILING = 128

# Log at most one saturation warning per this many seconds so a sustained
# stall does not flood the logs with one line per queued offload.
_SATURATION_LOG_INTERVAL_SECONDS = 30.0

_lock = threading.Lock()
_executor: Optional[ThreadPoolExecutor] = None
_max_workers: int = 0
_in_flight: int = 0
_last_saturation_log: float = float("-inf")


def _create_executor() -> ThreadPoolExecutor:
    max_workers = positive_int_env(
        "BLOCKING_IO_MAX_WORKERS",
        _DEFAULT_MAX_WORKERS,
        maximum=_MAX_WORKERS_CEILING,
    )
    global _max_workers
    _max_workers = max_workers
    return ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="blocking-io"
    )


def get_blocking_io_executor() -> ThreadPoolExecutor:
    """Return the process-wide blocking-I/O executor, creating it lazily."""
    global _executor
    with _lock:
        if _executor is None:
            _executor = _create_executor()
        return _executor


def reset_blocking_io_executor() -> None:
    """Discard the current executor so the next use creates a fresh one.

    Test hook: lets a test resize the pool via ``BLOCKING_IO_MAX_WORKERS`` or
    recover from a deliberately saturated pool. Does not wait for in-flight
    work (a stuck worker cannot be waited out anyway).
    """
    global _executor, _in_flight, _last_saturation_log
    with _lock:
        if _executor is not None:
            _executor.shutdown(wait=False)
        _executor = None
        _in_flight = 0
        _last_saturation_log = float("-inf")


def _track_submit(now: float) -> None:
    """Record a submission and warn when the pool is saturated."""
    global _in_flight, _last_saturation_log
    with _lock:
        _in_flight += 1
        queued = _in_flight - _max_workers
        if queued < 0:
            return
        if now - _last_saturation_log < _SATURATION_LOG_INTERVAL_SECONDS:
            return
        _last_saturation_log = now
        in_flight, max_workers = _in_flight, _max_workers
    logger.warning(
        "Blocking I/O executor saturated: %d offloads in flight against "
        "%d workers (%d queued). If this persists, workers may be stuck in "
        "uninterruptible I/O (e.g. a stalled network mount).",
        in_flight,
        max_workers,
        queued,
    )


def _track_done(_future: object) -> None:
    global _in_flight
    with _lock:
        _in_flight -= 1


async def run_blocking(
    func: Callable[..., T],
    /,
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> T:
    """Run ``func(*args, **kwargs)`` on the dedicated blocking-I/O executor.

    Drop-in replacement for ``asyncio.to_thread`` for file/OS I/O offloads.

    ``timeout`` (seconds) bounds the *caller*: on expiry the awaiting coroutine
    gets :class:`asyncio.TimeoutError`, but the worker thread keeps running
    until the blocking call returns — CPython cannot interrupt it. The pool
    isolation, not the timeout, is what protects the rest of the process.
    """
    loop = asyncio.get_running_loop()
    executor = get_blocking_io_executor()
    _track_submit(loop.time())
    future = loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))
    future.add_done_callback(_track_done)
    if timeout is None:
        return await future
    return await asyncio.wait_for(future, timeout=timeout)
