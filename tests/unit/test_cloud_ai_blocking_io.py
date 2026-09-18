from __future__ import annotations

import asyncio
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import youtube_extension.integrations.cloud_ai.blocking_io as blocking_io


@pytest.fixture
def isolated_pool(monkeypatch):
    original_executor = blocking_io._IO_EXECUTOR
    original_limit = blocking_io._IO_MAX_WORKERS
    gate = threading.Event()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="test-cloud-ai-io")
    monkeypatch.setattr(blocking_io, "_IO_EXECUTOR", executor)
    monkeypatch.setattr(blocking_io, "_IO_MAX_WORKERS", 1)
    try:
        yield gate
    finally:
        gate.set()
        executor.shutdown(wait=True)
        monkeypatch.setattr(blocking_io, "_IO_EXECUTOR", original_executor)
        monkeypatch.setattr(blocking_io, "_IO_MAX_WORKERS", original_limit)


@pytest.mark.asyncio
async def test_saturated_io_pool_does_not_starve_default_to_thread(isolated_pool):
    entered = threading.Event()

    def blocker():
        entered.set()
        isolated_pool.wait()
        return "released"

    first = asyncio.create_task(blocking_io.run_blocking(blocker, timeout=0.05))
    await asyncio.wait_for(asyncio.to_thread(entered.wait, 1), timeout=1)
    second = asyncio.create_task(blocking_io.run_blocking(blocker, timeout=0.05))

    with pytest.raises(asyncio.TimeoutError):
        await first
    with pytest.raises(asyncio.TimeoutError):
        await second

    result = await asyncio.wait_for(asyncio.to_thread(lambda: "default-ok"), timeout=0.5)
    assert result == "default-ok"


@pytest.mark.asyncio
async def test_logs_warning_when_io_pool_is_at_capacity(isolated_pool, caplog):
    entered = threading.Event()

    def blocker():
        entered.set()
        isolated_pool.wait()
        return "released"

    with caplog.at_level(logging.WARNING):
        first = asyncio.create_task(blocking_io.run_blocking(blocker, timeout=0.05))
        await asyncio.wait_for(asyncio.to_thread(entered.wait, 1), timeout=1)
        second = asyncio.create_task(blocking_io.run_blocking(blocker, timeout=0.05))

        with pytest.raises(asyncio.TimeoutError):
            await first
        with pytest.raises(asyncio.TimeoutError):
            await second

    assert any(
        "blocking_io_pool_near_capacity" in record.getMessage() for record in caplog.records
    )
