#!/usr/bin/env python3
"""
Video Processor Factory
======================

Factory module to provide working video processors with proper fallbacks.
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)

def get_video_processor(processor_type: str = "auto") -> Union['EnhancedVideoProcessor', 'RealVideoProcessor', 'DeepMCPAgentProcessor']:
    """
    Get appropriate video processor based on configuration
    
    Args:
        processor_type: Type of processor to create
            - "auto": Automatically select best working processor
            - "enhanced": Use enhanced Gemini processor
            - "real": Use real MCP processor
            
    Returns:
        Video processor instance
    """
    # Check environment for processor preference
    if processor_type == "auto":
        # Read from environment if set; default to enhanced
        try:
            env_choice = os.getenv('VIDEO_PROCESSOR_TYPE')
        except Exception:
            env_choice = None
        processor_type = env_choice or 'enhanced'
    # Prefer DeepMCP when explicitly enabled
    if processor_type == "deepmcp" or os.getenv('ENABLE_DEEP_MCP', 'false').lower() == 'true':
        try:
            from backend.deepmcp.deepmcp_processor import DeepMCPAgentProcessor
            logger.info("✅ Using DeepMCPAgentProcessor (agent orchestration)")
            return DeepMCPAgentProcessor()
        except Exception as e:
            logger.warning(f"DeepMCP processor failed: {e}, falling back to enhanced/real")
    
    logger.info(f"Creating video processor: {processor_type}")
    
    if processor_type == "enhanced":
        try:
            from .enhanced_video_processor import EnhancedVideoProcessor
            logger.info("✅ Using EnhancedVideoProcessor (Gemini + YouTube API)")
            return EnhancedVideoProcessor()
        except Exception as e:
            logger.warning(f"Enhanced processor failed: {e}, falling back to real processor")
            processor_type = "real"
    
    if processor_type == "real":
        try:
            from .real_video_processor import RealVideoProcessor
            logger.info("✅ Using RealVideoProcessor (MCP ecosystem)")
            return RealVideoProcessor()
        except Exception as e:
            logger.warning(f"Real processor failed: {e}, falling back to enhanced processor")
            try:
                from .enhanced_video_processor import EnhancedVideoProcessor
                logger.info("✅ Fallback to EnhancedVideoProcessor")
                return EnhancedVideoProcessor()
            except Exception as e2:
                logger.error(f"All processors failed: {e2}")
                raise ValueError(f"No working video processor available: {e2}")
    
    if processor_type == "hybrid":
        """Hybrid processor using FastVLM + Gemini pipeline for video understanding.

        Adapter downloads the YouTube video (via yt-dlp) to a temporary file and
        invokes the hybrid VideoPipeline. It then maps results into the common
        structure expected by the service layer so downstream normalization works.
        """
        try:
            import json
            import tempfile
            from typing import Dict, Any
            from fastvlm_gemini_hybrid.video_pipeline import VideoPipeline
            import yt_dlp  # type: ignore

            class HybridVideoProcessorAdapter:
                def __init__(self) -> None:
                    self._pipeline = VideoPipeline()

                async def process_video(self, video_url: str) -> Dict[str, Any]:
                    # Download to a temporary mp4 using yt-dlp
                    with tempfile.TemporaryDirectory() as tmpdir:
                        ydl_opts = {
                            "format": "mp4",
                            "noplaylist": True,
                            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(video_url, download=True)
                        video_id = info.get("id") or "unknown"
                        filepath = os.path.join(tmpdir, f"{video_id}.mp4")

                        # Run hybrid processing with a comprehensive prompt
                        prompt = "Provide a concise, structured summary of the video's key topics, steps, and takeaways."
                        result = self._pipeline.process_video_hybrid(filepath, prompt)

                        # Map to common structure
                        ai_analysis: Dict[str, Any] = {}
                        actions = []
                        # If Gemini returned JSON in text, parse it
                        resp_text = result.get("response") or ""
                        try:
                            parsed = json.loads(resp_text)
                            ai_analysis = parsed if isinstance(parsed, dict) else {"summary": str(parsed)}
                            # Pull actions if present
                            if isinstance(ai_analysis.get("actions"), list):
                                actions = ai_analysis.get("actions")
                        except Exception:
                            ai_analysis = {"summary": resp_text}

                        return {
                            "video_id": video_id,
                            "metadata": {"source": "hybrid_fastvlm_gemini"},
                            "ai_analysis": ai_analysis,
                            "actions": actions,
                            "transcript": [],
                            "success": bool(result.get("success", True)),
                            "processing_pipeline": ["fastvlm", "gemini"],
                        }

            logger.info("✅ Using HybridVideoProcessor (FastVLM + Gemini)")
            return HybridVideoProcessorAdapter()
        except Exception as e:
            logger.warning(f"Hybrid processor failed: {e}, falling back to enhanced processor")
            try:
                from .enhanced_video_processor import EnhancedVideoProcessor
                logger.info("✅ Fallback to EnhancedVideoProcessor")
                return EnhancedVideoProcessor()
            except Exception as e2:
                logger.error(f"Hybrid fallback failed: {e2}")
                raise ValueError(f"No working video processor available: {e2}")
    
    # Final fallback
    try:
        from .enhanced_video_processor import EnhancedVideoProcessor
        logger.info("✅ Final fallback to EnhancedVideoProcessor")
        return EnhancedVideoProcessor()
    except Exception as e:
        logger.error(f"Final fallback failed: {e}")
        raise ValueError(f"No working video processor available: {e}")


# Compatibility wrapper for gradual migration
async def process_video_with_best_processor(video_url: str) -> dict:
    """
    Process video using the best available processor
    
    This function provides a smooth migration path from legacy processors
    to the new working processors.
    """
    processor = get_video_processor("auto")
    
    try:
        result = await processor.process_video(video_url)
        return result
    finally:
        # Cleanup if processor has cleanup method
        if hasattr(processor, 'cleanup'):
            await processor.cleanup()

