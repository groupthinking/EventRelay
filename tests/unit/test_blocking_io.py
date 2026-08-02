"""Unit tests for utils/blocking_io.py — executor isolation for blocking I/O.

Covers issue #1234: every ``asyncio.to_thread`` / ``run_in_executor(None, ...)``
call in the process shares one bounded default ``ThreadPoolExecutor``. A blocking
read that never returns (NFS/FUSE) permanently leaks a worker slot, because
cancelling the awaiting coroutine does *not* reclaim the thread. Enough
concurrent stalls exhaust the pool and unrelated subsystems stop making progress.

The tests below pin *isolation* in both directions. Off-loop behaviour is already
covered by the provider suites; running off the loop but still on the shared pool
is exactly the failure mode #1234 describes, so "off the loop" is not sufficient.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from youtube_extension.utils.blocking_io import (  # noqa: E402
    get_blocking_io_executor,
    reset_blocking_io_executor,
    run_blocking,
)

# Bound every wait so a regression fails the suite instead of hanging it.
_TIMEOUT = 10.0


@pytest.fixture(autouse=True)
def _isolated_executor(monkeypatch):
    """Give each test a small, private I/O pool so saturation is exact."""
    monkeypatch.setenv("BLOCKING_IO_MAX_WORKERS", "2")
    reset_blocking_io_executor()
    yield
    reset_blocking_io_executor()


class _Saturator:
    """Occupies every worker of a pool until released.

    ``entered`` is released once per worker that has actually started running,
    so a test can wait for genuine saturation instead of sleeping and hoping.
    """

    def __init__(self, workers: int):
        self.workers = workers
        self.entered = threading.Semaphore(0)
        self.release = threading.Event()

    def hog(self) -> str:
        self.entered.release()
        # Bounded so a bug can never wedge the suite; far longer than any assert.
        self.release.wait(_TIMEOUT * 3)
        return "done"

    async def wait_until_saturated(self) -> None:
        """Wait for genuine saturation without starving the event loop.

        Must yield between polls: the hogs are scheduled as tasks, and a task
        does not begin executing until the loop gets control. A *blocking*
        acquire here would deadlock the harness before any hog reached the pool
        and produce a failure that looks like a product bug but is not one.
        """
        deadline = time.monotonic() + _TIMEOUT
        started = 0
        while started < self.workers:
            if self.entered.acquire(blocking=False):
                started += 1
                continue
            assert time.monotonic() < deadline, (
                f"only {started}/{self.workers} workers started; the pool is "
                "smaller than expected or the harness is broken"
            )
            await asyncio.sleep(0.01)

    def free(self) -> None:
        self.release.set()


# ---------------------------------------------------------------------------
# AC2 (literal): saturating the I/O pool must not block unrelated to_thread work
# ---------------------------------------------------------------------------


class TestIoPoolSaturationDoesNotStarveOthers:
    async def test_unrelated_to_thread_completes_while_io_pool_is_saturated(self):
        pool = get_blocking_io_executor()
        capacity = pool._max_workers  # noqa: SLF001 - asserting the bound we set
        assert capacity == 2

        sat = _Saturator(capacity)
        hogs = [asyncio.create_task(run_blocking(sat.hog)) for _ in range(capacity)]
        try:
            await sat.wait_until_saturated()

            # The I/O pool now has zero free workers. An unrelated subsystem
            # using the default executor must be completely unaffected.
            result = await asyncio.wait_for(
                asyncio.to_thread(lambda: "unrelated-ok"), timeout=_TIMEOUT
            )
            assert result == "unrelated-ok"
        finally:
            sat.free()
            await asyncio.gather(*hogs)

    async def test_io_offloads_do_not_run_on_the_default_executor(self):
        """Direct structural check: the worker thread is not a default-pool thread."""
        loop = asyncio.get_running_loop()
        previous = getattr(loop, "_default_executor", None)
        default_pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="default-probe"
        )
        loop.set_default_executor(default_pool)
        try:
            default_thread = await asyncio.to_thread(threading.current_thread)
            io_thread = await run_blocking(threading.current_thread)

            assert io_thread is not default_thread
            assert not io_thread.name.startswith("default-probe"), (
                "blocking I/O ran on the shared default executor; it must use "
                "the dedicated pool so a stall cannot starve other subsystems"
            )
        finally:
            if previous is None:
                # ``set_default_executor`` rejects ``None``; restore directly.
                loop._default_executor = None  # noqa: SLF001
            else:
                loop.set_default_executor(previous)
            default_pool.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Helper contract
# ---------------------------------------------------------------------------


class TestRunBlockingContract:
    async def test_runs_off_the_event_loop_thread(self):
        loop_thread = threading.get_ident()
        worker_thread = await run_blocking(threading.get_ident)
        assert worker_thread != loop_thread

    async def test_supports_keyword_arguments(self):
        """``run_in_executor`` takes no kwargs; the helper must bridge that."""

        def _join(a, b, sep="-"):
            return f"{a}{sep}{b}"

        assert await run_blocking(_join, "x", "y", sep="+") == "x+y"

    async def test_propagates_exceptions_unchanged(self):
        def _boom():
            raise FileNotFoundError("missing")

        with pytest.raises(FileNotFoundError, match="missing"):
            await run_blocking(_boom)

    async def test_timeout_releases_the_caller(self):
        """A deadline bounds the *caller*. It cannot reclaim the worker — that is
        precisely why isolation, not timeouts, is the fix — but an unbounded
        caller hang is still worth preventing."""
        sat = _Saturator(1)
        task = asyncio.create_task(run_blocking(sat.hog, timeout=0.25))
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(task, timeout=_TIMEOUT)
        finally:
            sat.free()

    def test_pool_size_is_configurable_and_bounded(self, monkeypatch):
        monkeypatch.setenv("BLOCKING_IO_MAX_WORKERS", "5")
        reset_blocking_io_executor()
        assert get_blocking_io_executor()._max_workers == 5  # noqa: SLF001

    def test_invalid_pool_size_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("BLOCKING_IO_MAX_WORKERS", "not-a-number")
        reset_blocking_io_executor()
        assert get_blocking_io_executor()._max_workers > 0  # noqa: SLF001

    def test_executor_is_a_process_wide_singleton(self):
        assert get_blocking_io_executor() is get_blocking_io_executor()


# ---------------------------------------------------------------------------
# AC3: saturation must be observable
# ---------------------------------------------------------------------------


class TestSaturationIsObservable:
    async def test_warns_when_the_pool_is_saturated(self, caplog):
        pool = get_blocking_io_executor()
        capacity = pool._max_workers  # noqa: SLF001
        sat = _Saturator(capacity)
        hogs = [asyncio.create_task(run_blocking(sat.hog)) for _ in range(capacity)]
        try:
            await sat.wait_until_saturated()
            with caplog.at_level(logging.WARNING, logger="youtube_extension.utils.blocking_io"):
                extra = asyncio.create_task(run_blocking(lambda: "queued"))
                await asyncio.sleep(0)  # let the submit path run
                sat.free()
                assert await asyncio.wait_for(extra, timeout=_TIMEOUT) == "queued"

            saturation_records = [
                r for r in caplog.records if "saturat" in r.getMessage().lower()
            ]
            assert saturation_records, (
                "pool saturation produced no warning; exhaustion must be "
                "observable before it becomes an outage"
            )
            record = saturation_records[0]
            assert getattr(record, "max_workers", None) == capacity
        finally:
            sat.free()
            await asyncio.gather(*hogs)

    async def test_no_warning_when_pool_is_idle(self, caplog):
        with caplog.at_level(logging.WARNING, logger="youtube_extension.utils.blocking_io"):
            await run_blocking(lambda: None)
        assert not [r for r in caplog.records if "saturat" in r.getMessage().lower()]
