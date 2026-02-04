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
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import aiohttp

# Google AI imports - using new google.genai SDK
try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google AI not available - install: pip install google-genai")

# Add shared modules to path
import sys
from pathlib import Path

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

# Banned video IDs (memes, inappropriate content, etc.)
BANNED_VIDEO_IDS = frozenset(
    [
        "dQw4w9WgXcQ",  # Rickroll - not a business/technical video
    ]
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [GEMINI_MASTER] %(message)s",
    handlers=[logging.FileHandler("gemini_master_agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger("gemini_master_agent")


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
    PERSONALITY_MAPPING = "personality_mapping"


class AIProvider(Enum):
    """Available AI providers with benchmarking"""

    # Gemini 2.5 Flash - confirmed working for video understanding
    GEMINI_2_5_FLASH = "models/gemini-2.5-flash"
    GEMINI_2_0_FLASH = "models/gemini-2.0-flash-exp"
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
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.output_dir = Path("gemini_processed_videos")
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

        # Task delegation - Enforcing Gemini 2.5 Flash for all video operations
        # Ping-Pong Strategy: Parallel execution for Visual Analysis (Gemini + NVIDIA)
        self.task_delegation = {
            TaskType.TRANSCRIPTION: AIProvider.GEMINI_2_5_FLASH,
            TaskType.SUMMARIZATION: AIProvider.GEMINI_2_5_FLASH,
            TaskType.VISUAL_ANALYSIS: AIProvider.GEMINI_2_5_FLASH,
            TaskType.ACTION_GENERATION: AIProvider.GEMINI_2_5_FLASH,
            TaskType.CONTENT_CATEGORIZATION: AIProvider.GEMINI_2_5_FLASH,
            TaskType.TIMESTAMP_ANALYSIS: AIProvider.GEMINI_2_5_FLASH,
            TaskType.KEY_INSIGHTS: AIProvider.GEMINI_2_5_FLASH,
            TaskType.IMPLEMENTATION_PLAN: AIProvider.GEMINI_2_5_FLASH,
        }

        # Benchmarking results
        self.benchmark_results = []

        logger.info("🎯 GEMINI VIDEO MASTER AGENT INITIALIZED")

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        parsed = urlparse(url)
        if parsed.hostname in ["youtube.com", "www.youtube.com", "youtu.be"]:
            if parsed.path == "/watch":
                return parse_qs(parsed.query)["v"][0]
            elif parsed.hostname == "youtu.be":
                return parsed.path[1:]
        return url

    async def process_video_with_gemini(self, video_url: str) -> dict[str, Any]:
        """Process video using Google AI (Gemini) with task delegation"""

        start_time = time.time()
        video_id = self.extract_video_id(video_url)

        logger.info(f"🚀 GEMINI MASTER AGENT PROCESSING: {video_id}")

        try:
            # Stage 1: Task breakdown and delegation
            tasks = self._break_down_tasks(video_url)
            logger.info(f"📋 Created {len(tasks)} tasks for delegation")

            # Stage 2: Execute tasks with appropriate AI providers
            task_results = await self._execute_tasks_with_delegation(tasks, video_url)

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
                "task_results": task_results,
                "benchmark_analysis": benchmark_analysis,
                "comprehensive_result": comprehensive_result,
                "save_result": save_result,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "processing_method": "gemini_master_agent",
                "success": True,
            }

            logger.info(
                f"✅ GEMINI MASTER AGENT COMPLETE: {video_id} in {processing_time:.3f}s"
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
        ]

        return tasks

    async def _execute_tasks_with_delegation(
        self, tasks: list[tuple[TaskType, str]], video_url: str
    ) -> list[TaskResult]:
        """Execute tasks with appropriate AI provider delegation in PARALLEL"""

        coroutines = []
        logger.info(f"🔄 Starting parallel execution of {len(tasks)} tasks...")

        for task_type, prompt in tasks:
            # Get the best AI provider for this task
            provider = self.task_delegation[task_type]

            # Create coroutine for primary task
            logger.info(f"✨ Scheduled {task_type.value} with {provider.value}")
            coroutines.append(
                self._execute_task_with_provider(task_type, prompt, provider, video_url)
            )

            # PING PONG: Add parallel NVIDIA task for Visual Analysis
            if task_type == TaskType.VISUAL_ANALYSIS:
                logger.info(
                    f"✨ Scheduled {task_type.value} (Parallel) with NVIDIA VILA"
                )
                coroutines.append(
                    self._execute_task_with_provider(
                        task_type, prompt, AIProvider.NVIDIA_VILA, video_url
                    )
                )

        # Run all tasks in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results
        task_results = []
        for res in results:
            if isinstance(res, TaskResult):
                task_results.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Task failed during parallel execution: {res}")
                # We could add a failed TaskResult here for completeness if needed

        return task_results

    async def _execute_task_with_provider(
        self, task_type: TaskType, prompt: str, provider: AIProvider, video_url: str
    ) -> TaskResult:
        """Execute a specific task with the designated AI provider"""

        start_time = time.time()

        try:
            if provider in [
                AIProvider.GEMINI_2_5_FLASH,
                AIProvider.GEMINI_2_0_FLASH,
            ]:
                content = await self._execute_with_gemini(prompt, provider, video_url)
            elif provider == AIProvider.GROK_4:
                content = await self._execute_with_grok4(prompt)
            elif provider == AIProvider.CLAUDE_3_5_SONNET:
                content = await self._execute_with_claude(prompt)
            elif provider == AIProvider.GPT_4O:
                content = await self._execute_with_gpt4o(prompt)
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
        self, prompt: str, provider: AIProvider, video_url: str
    ) -> str:
        """Execute task with Google AI (Gemini) using new google.genai SDK"""

        if not self.gemini_client:
            raise Exception("Gemini client not available")

        try:
            # Use Gemini's video analysis capabilities with new SDK
            # For video URLs, we use the file_uri in the content parts
            response = self.gemini_client.models.generate_content(
                model=provider.value,
                contents=[
                    types.Part.from_uri(file_uri=video_url, mime_type="video/*"),
                    types.Part.from_text(text=prompt),
                ],
            )

            return response.text

        except Exception as e:
            logger.error(f"❌ Gemini execution failed: {e}")
            raise

    async def _execute_with_grok4(self, prompt: str) -> str:
        """Execute task with GROK4"""

        grok_api_key = os.getenv("XAI_API_KEY")
        if not grok_api_key:
            raise Exception("GROK4 API key not available")

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

            async with aiohttp.ClientSession() as session:
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
                        raise Exception(f"GROK4 API error: {response.status}")

        except Exception as e:
            logger.error(f"❌ GROK4 execution failed: {e}")
            raise

    async def _execute_with_claude(self, prompt: str) -> str:
        """Execute task with Claude API"""
        if os.getenv("USE_PLACEHOLDER_PROVIDERS", "false").lower() == "true":
            logger.warning("Using placeholder Claude implementation")
            return f"Claude analysis (placeholder): {prompt[:100]}..."

        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not claude_api_key:
            logger.warning("ANTHROPIC_API_KEY not set, falling back to Gemini")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_2_5_FLASH, ""
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

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["content"][0]["text"]
                    else:
                        error_msg = f"Claude API error: {response.status}"
                        logger.error(error_msg)
                        # Fallback to Gemini
                        return await self._execute_with_gemini(
                            prompt, AIProvider.GEMINI_2_5_FLASH, ""
                        )

        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            # Fallback to Gemini
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_2_5_FLASH, ""
            )

    async def _execute_with_gpt4o(self, prompt: str) -> str:
        """Execute task with GPT-4o API"""
        if os.getenv("USE_PLACEHOLDER_PROVIDERS", "false").lower() == "true":
            logger.warning("Using placeholder GPT-4o implementation")
            return f"GPT-4o analysis (placeholder): {prompt[:100]}..."

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not set, falling back to Gemini")
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_2_5_FLASH, ""
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

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_msg = f"OpenAI API error: {response.status}"
                        logger.error(error_msg)
                        # Fallback to Gemini
                        return await self._execute_with_gemini(
                            prompt, AIProvider.GEMINI_2_5_FLASH, ""
                        )

        except Exception as e:
            logger.error(f"GPT-4o execution failed: {e}")
            # Fallback to Gemini
            return await self._execute_with_gemini(
                prompt, AIProvider.GEMINI_2_5_FLASH, ""
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
            AIProvider.GEMINI_2_5_FLASH: 0.00015,
            AIProvider.GEMINI_2_0_FLASH: 0.00010,
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

    video_url = None
    default_video = (
        "https://www.youtube.com/watch?v=FHOujnBfwvk"  # Google DeepMind: Gemini 1.5 Pro
    )

    if len(sys.argv) > 1:
        video_url = sys.argv[1]
    else:
        print("\n🎥 Gemini Video Master Agent")
        print("===========================")
        print(f"No video URL provided. Using default technical video:\n{default_video}")
        print("---------------------------")
        choice = input(
            "Press [Enter] to process default, or paste a YouTube URL: "
        ).strip()

        if choice:
            video_url = choice
        else:
            video_url = default_video

    # Check for banned video IDs
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(video_url)
    video_id = None
    if parsed.hostname in ("youtube.com", "www.youtube.com"):
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif parsed.hostname == "youtu.be":
        video_id = parsed.path.lstrip("/")

    if video_id and video_id in BANNED_VIDEO_IDS:
        print(f"❌ Video ID '{video_id}' is banned (meme/non-business content)")
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
            print(f"❌ PROCESSING FAILED: {result['error']}")
            sys.exit(1)

        return result

    except Exception as e:
        print(f"❌ PROCESSING FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
