"""Dedicated executor for potentially blocking Cloud AI local file I/O."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_DEFAULT_IO_WORKERS = max(1, min(8, (os.cpu_count() or 1)))


def _io_max_workers_from_env() -> int:
    raw = os.environ.get("CLOUD_AI_IO_MAX_WORKERS")
    if raw is None or not raw.strip():
        return _DEFAULT_IO_WORKERS
    try:
        return max(1, int(raw))
    except ValueError:
        logger.warning(
            "Invalid CLOUD_AI_IO_MAX_WORKERS=%r; using default=%d",
            raw,
            _DEFAULT_IO_WORKERS,
        )
        return _DEFAULT_IO_WORKERS


_IO_MAX_WORKERS = _io_max_workers_from_env()
_IO_EXECUTOR = ThreadPoolExecutor(
    max_workers=_IO_MAX_WORKERS,
    thread_name_prefix="cloud-ai-io",
)
_IO_ACTIVE = 0
_IO_QUEUED = 0
_IO_STATE_LOCK = threading.Lock()


def _log_pool_pressure(*, active: int, queued: int) -> None:
    if active + queued < _IO_MAX_WORKERS:
        return
    logger.warning(
        "blocking_io_pool_near_capacity active=%d queued=%d max_workers=%d",
        active,
        queued,
        _IO_MAX_WORKERS,
    )


async def run_blocking(
    func: Callable[..., _T], *args: Any, timeout: float | None = None, **kwargs: Any
) -> _T:
    """Run blocking work on the Cloud AI local-I/O pool."""
    loop = asyncio.get_running_loop()

    with _IO_STATE_LOCK:
        global _IO_QUEUED
        _IO_QUEUED += 1
        active = _IO_ACTIVE
        queued = _IO_QUEUED
    _log_pool_pressure(active=active, queued=queued)

    def _invoke() -> _T:
        global _IO_ACTIVE, _IO_QUEUED
        with _IO_STATE_LOCK:
            _IO_QUEUED -= 1
            _IO_ACTIVE += 1
        try:
            return func(*args, **kwargs)
        finally:
            with _IO_STATE_LOCK:
                _IO_ACTIVE -= 1

    future = loop.run_in_executor(_IO_EXECUTOR, _invoke)
    if timeout is None:
        return await future
    return await asyncio.wait_for(future, timeout=timeout)
