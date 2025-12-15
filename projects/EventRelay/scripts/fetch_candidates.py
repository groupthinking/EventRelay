#!/usr/bin/env python3
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict

from googleapiclient.discovery import build  # type: ignore


QUERIES = [
    # Educational / tutorials
    "tutorial programming", "machine learning tutorial", "math lecture",
    # Business / professional
    "business strategy", "marketing workflow", "productivity tips",
    # Creative / DIY
    "DIY project", "how to build", "design tutorial",
    # Health / Fitness / Cooking
    "fitness routine", "healthy cooking", "nutrition guide",
    # Tech toolings
    "React tutorial", "Python tips", "APIs best practices",
]


def search_videos(youtube, query: str, max_results: int = 50) -> List[str]:
    res = youtube.search().list(
        q=query,
        part="id",
        type="video",
        maxResults=max_results,
        videoDuration="medium",
        safeSearch="none",
    ).execute()
    ids = []
    for item in res.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if vid:
            ids.append(vid)
    return ids


def filter_available(youtube, ids: List[str]) -> List[str]:
    out: List[str] = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        res = youtube.videos().list(part="status", id=",".join(chunk)).execute()
        for it in res.get("items", []):
            st = it.get("status", {})
            if st.get("privacyStatus") == "public" and not st.get("uploadStatus") in {"rejected", "failed"}:
                out.append(it.get("id"))
    return out


def main():
    key = os.getenv("YOUTUBE_API_KEY") or os.getenv("REACT_APP_YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("Missing YOUTUBE_API_KEY")

    yt = build("youtube", "v3", developerKey=key)

    candidate_ids: List[str] = []
    for q in QUERIES:
        candidate_ids += search_videos(yt, q, max_results=25)

    candidate_ids = list(dict.fromkeys(candidate_ids))  # de-dup, preserve order
    candidate_ids = filter_available(yt, candidate_ids)

    queue_path = Path("workflow_results/video_queue.json")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    if queue_path.exists():
        data = json.loads(queue_path.read_text())
    else:
        data = {"pending": [], "processed": [], "failed": []}

    existing = set(data.get("pending", []) + data.get("processed", []) + [f.get("video_id") for f in data.get("failed", [])])
    new_ids = [v for v in candidate_ids if v not in existing]
    data["pending"] = data.get("pending", []) + new_ids
    queue_path.write_text(json.dumps(data, indent=2))
    print(f"Added {len(new_ids)} new candidates (total pending: {len(data['pending'])})")


if __name__ == "__main__":
    main()



