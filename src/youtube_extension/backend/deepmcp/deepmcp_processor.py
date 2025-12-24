#!/usr/bin/env python3
"""
DeepMCPAgent Video Processor
===========================

Agent-driven processor that orchestrates existing MCP servers with dynamic tool
discovery and model-agnostic AI selection. This provides a drop-in replacement
interface compatible with `RealVideoProcessor` where possible.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from youtube_extension.utils import extract_video_id
logger = logging.getLogger(__name__)


class DeepMCPAgentProcessor:
    """
    Agent-powered video processor intended to replace RealVideoProcessor.

    Public methods intentionally mirror `RealVideoProcessor`:
    - process_video(video_url: str, force_refresh: bool = False) -> Dict[str, Any]
    - validate_and_process(video_url: str) -> Dict[str, Any]
    - batch_process_videos(video_urls: List[str], max_concurrent: int = 3) -> Dict[str, Any]
    - get_processing_status() -> Dict[str, Any]
    - close()
    """

    def __init__(self):
        # Cache compatible with RealVideoProcessor cache layout
        self.cache_dir = Path("youtube_processed_videos/deepmcp_agent")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Feature toggles and configuration
        self.enable_caching = os.getenv('FALLBACK_TO_CACHE', 'true').lower() == 'true'
        self.model_selection = os.getenv('DEEP_MCP_MODEL_SELECTION', 'auto')
        self.discovery_mode = os.getenv('DEEP_MCP_TOOL_DISCOVERY', 'dynamic')

        # Lazy init handles for agent graph / tool registry (filled in later phases)
        self._agent = None
        self._tool_registry = None

        logger.info("🚀 DeepMCPAgentProcessor initialized (tool_discovery=%s, model=%s)", self.discovery_mode, self.model_selection)

    def _cache_path(self, video_id: str) -> Path:
        return self.cache_dir / f"{video_id}_processed.json"

    async def _maybe_load_cache(self, video_id: str) -> Optional[Dict[str, Any]]:
        if not self.enable_caching:
            return None
        try:
            path = self._cache_path(video_id)
            if path.exists():
                content = json.loads(path.read_text(encoding='utf-8'))
                content['cached'] = True
                return content
        except Exception as e:
            logger.warning("Cache load failed for %s: %s", video_id, e)
        return None

    async def _save_cache(self, video_id: str, result: Dict[str, Any]) -> None:
        if not self.enable_caching:
            return
        try:
            path = self._cache_path(video_id)
            # Avoid persisting cache flags
            clean = {k: v for k, v in result.items() if k not in ['cached']}
            path.write_text(json.dumps(clean, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        except Exception as e:
            logger.warning("Cache save failed for %s: %s", video_id, e)


    async def process_video(self, video_url: str, force_refresh: bool = False) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        processing_steps: List[Dict[str, Any]] = []
        total_cost = 0.0

        try:
            video_id = extract_video_id(video_url)
            processing_steps.append({
                'step': 'video_id_extraction',
                'status': 'completed',
                'result': video_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            if not force_refresh:
                cached = await self._maybe_load_cache(video_id)
                if cached:
                    return cached

            # Phase 1 placeholder orchestration: call existing real services indirectly if available
            # This ensures backward-compat while DeepMCP graph is wired in Phase 2/3.
            youtube_data = await self._get_youtube_data(video_url)
            processing_steps.append({
                'step': 'youtube_data_extraction',
                'status': 'completed' if youtube_data else 'failed',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            ai_analysis = await self._analyze_with_models(youtube_data)
            total_cost += ai_analysis.get('total_cost', 0.0)
            processing_steps.append({
                'step': 'ai_analysis',
                'status': 'completed' if ai_analysis.get('success') else 'partial',
                'providers_used': ai_analysis.get('processing_providers', []),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            result = {
                'video_id': video_id,
                'video_url': video_url,
                'success': True,
                'metadata': youtube_data.get('metadata', {}),
                'transcript': youtube_data.get('transcript', {}),
                'channel_info': youtube_data.get('channel_info', {}),
                'related_videos': youtube_data.get('related_videos', []),
                'ai_analysis': ai_analysis,
                'processing_steps': processing_steps,
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cost_breakdown': {
                    'total_cost': total_cost,
                    'providers_used': ai_analysis.get('processing_providers', [])
                },
                'cached': False,
                'save_path': str(self._cache_path(video_id)),
            }

            await self._save_cache(video_id, result)
            return result

        except Exception as e:
            return {
                'video_id': 'unknown',
                'video_url': video_url,
                'success': False,
                'error': str(e),
                'processing_steps': processing_steps,
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cost_breakdown': {'total_cost': total_cost},
                'cached': False
            }

    async def validate_and_process(self, video_url: str) -> Dict[str, Any]:
        try:
            # Basic validation via extraction for Phase 1
            video_id = extract_video_id(video_url)
            result = await self.process_video(video_url)
            result['valid'] = result.get('success', False)
            result['validation_message'] = 'valid' if result['valid'] else result.get('error', 'unknown')
            result['video_id'] = video_id or result.get('video_id')
            return result
        except Exception as e:
            return {
                'valid': False,
                'video_id': '',
                'error': f'Validation failed: {e}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def batch_process_videos(self, video_urls: List[str], max_concurrent: int = 3) -> Dict[str, Any]:
        import asyncio
        start_time = datetime.now(timezone.utc)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(url: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                try:
                    return url, await self.process_video(url)
                except Exception as e:
                    return url, {'success': False, 'error': str(e), 'video_url': url}

        tasks = [process_single(u) for u in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        total_cost = 0.0
        for item in results:
            if isinstance(item, Exception):
                failed.append({'success': False, 'error': str(item)})
                continue
            url, res = item
            if res.get('success'):
                successful.append(res)
                total_cost += res.get('cost_breakdown', {}).get('total_cost', 0.0)
            else:
                failed.append(res)

        return {
            'batch_processing': True,
            'total_videos': len(video_urls),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': (len(successful) / max(1, len(video_urls))) * 100.0,
            'total_cost': total_cost,
            'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'results': successful,
            'errors': failed,
        }

    async def get_processing_status(self) -> Dict[str, Any]:
        try:
            cached_files = len(list(self.cache_dir.glob("*_processed.json"))) if self.cache_dir.exists() else 0
            return {
                'service_status': 'operational',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cache': {
                    'enabled': self.enable_caching,
                    'cached_videos': cached_files,
                    'cache_directory': str(self.cache_dir)
                },
                'agent': {
                    'tool_discovery': self.discovery_mode,
                    'model_selection': self.model_selection,
                    'initialized': bool(self._agent is not None)
                }
            }
        except Exception as e:
            return {
                'service_status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def close(self):
        try:
            # Placeholder for agent/resource cleanup
            pass
        except Exception as e:
            logger.warning("DeepMCPAgentProcessor cleanup error: %s", e)

    async def _get_youtube_data(self, video_url: str) -> Dict[str, Any]:
        """Phase 1: delegate to existing real_youtube_api if present; fallback to minimal."""
        try:
            from ..services.real_youtube_api import get_youtube_service
            svc = get_youtube_service()
            data = await svc.get_comprehensive_video_data(video_url)
            return data
        except Exception as e:
            logger.warning("Falling back to minimal YouTube data: %s", e)
            # Minimal placeholder ensures interface stability
            video_id = extract_video_id(video_url)
            return {
                'video_id': video_id,
                'metadata': {'title': 'Unknown', 'duration': 'PT0M', 'channel_title': 'Unknown'},
                'transcript': {'has_transcript': False, 'segment_count': 0, 'full_text': ''},
                'channel_info': {},
                'related_videos': []
            }

    async def _analyze_with_models(self, youtube_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: delegate to existing real_ai_processor if present; support auto provider."""
        try:
            from ..services.real_ai_processor import analyze_video_with_ai
            result = await analyze_video_with_ai(youtube_data)
            return result
        except Exception as e:
            logger.warning("AI analysis unavailable, returning minimal analysis: %s", e)
            return {
                'success': False,
                'total_cost': 0.0,
                'processing_providers': [],
                'error': str(e)
            }


# Module-level singleton for compatibility
_deepmcp_processor: Optional[DeepMCPAgentProcessor] = None


def get_deepmcp_processor() -> DeepMCPAgentProcessor:
    global _deepmcp_processor
    if _deepmcp_processor is None:
        _deepmcp_processor = DeepMCPAgentProcessor()
    return _deepmcp_processor

