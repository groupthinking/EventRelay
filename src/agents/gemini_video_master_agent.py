#!/usr/bin/env python3
"""
GEMINI VIDEO MASTER AGENT
Comprehensive video processing using Google AI (Gemini) with agent delegation
and benchmarking across multiple AI providers
"""

import asyncio
import json
import logging
import os
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import aiohttp

try:
    import certifi
except ImportError:  # pragma: no cover - optional runtime hardening
    certifi = None

# Google AI imports - using new google.genai SDK
try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google AI not available - install: pip install google-genai")

# Add shared modules to path

sys.path.append(str(Path(__file__).parents[2] / "mcp-servers" / "shared-state"))

# Import Vision Processor for NVIDIA integration
try:
    from vision_processor import get_processor
except ImportError:
    logging.warning("Could not import VisionProcessor - NVIDIA capabilities disabled")

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv(override=True)  # Ensure latest .env values are used
except ImportError:
    logging.warning("python-dotenv not available")

try:
    from youtube_extension.utils.proxy import get_proxy_url, redact_proxy_credentials
except ImportError:  # pragma: no cover - optional when running outside the package
    def get_proxy_url():  # type: ignore[misc]
        return None
    def redact_proxy_credentials(text: str) -> str:  # type: ignore[misc]
        return text

# Banned video IDs (memes, inappropriate content, etc.)
BANNED_VIDEO_IDS = frozenset(
    [
        "dQw4w9WgXcQ",  # Rickroll - not a business/technical video
    ]
)

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "models/gemini-3.5-flash")
COMPAT_GEMINI_MODEL = os.getenv("GEMINI_COMPAT_VIDEO_MODEL", "models/gemini-2.5-flash")
DEFAULT_VIDEO_URL = os.getenv("GEMINI_DEFAULT_VIDEO_URL", "").strip()

# Configure logging (stdout only for Cloud Run compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [GEMINI_MASTER] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("gemini_master_agent")


def get_gemini_api_key() -> Optional[str]:
    """Prefer the dedicated Gemini key; GOOGLE_API_KEY is often shared/stale."""

    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
    )


def build_ssl_context() -> ssl.SSLContext:
    """Create a certificate-validating context for aiohttp on macOS and CI."""

    if certifi:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def extract_video_id(url: str) -> str:
    """Extract a YouTube video ID from common URL formats."""

    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()

    if hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]
        if parsed.path.startswith(("/embed/", "/shorts/")):
            return parsed.path.rstrip("/").split("/")[-1]

    if hostname == "youtu.be":
        return parsed.path.lstrip("/").split("/")[0]

    return url.strip()


def normalize_youtube_url(url: str) -> str:
    """Return a canonical public YouTube watch URL for Gemini video input."""

    video_id = extract_video_id(url)
    if video_id and video_id != url.strip():
        return f"https://www.youtube.com/watch?v={video_id}"
    return url.strip()


def is_banned_video_url(video_url: str) -> bool:
    """Return whether a URL points at a blocked non-business/non-technical video."""

    return extract_video_id(video_url) in BANNED_VIDEO_IDS


def build_default_video_prompt(default_video: str | None = None) -> str:
    """Build the no-argument CLI prompt without surfacing banned examples."""

    candidate = (default_video if default_video is not None else DEFAULT_VIDEO_URL).strip()
    lines = [
        "",
        "Gemini Video Master Agent",
        "=========================",
    ]

    if candidate and not is_banned_video_url(candidate):
        lines.extend(
            [
                "No video URL provided.",
                f"Press [Enter] to process the configured default video: {candidate}",
                "Or paste a different business or technical YouTube URL.",
            ]
        )
    else:
        lines.extend(
            [
                "No video URL provided.",
                "Paste a business or technical YouTube URL to process.",
                "Press [Enter] without a URL to exit.",
            ]
        )

    return "\n".join(lines)


class TaskType(Enum):
    """Different types of video processing tasks"""

    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    VISUAL_ANALYSIS = "visual_analysis"
    ACTION_GENERATION = "action_generation"
    CONTENT_CATEGORIZATION = "content_categorization"
    TIMESTAMP_ANALYSIS = "timestamp_analysis"
    KEY_INSIGHTS = "key_insights"
    IMPLEMENTATION_PLAN = "implementation_plan"
    STRATEGIC_ANALYSIS = "strategic_analysis"
    PRECISION_EXTRACTION = "precision_extraction"


class AIProvider(Enum):
    """Available AI providers with benchmarking"""

    # Current Gemini video models. Avoid 1.5/2.0 aliases; they are stale.
    GEMINI_FLASH = DEFAULT_GEMINI_MODEL
    GEMINI_COMPAT_FLASH = COMPAT_GEMINI_MODEL
    # External providers
    GROK_4 = "grok-4-0709"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    GPT_4O = "gpt-4o"
    # NVIDIA Cosmos/VLM (New - Cognitive Video)
    NVIDIA_VILA = "nvidia/vila-1.5-40b"


@dataclass
class BenchmarkResult:
    """Benchmark result for AI provider comparison"""

    provider: AIProvider
    task_type: TaskType
    processing_time: float
    quality_score: float
    cost_estimate: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class TaskResult:
    """Result from a specific task"""

    task_type: TaskType
    provider: AIProvider
    content: str
    metadata: dict[str, Any]
    benchmark: BenchmarkResult


