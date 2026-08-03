"""Isolated, bounded thread pool for blocking I/O offloads.

Why this module exists (issue #1234)
------------------------------------
``asyncio.to_thread(fn)`` is defined as ``loop.run_in_executor(None, fn)``: it
runs on the loop's **shared default** ``ThreadPoolExecutor``, sized
``min(32, cpu_count + 4)``. Every ``to_thread`` and every
``run_in_executor(None, ...)`` caller in the process therefore competes for the
same small pool.

That is fine for work that always terminates. It is not fine for file I/O. A
path handed to ``open()`` may resolve to NFS/FUSE/remote-backed storage and stall
without limit, and a stalled work item **permanently leaks its worker slot**:

    task = asyncio.create_task(asyncio.to_thread(blocking_read))
    task.cancel()          # the *caller* is released...
                           # ...the worker thread is still stuck.

``concurrent.futures`` cannot interrupt a thread that is blocked in a syscall, so
cancellation frees the awaiting coroutine and nothing else. Enough concurrent
stalls exhaust the pool and every unrelated subsystem that uses ``to_thread``
stops making progress.

A timeout does not fix this. ``asyncio.wait_for`` bounds the *caller*, not the
*worker*; it converts an indefinite hang into a prompt error (worth having) but
returns no capacity to the pool. The only thing that actually contains the
failure is **isolation**: give blocking I/O its own bounded pool, so a stall can
exhaust that pool and never the one the rest of the process depends on.

Usage::

    from youtube_extension.utils.blocking_io import run_blocking

    data = await run_blocking(_read_file_bytes, path)

Configuration
-------------
``BLOCKING_IO_MAX_WORKERS`` — worker count for the dedicated pool. Defaults to
``8``. Invalid or non-positive values fall back to the default rather than
raising, since a bad env var must not take the process down at import time.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_WORKERS_ENV = "BLOCKING_IO_MAX_WORKERS"
_DEFAULT_MAX_WORKERS = 8
_THREAD_NAME_PREFIX = "blocking-io"

# Sustained saturation would otherwise emit one warning per submission and drown
# the logs at exactly the moment they matter most.
_SATURATION_WARN_INTERVAL_SECONDS = 30.0

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()

_state_lock = threading.Lock()
_in_flight = 0
_last_saturation_warning = 0.0


def _configured_max_workers() -> int:
    """Read the pool size from the environment, tolerating bad input."""
    raw = os.environ.get(_MAX_WORKERS_ENV)
    if raw is None or not raw.strip():
        return _DEFAULT_MAX_WORKERS
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        logger.warning(
            "%s=%r is not an integer; falling back to %d workers",
            _MAX_WORKERS_ENV,
            raw,
            _DEFAULT_MAX_WORKERS,
        )
        return _DEFAULT_MAX_WORKERS
    if value <= 0:
        logger.warning(
            "%s=%r must be positive; falling back to %d workers",
            _MAX_WORKERS_ENV,
            raw,
            _DEFAULT_MAX_WORKERS,
        )
        return _DEFAULT_MAX_WORKERS
    return value


def get_blocking_io_executor() -> ThreadPoolExecutor:
    """Return the process-wide executor dedicated to blocking I/O.

    Built lazily under a lock so concurrent first-callers cannot race two pools
    into existence.
    """
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_configured_max_workers(),
                    thread_name_prefix=_THREAD_NAME_PREFIX,
                )
    return _executor


def reset_blocking_io_executor() -> None:
    """Dispose of the current pool so the next call rebuilds it.

    Intended for tests and for process lifecycle hooks. ``wait=False`` because a
    genuinely stuck worker is precisely what this module exists to contain —
    blocking shutdown on it would reintroduce the hang.
    """
    global _executor, _in_flight, _last_saturation_warning
    with _executor_lock:
        previous, _executor = _executor, None
    with _state_lock:
        _in_flight = 0
        _last_saturation_warning = 0.0
    if previous is not None:
        previous.shutdown(wait=False)


def _enter(max_workers: int) -> None:
    """Account for a submission and warn (throttled) once the pool is oversubscribed."""
    global _in_flight, _last_saturation_warning
    with _state_lock:
        _in_flight += 1
        in_flight = _in_flight
        if in_flight <= max_workers:
            return
        now = time.monotonic()
        if now - _last_saturation_warning < _SATURATION_WARN_INTERVAL_SECONDS:
            return
        _last_saturation_warning = now
    logger.warning(
        "blocking I/O pool saturated: %d in flight for %d workers; %d call(s) "
        "queued. A stalled read holds its worker until it returns.",
        in_flight,
        max_workers,
        in_flight - max_workers,
        extra={
            "in_flight": in_flight,
            "max_workers": max_workers,
            "queued": in_flight - max_workers,
        },
    )


def _exit() -> None:
    global _in_flight
    with _state_lock:
        _in_flight = max(0, _in_flight - 1)


async def run_blocking(
    func: Callable[..., T],
    *args: Any,
    timeout: float | None = None,
    **kwargs: Any,
) -> T:
    """Run ``func`` on the dedicated blocking-I/O pool.

    Args:
        func: Blocking callable. Must be safe to run off the event loop.
        *args: Positional arguments for ``func``.
        timeout: Optional caller-side deadline in seconds. Bounds *this
            coroutine* only — see the module docstring: a timed-out worker keeps
            running until its syscall returns. Isolation, not the timeout, is
            what prevents starvation.
        **kwargs: Keyword arguments for ``func``. ``run_in_executor`` accepts
            none, so they are bound with ``functools.partial``.

    Raises:
        asyncio.TimeoutError: If ``timeout`` elapses first.
        Exception: Whatever ``func`` raised, unwrapped and unmodified.
    """
    executor = get_blocking_io_executor()
    call = functools.partial(func, *args, **kwargs)
    _enter(executor._max_workers)  # noqa: SLF001 - stdlib exposes no public getter

    # Submit to the executor directly rather than via ``run_in_executor`` so the
    # completion callback can be attached to the *concurrent* future. That makes
    # ``_in_flight`` track real worker occupancy: a caller released by ``timeout``
    # leaves its worker running, and this keeps counting it. Attaching to the
    # asyncio future instead would decrement on cancellation and hide exactly the
    # leaked slots this instrumentation exists to reveal.
    try:
        worker_future = executor.submit(call)
    except RuntimeError:
        _exit()
        raise
    worker_future.add_done_callback(lambda _f: _exit())

    awaitable = asyncio.wrap_future(worker_future)
    if timeout is None:
        return await awaitable
    return await asyncio.wait_for(awaitable, timeout=timeout)
