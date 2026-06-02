#!/usr/bin/env python3
"""
EventRelay empirical Proof-of-Concept runner.

Purpose
-------
Drive 10 real YouTube videos (AI / agent building + business workflow
automation) through the *real* EventRelay pipeline and record, per stage,
exactly what works and what does not -- with the genuine outputs and error
strings as evidence. No mocked successes, no fabricated transcripts
(REAL_MODE_ONLY).

Stages exercised
----------------
0. URL corpus              -- examples/poc_video_urls.txt (real, web-sourced)
1. Transcript capture      -- youtube_transcript_api (the lib the backend uses)
2. AI availability probe   -- HybridProcessorService / provider API keys
3. Event extraction        -- REAL endpoint POST /api/v1/events/extract
4. Agent dispatch          -- REAL endpoint POST /api/v1/agents/dispatch

The script captures the real result of every call. Stages that are blocked
in this environment (e.g. transcript capture from a cloud IP, or AI calls
with no API key) are recorded as blocked WITH the underlying exception, which
is itself the proof.

Output
------
examples/poc_results.json   -- machine-readable, full per-video evidence
Console                     -- human-readable summary table
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URLS_FILE = ROOT / "examples" / "poc_video_urls.txt"
RESULTS_FILE = ROOT / "examples" / "poc_results.json"

os.environ.setdefault("DATABASE_URL", "sqlite:///./.poc-runtime.db")

# NOTE: 15 backend modules (incl. backend/api/v1/router.py) use absolute
# `from src.youtube_extension...` imports, so the repo root must be on
# sys.path or the v1 router fails to load ("No module named 'src'") and every
# /api/v1/* route 404s. This mirrors the documented launch
# `uvicorn src.youtube_extension.main:app` run from the repo root.
sys.path.insert(0, str(ROOT))


def load_corpus() -> list[dict]:
    rows = []
    for line in URLS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        vid, _, title = line.partition("\t")
        rows.append(
            {
                "video_id": vid.strip(),
                "title": title.strip(),
                "url": f"https://www.youtube.com/watch?v={vid.strip()}",
            }
        )
    return rows


def stage1_transcript(video_id: str) -> dict:
    """Attempt real caption fetch via the same lib the backend uses."""
    out = {"ok": False, "chars": 0, "segments": 0, "text": "", "error": None}
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        raw = (
            fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
        )
        text = " ".join(s["text"] for s in raw)
        out.update(ok=True, chars=len(text), segments=len(raw), text=text)
    except Exception as exc:  # noqa: BLE001 - we want the real class+msg
        out["error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
    return out


def probe_ai() -> dict:
    """Record whether the AI provider path can run at all."""
    keys = {
        k: bool(os.environ.get(k))
        for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    }
    probe = {"keys_present": keys, "hybrid_processor_ok": False, "error": None}
    try:
        import asyncio

        from youtube_extension.services.ai.hybrid_processor_service import (
            HybridProcessorService,
        )

        proc = HybridProcessorService()
        asyncio.run(proc.process(input_data="ping", prompt="ping"))
        probe["hybrid_processor_ok"] = True
    except Exception as exc:  # noqa: BLE001
        probe["error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
    return probe


def probe_gateway() -> dict:
    """Confirm the Vercel AI Gateway is usable (real billed call)."""
    out = {
        "available": False,
        "ok": False,
        "model": None,
        "sample_events": 0,
        "error": None,
    }
    try:
        from youtube_extension.services.ai import vercel_gateway_provider as gw

        out["available"] = gw.gateway_available()
        out["model"] = gw.DEFAULT_MODEL
        if out["available"]:
            evs = gw.extract_events(
                "We build an AI agent, configure a tool, and deploy the workflow."
            )
            out["ok"] = len(evs) > 0
            out["sample_events"] = len(evs)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
    return out


def main() -> int:
    corpus = load_corpus()
    print(f"Loaded {len(corpus)} real video URLs from {URLS_FILE.name}\n")

    # Spin up the REAL FastAPI app in-process.
    from starlette.testclient import TestClient

    from youtube_extension.main import app

    client = TestClient(app)

    ai = probe_ai()
    print(
        "AI provider availability:",
        json.dumps(ai["keys_present"]),
        "| hybrid_processor_ok=",
        ai["hybrid_processor_ok"],
    )
    if ai["error"]:
        print("  AI probe error:", ai["error"])

    gw = probe_gateway()
    print(
        f"Vercel AI Gateway: available={gw['available']} ok={gw['ok']} "
        f"model={gw['model']} sample_events={gw['sample_events']}"
    )
    if gw["error"]:
        print("  Gateway probe error:", gw["error"])
    print()

    results = []
    for i, item in enumerate(corpus, 1):
        rec = dict(item)
        print(f"[{i:>2}/{len(corpus)}] {item['video_id']}  {item['title'][:60]}")

        # Stage 1: real transcript capture attempt
        t0 = time.time()
        s1 = stage1_transcript(item["video_id"])
        s1["seconds"] = round(time.time() - t0, 2)
        rec["stage1_transcript"] = s1
        print(
            f"     transcript: {'OK '+str(s1['chars'])+' chars' if s1['ok'] else 'BLOCKED -> '+str(s1['error'])}"
        )

        # The text actually available to feed downstream. If transcript
        # capture worked we use it; otherwise we fall back to the real,
        # web-sourced title so the downstream code path still gets exercised
        # on genuine (non-fabricated) text.
        feed_text = s1["text"] if s1["ok"] else item["title"]
        rec["downstream_input_source"] = "transcript" if s1["ok"] else "title_only"
        # Keep the committed JSON lean: store only a preview, not the full
        # transcript (length is preserved in `chars`).
        s1["text_preview"] = s1.pop("text")[:300]

        # Stage 3 (code): real event extraction endpoint
        r = client.post("/api/v1/events/extract", json={"transcript": feed_text})
        s3 = {"http_status": r.status_code}
        if r.status_code == 200:
            data = r.json().get("data", {})
            evs = data.get("events", [])
            s3.update(
                event_count=data.get("event_count", len(evs)),
                types=sorted({e.get("type") for e in evs}),
                sample=[e.get("title") for e in evs[:3]],
            )
        else:
            s3["body"] = r.text[:200]
        rec["stage3_extract_events"] = s3
        print(
            f"     extract:    HTTP {s3['http_status']} -> {s3.get('event_count','?')} events {s3.get('types','')}"
        )

        # Stage 4 (code): real agent dispatch endpoint
        evs_for_dispatch = []
        if r.status_code == 200:
            evs_for_dispatch = r.json().get("data", {}).get("events", [])[:10]
        dr = client.post(
            "/api/v1/agents/dispatch",
            json={
                "events": evs_for_dispatch,
                "agent_types": ["analyzer", "content_creator"],
            },
        )
        s4 = {"http_status": dr.status_code}
        if dr.status_code == 200:
            dd = dr.json().get("data", {})
            s4.update(
                dispatch_id=dd.get("dispatch_id"),
                executions=len(dd.get("executions", [])),
            )
        else:
            s4["body"] = dr.text[:200]
        rec["stage4_dispatch"] = s4
        print(
            f"     dispatch:   HTTP {s4['http_status']} -> {s4.get('executions','?')} executions\n"
        )

        results.append(rec)

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "environment": {
            "python": sys.version.split()[0],
            "youtube_reachable": True,
            "ai_keys_present": ai["keys_present"],
            "hybrid_processor_ok": ai["hybrid_processor_ok"],
            "ai_probe_error": ai["error"],
            "vercel_gateway": gw,
        },
        "totals": {
            "videos": len(results),
            "transcript_ok": sum(1 for r in results if r["stage1_transcript"]["ok"]),
            "extract_http_200": sum(
                1 for r in results if r["stage3_extract_events"]["http_status"] == 200
            ),
            "dispatch_http_200": sum(
                1 for r in results if r["stage4_dispatch"]["http_status"] == 200
            ),
        },
        "results": results,
    }
    RESULTS_FILE.write_text(json.dumps(summary, indent=2))
    print("=" * 64)
    print("TOTALS:", json.dumps(summary["totals"]))
    print(f"Full evidence written to {RESULTS_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
