#!/usr/bin/env python3
"""Workflow that extracts transcripts and orchestrates deployable action plans."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from youtube_extension.backend.services.metrics_service import MetricsService
from src.shared.youtube import RobustYouTubeMetadata, RobustYouTubeService
from typing import TYPE_CHECKING

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

    def __init__(
        self,
        *,
        youtube_service_factory=None,
        orchestrator: Optional[AgentOrchestrator] = None,
        hybrid_processor: Optional["HybridProcessorService"] = None,
        speech_service: Optional[SpeechToTextService] = None,
        metrics_service: Optional[MetricsService] = None,
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

    async def run(
        self,
        video_url: str,
        language: str = "en",
        transcript_text: Optional[str] = None,
        video_options: Optional[Any] = None,
    ) -> Dict[str, Any]:
        video_metadata = self._build_video_metadata(video_options)

        gemini_transcript: Dict[str, Any] = {}

        async with self._youtube_service_factory() as yt_service:
            metadata = await yt_service.get_video_metadata(video_url)
            if transcript_text is not None:
                transcript = {
                    "text": transcript_text,
                    "source": "provided",
                    "segments": [],
                }
            else:
                transcript = await yt_service.get_transcript(metadata.video_id, language=language)

            if not transcript.get("text"):
                transcript = await self._fallback_transcript_with_speech_service(
                    video_url,
                    language=language,
                )

            if not transcript.get("text"):
                gemini_transcript = await self._fallback_transcript_with_gemini(
                    video_url,
                    language=language,
                    video_metadata=video_metadata,
                )

                if gemini_transcript.get("text"):
                    transcript = gemini_transcript
                elif gemini_transcript.get("error") and "error" not in transcript:
                    transcript["error"] = gemini_transcript["error"]

        if video_metadata:
            transcript.setdefault("requested_video_metadata", video_metadata)

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

    async def _invoke_orchestrator(
        self,
        video_url: str,
        metadata: RobustYouTubeMetadata,
        transcript: Dict[str, Any],
        language: str,
        *,
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        agent_input = {
            "video_url": video_url,
            "metadata": asdict(metadata),
            "transcript": transcript.get("text", ""),
            "transcript_source": transcript.get("source"),
            "transcript_segments": transcript.get("segments", []),
        }

        if video_metadata:
            agent_input["video_metadata"] = video_metadata

        agent_configs = {
            "transcript_action": {
                "hybrid_processor": self._hybrid_processor,
                "language": language,
            }
        }

        orchestration_result = await self._orchestrator.execute_task(
            "transcript_action",
            agent_input,
            agent_configs=agent_configs,
        )
        return self._serialize_orchestration(orchestration_result, metadata)

    @staticmethod
    def _serialize_orchestration(result: OrchestrationResult, metadata: RobustYouTubeMetadata) -> Dict[str, Any]:
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
    def _serialize_agent(agent_result: AgentResult) -> Dict[str, Any]:
        success = getattr(agent_result, "success", None)
        if success is None and hasattr(agent_result, "status"):
            success = getattr(agent_result, "status") == "ok"

        data = getattr(agent_result, "data", None)
        if data is None and hasattr(agent_result, "output"):
            data = getattr(agent_result, "output")

        errors = getattr(agent_result, "errors", None)
        if errors is None and hasattr(agent_result, "logs"):
            errors = getattr(agent_result, "logs")

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
    ) -> Dict[str, Any]:
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

    def _build_video_metadata(self, options: Optional[Any]) -> Optional[Dict[str, Any]]:
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

        metadata: Dict[str, Any] = {}

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
        video_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
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

        video_path: Optional[Path] = None
        temp_root: Optional[Path] = None
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
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        if not self._metrics_service:
            return
        try:
            await self._metrics_service.record_metric(name, value, tags=tags)
        except Exception:  # pragma: no cover - metrics failures should not break flow
            logger.debug("Metric %s recording failed", name, exc_info=True)

    @staticmethod
    def _parse_gemini_transcript_payload(payload: str) -> Tuple[str, list[Dict[str, Any]]]:
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
    def _normalise_segments(raw_segments: Any) -> list[Dict[str, Any]]:
        """Coerce Gemini segment payloads into a consistent shape."""

        normalised: list[Dict[str, Any]] = []
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

    async def _download_video_file(self, video_url: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Download video content locally for Gemini File API processing."""

        try:
            import yt_dlp  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("yt-dlp not available for Gemini file fallback: %s", exc)
            return None, None

        def _download() -> Tuple[Optional[Path], Optional[Path]]:
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