class GeminiVideoMasterAgent:
    """Master agent for video processing using Google AI with agent delegation"""

    def __init__(self):
        self.gemini_api_key = get_gemini_api_key()
        if self.gemini_api_key:
            os.environ["GOOGLE_API_KEY"] = self.gemini_api_key
        self.ssl_context = build_ssl_context()
        # Use /tmp for Cloud Run compatibility (read-only root filesystem)
        self.output_dir = Path(
            os.getenv("GEMINI_OUTPUT_DIR", "/tmp/gemini_processed_videos")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Google AI - using new google.genai Client
        if GEMINI_AVAILABLE and self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            logger.info("✅ Google AI (Gemini) initialized with new SDK")
        else:
            self.gemini_client = None
            logger.warning("⚠️ Google AI not available - using fallback methods")

        # Initialize Vision Processor for NVIDIA VLM
        try:
            self.vision_processor = get_processor()
            if self.vision_processor.nvidia.available:
                logger.info("✅ NVIDIA Processor initialized for VLM tasks")
            else:
                logger.warning("⚠️ NVIDIA Processor available but key missing")
        except Exception as e:
            self.vision_processor = None
            logger.warning(f"⚠️ Vision Processor could not be initialized: {e}")

        # Task delegation - Enforcing current Gemini Flash for all video operations
        # Ping-Pong Strategy: Parallel execution for Visual Analysis (Gemini + NVIDIA)
        self.task_delegation = {
            TaskType.TRANSCRIPTION: AIProvider.GEMINI_FLASH,
            TaskType.SUMMARIZATION: AIProvider.GEMINI_FLASH,
            TaskType.VISUAL_ANALYSIS: AIProvider.GEMINI_FLASH,
            TaskType.ACTION_GENERATION: AIProvider.GEMINI_FLASH,
            TaskType.CONTENT_CATEGORIZATION: AIProvider.GEMINI_FLASH,
            TaskType.TIMESTAMP_ANALYSIS: AIProvider.GEMINI_FLASH,
            TaskType.KEY_INSIGHTS: AIProvider.GEMINI_FLASH,
            TaskType.IMPLEMENTATION_PLAN: AIProvider.GEMINI_FLASH,
            TaskType.PRECISION_EXTRACTION: AIProvider.GEMINI_FLASH,
        }

        # Benchmarking results
        self.benchmark_results = []

        logger.info("🎯 GEMINI VIDEO MASTER AGENT INITIALIZED")

        # Best-effort cleanup registration for any internal clients/sessions
        try:
            import atexit
            atexit.register(self.close)
        except Exception:
            pass

    def close(self):
        """Explicit close for the Gemini client and any held resources (unclosed hygiene)."""
        try:
            if getattr(self, 'gemini_client', None) is not None:
                # google-genai Client may expose transport close in newer sdks
                client = self.gemini_client
                for attr in ('close', 'aclose', '_close'):
                    if hasattr(client, attr):
                        fn = getattr(client, attr)
                        try:
                            if asyncio.iscoroutinefunction(fn):
                                # schedule if possible; ignore in sync close
                                pass
                            else:
                                fn()
                        except Exception:
                            pass
                        break
                self.gemini_client = None
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        return extract_video_id(url)

    async def process_video_with_gemini(self, video_url: str) -> dict[str, Any]:
        """Process video using Google AI (Gemini) with task delegation"""

        start_time = time.time()
        video_id = self.extract_video_id(video_url)
        gemini_video_url = normalize_youtube_url(video_url)

        logger.info(f"🚀 GEMINI MASTER AGENT PROCESSING: {video_id}")

        try:
            # Stage 1: Task breakdown and delegation
            tasks = self._break_down_tasks(video_url)
            logger.info(f"📋 Created {len(tasks)} tasks for delegation")

            # Stage 2: Execute tasks with appropriate AI providers
            task_results = await self._execute_tasks_with_delegation(
                tasks, gemini_video_url
            )

            # Stage 3: Benchmark and compare results
            benchmark_analysis = self._analyze_benchmarks()

            # Stage 4: Generate comprehensive report
            comprehensive_result = await self._generate_comprehensive_report(
                video_id, video_url, task_results, benchmark_analysis
            )

            # Stage 5: Save results
            save_result = await self._save_gemini_results(
                video_id, comprehensive_result
            )

            processing_time = time.time() - start_time

            result = {
                "video_id": video_id,
                "video_url": video_url,
                "gemini_video_url": gemini_video_url,
                "task_results": task_results,
                "benchmark_analysis": benchmark_analysis,
                "comprehensive_result": comprehensive_result,
                "save_result": save_result,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "processing_method": "gemini_master_agent",
                "success": save_result["successful_tasks"] > 0,
            }

            if result["success"]:
                logger.info(
                    f"✅ GEMINI MASTER AGENT COMPLETE: {video_id} in {processing_time:.3f}s"
                )
            else:
                logger.error(
                    f"❌ GEMINI MASTER AGENT COMPLETED WITH 0 SUCCESSFUL TASKS: {video_id}"
                )
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ GEMINI MASTER AGENT FAILED: {video_id} - {e}")

            return {
                "video_id": video_id,
                "error": str(e),
                "processing_time": processing_time,
                "success": False,
            }

    def _break_down_tasks(self, video_url: str) -> list[tuple[TaskType, str]]:
        """Break down video processing into specific tasks"""

        tasks = [
            (
                TaskType.TRANSCRIPTION,
                f"Transcribe the audio from this video, giving timestamps for salient events in the video. Also provide visual descriptions. Video: {video_url}",
            ),
            (
                TaskType.SUMMARIZATION,
                f"Please summarize the video in 3 sentences. Video: {video_url}",
            ),
            (
                TaskType.VISUAL_ANALYSIS,
                f"Analyze the visual content of this video, describing key visual elements, graphics, charts, or demonstrations shown. Video: {video_url}",
            ),
            (
                TaskType.CONTENT_CATEGORIZATION,
                f"Categorize this video content and identify the target audience, complexity level, and learning objectives. Video: {video_url}",
            ),
            (
                TaskType.TIMESTAMP_ANALYSIS,
                f"What are the key examples and concepts mentioned at different timestamps in this video? Provide timestamp analysis. Video: {video_url}",
            ),
            (
                TaskType.KEY_INSIGHTS,
                f"Extract the most important insights, key takeaways, and actionable points from this video. Video: {video_url}",
            ),
            (
                TaskType.ACTION_GENERATION,
                f"Generate specific, actionable steps that someone could take to implement or learn from this video content. Video: {video_url}",
            ),
            (
                TaskType.IMPLEMENTATION_PLAN,
                f"Create a detailed implementation plan with timelines, resources needed, and success metrics based on this video content. Video: {video_url}",
            ),
            (
                TaskType.PRECISION_EXTRACTION,
                f"Extract physical entities (ingredients, tools, parts, steps) with high precision, noticing what is visually present even if not verbally mentioned. Video: {video_url}",
            ),
        ]

        return tasks

    async def _execute_tasks_with_delegation(
        self, tasks: list[tuple[TaskType, str]], video_url: str
    ) -> list[TaskResult]:
        """Execute tasks with appropriate AI provider delegation in PARALLEL"""

        coroutines = []
        gemini_groups: dict[AIProvider, list[tuple[TaskType, str]]] = {}
        logger.info(f"🔄 Starting parallel execution of {len(tasks)} tasks...")

        for task_type, prompt in tasks:
            # Get the best AI provider for this task
            provider = self.task_delegation[task_type]

            if provider in (AIProvider.GEMINI_FLASH, AIProvider.GEMINI_COMPAT_FLASH):
                logger.info(f"✨ Queued {task_type.value} for Gemini batch")
                gemini_groups.setdefault(provider, []).append((task_type, prompt))
            else:
                logger.info(f"✨ Scheduled {task_type.value} with {provider.value}")
                coroutines.append(
                    self._execute_task_with_provider(
                        task_type, prompt, provider, video_url
                    )
                )

            # PING PONG: Add parallel NVIDIA task for Visual Analysis
            if task_type == TaskType.VISUAL_ANALYSIS:
                if (
                    self.vision_processor
                    and getattr(self.vision_processor, "nvidia", None)
                    and self.vision_processor.nvidia.available
                ):
                    logger.info(
                        f"✨ Scheduled {task_type.value} (Parallel) with NVIDIA VILA"
                    )
                    coroutines.append(
                        self._execute_task_with_provider(
                            task_type, prompt, AIProvider.NVIDIA_VILA, video_url
                        )
                    )
                else:
                    logger.info("NVIDIA VILA unavailable; skipping optional visual pass")

        for provider, provider_tasks in gemini_groups.items():
            logger.info(
                "✨ Scheduled Gemini batch with %s for %d tasks",
                provider.value,
                len(provider_tasks),
            )
            coroutines.append(
                self._execute_gemini_task_batch(provider_tasks, video_url, provider)
            )

        # Run all tasks in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results
        task_results = []
        for res in results:
            if isinstance(res, list):
                task_results.extend(
                    item for item in res if isinstance(item, TaskResult)
                )
            elif isinstance(res, TaskResult):
                task_results.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Task failed during parallel execution: {res}")
                # We could add a failed TaskResult here for completeness if needed

        return task_results

    async def _execute_gemini_task_batch(
        self,
        tasks: list[tuple[TaskType, str]],
        video_url: str,
        provider: AIProvider,
    ) -> list[TaskResult]:
        """Execute multiple Gemini video tasks with one video request."""

        start_time = time.time()
        prompt = self._build_gemini_batch_prompt(tasks, video_url)

        try:
            raw_content = await self._execute_with_gemini(
                prompt,
                provider,
                video_url,
                response_mime_type="application/json",
            )
            parsed = await self._parse_or_repair_gemini_batch_response(
                raw_content,
                tasks,
                provider,
            )
            processing_time = time.time() - start_time
            per_task_time = processing_time / max(len(tasks), 1)

            task_results: list[TaskResult] = []
            for task_type, _ in tasks:
                content = self._stringify_task_content(parsed.get(task_type.value))
                if not content:
                    content = f"Task failed: Gemini batch omitted {task_type.value}"
                    success = False
                    quality_score = 0.0
                else:
                    success = True
                    quality_score = self._calculate_quality_score(content, task_type)

                cost_estimate = self._estimate_cost(provider, len(content))
                benchmark = BenchmarkResult(
                    provider=provider,
                    task_type=task_type,
                    processing_time=per_task_time,
                    quality_score=quality_score,
                    cost_estimate=cost_estimate,
                    success=success,
                    error_message=None if success else content,
                )
                self.benchmark_results.append(benchmark)
                task_results.append(
                    TaskResult(
                        task_type=task_type,
                        provider=provider,
                        content=content,
                        metadata={
                            "processing_time": per_task_time,
                            "batch_processing_time": processing_time,
                            "quality_score": quality_score,
                            "cost_estimate": cost_estimate,
                            "batched": True,
                        },
                        benchmark=benchmark,
                    )
                )

            return task_results

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Gemini batch execution failed: {e}")

            if self._is_youtube_access_error(e):
                try:
                    return await self._execute_gemini_text_fallback_batch(
                        tasks,
                        video_url,
                        provider,
                        str(e),
                        processing_time,
                    )
                except Exception as fallback_error:
                    logger.error(
                        "❌ Gemini text fallback failed: %s", fallback_error
                    )
                    e = fallback_error

            return [
                self._failed_task_result(
                    task_type,
                    provider,
                    processing_time / max(len(tasks), 1),
                    str(e),
                )
                for task_type, _ in tasks
            ]

    async def _execute_gemini_text_fallback_batch(
        self,
        tasks: list[tuple[TaskType, str]],
        video_url: str,
        provider: AIProvider,
        video_error: str,
        previous_processing_time: float,
    ) -> list[TaskResult]:
        """Fallback to transcript/metadata context when Gemini cannot fetch video."""

        start_time = time.time()
        context = await self._build_youtube_text_context(video_url)
        prompt = self._build_gemini_text_fallback_prompt(
            tasks,
            video_url,
            context,
            video_error,
        )
        raw_content = await self._execute_with_gemini_text(
            prompt,
            provider,
            response_mime_type="application/json",
        )
        parsed = await self._parse_or_repair_gemini_batch_response(
            raw_content,
            tasks,
            provider,
        )
        processing_time = previous_processing_time + (time.time() - start_time)
        per_task_time = processing_time / max(len(tasks), 1)

        results: list[TaskResult] = []
        for task_type, _ in tasks:
            content = self._stringify_task_content(parsed.get(task_type.value))
            if not content:
                content = f"Task failed: Gemini text fallback omitted {task_type.value}"
                success = False
                quality_score = 0.0
            else:
                success = True
                quality_score = self._calculate_quality_score(content, task_type)

            cost_estimate = self._estimate_cost(provider, len(content))
            benchmark = BenchmarkResult(
                provider=provider,
                task_type=task_type,
                processing_time=per_task_time,
                quality_score=quality_score,
                cost_estimate=cost_estimate,
                success=success,
                error_message=None if success else content,
            )
            self.benchmark_results.append(benchmark)
            results.append(
                TaskResult(
                    task_type=task_type,
                    provider=provider,
                    content=content,
                    metadata={
                        "processing_time": per_task_time,
                        "quality_score": quality_score,
                        "cost_estimate": cost_estimate,
                        "batched": True,
                        "source": "youtube_text_fallback",
                        "video_error": video_error,
                    },
                    benchmark=benchmark,
                )
            )

        return results

    async def _build_youtube_text_context(self, video_url: str) -> str:
        """Build fallback text context from captions and metadata."""

        video_id = extract_video_id(video_url)
        context_parts = [f"Video URL: {normalize_youtube_url(video_url)}"]

        try:
            from src.shared.youtube import fetch_innertube_transcript

            segments = await fetch_innertube_transcript(video_id)
            transcript = "\n".join(
                f"[{segment.start:.1f}s] {segment.text}" for segment in segments[:500]
            )
            if transcript.strip():
                context_parts.append("Transcript:\n" + transcript)
        except Exception as exc:
            logger.warning("YouTube transcript fallback unavailable: %s", exc)

        try:
            metadata = await asyncio.to_thread(
                self._extract_youtube_metadata_with_ytdlp,
                normalize_youtube_url(video_url),
            )
            if metadata:
                context_parts.append(
                    "Metadata:\n" + json.dumps(metadata, indent=2, default=str)
                )
        except Exception as exc:
            logger.warning("YouTube metadata fallback unavailable: %s", exc)

        if len(context_parts) == 1:
            raise RuntimeError("No transcript or metadata available for text fallback")

        return "\n\n".join(context_parts)

    @staticmethod
    def _extract_youtube_metadata_with_ytdlp(video_url: str) -> dict[str, Any]:
        import yt_dlp

        proxy_url = get_proxy_url()
        options: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "noplaylist": True,
        }
        if proxy_url:
            options["proxy"] = proxy_url
            logger.debug(
                "yt-dlp metadata extraction using proxy: %s",
                redact_proxy_credentials(proxy_url),
            )
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=False)

        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "duration": info.get("duration"),
            "description": (info.get("description") or "")[:4000],
            "categories": info.get("categories"),
            "tags": (info.get("tags") or [])[:30],
        }

    @staticmethod
    def _build_gemini_text_fallback_prompt(
        tasks: list[tuple[TaskType, str]],
        video_url: str,
        context: str,
        video_error: str,
    ) -> str:
        task_lines = "\n".join(
            f'- "{task_type.value}": {prompt}' for task_type, prompt in tasks
        )
        schema_lines = ",\n".join(
            f'  "{task_type.value}": "string"' for task_type, _ in tasks
        )
        return f"""
Gemini could not access the video file directly.
Direct video error: {video_error}

Use the transcript and metadata context below to complete every task possible.
If a task requires visual-only details that are not present in the context, say so
inside that task's value instead of inventing details.

Video: {video_url}

Context:
{context}

Tasks:
{task_lines}

Return ONLY valid JSON with exactly these top-level keys:
{{
{schema_lines}
}}
""".strip()

    @staticmethod
    def _is_youtube_access_error(error: Exception) -> bool:
        message = str(error).lower()
        markers = (
            "permission_denied",
            "does not have permission",
            "unsupported mime type",
            "text/html",
        )
        return any(marker in message for marker in markers)

    def _failed_task_result(
        self,
        task_type: TaskType,
        provider: AIProvider,
        processing_time: float,
        error: str,
    ) -> TaskResult:
        benchmark = BenchmarkResult(
            provider=provider,
            task_type=task_type,
            processing_time=processing_time,
            quality_score=0.0,
            cost_estimate=0.0,
            success=False,
            error_message=error,
        )
        self.benchmark_results.append(benchmark)
        return TaskResult(
            task_type=task_type,
            provider=provider,
            content=f"Task failed: {error}",
            metadata={"error": error, "processing_time": processing_time},
            benchmark=benchmark,
        )

    @staticmethod
    def _build_gemini_batch_prompt(
        tasks: list[tuple[TaskType, str]], video_url: str
    ) -> str:
        task_lines = "\n".join(
            f'- "{task_type.value}": {prompt}' for task_type, prompt in tasks
        )
        schema_lines = ",\n".join(
            f'  "{task_type.value}": "string"' for task_type, _ in tasks
        )
        return f"""
Analyze this YouTube video once and complete every task below.
Video: {video_url}

Tasks:
{task_lines}

Return ONLY valid JSON with exactly these top-level keys:
{{
{schema_lines}
}}

Each value must be a detailed string. Include timestamps where relevant.
Keep each value concise enough for stable JSON: no more than 12 bullets or
roughly 900 words per key. For transcription, provide timestamped salient
events instead of attempting a full verbatim transcript.
""".strip()

    async def _parse_or_repair_gemini_batch_response(
        self,
        raw_content: str,
        tasks: list[tuple[TaskType, str]],
        provider: AIProvider,
    ) -> dict[str, Any]:
        """Parse batch JSON, repairing malformed model output if needed."""

        try:
            return self._parse_gemini_batch_response(raw_content)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini batch JSON parse failed, attempting repair: %s", exc)
            repair_prompt = self._build_gemini_json_repair_prompt(raw_content, tasks)
            repaired = await self._execute_with_gemini_text(
                repair_prompt,
                provider,
                response_mime_type="application/json",
            )
            return self._parse_gemini_batch_response(repaired)

    @staticmethod
    def _build_gemini_json_repair_prompt(
        raw_content: str,
        tasks: list[tuple[TaskType, str]],
    ) -> str:
        schema_lines = ",\n".join(
            f'  "{task_type.value}": "string"' for task_type, _ in tasks
        )
        return f"""
Repair the malformed JSON below into valid compact JSON.
Return ONLY valid JSON with exactly these top-level keys:
{{
{schema_lines}
}}

Preserve the useful content, but shorten any overlong field enough to make the
JSON stable. Do not add commentary outside JSON.

Malformed JSON:
{raw_content[:24000]}
""".strip()

    @staticmethod
    def _parse_gemini_batch_response(raw_content: str) -> dict[str, Any]:
        content = raw_content.strip()
        if content.startswith("```json"):
            content = content[len("```json") :].strip()
        if content.startswith("```"):
            content = content[len("```") :].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini batch response must be a JSON object")
        return parsed

    @staticmethod
    def _stringify_task_content(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return json.dumps(value, indent=2)

    async def _execute_task_with_provider(
        self, task_type: TaskType, prompt: str, provider: AIProvider, video_url: str
    ) -> TaskResult:
        """Execute a specific task with the designated AI provider"""

        start_time = time.time()

        try:
            if provider in [
                AIProvider.GEMINI_FLASH,
                AIProvider.GEMINI_COMPAT_FLASH,
            ]:
                content = await self._execute_with_gemini(prompt, provider, video_url)
            elif provider == AIProvider.GROK_4:
                content = await self._execute_with_grok4(prompt, video_url)
            elif provider == AIProvider.CLAUDE_3_5_SONNET:
                content = await self._execute_with_claude(prompt, video_url)
            elif provider == AIProvider.GPT_4O:
                content = await self._execute_with_gpt4o(prompt, video_url)
            elif provider == AIProvider.NVIDIA_VILA:
                content = await self._execute_with_nvidia(prompt, video_url)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            processing_time = time.time() - start_time

            # Calculate quality score based on content length and task type
            quality_score = self._calculate_quality_score(content, task_type)

            # Estimate cost (simplified)
            cost_estimate = self._estimate_cost(provider, len(content))

            benchmark = BenchmarkResult(
                provider=provider,
                task_type=task_type,
                processing_time=processing_time,
                quality_score=quality_score,
                cost_estimate=cost_estimate,
                success=True,
            )

            self.benchmark_results.append(benchmark)

            return TaskResult(
                task_type=task_type,
                provider=provider,
                content=content,
                metadata={
                    "processing_time": processing_time,
                    "quality_score": quality_score,
                    "cost_estimate": cost_estimate,
                },
                benchmark=benchmark,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Task execution failed: {e}")

            benchmark = BenchmarkResult(
                provider=provider,
                task_type=task_type,
                processing_time=processing_time,
                quality_score=0.0,
                cost_estimate=0.0,
                success=False,
                error_message=str(e),
            )

            self.benchmark_results.append(benchmark)

            return TaskResult(
                task_type=task_type,
                provider=provider,
                content=f"Task failed: {str(e)}",
                metadata={"error": str(e)},
                benchmark=benchmark,
            )

    async def _execute_with_nvidia(self, prompt: str, video_url: str) -> str:
        """Execute task with NVIDIA VILA/Cosmos"""
        if not self.vision_processor or not self.vision_processor.nvidia.available:
            raise Exception("NVIDIA Processor not available")

        return await self.vision_processor.nvidia.analyze_video_vlm(video_url, prompt)

    async def _execute_with_gemini(
        self,
        prompt: str,
        provider: AIProvider,
        video_url: str,
        *,
        response_mime_type: str | None = None,
    ) -> str:
        """Execute task with Google AI (Gemini) using new google.genai SDK"""

        if not self.gemini_client:
            raise Exception("Gemini client not available")

        if not video_url or not video_url.strip():
            raise ValueError("Gemini video URL is required for video analysis")

        model_candidates = [provider]
        if provider == AIProvider.GEMINI_FLASH and (
            AIProvider.GEMINI_COMPAT_FLASH.value != provider.value
        ):
            model_candidates.append(AIProvider.GEMINI_COMPAT_FLASH)

        errors: list[str] = []
        for candidate in model_candidates:
            try:
                request: dict[str, Any] = {
                    "model": candidate.value,
                    "contents": types.Content(
                        parts=[
                            types.Part(file_data=types.FileData(file_uri=video_url)),
                            types.Part(text=prompt),
                        ]
                    ),
                }

                config_kwargs = {
                    "max_output_tokens": int(
                        os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "16384")
                    )
                }
                if response_mime_type:
                    config_kwargs["response_mime_type"] = response_mime_type
                request["config"] = types.GenerateContentConfig(**config_kwargs)

                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    **request,
                )

                content = self._extract_gemini_text(response).strip()
                if not content:
                    raise ValueError(
                        f"Gemini returned empty response for {candidate.value}"
                    )

                return content

            except Exception as e:
                error_text = str(e)
                errors.append(f"{candidate.value}: {error_text}")
                logger.error(f"❌ Gemini execution failed with {candidate.value}: {e}")
                if not self._should_try_compat_gemini(e):
                    raise

        raise RuntimeError("Gemini execution failed for all models: " + " | ".join(errors))

    async def _execute_with_gemini_text(
        self,
        prompt: str,
        provider: AIProvider,
        *,
        response_mime_type: str | None = None,
    ) -> str:
        """Execute a text-only Gemini request for transcript/metadata fallback."""

        if not self.gemini_client:
            raise Exception("Gemini client not available")

        model_candidates = [provider]
        if provider == AIProvider.GEMINI_FLASH and (
            AIProvider.GEMINI_COMPAT_FLASH.value != provider.value
        ):
            model_candidates.append(AIProvider.GEMINI_COMPAT_FLASH)

        errors: list[str] = []
        for candidate in model_candidates:
            try:
                request: dict[str, Any] = {
                    "model": candidate.value,
                    "contents": prompt,
                    "config": self._build_gemini_generation_config(
                        response_mime_type=response_mime_type
                    ),
                }
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    **request,
                )
                content = self._extract_gemini_text(response).strip()
                if not content:
                    raise ValueError(
                        f"Gemini returned empty response for {candidate.value}"
                    )
                return content
            except Exception as e:
                errors.append(f"{candidate.value}: {e}")
                logger.error(
                    "❌ Gemini text execution failed with %s: %s",
                    candidate.value,
                    e,
                )
                if not self._should_try_compat_gemini(e):
                    raise

        raise RuntimeError(
            "Gemini text execution failed for all models: " + " | ".join(errors)
        )

    @staticmethod
    def _build_gemini_generation_config(
        response_mime_type: str | None = None,
    ) -> types.GenerateContentConfig:
        config_kwargs = {
            "max_output_tokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "16384"))
        }
        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type
        return types.GenerateContentConfig(**config_kwargs)

    @staticmethod
    def _extract_gemini_text(response: Any) -> str:
        """Extract text from google-genai responses without accepting empty parts."""

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        parts: list[str] = []
        for candidate in getattr(response, "candidates", None) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    parts.append(part_text)

        return "\n".join(parts)

    @staticmethod
    def _should_try_compat_gemini(error: Exception) -> bool:
        """Retry with the compatibility Flash model for model/quota surface issues."""

        message = str(error).lower()
        retry_markers = (
            "model not found",
            "not found for api version",
            "resource_exhausted",
            "quota",
            "unsupported",
        )
        return any(marker in message for marker in retry_markers)

    def _create_aiohttp_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with certificate validation enabled."""

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        return aiohttp.ClientSession(connector=connector)

    async def _execute_with_grok4(self, prompt: str, video_url: str) -> str:
        """Execute task with GROK4"""

        grok_api_key = os.getenv("XAI_API_KEY")
        if not grok_api_key:
            logger.warning("XAI_API_KEY not set, falling back to Gemini")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

        try:
            headers = {
                "Authorization": f"Bearer {grok_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "grok-4-0709",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert video content analyzer.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
            }

            async with self._create_aiohttp_session() as session:
                async with session.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        raise Exception(
                            f"GROK4 API error: {response.status}: {await response.text()}"
                        )

        except Exception as e:
            logger.error(f"❌ GROK4 execution failed: {e}")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

    async def _execute_with_claude(self, prompt: str, video_url: str) -> str:
        """Execute task with Claude API"""
        if os.getenv("USE_PLACEHOLDER_PROVIDERS", "false").lower() == "true":
            logger.warning("Using placeholder Claude implementation")
            return f"Claude analysis (placeholder): {prompt[:100]}..."

        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not claude_api_key:
            logger.warning("ANTHROPIC_API_KEY not set, falling back to Gemini")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

        try:
            headers = {
                "x-api-key": claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }

            async with self._create_aiohttp_session() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["content"][0]["text"]
                    else:
                        error_msg = (
                            f"Claude API error: {response.status}: "
                            f"{await response.text()}"
                        )
                        logger.error(error_msg)
                        # Fallback to Gemini
                        return await self._execute_with_gemini(
                            prompt, AIProvider.GEMINI_FLASH, video_url
                        )

        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            # Fallback to Gemini
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

    async def _execute_with_gpt4o(self, prompt: str, video_url: str) -> str:
        """Execute task with GPT-4o API"""
        if os.getenv("USE_PLACEHOLDER_PROVIDERS", "false").lower() == "true":
            logger.warning("Using placeholder GPT-4o implementation")
            return f"GPT-4o analysis (placeholder): {prompt[:100]}..."

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not set, falling back to Gemini")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

        try:
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }

            async with self._create_aiohttp_session() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_msg = (
                            f"OpenAI API error: {response.status}: "
                            f"{await response.text()}"
                        )
                        logger.error(error_msg)
                        # Fallback to Gemini
                        return await self._execute_with_gemini(
                            prompt, AIProvider.GEMINI_FLASH, video_url
                        )

        except Exception as e:
            logger.error(f"GPT-4o execution failed: {e}")
            # Fallback to Gemini
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_FLASH, video_url
            )

    def _calculate_quality_score(self, content: str, task_type: TaskType) -> float:
        """Calculate quality score based on content and task type"""

        base_score = min(len(content) / 1000.0, 1.0)  # Normalize by length

        # Task-specific scoring
        if task_type == TaskType.TRANSCRIPTION:
            # Look for timestamps
            timestamp_count = content.count(":") // 2  # Rough estimate
            base_score += min(timestamp_count / 10.0, 0.3)

        elif task_type == TaskType.SUMMARIZATION:
            # Look for sentence structure
            sentence_count = (
                content.count(".") + content.count("!") + content.count("?")
            )
            if 2 <= sentence_count <= 5:  # Good summary length
                base_score += 0.2

        elif task_type == TaskType.ACTION_GENERATION:
            # Look for action words
            action_words = [
                "create",
                "implement",
                "build",
                "develop",
                "analyze",
                "apply",
            ]
            action_count = sum(1 for word in action_words if word in content.lower())
            base_score += min(action_count / 5.0, 0.3)

        return min(base_score, 1.0)

    def _estimate_cost(self, provider: AIProvider, content_length: int) -> float:
        """Estimate cost for different providers"""

        # Simplified cost estimation (tokens per 1K characters)
        costs = {
            AIProvider.GEMINI_FLASH: 0.00015,
            AIProvider.GEMINI_COMPAT_FLASH: 0.00015,
            AIProvider.GROK_4: 0.00025,
            AIProvider.CLAUDE_3_5_SONNET: 0.00030,
            AIProvider.GPT_4O: 0.00040,
        }

        tokens = content_length * 1.3  # Rough token estimation
        return (tokens / 1000) * costs.get(provider, 0.00020)

    def _analyze_benchmarks(self) -> dict[str, Any]:
        """Analyze benchmarking results"""

        if not self.benchmark_results:
            return {"error": "No benchmark results available"}

        # Group by provider
        provider_stats = {}
        for result in self.benchmark_results:
            provider = result.provider.value
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "avg_processing_time": 0.0,
                    "avg_quality_score": 0.0,
                    "total_cost": 0.0,
                }

            stats = provider_stats[provider]
            stats["total_tasks"] += 1
            if result.success:
                stats["successful_tasks"] += 1
            stats["avg_processing_time"] += result.processing_time
            stats["avg_quality_score"] += result.quality_score
            stats["total_cost"] += result.cost_estimate

        # Calculate averages
        for provider, stats in provider_stats.items():
            if stats["total_tasks"] > 0:
                stats["avg_processing_time"] /= stats["total_tasks"]
                stats["avg_quality_score"] /= stats["total_tasks"]
                stats["success_rate"] = stats["successful_tasks"] / stats["total_tasks"]

        # Find best performers
        best_quality = max(
            provider_stats.items(), key=lambda x: x[1]["avg_quality_score"]
        )
        fastest = min(provider_stats.items(), key=lambda x: x[1]["avg_processing_time"])
        most_cost_effective = min(
            provider_stats.items(), key=lambda x: x[1]["total_cost"]
        )

        return {
            "provider_stats": provider_stats,
            "best_quality": best_quality[0],
            "fastest": fastest[0],
            "most_cost_effective": most_cost_effective[0],
            "total_tasks": len(self.benchmark_results),
            "successful_tasks": sum(1 for r in self.benchmark_results if r.success),
        }

    async def _generate_comprehensive_report(
        self,
        video_id: str,
        video_url: str,
        task_results: list[TaskResult],
        benchmark_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive report from all task results"""

        # Organize results by task type
        results_by_task = {}
        for result in task_results:
            task_name = result.task_type.value
            results_by_task[task_name] = {
                "content": result.content,
                "provider": result.provider.value,
                "quality_score": result.benchmark.quality_score,
                "processing_time": result.benchmark.processing_time,
                "cost_estimate": result.benchmark.cost_estimate,
            }

        # Generate summary
        summary = {
            "video_id": video_id,
            "video_url": video_url,
            "total_tasks": len(task_results),
            "successful_tasks": sum(1 for r in task_results if r.benchmark.success),
            "total_processing_time": sum(
                r.benchmark.processing_time for r in task_results
            ),
            "total_cost_estimate": sum(r.benchmark.cost_estimate for r in task_results),
            "average_quality_score": (
                sum(r.benchmark.quality_score for r in task_results) / len(task_results)
                if task_results
                else 0
            ),
        }

        return {
            "summary": summary,
            "task_results": results_by_task,
            "benchmark_analysis": benchmark_analysis,
            "recommendations": self._generate_recommendations(
                results_by_task, benchmark_analysis
            ),
        }

    def _generate_recommendations(
        self, results_by_task: dict[str, Any], benchmark_analysis: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations based on results"""

        recommendations = []

        # Quality-based recommendations
        if benchmark_analysis.get("best_quality"):
            recommendations.append(
                f"Use {benchmark_analysis['best_quality']} for high-quality content generation"
            )

        # Speed-based recommendations
        if benchmark_analysis.get("fastest"):
            recommendations.append(
                f"Use {benchmark_analysis['fastest']} for time-sensitive tasks"
            )

        # Cost-based recommendations
        if benchmark_analysis.get("most_cost_effective"):
            recommendations.append(
                f"Use {benchmark_analysis['most_cost_effective']} for cost-effective processing"
            )

        # Task-specific recommendations
        if "transcription" in results_by_task:
            if results_by_task["transcription"]["quality_score"] > 0.8:
                recommendations.append(
                    "High-quality transcription achieved - good for detailed analysis"
                )
            else:
                recommendations.append(
                    "Consider improving transcription quality for better analysis"
                )

        if "action_generation" in results_by_task:
            if results_by_task["action_generation"]["quality_score"] > 0.7:
                recommendations.append(
                    "Strong action generation - ready for implementation"
                )
            else:
                recommendations.append(
                    "Consider refining action generation for better implementation"
                )

        return recommendations

    async def _save_gemini_results(
        self, video_id: str, comprehensive_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Save comprehensive Gemini processing results"""

        logger.info(f"💾 Saving Gemini results for {video_id}")

        # Create result file
        result_file = self.output_dir / f"{video_id}_gemini_master_results.json"

        result_data = {
            "video_id": video_id,
            "processing_timestamp": datetime.now().isoformat(),
            "comprehensive_result": comprehensive_result,
            "benchmark_results": [r.__dict__ for r in self.benchmark_results],
            "file_path": str(result_file),
            "processing_method": "gemini_master_agent",
        }

        # Save to file - use custom encoder for Enum types
        def json_serializer(obj):
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable"
            )

        with open(result_file, "w") as f:
            json.dump(result_data, f, indent=2, default=json_serializer)

        logger.info(f"✅ Gemini results saved to: {result_file}")

        return {
            "success": True,
            "file_path": str(result_file),
            "total_tasks": comprehensive_result["summary"]["total_tasks"],
            "successful_tasks": comprehensive_result["summary"]["successful_tasks"],
        }


