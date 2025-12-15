#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any

import sys
# Import from agents directory with fallback for standalone execution
try:
    from ..agents.process_video_with_mcp import RealVideoProcessor
except ImportError:
    # Fallback for standalone script execution
    from agents.process_video_with_mcp import RealVideoProcessor
from pathlib import Path
import json
import os
from datetime import datetime

# Reuse existing implementer to turn actions into plans
try:
    from ..agents.action_implementer import ActionImplementer
except ImportError:
    try:
        from agents.action_implementer import ActionImplementer
    except ImportError:
        ActionImplementer = None  # graceful fallback

try:
    from ..agents.specialized.quality_agent import QualityAgent  # type: ignore
except ImportError:
    try:
        from agents.specialized.quality_agent import QualityAgent  # type: ignore
    except ImportError:
        QualityAgent = None

try:
    from ..shared.run_validation import persist_run_artifacts
except ImportError:
    try:
        from shared.run_validation import persist_run_artifacts
    except ImportError:
        persist_run_artifacts = None
try:
    from googleapiclient.discovery import build  # type: ignore
    HAS_YT_API = True
except Exception:
    HAS_YT_API = False

USE_PROXY_ONLY = os.getenv('USE_PROXY_ONLY', '').lower() in ('1','true','yes')

async def process_id(video_id: str) -> Dict[str, Any]:
    proc = RealVideoProcessor(real_mode_only=False)
    url = f"https://www.youtube.com/watch?v={video_id}"
    return await proc.process_video_real(url)

async def main():
    queue_path = Path("workflow_results/video_queue.json")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    if not queue_path.exists():
        queue_path.write_text(json.dumps({"pending": [], "processed": [], "failed": []}, indent=2))

    videos_dir = Path("workflow_results/videos")
    failures_dir = Path("workflow_results/failures")
    videos_dir.mkdir(parents=True, exist_ok=True)
    failures_dir.mkdir(parents=True, exist_ok=True)
    learning_log = Path("workflow_results/learning_log.json")
    if not learning_log.exists():
        learning_log.write_text(json.dumps([], indent=2))

    yt_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("REACT_APP_YOUTUBE_API_KEY")
    yt = build("youtube", "v3", developerKey=yt_key) if (HAS_YT_API and yt_key) else None

    while True:
        data = json.loads(queue_path.read_text())
        if not data.get('pending'):
            print('No pending videos. Sleeping 60s...')
            await asyncio.sleep(60)
            continue

        # Take small batches to stay safe
        batch = data['pending'][:10]
        del data['pending'][:10]

        # Pre-check availability via YouTube Data API if available
        if yt:
            kept = []
            skip = []
            for i in range(0, len(batch), 50):
                chunk = batch[i:i+50]
                try:
                    res = yt.videos().list(part="status", id=",".join(chunk)).execute()
                    status_map = {it.get('id'): it.get('status', {}) for it in res.get('items', [])}
                except Exception:
                    status_map = {}
                for vid in chunk:
                    st = status_map.get(vid, {})
                    if st.get('privacyStatus') == 'public' and st.get('uploadStatus') not in {"rejected","failed"}:
                        kept.append(vid)
                    else:
                        skip.append(vid)
                        (failures_dir / f"{vid}.json").write_text(json.dumps({"video_id": vid, "error": "precheck_unavailable"}, indent=2), encoding='utf-8')
                        data.setdefault('failed', []).append({"video_id": vid, "error": "precheck_unavailable"})
            batch = kept

        print(f"Processing batch of {len(batch)}: {batch}")
        results = await asyncio.gather(*[process_id(v) for v in batch])

        for res in results:
            vid = res.get('video_id')
            ok = res.get('success', True) is not False and bool(res.get('transcript_data'))
            if ok:
                # Persist per-video output for auditing
                (videos_dir / f"{vid}.json").write_text(json.dumps(res, indent=2), encoding='utf-8')
                if vid not in data.setdefault('processed', []):
                    data['processed'].append(vid)

                if persist_run_artifacts is not None:
                    try:
                        persist_run_artifacts(res, source="continuous-runner")
                    except Exception as exc:
                        print(f"[run-validation] Unable to validate run for {vid}: {exc}")

                # Generate implementation plan when possible
                if ActionImplementer is not None:
                    try:
                        impl = ActionImplementer()
                        processed_video_data = {
                            'video_id': vid,
                            'category': res.get('actionable_content', {}).get('category', 'Unknown'),
                            'actions': res.get('actionable_content', {}).get('actions', []),
                            'metadata': {
                                'title': res.get('metadata', {}).get('title', ''),
                                'extraction_method': res.get('metadata', {}).get('extraction_method', 'unknown')
                            }
                        }
                        plan = impl.create_implementation_plan(processed_video_data)
                        impl.save_implementation_plan(plan)
                    except Exception:
                        pass

                # Append to learning log for future ML
                try:
                    log = json.loads(learning_log.read_text())
                    ac = res.get('actionable_content', {})
                    qa = None
                    qa_result = None
                    if QualityAgent is not None:
                        try:
                            qa = QualityAgent()
                            qa_result = qa.assess_actionability(
                                actions=ac.get('actions', []) or [],
                                transcript_segments=res.get('transcript_data') or [],
                                metadata=res.get('metadata') or {}
                            )
                        except Exception:
                            qa_result = None
                    log.append({
                        'video_id': vid,
                        'category': ac.get('category', 'Unknown'),
                        'actions_generated': len(ac.get('actions', []) or []),
                        'transcript_segments': len(res.get('transcript_data') or []),
                        'processing_time': res.get('processing_time'),
                        'quality_assessment': qa_result,
                        'timestamp': datetime.now().isoformat()
                    })
                    learning_log.write_text(json.dumps(log, indent=2))
                except Exception:
                    pass
            else:
                (failures_dir / f"{vid}.json").write_text(json.dumps(res, indent=2), encoding='utf-8')
                data.setdefault('failed', []).append({"video_id": vid, "error": res.get('error')})

        queue_path.write_text(json.dumps(data, indent=2))
        # Short pause between batches
        await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
