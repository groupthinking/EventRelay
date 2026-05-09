#!/usr/bin/env python3
"""Workflow that extracts transcripts and orchestrates deployable action plans."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from src.shared.youtube import RobustYouTubeMetadata, RobustYouTubeService
from src.youtube_extension.utils.video_utils import extract_video_id
from uvai.ml.client import UVAIMLClient, get_uvai_ml_client
from youtube_extension.backend.services.metrics_service import MetricsService
from youtube_extension.utils import parse_duration_to_seconds

try:
    from youtube_extension.services.agents.adapters.agent_orchestrator import (
        AgentOrchestrator,
        OrchestrationResult,
    )
except ImportError:  # pragma: no cover - legacy path
    from youtube_extension.services.agents.agent_orchestrator import (  # type: ignore
        AgentOrchestrator,
        OrchestrationResult,
    )

try:
    from youtube_extension.services.agents.dto import AgentResult
except ImportError:  # pragma: no cover - fallback to base agent module
    from youtube_extension.services.agents.base_agent import AgentResult  # type: ignore
from youtube_extension.services.ai.speech_to_text_service import (
    SpeechToTextResult,
    SpeechToTextService,
)
from youtube_extension.services.skill_builder import get_skill_builder

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from youtube_extension.services.ai.hybrid_processor_service import (
        HybridProcessorService,
        TaskType,
    )
else:  # Runtime import deferral to avoid heavy GPU libraries in constrained envs
    HybridProcessorService = None  # type: ignore[assignment, misc]
    TaskType = None  # type: ignore[assignment, misc]


logger = logging.getLogger(__name__)


class TranscriptActionWorkflow:
    """End-to-end pipeline from transcript extraction to action plan generation."""

    ASYNC_VIDEO_THRESHOLD_SECONDS = 15 * 60
    TRANSCRIPT_OUTCOME_BASE_SCORE = 0.6
    TRANSCRIPT_OUTCOME_WORD_DIVISOR = 600.0
    TRANSCRIPT_OUTCOME_WORD_CAP = 0.25
    TRANSCRIPT_OUTCOME_SEGMENT_DIVISOR = 50.0
    TRANSCRIPT_OUTCOME_SEGMENT_CAP = 0.15

    def __init__(
        self,
        *,
        youtube_service_factory=None,
        orchestrator: AgentOrchestrator | None = None,
        hybrid_processor: HybridProcessorService | None = None,
        speech_service: SpeechToTextService | None = None,
        metrics_service: MetricsService | None = None,
        ml_client: UVAIMLClient | None = None,
    ):
        self._youtube_service_factory = youtube_service_factory or RobustYouTubeService
        self._orchestrator = orchestrator or AgentOrchestrator()
        if hybrid_processor is None:
            try:
                from youtube_extension.services.ai.hybrid_processor_service import (
                    HybridProcessorService as _HybridProcessorService,
                )
            except Exception as import_error:  # pragma: no cover - environment specific
                logger.warning(
                    "HybridProcessorService unavailable; disabling Gemini fallback: %s",
                    import_error,
                )
                self._hybrid_processor = None
            else:
                self._hybrid_processor = _HybridProcessorService()
        else:
            self._hybrid_processor = hybrid_processor
        self._speech_service = speech_service or SpeechToTextService()
        self._metrics_service = metrics_service
        self._skill_builder = get_skill_builder()
        self._ml_client = ml_client or get_uvai_ml_client()

    async def run(
        self,
        video_url: str,
        language: str = "en",
        transcript_text: str | None = None,
        video_options: Any | None = None,
        prefetched_metadata: RobustYouTubeMetadata | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.validate_video_url(video_url)
        video_metadata = self._build_video_metadata(video_options)

        gemini_transcript: dict[str, Any] = {}
        metadata = self._coerce_metadata(prefetched_metadata) or await self.fetch_video_metadata(
            video_url
        )
        metadata_dict = asdict(metadata)
        metadata_dict["duration_seconds"] = self.get_duration_seconds(metadata)
        metadata_dict["has_captions"] = bool(metadata.transcript_available)
        metadata_dict["language"] = metadata.default_audio_language or metadata.default_language
        predicted_transcript = (
            None
            if transcript_text is not None
            else await self._safe_score_transcript(metadata_dict)
        )

        async with self._youtube_service_factory() as yt_service:
            if transcript_text is not None:
                transcript = {
                    "text": transcript_text,
                    "source": "provided",
                    "segments": [],
                }
            else:
                transcript = await self._extract_transcript(
                    yt_service,
                    metadata,
                    video_url,
                    language=language,
                    video_metadata=video_metadata,
                    predicted_source=(
                        predicted_transcript.get("recommended_source")
                        if predicted_transcript
                        else None
                    ),
                )
                if transcript.get("source") in {"gemini_video", "gemini_video_file"}:
                    gemini_transcript = transcript

        if video_metadata:
            transcript.setdefault("requested_video_metadata", video_metadata)

        await self._record_transcript_outcome(metadata_dict, transcript)

        if not transcript.get("text"):
            errors: list[str] = []
            if transcript.get("error"):
                errors.append(transcript["error"])
            if gemini_transcript.get("error") and gemini_transcript["error"] not in errors:
                errors.append(gemini_transcript["error"])

            logger.error(
                "Transcript generation failed",
                extra={
                    "video_url": video_url,
                    "errors": errors or ["unknown"],
                },
            )

            await self._record_metric(
                "transcript_pipeline_failure",
                1.0,
                tags={"stage": "transcript_generation"},
            )

            response_metadata = asdict(metadata)
            if video_metadata:
                response_metadata["requested_video_metadata"] = video_metadata

            return {
                "success": False,
                "video_url": video_url,
                "metadata": response_metadata,
                "transcript": transcript,
                "outputs": {},
                "errors": errors or ["Transcript generation failed"],
                "orchestration_meta": {
                    "processing_time": 0.0,
                    "agents_used": [],
                },
            }

        orchestration = await self._invoke_orchestrator(
            video_url,
            metadata,
            transcript,
            language,
            video_metadata=video_metadata,
        )
        await self._rank_orchestrated_actions(orchestration, metadata)

        # Record outcome for continuous learning
        self._skill_builder.record_deployment(
            framework="video_analysis",
            deployment_target=transcript.get("source", "pipeline"),
            success=orchestration["success"],
            error_message="; ".join(orchestration["errors"]) if orchestration["errors"] else None,
            config={
                "agents_used": orchestration["agents_used"],
                "transcript_source": transcript.get("source"),
                "processing_time": orchestration["processing_time"],
            },
        )

        return {
            "success": orchestration["success"],
            "video_url": video_url,
            "metadata": orchestration["metadata"],
            "transcript": transcript,
            "outputs": orchestration["agents"],
            "errors": orchestration["errors"],
            "orchestration_meta": {
                "processing_time": orchestration["processing_time"],
                "agents_used": orchestration["agents_used"],
            },
        }

    def validate_video_url(self, video_url: str) -> None:
        parsed = urlparse(video_url)
        query_params = parse_qs(parsed.query)
        is_playlist_path = parsed.path.rstrip("/").endswith("/playlist")
        
        # Try to extract video ID from the URL (supports both youtu.be/ and v= formats)
        try:
            extract_video_id(video_url)
            has_video_id = True
        except ValueError:
            has_video_id = False
        
        # Reject if it's a playlist path or if there's a list parameter but no video ID
        playlist_without_video = bool(query_params.get("list")) and not has_video_id
        if is_playlist_path or playlist_without_video:
            raise ValueError(
                "Playlist URLs are not supported. Please provide a single YouTube video URL."
            )

    async def fetch_video_metadata(self, video_url: str) -> RobustYouTubeMetadata:
        self.validate_video_url(video_url)
        async with self._youtube_service_factory() as yt_service:
            try:
                return await yt_service.get_video_metadata(video_url)
            except Exception as meta_err:
                logger.warning(
                    "Metadata fetch failed for %s: %s — using minimal metadata",
                    video_url,
                    meta_err,
                )
                import re as _re

                video_id_match = _re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", video_url)
                video_id = video_id_match.group(1) if video_id_match else "unknown"
                return RobustYouTubeMetadata(
                    video_id=video_id,
                    title=f"Video {video_id}",
                    description="",
                    channel_id="",
                    channel_title="Unknown",
                    published_at="",
                    duration="PT0S",
                    view_count=0,
                    like_count=0,
                    comment_count=0,
                    thumbnail_urls={},
                    tags=[],
                    category_id="",
                    default_language="en",
                    default_audio_language="en",
                    live_broadcast_content="none",
                    transcript_available=False,
                    transcript_segments=0,
                    source_api="fallback",
                )

    @staticmethod
    def get_duration_seconds(metadata: RobustYouTubeMetadata | dict[str, Any]) -> int:
        duration_value = (
            metadata.get("duration") if isinstance(metadata, dict) else metadata.duration
        )
        return parse_duration_to_seconds(str(duration_value or "PT0S"))

    @staticmethod
    def _coerce_metadata(
        metadata: RobustYouTubeMetadata | dict[str, Any] | None,
    ) -> RobustYouTubeMetadata | None:
        if metadata is None:
            return None
        if isinstance(metadata, RobustYouTubeMetadata):
            return metadata
        return RobustYouTubeMetadata(**metadata)

    async def _safe_score_transcript(
        self, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            return await self._ml_client.score_transcript(metadata)
        except Exception:
            logger.debug("Transcript scoring unavailable", exc_info=True)
            return None

    async def _extract_transcript(
        self,
        yt_service: Any,
        metadata: RobustYouTubeMetadata,
        video_url: str,
        *,
        language: str,
        video_metadata: dict[str, Any] | None,
        predicted_source: str | None,
    ) -> dict[str, Any]:
        transcript: dict[str, Any] = {"text": "", "segments": [], "source": "unavailable"}
        attempted_sources: set[str] = set()

        for source in self._build_transcript_source_order(predicted_source):
            attempted_sources.add(source)
            if source == "youtube_api":
                transcript = await yt_service.get_transcript(
                    metadata.video_id,
                    language=language,
                )
            elif source == "speech_v2":
                transcript = await self._fallback_transcript_with_speech_service(
                    video_url,
                    language=language,
                )
            else:
                transcript = await self._fallback_transcript_with_gemini(
                    video_url,
                    language=language,
                    video_metadata=video_metadata,
                )

            if transcript.get("text"):
                return transcript

        if "error" not in transcript:
            transcript["error"] = (
                "Transcript generation failed after trying "
                + ", ".join(sorted(attempted_sources))
            )
        return transcript

    @staticmethod
    def _build_transcript_source_order(predicted_source: str | None) -> list[str]:
        preferred = {
            "youtube_api": ["youtube_api", "speech_v2", "gemini_video"],
            "speech_v2": ["speech_v2", "youtube_api", "gemini_video"],
            "gemini_video": ["gemini_video", "speech_v2", "youtube_api"],
            "gemini_video_file": ["gemini_video", "speech_v2", "youtube_api"],
        }.get(predicted_source or "", [])
        fallback = ["youtube_api", "speech_v2", "gemini_video"]
        ordered_sources: list[str] = []
        for source in [*preferred, *fallback]:
            if source not in ordered_sources:
                ordered_sources.append(source)
        return ordered_sources

    @staticmethod
    def _normalize_transcript_source(actual_source: str) -> str:
        """Normalize actual service source names to routing category names for ML consistency.
        
        Maps actual sources returned by services to the routing names used in _build_transcript_source_order,
        ensuring ML model training/inference uses consistent source names.
        """
        # YouTube API sources map to "youtube_api"
        if actual_source in {"youtube_transcript_api", "innertube_android", "youtube_search_python"}:
            return "youtube_api"
        
        # Speech-to-Text sources map to "speech_v2"
        if actual_source.startswith("speech_to_text_v2"):
            return "speech_v2"
        
        # Gemini sources map to their category
        if actual_source in {"gemini_video", "gemini_video_file"}:
            return actual_source
        
        # Fallback: return as-is for unknown sources
        return actual_source

    async def _record_transcript_outcome(
        self,
        metadata: dict[str, Any],
        transcript: dict[str, Any],
    ) -> None:
        transcript_text = str(transcript.get("text") or "").strip()
        success = bool(transcript_text)
        word_count = len(transcript_text.split())
        segment_count = len(transcript.get("segments") or [])
        actual_quality = min(
            1.0,
            max(
                0.0,
                (
                    self.TRANSCRIPT_OUTCOME_BASE_SCORE
                    if success
                    else 0.0
                )
                + min(
                    word_count / self.TRANSCRIPT_OUTCOME_WORD_DIVISOR,
                    self.TRANSCRIPT_OUTCOME_WORD_CAP,
                )
                + min(
                    segment_count / self.TRANSCRIPT_OUTCOME_SEGMENT_DIVISOR,
                    self.TRANSCRIPT_OUTCOME_SEGMENT_CAP,
                ),
            ),
        )
        try:
            actual_source = str(transcript.get("source") or "unknown")
            normalized_source = self._normalize_transcript_source(actual_source)
            await self._ml_client.record_transcript_outcome(
                metadata=metadata,
                actual_source=normalized_source,
                actual_quality=actual_quality,
                success=success,
            )
        except Exception:
            logger.debug("Transcript outcome recording unavailable", exc_info=True)

    async def _rank_orchestrated_actions(
        self,
        orchestration: dict[str, Any],
        metadata: RobustYouTubeMetadata,
    ) -> None:
        transcript_action = orchestration.get("agents", {}).get("transcript_action", {})
        transcript_action_data = transcript_action.get("data")
        if not isinstance(transcript_action_data, dict):
            return

        ranked_candidates = self._extract_actions_for_ranking(transcript_action_data)
        if not ranked_candidates:
            return

        try:
            ranking = await self._ml_client.rank_actions(
                ranked_candidates,
                video_context=asdict(metadata),
            )
        except Exception:
            logger.debug("Action ranking unavailable", exc_info=True)
            return

        ranked_actions = ranking.get("ranked_actions")
        if not isinstance(ranked_actions, list) or not ranked_actions:
            return

        transcript_action_data["priority_ranked_actions"] = ranked_actions
        transcript_action_data["action_ranking_meta"] = {
            "total_actions": ranking.get("total_actions", len(ranked_actions)),
            "processing_time_seconds": ranking.get("processing_time_seconds"),
        }

    @staticmethod
    def _extract_actions_for_ranking(
        transcript_action_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ranked_candidates: list[dict[str, Any]] = []
        task_board = transcript_action_data.get("task_board")
        if not isinstance(task_board, dict):
            return ranked_candidates

        for column, items in task_board.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                description = str(
                    item.get("definition_of_done")
                    or item.get("description")
                    or ""
                ).strip()
                title = str(item.get("title") or "").strip()
                text = " — ".join(part for part in [title, description] if part)
                if not text:
                    continue
                ranked_candidates.append(
                    {
                        "text": text,
                        "category": column,
                        "type": "task",
                    }
                )
        return ranked_candidates

    async def _invoke_orchestrator(
        self,
        video_url: str,
        metadata: RobustYouTubeMetadata,
        transcript: dict[str, Any],
        language: str,
        *,
        video_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        agent_input = {
            "video_url": video_url,
            "metadata": asdict(metadata),
            "transcript": transcript.get("text", ""),
            "transcript_source": transcript.get("source"),
            "transcript_segments": transcript.get("segments", []),
        }

        if video_metadata:
            agent_input["video_metadata"] = video_metadata

        # Inject learned lessons from previous pipeline runs
        skill_context = self._skill_builder.get_context(
            framework="video_analysis",
            deployment_target=transcript.get("source", "pipeline"),
        )
        if skill_context.get("has_data"):
            agent_input["learned_lessons"] = skill_context["lessons"]
            logger.info(
                "Injected %d learned lessons (success_rate=%.2f)",
                len(skill_context["lessons"]),
                skill_context.get("success_rate", 0),
            )

        agent_configs = {
            "transcript_action": {
                "hybrid_processor": self._hybrid_processor,
                "language": language,
            },
            "personality_agent": {
                "hybrid_processor": self._hybrid_processor,
            },
            "strategy_agent": {
                "hybrid_processor": self._hybrid_processor,
            }
        }

        task_calls = {
            "transcript_action": self._orchestrator.execute_task(
                "transcript_action",
                agent_input,
                agent_configs=agent_configs,
            ),
            "strategic_analysis": self._orchestrator.execute_task(
                "strategic_analysis",
                agent_input,
                agent_configs=agent_configs,
            ),
        }
        include_hyperframes = self._hyperframes_enabled()
        if include_hyperframes:
            task_calls["video_rendering"] = self._orchestrator.execute_task(
                "video_rendering",
                agent_input,
                agent_configs=agent_configs,
            )

        task_results = dict(
            zip(
                task_calls.keys(),
                await asyncio.gather(*task_calls.values()),
            )
        )
        transcript_result = task_results["transcript_action"]
        strategic_result = task_results["strategic_analysis"]
        rendering_result = task_results.get("video_rendering")

        # Merge results for final serialization
        merged_results = transcript_result.results.copy()
        merged_results.update(strategic_result.results)
        if rendering_result is not None:
            merged_results.update(rendering_result.results)

        final_result = OrchestrationResult(
            success=all(result.success for result in task_results.values()),
            results=merged_results,
            errors=[
                error
                for result in task_results.values()
                for error in result.errors
            ],
            total_processing_time=sum(
                result.total_processing_time for result in task_results.values()
            ),
            agents_used=list(
                {
                    agent_name
                    for result in task_results.values()
                    for agent_name in result.agents_used
                }
            ),
        )

        return self._serialize_orchestration(final_result, metadata)

    @staticmethod
    def _hyperframes_enabled() -> bool:
        return os.getenv("HYPERFRAMES_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @staticmethod
    def _serialize_orchestration(result: OrchestrationResult, metadata: RobustYouTubeMetadata) -> dict[str, Any]:
        return {
            "success": result.success,
            "agents": {
                name: TranscriptActionWorkflow._serialize_agent(agent_result)
                for name, agent_result in result.results.items()
            },
            "errors": result.errors,
            "processing_time": result.total_processing_time,
            "agents_used": result.agents_used,
            "metadata": asdict(metadata),
        }

    @staticmethod
    def _serialize_agent(agent_result: AgentResult) -> dict[str, Any]:
        success = getattr(agent_result, "success", None)
        if success is None and hasattr(agent_result, "status"):
            success = agent_result.status == "ok"

        data = getattr(agent_result, "data", None)
        if data is None and hasattr(agent_result, "output"):
            data = agent_result.output

        errors = getattr(agent_result, "errors", None)
        if errors is None and hasattr(agent_result, "logs"):
            errors = agent_result.logs

        processing_time = getattr(agent_result, "processing_time", None)
        timestamp = getattr(agent_result, "timestamp", None)

        if timestamp is not None and hasattr(timestamp, "isoformat"):
            timestamp_str = timestamp.isoformat()
        else:
            timestamp_str = None

        return {
            "success": success,
            "data": data,
            "errors": errors,
            "processing_time": processing_time,
            "timestamp": timestamp_str,
        }

    async def _fallback_transcript_with_speech_service(
        self,
        video_url: str,
        *,
        language: str,
    ) -> dict[str, Any]:
        start_time = asyncio.get_event_loop().time()
        result: SpeechToTextResult = await self._speech_service.transcribe_youtube_video(
            video_url,
            language_code=language,
        )

        if not result.success:
            await self._record_metric(
                "transcript_fallback_success",
                0.0,
                tags={"provider": "speech_v2"},
            )
            await self._record_metric(
                "transcript_fallback_latency_seconds",
                result.latency or (asyncio.get_event_loop().time() - start_time),
                tags={"provider": "speech_v2"},
            )
            return {
                "text": "",
                "source": result.source,
                "segments": result.segments,
                "error": result.error or "Speech-to-Text transcription failed",
            }

        latency = result.latency or (asyncio.get_event_loop().time() - start_time)
        await self._record_metric(
            "transcript_fallback_success",
            1.0,
            tags={"provider": "speech_v2"},
        )
        await self._record_metric(
            "transcript_fallback_latency_seconds",
            latency,
            tags={"provider": "speech_v2"},
        )

        return {
            "text": result.transcript,
            "source": result.source,
            "segments": result.segments,
            "processing_time": latency,
        }

    def _build_video_metadata(self, options: Any | None) -> dict[str, Any] | None:
        """Translate incoming request options into Gemini VideoMetadata payload."""

        if options is None:
            return None

        if isinstance(options, dict):
            data = options
        else:
            data = {
                "start_seconds": getattr(options, "start_seconds", None),
                "end_seconds": getattr(options, "end_seconds", None),
                "fps": getattr(options, "fps", None),
            }

        metadata: dict[str, Any] = {}

        start_seconds = data.get("start_seconds")
        if start_seconds is not None:
            metadata["start_offset"] = self._seconds_to_offset(float(start_seconds))

        end_seconds = data.get("end_seconds")
        if end_seconds is not None:
            metadata["end_offset"] = self._seconds_to_offset(float(end_seconds))

        fps = data.get("fps")
        if fps is not None:
            metadata["fps"] = float(fps)

        return metadata or None

    async def _fallback_transcript_with_gemini(
        self,
        video_url: str,
        *,
        language: str,
        video_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Attempt to transcribe via Gemini when Speech-to-Text cannot."""

        if self._hybrid_processor is None:
            logger.warning("Hybrid processor not configured; skipping Gemini fallback")
            return {
                "text": "",
                "segments": [],
                "source": "gemini_unavailable",
                "error": "Hybrid processor service is not available",
            }

        gemini_service = getattr(self._hybrid_processor, "gemini", None)
        if gemini_service is None or not gemini_service.is_available():
            logger.warning("Gemini fallback unavailable for transcript generation")
            return {
                "text": "",
                "segments": [],
                "source": "gemini_video_unavailable",
                "error": "Gemini service is not configured",
            }

        try:
            if TaskType is None:
                raise ImportError
            model_key = TaskType.VIDEO_UNDERSTANDING
        except Exception:
            model_key = None

        if model_key is not None:
            model_name = self._hybrid_processor.config.model_routing.get(
                model_key,
                self._hybrid_processor.config.gemini.model_name,
            )
        else:
            model_name = self._hybrid_processor.config.gemini.model_name
        gemini_service.select_model(model_name)

        transcription_prompt = (
            "You are a precise transcription engine. Transcribe the provided video in {lang}. "
            "Respond with JSON containing two keys: 'transcript' (string with the full transcript) "
            "and 'segments' (an array of objects with 'text', 'start', and 'duration' in seconds). "
            "Return well-formed JSON only."
        ).format(lang=language or "the original language")

        errors: list[str] = []

        primary_result = await gemini_service.process_youtube(
            video_url,
            transcription_prompt,
            response_mime_type="application/json",
            video_metadata=video_metadata,
        )

        await self._record_metric(
            "transcript_fallback_latency_seconds",
            (primary_result.latency or 0.0),
            tags={"provider": "gemini_youtube"},
        )
        await self._record_metric(
            "transcript_fallback_success",
            1.0 if (primary_result.success and primary_result.response) else 0.0,
            tags={"provider": "gemini_youtube"},
        )

        if primary_result.success and primary_result.response:
            text, segments = self._parse_gemini_transcript_payload(primary_result.response)
            if text:
                return {
                    "text": text,
                    "segments": segments,
                    "source": "gemini_video",
                    "processing_time": primary_result.latency,
                }

        if primary_result.error:
            errors.append(primary_result.error)

        video_path: Path | None = None
        temp_root: Path | None = None
        try:
            video_path, temp_root = await self._download_video_file(video_url)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to download video for Gemini fallback: %s", exc)
            errors.append(str(exc))

        if video_path:
            try:
                file_result = await gemini_service.process_video(
                    str(video_path),
                    transcription_prompt,
                    response_mime_type="application/json",
                    video_metadata=video_metadata,
                )

                await self._record_metric(
                    "transcript_fallback_latency_seconds",
                    (file_result.latency or 0.0),
                    tags={"provider": "gemini_file"},
                )
                await self._record_metric(
                    "transcript_fallback_success",
                    1.0 if (file_result.success and file_result.response) else 0.0,
                    tags={"provider": "gemini_file"},
                )

                if file_result.success and file_result.response:
                    text, segments = self._parse_gemini_transcript_payload(file_result.response)
                    if text:
                        return {
                            "text": text,
                            "segments": segments,
                            "source": "gemini_video_file",
                            "processing_time": file_result.latency,
                        }

                if file_result.error:
                    errors.append(file_result.error)
            finally:
                if video_path.exists():
                    try:
                        video_path.unlink()
                    except OSError:
                        pass
                if temp_root and temp_root.exists():
                    shutil.rmtree(temp_root, ignore_errors=True)

        error_message = errors[0] if errors else "Gemini transcription failed"
        logger.warning("Gemini transcription fallback failed: %s", error_message)

        return {
            "text": "",
            "segments": [],
            "source": "gemini_video_failed",
            "error": error_message,
        }

    async def _record_metric(
        self,
        name: str,
        value: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._metrics_service:
            return
        try:
            await self._metrics_service.record_metric(name, value, tags=tags)
        except Exception:  # pragma: no cover - metrics failures should not break flow
            logger.debug("Metric %s recording failed", name, exc_info=True)

    @staticmethod
    def _parse_gemini_transcript_payload(payload: str) -> tuple[str, list[dict[str, Any]]]:
        """Extract transcript text and segments from Gemini response payload."""

        if not payload:
            return "", []

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return payload.strip(), []

        if isinstance(parsed, dict):
            text = str(parsed.get("transcript") or parsed.get("text") or "").strip()
            segments = TranscriptActionWorkflow._normalise_segments(parsed.get("segments"))
            if text:
                return text, segments

            if parsed:
                return json.dumps(parsed, ensure_ascii=False), segments
            return "", segments

        if isinstance(parsed, list):
            segments = TranscriptActionWorkflow._normalise_segments(parsed)
            text_parts = []
            for item in parsed:
                if isinstance(item, dict):
                    value = item.get("text") or item.get("transcript")
                    if value:
                        text_parts.append(str(value))
                else:
                    text_parts.append(str(item))

            return "\n".join(part.strip() for part in text_parts if part).strip(), segments

        return str(parsed).strip(), []

    @staticmethod
    def _normalise_segments(raw_segments: Any) -> list[dict[str, Any]]:
        """Coerce Gemini segment payloads into a consistent shape."""

        normalised: list[dict[str, Any]] = []
        if not isinstance(raw_segments, list):
            return normalised

        for entry in raw_segments:
            if not isinstance(entry, dict):
                continue

            text = str(entry.get("text") or entry.get("transcript") or "").strip()
            if not text:
                continue

            start = TranscriptActionWorkflow._parse_to_seconds(
                entry.get("start")
                or entry.get("start_time")
                or entry.get("offset")
            )

            duration_value = entry.get("duration")
            if duration_value is None and entry.get("end") is not None:
                end_seconds = TranscriptActionWorkflow._parse_to_seconds(entry.get("end"))
                duration_value = max(0.0, end_seconds - start)

            duration = TranscriptActionWorkflow._parse_to_seconds(duration_value)

            normalised.append(
                {
                    "text": text,
                    "start": start,
                    "duration": max(duration, 0.0),
                }
            )

        return normalised

    @staticmethod
    def _parse_to_seconds(value: Any) -> float:
        """Best-effort conversion of common timestamp formats to seconds."""

        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned.endswith("s"):
                cleaned = cleaned[:-1]

            if ":" in cleaned:
                parts = [p or "0" for p in cleaned.split(":")]
                parts = [float(p) for p in parts]
                while len(parts) < 3:
                    parts.insert(0, 0.0)
                hours, minutes, seconds = parts[-3:]
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return 0.0

    @staticmethod
    def _seconds_to_offset(value: float) -> str:
        trimmed = f"{value:.3f}".rstrip("0").rstrip(".")
        return f"{trimmed}s"

    async def _download_video_file(self, video_url: str) -> tuple[Path | None, Path | None]:
        """Download video content locally for Gemini File API processing."""

        try:
            import yt_dlp  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("yt-dlp not available for Gemini file fallback: %s", exc)
            return None, None

        def _download() -> tuple[Path | None, Path | None]:
            temp_dir = Path(tempfile.mkdtemp(prefix="gemini_video_"))
            output_template = str(temp_dir / "%(id)s.%(ext)s")
            ydl_opts = {
                "skip_download": False,
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "merge_output_format": "mp4",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[attr-defined]
                info = ydl.extract_info(video_url, download=True)
                filename = Path(ydl.prepare_filename(info))
                if not filename.exists():
                    raise FileNotFoundError("Video download failed")
                return filename, temp_dir

        return await asyncio.to_thread(_download)
