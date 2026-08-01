"""Unit tests for cloud_ai_routes.process_batch_videos batch fan-out."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_extension.backend import cloud_ai_routes as routes


class _FakeIntegrator:
    """Async context manager standing in for CloudAIIntegrator."""

    def __init__(self, analyze):
        self.analyze_video = analyze

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


@contextlib.contextmanager
def _fake_cloud_ai(analyze):
    """Run process_batch_videos against a fake integrator.

    ``routes.asyncio`` is replaced so the inter-batch ``asyncio.sleep(1)``
    pause does not add real wall-clock time. Only the module-level name is
    patched, so ``asyncio`` inside these tests is untouched and ``gather``
    keeps its real behaviour.
    """
    fake_asyncio = MagicMock()
    fake_asyncio.gather = asyncio.gather
    fake_asyncio.sleep = AsyncMock()
    with (
        patch.object(routes, "get_cloud_ai_config", return_value={}),
        patch.object(routes, "CloudAIIntegrator", lambda _cfg: _FakeIntegrator(analyze)),
        patch.object(routes, "format_analysis_result", side_effect=lambda r: r),
        patch.object(routes, "asyncio", fake_asyncio),
    ):
        yield fake_asyncio


def _tracking_analyze(state, failures=()):
    """analyze_video stand-in that records peak concurrent in-flight calls."""

    async def _analyze(video_url, **_kwargs):
        state["inflight"] += 1
        state["peak"] = max(state["peak"], state["inflight"])
        try:
            await asyncio.sleep(0.01)
            if video_url in failures:
                raise RuntimeError(f"provider rejected {video_url}")
            return f"result:{video_url}"
        finally:
            state["inflight"] -= 1

    return _analyze


class TestProcessBatchVideosFanOut:
    """A batch must be analysed concurrently, bounded by batch_size.

    The previous implementation awaited each video in turn, so batch_size
    controlled nothing but the cadence of the inter-batch pause while
    wall-clock cost stayed the full sum of every per-video analysis.
    """

    async def test_batch_is_analysed_concurrently(self):
        state = {"inflight": 0, "peak": 0}
        urls = [f"https://v/{i}" for i in range(4)]

        with _fake_cloud_ai(_tracking_analyze(state)):
            await routes.process_batch_videos(urls, [], None, 4, "task-1")

        assert state["peak"] == 4, (
            f"batch peaked at {state['peak']} concurrent analyze_video call(s) "
            "for a batch of 4 - the batch is being analysed sequentially"
        )

    async def test_batch_size_bounds_concurrency(self):
        """batch_size must remain a real bound on the shared upstream API."""
        state = {"inflight": 0, "peak": 0}
        urls = [f"https://v/{i}" for i in range(6)]

        with _fake_cloud_ai(_tracking_analyze(state)):
            await routes.process_batch_videos(urls, [], None, 2, "task-2")

        assert state["peak"] == 2, (
            f"batch_size=2 but peak concurrency was {state['peak']}; the batch "
            "boundary must still bound in-flight provider calls"
        )

    async def test_pause_still_applied_between_batches_only(self):
        state = {"inflight": 0, "peak": 0}
        urls = [f"https://v/{i}" for i in range(6)]

        with _fake_cloud_ai(_tracking_analyze(state)) as fake_asyncio:
            await routes.process_batch_videos(urls, [], None, 2, "task-3")

        # 6 urls / batch_size 2 = 3 batches -> 2 inter-batch pauses.
        assert fake_asyncio.sleep.await_count == 2

    async def test_failed_video_does_not_abort_the_batch(self):
        state = {"inflight": 0, "peak": 0}
        urls = ["https://v/0", "https://v/1", "https://v/2"]
        collected = []

        analyze = _tracking_analyze(state, failures={"https://v/0"})
        with _fake_cloud_ai(analyze):
            with patch.object(
                routes, "format_analysis_result", side_effect=lambda r: collected.append(r) or r
            ):
                await routes.process_batch_videos(urls, [], None, 3, "task-4")

        assert collected == ["result:https://v/1", "result:https://v/2"], (
            f"expected the two healthy videos to be collected, got {collected}"
        )

    async def test_empty_url_list_is_a_noop(self):
        state = {"inflight": 0, "peak": 0}
        with _fake_cloud_ai(_tracking_analyze(state)):
            await routes.process_batch_videos([], [], None, 4, "task-5")
        assert state["peak"] == 0


class TestProcessBatchVideosCancellation:
    """Cancellation must propagate, not be misread as a successful result.

    ``asyncio.gather(..., return_exceptions=True)`` captures a child's
    ``CancelledError`` as a *value*. Because it derives from ``BaseException``
    and not ``Exception``, an ``isinstance(result, Exception)`` filter alone
    would hand it to ``format_analysis_result`` as if it were an analysis.
    The previous sequential ``await``/``except Exception`` loop let
    cancellation escape, so it must still escape here.
    """

    async def test_cancelled_analysis_is_re_raised_not_treated_as_a_result(self):
        async def analyze(video_url, **_kwargs):
            if video_url == "u2":
                raise asyncio.CancelledError()
            await asyncio.sleep(0)
            return f"result:{video_url}"

        formatted: list[object] = []

        with _fake_cloud_ai(analyze) as fake_asyncio:
            with patch.object(
                routes,
                "format_analysis_result",
                side_effect=lambda r: formatted.append(r) or r,
            ):
                with pytest.raises(asyncio.CancelledError):
                    await routes.process_batch_videos(
                        task_id="t-cancel",
                        video_urls=["u1", "u2", "u3", "u4"],
                        analysis_types=[],
                        preferred_provider=None,
                        batch_size=2,
                    )

        assert not any(isinstance(r, BaseException) for r in formatted), (
            f"a CancelledError leaked into format_analysis_result: {formatted}"
        )
        assert fake_asyncio.sleep.await_count == 0, (
            "cancellation did not abort the run: the inter-batch pause ran and "
            "the following batch was still dispatched"
        )

    async def test_cancellation_takes_precedence_over_ordinary_failures(self):
        """A cancelled peer still propagates when siblings also failed."""

        async def analyze(video_url, **_kwargs):
            if video_url == "boom":
                raise RuntimeError("provider exploded")
            if video_url == "cancelled":
                raise asyncio.CancelledError()
            await asyncio.sleep(0)
            return f"result:{video_url}"

        with _fake_cloud_ai(analyze):
            with pytest.raises(asyncio.CancelledError):
                await routes.process_batch_videos(
                    task_id="t-mixed",
                    video_urls=["ok", "boom", "cancelled"],
                    analysis_types=[],
                    preferred_provider=None,
                    batch_size=3,
                )
