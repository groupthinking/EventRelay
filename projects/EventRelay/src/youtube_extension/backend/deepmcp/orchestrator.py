#!/usr/bin/env python3
"""
DeepMCPAgent Orchestrator
=========================

Agent workflow orchestrator intended to replace `autonomous_processor.py` when
enabled via feature flag. It coordinates multi-video processing using the
`DeepMCPAgentProcessor` and writes results to workflow outputs for the UI.
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from youtube_extension.utils import extract_video_id
from .deepmcp_processor import DeepMCPAgentProcessor

logger = logging.getLogger(__name__)


def deepmcp_autonomy_enabled() -> bool:
    return os.getenv('ENABLE_DEEP_MCP_AUTONOMY', 'false').lower() == 'true'


class DeepMCPAgentOrchestrator:
    """
    Orchestrates autonomous video processing using the DeepMCPAgentProcessor.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.processor = DeepMCPAgentProcessor()
        self.output_dir = output_dir or (Path(__file__).resolve().parents[1] / 'workflow_results' / 'videos')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = None

    async def process_and_save(self, video_url: str) -> Dict[str, Any]:
        try:
            result = await self.processor.process_video(video_url)
            video_id = result.get('video_id') or extract_video_id(video_url)
            out_path = self.output_dir / f"{video_id}.json"
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
            logger.info("Saved processing result to %s", out_path)
            return result
        except Exception as e:
            logger.error("Processing failed for %s: %s", video_url, e)
            return {'success': False, 'video_url': video_url, 'error': str(e)}

    async def run(self, video_urls: List[str], max_concurrent: int = 3) -> List[Dict[str, Any]]:
        if not video_urls:
            return []
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _guarded(url: str) -> Dict[str, Any]:
            async with self._semaphore:
                return await self.process_and_save(url)

        tasks = [_guarded(u) for u in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                out.append({'success': False, 'error': str(r)})
            else:
                out.append(r)
        return out


async def _main_from_env():
    """Convenience entry to run orchestrator from env configuration."""
    # Comma separated video URLs in DEEP_MCP_VIDEOS
    urls_env = os.getenv('DEEP_MCP_VIDEOS', '').strip()
    if not urls_env:
        logger.warning("No videos provided in DEEP_MCP_VIDEOS; nothing to process")
        return 0
    video_urls = [u.strip() for u in urls_env.split(',') if u.strip()]
    orch = DeepMCPAgentOrchestrator()
    results = await orch.run(video_urls)
    successes = sum(1 for r in results if r.get('success'))
    logger.info("DeepMCPAgentOrchestrator run complete: %s/%s successful", successes, len(results))
    return 0 if successes == len(results) else 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    exit(asyncio.run(_main_from_env()))

