"""Concurrency tests for the chunked AI extraction in /api/v1/events/extract.

A transcript longer than the 24 000-char chunk window is split into several
overlapping chunks, each of which is an independent AI round-trip.  Those
round-trips used to run strictly one after another, so a long transcript paid
the full provider latency once per chunk.

These tests lock in the bounded-window fan-out:

* chunks in the same window are extracted concurrently;
* the window is bounded, so a very long transcript cannot fire an unbounded
  number of billed provider calls at once;
* results are merged in chunk order (not completion order), so dedup and the
  50-event budget select exactly the events the serial walk selected;
* the event budget is re-checked between windows, so extraction still stops
  early once it is full;
* a chunk that fails does not take its siblings down with it.

REAL_MODE_ONLY: no mocked provider *success* is asserted against a real
backend -- the stand-in reports ``backend="gemini"`` purely so the router's own
mock-rejection guard does not divert to the heuristic path, and every assertion
here is about the router's scheduling, not about AI output quality.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from youtube_extension.backend.api.v1 import router as router_mod
from youtube_extension.main import app

client = TestClient(app)

# Mirrors the router's own constants; asserted against them indirectly via the
# observed window size rather than by importing (they are function-locals).
_CHUNK_SIZE = 24_000
_EXPECTED_MAX_CONCURRENCY = 4
_MAX_EVENTS = 50


def _disable_gateway(monkeypatch) -> None:
    """Force the Vercel AI Gateway off so only the chunked path is exercised."""
    from youtube_extension.services.ai import vercel_gateway_provider as gw

    monkeypatch.setattr(gw, "gateway_available", lambda: False)


def _transcript_for(n_chunks: int) -> str:
    """Build a transcript long enough to split into at least ``n_chunks``.

    Every sentence is unique, which guarantees every chunk is a unique
    substring -- the tests rely on ``transcript.index(chunk)`` being a stable,
    strictly increasing identifier for each chunk.
    """
    # ~24 chars per sentence; oversize generously so boundary snapping cannot
    # leave us one chunk short.
    n_sentences = (n_chunks + 1) * (_CHUNK_SIZE // 20)
    return " ".join(f"w{i} filler token here." for i in range(n_sentences))


def _install_tracking_process(
    monkeypatch,
    transcript: str,
    *,
    events_per_chunk: int = 1,
    fail_at_offset: int | None = None,
    invert_latency: bool = False,
) -> dict:
    """Patch ``HybridProcessorService.process`` with a concurrency-aware stub.

    Records peak in-flight calls and the offset of every chunk it was handed.
    Each chunk is identified by its start offset in ``transcript``, which is
    also its position in chunk order.
    """
    record: dict = {"inflight": 0, "max_inflight": 0, "offsets": []}

    async def fake_process(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        chunk = args[0] if args else kwargs["input_data"]
        offset = transcript.index(chunk)
        record["offsets"].append(offset)

        record["inflight"] += 1
        record["max_inflight"] = max(record["max_inflight"], record["inflight"])
        try:
            if invert_latency:
                # Later chunks finish *first*.  If the router merged results in
                # completion order the final event order would be reversed.
                await asyncio.sleep(0.15 / (1 + offset / 20_000.0))
            else:
                await asyncio.sleep(0.05)

            if fail_at_offset is not None and offset == fail_at_offset:
                raise RuntimeError("provider blew up for this chunk")

            lines = "\n".join(
                f"- Event {n} at offset {offset}" for n in range(events_per_chunk)
            )
            return SimpleNamespace(
                success=True,
                response=lines,
                cloud_result=SimpleNamespace(backend="gemini"),
            )
        finally:
            record["inflight"] -= 1

    monkeypatch.setattr(
        router_mod.HybridProcessorService, "process", fake_process, raising=True
    )
    return record


def _extract(transcript: str) -> list[dict]:
    resp = client.post("/api/v1/events/extract", json={"transcript": transcript})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["events"]


def _offsets_of(events: list[dict]) -> list[int]:
    return [int(e["title"].rsplit(" ", 1)[-1]) for e in events]


class TestExtractEventsChunkConcurrency:
    """The serial ``for chunk in transcript_chunks`` walk is now windowed."""

    def test_chunks_are_extracted_concurrently(self, monkeypatch):
        """Peak in-flight calls above 1 is only reachable without a serial loop."""
        _disable_gateway(monkeypatch)
        transcript = _transcript_for(4)
        record = _install_tracking_process(monkeypatch, transcript)

        _extract(transcript)

        assert len(record["offsets"]) > 1, "transcript did not split into chunks"
        assert record["max_inflight"] > 1, (
            "chunks were extracted one at a time; peak in-flight was "
            f"{record['max_inflight']}"
        )

    def test_concurrency_is_bounded(self, monkeypatch):
        """A long transcript must not fire every billed call at once."""
        _disable_gateway(monkeypatch)
        transcript = _transcript_for(12)
        record = _install_tracking_process(monkeypatch, transcript)

        _extract(transcript)

        assert len(record["offsets"]) > _EXPECTED_MAX_CONCURRENCY
        assert 1 < record["max_inflight"] <= _EXPECTED_MAX_CONCURRENCY, (
            f"expected a bounded window, saw {record['max_inflight']} in flight"
        )

    def test_events_are_merged_in_chunk_order(self, monkeypatch):
        """Results are merged by chunk position, not by completion time."""
        _disable_gateway(monkeypatch)
        transcript = _transcript_for(4)
        record = _install_tracking_process(
            monkeypatch, transcript, invert_latency=True
        )

        events = _extract(transcript)
        offsets = _offsets_of(events)

        # Later chunks completed first, so a completion-ordered merge would
        # produce a descending sequence here.
        assert offsets == sorted(offsets), (
            f"events merged out of chunk order: {offsets}"
        )
        assert record["max_inflight"] > 1, "latency inversion needs real overlap"

    def test_event_budget_is_rechecked_between_windows(self, monkeypatch):
        """Once the 50-event budget is full, no further window is dispatched."""
        _disable_gateway(monkeypatch)
        transcript = _transcript_for(12)
        # One chunk alone overfills the budget.
        record = _install_tracking_process(
            monkeypatch, transcript, events_per_chunk=_MAX_EVENTS + 10
        )

        events = _extract(transcript)

        assert len(events) == _MAX_EVENTS
        # The first window is dispatched before the budget can be checked, so
        # up to _EXPECTED_MAX_CONCURRENCY calls are expected -- but not the
        # remaining windows.
        assert len(record["offsets"]) <= _EXPECTED_MAX_CONCURRENCY, (
            "extraction kept dispatching windows after the budget was full: "
            f"{len(record['offsets'])} calls"
        )

    def test_one_failing_chunk_does_not_abort_siblings(self, monkeypatch):
        """A provider error in one chunk must not cancel the rest of its window."""
        _disable_gateway(monkeypatch)
        transcript = _transcript_for(4)
        probe = _install_tracking_process(monkeypatch, transcript)
        _extract(transcript)
        all_offsets = sorted(set(probe["offsets"]))
        assert len(all_offsets) >= 3

        doomed = all_offsets[1]
        _install_tracking_process(monkeypatch, transcript, fail_at_offset=doomed)
        events = _extract(transcript)
        offsets = set(_offsets_of(events))

        assert doomed not in offsets
        assert offsets == set(all_offsets) - {doomed}

    def test_short_transcript_still_makes_one_call(self, monkeypatch):
        """Regression guard: the single-chunk path is unchanged."""
        _disable_gateway(monkeypatch)
        transcript = "We build the agent. Then we deploy it."
        record = _install_tracking_process(monkeypatch, transcript)

        events = _extract(transcript)

        assert len(record["offsets"]) == 1
        assert record["max_inflight"] == 1
        assert _offsets_of(events) == [0]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
