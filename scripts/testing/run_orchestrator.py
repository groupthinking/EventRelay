#!/usr/bin/env python3
"""
Run the VideoPipelineOrchestrator (the reactive agent network in action).

Usage examples:
  # Mock / structure-only dry run (no heavy downloads or LLM calls)
  python scripts/testing/run_orchestrator.py --video-url https://www.youtube.com/watch?v=ftBWgcwvEk4 --mock

  # Real (after pip install -e ".[dev,youtube,ml]" and MCP servers running)
  python scripts/testing/run_orchestrator.py --video-url https://www.youtube.com/watch?v=ftBWgcwvEk4 --mode sequential

  # DAG parallel mode
  python scripts/testing/run_orchestrator.py --video-id ftBWgcwvEk4 --mode dag
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

def parse_args():
    p = argparse.ArgumentParser(description="Run Video-to-Software agent pipeline")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--video-url", help="Full YouTube URL")
    src.add_argument("--video-id", help="Just the YouTube video ID")
    p.add_argument("--mode", choices=["sequential", "dag"], default="sequential",
                   help="Execution mode (default: sequential)")
    p.add_argument("--mock", action="store_true",
                   help="Force mock-friendly mode (sets USE_MOCK_SERVERS, skips some heavy steps where supported)")
    p.add_argument("--continue-on-error", action="store_true")
    p.add_argument("--pipeline", choices=["default", "extended"], default="default")
    p.add_argument("--json", action="store_true", help="Output full result as JSON")
    return p.parse_args()

def build_video_url(args):
    if args.video_url:
        return args.video_url
    vid = args.video_id.strip()
    if vid.startswith("http"):
        return vid
    return f"https://www.youtube.com/watch?v={vid}"

async def main_async(args):
    video_url = build_video_url(args)

    if args.mock:
        os.environ.setdefault("USE_MOCK_SERVERS", "true")
        os.environ.setdefault("REAL_MODE", "false")
        print("[orchestrator] Running in MOCK mode (USE_MOCK_SERVERS=true)")
    else:
        print("[orchestrator] Running in REAL mode (requires full deps + MCP servers)")

    options = {
        "execution_mode": args.mode,
        "pipeline": args.pipeline,
        "continue_on_error": args.continue_on_error,
    }

    print(f"[orchestrator] Starting pipeline for {video_url}")
    print(f"[orchestrator] mode={args.mode} pipeline={args.pipeline}")

    try:
        if args.mode == "dag":
            from agents.pipeline_orchestrator import run_video_to_software_parallel
            result = await run_video_to_software_parallel(video_url, **options)
        else:
            from agents.pipeline_orchestrator import run_video_to_software
            result = await run_video_to_software(video_url, **options)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("\n=== PIPELINE RESULT SUMMARY ===")
            print(f"Success: {result.get('success', 'unknown')}")
            print(f"Run ID:  {result.get('run_id')}")
            print(f"Stages completed: {result.get('stages_completed', [])}")
            print(f"Total duration (ms): {result.get('total_duration_ms')}")
            if result.get("error"):
                print(f"Error: {result['error']}")
            stages = result.get("stages", {}) or result.get("results", {})
            if stages:
                print("\nPer-stage:")
                for sid, data in stages.items():
                    if isinstance(data, dict):
                        ok = data.get("success")
                        dur = data.get("duration_ms")
                        err = str(data.get("error", ""))[:50]
                        print(f"  {sid}: success={ok} duration_ms={dur} err={err}")
                    else:
                        print(f"  {sid}: {data}")

        return 0 if result.get("success") else 1

    except Exception as e:
        print(f"\n[ERROR] Pipeline run failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 2

def main():
    args = parse_args()
    try:
        rc = asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        rc = 130
    sys.exit(rc)

if __name__ == "__main__":
    main()
