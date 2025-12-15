#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from typing import List
from pathlib import Path
import sys

# Import from agents directory with fallback for standalone execution
try:
    from ..agents.process_video_with_mcp import RealVideoProcessor
except ImportError:
    # Fallback for standalone script execution
    from agents.process_video_with_mcp import RealVideoProcessor

VIDEO_IDS: List[str] = [
    "lFXQkBvEe0o", "k7HaeJs-N-o", "yAXVW-lUINc", "BAjzkaCdRok",
    "c1NYw35eIjk", "aircAruvnKk", "2tXh1U3Rpko", "4H1-hQZ4tGg",
    "Gv9_4yMHFhI", "uQXjSxrZlEQ", "z5ncgB3_7xE", "TTahY8XQzEo",
    "d0bPIU3ac10", "omr9FbRcU28", "71wSzpLyW9k", "5R1aN6J0ZzU",
    "7CqJlxBYj-M", "CJ6W06nA6Oc", "bMknfKXIFA8", "hwUNUw3cI0w",
    "8aGhZQkoFbQ", "GQp1zzTwrIg",
]

async def process_one(video_id: str):
    proc = RealVideoProcessor(real_mode_only=False)
    url = f"https://www.youtube.com/watch?v={video_id}"
    return await proc.process_video_real(url)

async def main():
    results = []
    for i in range(0, len(VIDEO_IDS), 5):
        batch = VIDEO_IDS[i:i+5]
        print(f"Processing batch {i//5+1}: {batch}")
        results.extend(await asyncio.gather(*[process_one(v) for v in batch]))
    out = Path('workflow_results/batch_results.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    out.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f"Saved results to {out}")

if __name__ == '__main__':
    asyncio.run(main())

