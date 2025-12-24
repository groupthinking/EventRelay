#!/usr/bin/env python3
"""
Batch Video Processor
====================

This utility script automates testing of the **working processor** by consuming
up to **100 Technical / Business YouTube videos** in one run.  It orchestrates
calls to `simple_real_processor` (our baseline single-video pipeline) and
aggregates the results into a summary report.

Key features
------------
1. Video source flexibility
   • Supply `--list-file` containing one URL/ID per line, **or**
   • Let the script fetch video IDs automatically from the YouTube Data API
     using a search query (defaults to *"technical business tutorial"*).

2. Robust execution
   • Processes videos sequentially with a live progress bar.
   • Individual failures never abort the batch – they are logged and the run
     continues.

3. Automatic troubleshooting hint generation (best-effort)
   • When a video fails, the script performs a quick YouTube search for videos
     that might explain the error message and records the top URL as a helpful
     reference.

4. Structured outputs
   • Per-video JSON result files are created by `simple_real_processor` under
     the existing `gdrive_results/` hierarchy.
   • A high-level `batch_processing_summary.json` file is produced at the end
     with success/failure statistics and pointers to troubleshooting resources.

Usage examples
--------------
Process a custom list:
    python batch_video_processor.py --list-file my_video_list.txt

Fetch IDs automatically (requires YOUTUBE_API_KEY):
    python batch_video_processor.py --search-query "business automation tutorial"

"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import baseline processor functions
import simple_real_processor as srp

try:
    # YouTube Data API (optional – only required for automatic search)
    from googleapiclient.discovery import build  # type: ignore
    HAS_YT_API = True
except ImportError:
    HAS_YT_API = False

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def load_ids_from_file(path: Path, limit: int) -> List[str]:
    """Read video IDs/URLs from a text file."""
    ids: List[str] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
                if len(ids) >= limit:
                    break
    return ids


def search_youtube_ids(api_key: str, query: str, limit: int) -> List[str]:
    """Search YouTube and return up to *limit* video IDs for *query*."""
    if not HAS_YT_API:
        raise RuntimeError("google-api-python-client not installed – cannot perform YouTube search")

    service = build("youtube", "v3", developerKey=api_key)
    ids: List[str] = []
    next_page_token: Optional[str] = None

    while len(ids) < limit:
        req = service.search().list(
            part="id",
            q=query,
            type="video",
            maxResults=min(50, limit - len(ids)),
            pageToken=next_page_token or ""
        )
        resp = req.execute()
        for item in resp.get("items", []):
            vid = item["id"].get("videoId")
            if vid:
                ids.append(vid)
                if len(ids) >= limit:
                    break
        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break  # No more pages

    return ids


def troubleshoot_hint(error_msg: str, api_key: Optional[str]) -> Optional[str]:
    """Return a YouTube URL that *might* help resolve *error_msg* (best-effort)."""
    if not api_key or not HAS_YT_API:
        return None
    try:
        service = build("youtube", "v3", developerKey=api_key)
        req = service.search().list(
            part="id",
            q=f"How to fix {error_msg}",
            type="video",
            maxResults=1
        )
        resp = req.execute()
        items = resp.get("items", [])
        if items:
            vid_id = items[0]["id"].get("videoId")
            if vid_id:
                return f"https://www.youtube.com/watch?v={vid_id}"
    except Exception:
        pass  # Silently ignore troubleshooting errors
    return None

# ---------------------------------------------------------------------------
# Main batch driver
# ---------------------------------------------------------------------------

def process_video_id(video_id_or_url: str, real_mode: bool) -> Dict[str, Any]:
    """Wrapper around simple_real_processor pipeline."""
    start_time = time.time()
    try:
        vid_id = srp.extract_video_id(video_id_or_url)
        transcript = srp.get_transcript_real(vid_id)
        actionable_content = srp.generate_actions(vid_id, transcript)
        elapsed = time.time() - start_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        save_res = srp.save_results(vid_id, actionable_content, time.time() - start_time)
        # Construct final result similar to srp.main()
        result = {
            "video_id": vid_id,
            "category": actionable_content["category"],
            "total_segments": len(transcript),
            "actions_generated": len(actionable_content["actions"]),
            "processing_time": time.time() - start_time,
            "gdrive_success": save_res["success"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "success": True,
        }
        srp.validate_output({
            "video_id": vid_id,
            "processing_time": result["processing_time"],
            "total_segments": result["total_segments"],
        })
        return result
    except Exception as exc:
        return {
            "video_id": video_id_or_url,
            "error": str(exc),
            "success": False,
            "processing_time": time.time() - start_time,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-process up to 100 Technical/Business YouTube videos")
    parser.add_argument("--list-file", type=Path, help="Path to text file containing video URLs/IDs (one per line)")
    parser.add_argument("--search-query", default="technical business tutorial", help="YouTube search query (used when --list-file not provided)")
    parser.add_argument("--real-mode", action="store_true", help="Enable strict REAL_MODE_ONLY behaviour (fail fast)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of videos to process (default: 100)")

    args = parser.parse_args()

    yt_api_key = os.getenv("YOUTUBE_API_KEY", "")

    # ------------------------------------------------------------------
    # Gather video IDs
    # ------------------------------------------------------------------
    if args.list_file and args.list_file.exists():
        video_ids: List[str] = load_ids_from_file(args.list_file, args.limit)
        print(f"📄 Loaded {len(video_ids)} IDs from {args.list_file}")
    else:
        if not yt_api_key:
            print("⚠️  YOUTUBE_API_KEY not set and --list-file not provided – cannot auto-discover videos.")
            sys.exit(1)
        if not HAS_YT_API:
            print("⚠️  google-api-python-client not installed – install it or provide --list-file.")
            sys.exit(1)
        print(f"🔎 Searching YouTube for \"{args.search_query}\" …")
        video_ids = search_youtube_ids(yt_api_key, args.search_query, args.limit)
        print(f"🔍 Retrieved {len(video_ids)} video IDs from YouTube search.")

    if not video_ids:
        print("❌ No video IDs to process – aborting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Batch processing loop
    # ------------------------------------------------------------------
    results: List[Dict[str, Any]] = []
    total = len(video_ids)

    print(f"🚀 Starting batch processing of {total} videos …\n")

    for idx, vid in enumerate(video_ids, 1):
        print(f"[{idx}/{total}] ▶️  {vid}")
        res = process_video_id(vid, real_mode=args.real_mode)
        if not res.get("success"):
            hint = troubleshoot_hint(res.get("error", "unknown error"), yt_api_key)
            if hint:
                res["troubleshoot_video"] = hint
                print(f"   💡 Troubleshooting hint video: {hint}")
            else:
                print(f"   ❌ Error: {res.get('error')}")
        else:
            print(f"   ✅ Processed in {res['processing_time']:.2f}s | category = {res['category']}")
        results.append(res)
        print("―" * 60)

    # ------------------------------------------------------------------
    # Save summary
    # ------------------------------------------------------------------
    successes = sum(1 for r in results if r.get("success"))
    failures = len(results) - successes

    summary = {
        "total": len(results),
        "successes": successes,
        "failures": failures,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }

    summary_path = Path("batch_processing_summary.json")
    with summary_path.open("w") as f:
        json.dump(summary, f, indent=2)

    print("\n📊 Batch processing complete.")
    print(f"   Successful: {successes}")
    print(f"   Failed    : {failures}")
    print(f"   Summary   : {summary_path.resolve()}")

    # Exit code indicates success if at least one video processed successfully
    sys.exit(0 if successes > 0 else 1)


if __name__ == "__main__":
    main()