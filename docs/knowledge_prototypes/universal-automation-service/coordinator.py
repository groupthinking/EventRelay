#!/usr/bin/env python3
"""
Universal Automation Service - Main Coordinator
YouTube URL → EventRelay → UVAI → Self-Correcting Executor Pipeline
Supports multiple processing modes: eventrelay, gemini, hybrid, auto
"""
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional


class UniversalAutomationCoordinator:
    """Orchestrates YouTube URL processing through integrated MCP services"""

    def __init__(self, processing_mode: str = "auto", gemini_api_key: Optional[str] = None):
        """
        Initialize coordinator with processing mode selection

        Args:
            processing_mode: "auto", "eventrelay", "gemini", or "hybrid"
            gemini_api_key: Optional Gemini API key (uses env var if not provided)
        """
        self.processing_mode = processing_mode
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

        # Check availability of processors
        self.gemini_available = self._check_gemini_available()
        self.eventrelay_available = self._check_eventrelay_available()

        # Auto-select best mode
        if self.processing_mode == "auto":
            self.processing_mode = self._select_best_mode()

        self.pipeline_state = {
            "status": "initialized",
            "current_stage": None,
            "youtube_url": None,
            "video_data": {},
            "intelligence_output": {},
            "executor_results": {},
            "processing_mode": self.processing_mode,
            "timestamp": datetime.now().isoformat()
        }

    def _check_gemini_available(self) -> bool:
        """Check if Gemini API is available"""
        if not self.gemini_api_key:
            return False
        try:
            from gemini_video_processor import GeminiVideoProcessor
            return True
        except ImportError:
            return False

    def _check_eventrelay_available(self) -> bool:
        """Check if EventRelay backend is available"""
        try:
            import requests
            youtube_extension_base = os.getenv("YOUTUBE_EXTENSION_BASE", "http://localhost:8000")
            response = requests.get(f"{youtube_extension_base}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def _select_best_mode(self) -> str:
        """Auto-select best processing mode based on availability"""
        if self.gemini_available and self.eventrelay_available:
            return "hybrid"  # Best of both
        elif self.gemini_available:
            return "gemini"  # Fast cloud-based
        elif self.eventrelay_available:
            return "eventrelay"  # Local processing
        else:
            return "gemini"  # Try Gemini even if backend check fails

    def validate_youtube_url(self, url: str) -> bool:
        """Validate YouTube URL format"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+'
        ]
        return any(re.match(pattern, url) for pattern in youtube_patterns)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def process_youtube_url(self, youtube_url: str) -> Dict[str, Any]:
        """Main pipeline orchestrator with multi-mode support"""

        # Stage 1: Validate input
        if not self.validate_youtube_url(youtube_url):
            return {
                "success": False,
                "error": "Invalid YouTube URL",
                "pipeline_state": self.pipeline_state
            }

        video_id = self.extract_video_id(youtube_url)
        self.pipeline_state["youtube_url"] = youtube_url
        self.pipeline_state["video_id"] = video_id
        self.pipeline_state["current_stage"] = f"{self.processing_mode}_processing"

        print(f"\n🚀 Processing with mode: {self.processing_mode}")

        # Stage 2: Video Processing (mode-dependent)
        try:
            if self.processing_mode == "gemini":
                relay_result = self._process_with_gemini(youtube_url)
            elif self.processing_mode == "eventrelay":
                relay_result = self._process_with_eventrelay(video_id)
            elif self.processing_mode == "hybrid":
                relay_result = self._process_hybrid(youtube_url, video_id)
            else:
                raise ValueError(f"Unknown processing mode: {self.processing_mode}")

            self.pipeline_state["video_data"] = relay_result
            self.pipeline_state["current_stage"] = "uvai_intelligence"

        except Exception as e:
            self.pipeline_state["error"] = f"Video processing failed: {str(e)}"
            return {"success": False, "pipeline_state": self.pipeline_state}

    def _process_with_gemini(self, youtube_url: str) -> Dict[str, Any]:
        """Process video using Gemini API"""
        print("📺 Using Gemini 2.5 Flash for video understanding...")
        from gemini_video_processor import GeminiVideoProcessor
        processor = GeminiVideoProcessor(api_key=self.gemini_api_key)
        return processor.process_video(youtube_url)

    def _process_with_eventrelay(self, video_id: str) -> Dict[str, Any]:
        """Process video using EventRelay servers"""
        print("⚙️  Using EventRelay MCP servers for video processing...")
        from youtube_ingestion import EventRelayProcessor
        relay_processor = EventRelayProcessor()
        return relay_processor.process_video(video_id)

    def _process_hybrid(self, youtube_url: str, video_id: str) -> Dict[str, Any]:
        """Process video using both Gemini and EventRelay (best of both)"""
        print("🔄 Using hybrid mode (Gemini + EventRelay)...")

        # Get Gemini analysis (fast, comprehensive)
        try:
            gemini_result = self._process_with_gemini(youtube_url)
        except Exception as e:
            print(f"⚠️  Gemini processing failed: {e}")
            gemini_result = None

        # Get EventRelay analysis (detailed, local)
        try:
            eventrelay_result = self._process_with_eventrelay(video_id)
        except Exception as e:
            print(f"⚠️  EventRelay processing failed: {e}")
            eventrelay_result = None

        # Merge results (prefer Gemini for main content, EventRelay for supplementary)
        if gemini_result and eventrelay_result:
            # Hybrid: merge both
            merged = gemini_result.copy()
            merged["eventrelay_supplementary"] = eventrelay_result
            merged["processing_mode"] = "hybrid"
            return merged
        elif gemini_result:
            return gemini_result
        elif eventrelay_result:
            return eventrelay_result
        else:
            raise Exception("Both Gemini and EventRelay processing failed")

        # Stage 3: UVAI Intelligence Processing (uvai_intelligence.py)
        try:
            from uvai_intelligence import UVAIProcessor
            uvai_processor = UVAIProcessor()
            intelligence_output = uvai_processor.analyze(relay_result)

            self.pipeline_state["intelligence_output"] = intelligence_output
            self.pipeline_state["current_stage"] = "executor_action"

        except Exception as e:
            self.pipeline_state["error"] = f"UVAI processing failed: {str(e)}"
            return {"success": False, "pipeline_state": self.pipeline_state}

        # Stage 4: Self-Correcting Executor (executor_action.py)
        try:
            from executor_action import SelfCorrectingExecutor
            executor = SelfCorrectingExecutor()
            execution_results = executor.execute(intelligence_output)

            self.pipeline_state["executor_results"] = execution_results
            self.pipeline_state["current_stage"] = "completed"
            self.pipeline_state["status"] = "success"

        except Exception as e:
            self.pipeline_state["error"] = f"Executor failed: {str(e)}"
            return {"success": False, "pipeline_state": self.pipeline_state}

        return {
            "success": True,
            "pipeline_state": self.pipeline_state,
            "final_output": execution_results
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return self.pipeline_state

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Universal Automation Service - YouTube to Skills Pipeline')
    parser.add_argument('youtube_url', help='YouTube URL to process')
    parser.add_argument('--mode', choices=['auto', 'gemini', 'eventrelay', 'hybrid'],
                        default='auto', help='Processing mode (default: auto)')
    parser.add_argument('--gemini-key', help='Gemini API key (optional, uses GEMINI_API_KEY env var if not provided)')

    args = parser.parse_args()

    # Resolve Gemini API key from flag or env; fail closed only for modes that
    # always require Gemini. "auto" can fall back to EventRelay via
    # _select_best_mode(), so it must not hard-require a key here.
    gemini_key = args.gemini_key or os.getenv("GEMINI_API_KEY")
    if args.mode in {"gemini", "hybrid"} and not gemini_key:
        parser.error("gemini and hybrid modes require --gemini-key or the GEMINI_API_KEY env var")

    coordinator = UniversalAutomationCoordinator(
        processing_mode=args.mode,
        gemini_api_key=gemini_key
    )

    result = coordinator.process_youtube_url(args.youtube_url)

    print("\n" + "="*80)
    print("PIPELINE RESULTS")
    print("="*80)
    print(json.dumps(result, indent=2))