async def main():
    """Main execution function"""

    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        print(build_default_video_prompt())
        if not sys.stdin.isatty():
            print("Run again with: python src/agents/gemini_video_master_agent.py <YouTube URL>")
            sys.exit(2)

        try:
            choice = input("> ").strip()
        except EOFError:
            print("No video URL supplied.")
            sys.exit(2)

        if choice:
            video_url = choice
        elif DEFAULT_VIDEO_URL and not is_banned_video_url(DEFAULT_VIDEO_URL):
            video_url = DEFAULT_VIDEO_URL
        else:
            print("No video URL supplied.")
            sys.exit(0)

    # Check for banned video IDs
    video_id = extract_video_id(video_url)

    if video_id in BANNED_VIDEO_IDS:
        print("❌ This video is blocked because it is meme/non-business content.")
        print("   Please use a business or technical video for analysis.")
        sys.exit(1)

    master_agent = GeminiVideoMasterAgent()

    try:
        # Process with Gemini master agent
        result = await master_agent.process_video_with_gemini(video_url)

        if result["success"]:
            print("\n🎯 GEMINI MASTER AGENT SUCCESS:")
            print(f"   Video ID: {result['video_id']}")
            print(
                f"   Total Tasks: {result['comprehensive_result']['summary']['total_tasks']}"
            )
            print(
                f"   Successful Tasks: {result['comprehensive_result']['summary']['successful_tasks']}"
            )
            print(f"   Processing Time: {result['processing_time']:.3f}s")
            print(f"   Results File: {result['save_result']['file_path']}")

            # Display benchmark analysis
            benchmark = result["comprehensive_result"]["benchmark_analysis"]
            print("\n📊 BENCHMARK ANALYSIS:")
            print(f"   Best Quality: {benchmark.get('best_quality', 'N/A')}")
            print(f"   Fastest: {benchmark.get('fastest', 'N/A')}")
            print(
                f"   Most Cost-Effective: {benchmark.get('most_cost_effective', 'N/A')}"
            )

            # Display recommendations
            recommendations = result["comprehensive_result"]["recommendations"]
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

            # Display task results
            print("\n🤖 TASK RESULTS:")
            for task_name, task_data in result["comprehensive_result"][
                "task_results"
            ].items():
                print(
                    f"   {task_name}: {task_data['provider']} (Quality: {task_data['quality_score']:.2f})"
                )
        else:
            print(
                "❌ PROCESSING FAILED: "
                f"{result.get('error', 'No tasks completed successfully')}"
            )
            sys.exit(1)

        return result

    except Exception as e:
        print(f"❌ PROCESSING FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
