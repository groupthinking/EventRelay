"""Speech-to-Text integration for high-fidelity video transcripts."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:  # pragma: no cover - optional dependency
    from google.cloud import speech_v2
    from google.api_core import exceptions as google_exceptions
    SPEECH_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    speech_v2 = None
    google_exceptions = None
    SPEECH_AVAILABLE = False

try:  # pragma: no cover - optional dependency
    from google.cloud import storage  # type: ignore
    STORAGE_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    storage = None  # type: ignore
    STORAGE_AVAILABLE = False

try:  # pragma: no cover - optional dependency
    import yt_dlp  # type: ignore
    YT_DLP_AVAILABLE = True
except Exception:
    yt_dlp = None  # type: ignore
    YT_DLP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SpeechToTextConfig:
    """Configuration for Google Speech-to-Text V2."""

    project_id: Optional[str] = os.getenv("GOOGLE_SPEECH_PROJECT_ID")
    location: str = os.getenv("GOOGLE_SPEECH_LOCATION", "us-central1")
    recognizer_id: str = os.getenv("GOOGLE_SPEECH_RECOGNIZER", "default")
    model: str = os.getenv("GOOGLE_SPEECH_MODEL", "latest_long")
    enable_word_time_offsets: bool = True
    enable_automatic_punctuation: bool = True
    preferred_language_code: str = os.getenv("GOOGLE_SPEECH_LANGUAGE", "en-US")
    max_download_bytes: int = 200 * 1024 * 1024  # 200MB safety guard
    long_running_threshold_bytes: int = int(os.getenv("GOOGLE_SPEECH_LONG_RUNNING_THRESHOLD", str(10 * 1024 * 1024)))
    batch_timeout_seconds: int = int(os.getenv("GOOGLE_SPEECH_BATCH_TIMEOUT", "1800"))
    gcs_bucket: Optional[str] = os.getenv("GOOGLE_SPEECH_GCS_BUCKET")
    gcs_path_prefix: str = os.getenv("GOOGLE_SPEECH_GCS_PREFIX", "speech-transcripts")

    @property
    def recognizer_path(self) -> Optional[str]:
        if not self.project_id:
            return None
        recognizer = self.recognizer_id or "default"
        return f"projects/{self.project_id}/locations/{self.location}/recognizers/{recognizer}"


@dataclass
class SpeechToTextResult:
    success: bool
    transcript: str
    segments: list[dict[str, Any]]
    latency: float
    error: Optional[str] = None
    source: str = "speech_to_text_v2"


class SpeechToTextService:
    """High-level wrapper around Google Speech-to-Text V2."""

    def __init__(self, config: Optional[SpeechToTextConfig] = None):
        self.config = config or SpeechToTextConfig()
        self._client: Optional[Any] = None
        self._storage_client: Optional[Any] = None

    async def transcribe_youtube_video(
        self,
        video_url: str,
        *,
        language_code: Optional[str] = None,
    ) -> SpeechToTextResult:
        """Transcribe a YouTube video by downloading the audio track and sending it to Speech-to-Text."""

        if not SPEECH_AVAILABLE:
            error = "google-cloud-speech is not installed"
            logger.warning("Speech-to-Text unavailable: %s", error)
            return SpeechToTextResult(False, "", [], 0.0, error=error, source="speech_to_text_v2_unavailable")

        if not YT_DLP_AVAILABLE:
            error = "yt-dlp is required to download audio for transcription"
            logger.warning("Speech-to-Text fallback missing dependency: %s", error)
            return SpeechToTextResult(False, "", [], 0.0, error=error, source="speech_to_text_v2_unavailable")

        recognizer = self.config.recognizer_path
        if not recognizer:
            error = "Speech-to-Text recognizer configuration missing (set GOOGLE_SPEECH_PROJECT_ID/RECOGNIZER)"
            logger.warning(error)
            return SpeechToTextResult(False, "", [], 0.0, error=error, source="speech_to_text_v2_unconfigured")

        language = language_code or self.config.preferred_language_code
        if language and "-" not in language:
            # Speech-to-Text requires full BCP-47 codes; fallback to preferred locale for short codes.
            language = self.config.preferred_language_code or language

        start_time = time.perf_counter()
        logger.info(
            "speech_to_text.start",
            extra={
                "video_url": video_url,
                "language": language,
                "recognizer": recognizer,
            },
        )

        try:
            audio_bytes, mime_type, file_size = await self._download_audio_bytes(video_url)
        except Exception as exc:  # pragma: no cover - network / runtime specific
            logger.exception("Failed to download audio for %s: %s", video_url, exc)
            return SpeechToTextResult(False, "", [], 0.0, error=str(exc), source="audio_download_failed")

        if not audio_bytes:
            error = "Audio download returned empty payload"
            logger.warning(error)
            return SpeechToTextResult(False, "", [], 0.0, error=error, source="audio_download_failed")

        if file_size >= self.config.long_running_threshold_bytes:
            logger.info(
                "speech_to_text.batch_candidate",
                extra={
                    "video_url": video_url,
                    "file_size_bytes": file_size,
                    "threshold_bytes": self.config.long_running_threshold_bytes,
                },
            )

            if not self.config.gcs_bucket:
                latency = time.perf_counter() - start_time
                error = "Batch transcription required but GOOGLE_SPEECH_GCS_BUCKET is not configured"
                logger.error("%s (video=%s)", error, video_url)
                return SpeechToTextResult(
                    False,
                    "",
                    [],
                    latency,
                    error=error,
                    source="speech_to_text_v2_batch_unconfigured",
                )

            if not STORAGE_AVAILABLE:
                latency = time.perf_counter() - start_time
                error = "google-cloud-storage dependency missing for batch transcription"
                logger.error("%s (video=%s)", error, video_url)
                return SpeechToTextResult(
                    False,
                    "",
                    [],
                    latency,
                    error=error,
                    source="speech_to_text_v2_batch_unavailable",
                )

            batch_result = await self._transcribe_with_batch(
                audio_bytes,
                recognizer,
                language,
                mime_type,
            )

            if batch_result.success:
                return batch_result
            if batch_result.error:
                logger.warning(
                    "Batch transcription failed, falling back to synchronous recognition: %s",
                    batch_result.error,
                )

        try:
            response = await asyncio.to_thread(
                self._recognize_content,
                audio_bytes,
                recognizer,
                language,
                mime_type,
            )
        except google_exceptions.GoogleAPICallError as exc:  # pragma: no cover - depends on API
            latency = time.perf_counter() - start_time
            logger.exception("Speech-to-Text API error for %s: %s", video_url, exc)
            return SpeechToTextResult(False, "", [], latency, error=str(exc), source="speech_to_text_v2_error")
        except Exception as exc:  # pragma: no cover - defensive
            latency = time.perf_counter() - start_time
            logger.exception("Unexpected transcription error for %s: %s", video_url, exc)
            return SpeechToTextResult(False, "", [], latency, error=str(exc), source="speech_to_text_v2_error")

        latency = time.perf_counter() - start_time
        transcript, segments = self._parse_response(response)
        success = bool(transcript.strip())

        return SpeechToTextResult(
            success,
            transcript,
            segments,
            latency,
            error=None if success else "Speech-to-Text returned empty transcript",
        )

    async def _download_audio_bytes(self, video_url: str) -> Tuple[bytes, str, int]:
        """Download best available audio track using yt-dlp and return raw bytes."""

        def _download() -> Tuple[bytes, str]:
            with tempfile.TemporaryDirectory(prefix="stt_") as tmpdir:
                output_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
                ydl_opts = {
                    "skip_download": False,
                    "format": "bestaudio/best",
                    "outtmpl": output_template,
                    "noplaylist": True,
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[attr-defined]
                    info = ydl.extract_info(video_url, download=True)
                    filename = Path(ydl.prepare_filename(info))

                    if not filename.exists():
                        raise FileNotFoundError(f"Audio file not found after download: {filename}")

                    file_size = filename.stat().st_size
                    if file_size > self.config.max_download_bytes:
                        raise ValueError(
                            f"Downloaded audio exceeds max size {self.config.max_download_bytes} bytes"
                        )

                    data = filename.read_bytes()
                    mime_type = info.get("ext", "")
                    if mime_type:
                        mime_type = f"audio/{mime_type}"
                    else:
                        mime_type = "audio/webm"

                    return data, mime_type

        data, mime_type = await asyncio.to_thread(_download)
        return data, mime_type, len(data)

    async def _transcribe_with_batch(
        self,
        audio_content: bytes,
        recognizer: str,
        language: str,
        mime_type: str,
    ) -> SpeechToTextResult:
        start_time = time.perf_counter()
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                self._batch_recognize_content,
                audio_content,
                recognizer,
                language,
                mime_type,
            )
        except google_exceptions.GoogleAPICallError as exc:  # pragma: no cover - API specific
            latency = time.perf_counter() - start_time
            logger.exception("Batch transcription error: %s", exc)
            return SpeechToTextResult(
                False,
                "",
                [],
                latency,
                error=str(exc),
                source="speech_to_text_v2_batch_error",
            )
        except Exception as exc:  # pragma: no cover - defensive failover
            latency = time.perf_counter() - start_time
            logger.exception("Batch transcription unexpected error: %s", exc)
            return SpeechToTextResult(
                False,
                "",
                [],
                latency,
                error=str(exc),
                source="speech_to_text_v2_batch_error",
            )

        transcript, segments = self._parse_batch_response(response)
        latency = time.perf_counter() - start_time
        success = bool(transcript.strip())

        return SpeechToTextResult(
            success,
            transcript,
            segments,
            latency,
            error=None if success else "Batch transcription returned empty transcript",
            source="speech_to_text_v2_batch",
        )

    def _recognize_content(
        self,
        audio_content: bytes,
        recognizer: str,
        language: str,
        mime_type: str,
    ):
        """Send audio bytes to Speech-to-Text synchronously (runs in executor)."""

        if self._client is None:
            endpoint = "speech.googleapis.com"
            if self.config.location and self.config.location != "global":
                endpoint = f"{self.config.location}-speech.googleapis.com"

            self._client = speech_v2.SpeechClient(
                client_options={"api_endpoint": endpoint}
            )

        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=[language],
            model=self.config.model,
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=self.config.enable_word_time_offsets,
                enable_automatic_punctuation=self.config.enable_automatic_punctuation,
            ),
        )

        request = speech_v2.RecognizeRequest(
            recognizer=recognizer,
            config=config,
            content=audio_content,
        )

        return self._client.recognize(request=request)

    def _batch_recognize_content(
        self,
        audio_content: bytes,
        recognizer: str,
        language: str,
        mime_type: str,
    ):
        if self._client is None:
            endpoint = "speech.googleapis.com"
            if self.config.location and self.config.location != "global":
                endpoint = f"{self.config.location}-speech.googleapis.com"

            self._client = speech_v2.SpeechClient(
                client_options={"api_endpoint": endpoint}
            )

        if self._storage_client is None:
            if not STORAGE_AVAILABLE:
                raise RuntimeError("google-cloud-storage is required for batch transcription")
            self._storage_client = storage.Client()

        bucket = self._storage_client.bucket(self.config.gcs_bucket)
        blob_name = f"{self.config.gcs_path_prefix.rstrip('/')}/{uuid.uuid4().hex}"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(audio_content, content_type=mime_type)
        gcs_uri = f"gs://{self.config.gcs_bucket}/{blob_name}"
        logger.info(
            "speech_to_text.batch_upload",
            extra={
                "gcs_uri": gcs_uri,
                "recognizer": recognizer,
                "language": language,
                "mime_type": mime_type,
            },
        )

        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=[language],
            model=self.config.model,
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=self.config.enable_word_time_offsets,
                enable_automatic_punctuation=self.config.enable_automatic_punctuation,
            ),
        )

        file_metadata = speech_v2.BatchRecognizeFileMetadata(
            uri=gcs_uri,
        )

        request = speech_v2.BatchRecognizeRequest(
            recognizer=recognizer,
            config=config,
            files=[file_metadata],
            recognition_output_config=speech_v2.RecognitionOutputConfig(
                inline_response_config=speech_v2.InlineOutputConfig(),
            ),
        )

        try:
            operation = self._client.batch_recognize(request=request)
            operation_name = getattr(getattr(operation, "operation", None), "name", None) or getattr(operation, "name", None)
            if operation_name:
                logger.info(
                    "speech_to_text.batch_started",
                    extra={
                        "operation_name": operation_name,
                        "timeout_seconds": self.config.batch_timeout_seconds,
                    },
                )
            response = operation.result(timeout=self.config.batch_timeout_seconds)
            logger.info(
                "speech_to_text.batch_completed",
                extra={
                    "operation_name": operation_name,
                },
            )
        finally:
            try:
                blob.delete()  # Clean up uploaded audio
            except Exception:  # pragma: no cover - deletion best effort
                logger.debug("Failed to delete temporary GCS object %s", gcs_uri, exc_info=True)

        return response

    @staticmethod
    def _parse_response(response) -> Tuple[str, list[dict[str, Any]]]:  # pragma: no cover - simple parsing
        results = getattr(response, "results", []) or []
        return SpeechToTextService._parse_speech_results(results)

    @staticmethod
    def _parse_batch_response(response) -> Tuple[str, list[dict[str, Any]]]:
        transcript_parts: list[str] = []
        segments: list[dict[str, Any]] = []

        for file_result in getattr(response, "results", {}).values():
            inline_result = getattr(file_result, "inline_result", None)
            if inline_result is None:
                continue

            transcript = getattr(inline_result, "transcript", None)
            if transcript is None:
                continue

            text, segs = SpeechToTextService._parse_speech_results(getattr(transcript, "results", []))
            if text:
                transcript_parts.append(text)
            segments.extend(segs)

        full_transcript = "\n".join(part for part in transcript_parts if part).strip()
        return full_transcript, segments

    @staticmethod
    def _parse_speech_results(results) -> Tuple[str, list[dict[str, Any]]]:
        transcript_parts: list[str] = []
        segments: list[dict[str, Any]] = []

        for result in results or []:
            alternatives = getattr(result, "alternatives", [])
            if not alternatives:
                continue

            top_alt = alternatives[0]
            text = getattr(top_alt, "transcript", "").strip()
            if not text:
                continue

            transcript_parts.append(text)
            start = 0.0
            end = 0.0
            words = getattr(top_alt, "words", [])
            if words:
                first = words[0]
                last = words[-1]
                start = SpeechToTextService._duration_to_seconds(getattr(first, "start_offset", None))
                end = SpeechToTextService._duration_to_seconds(getattr(last, "end_offset", None))

            segments.append(
                {
                    "text": text,
                    "start": start,
                    "duration": max(0.0, end - start) if end and start else 0.0,
                }
            )

        full_transcript = "\n".join(transcript_parts).strip()
        return full_transcript, segments

    @staticmethod
    def _duration_to_seconds(duration: Any) -> float:
        if duration is None:
            return 0.0
        seconds = getattr(duration, "seconds", 0) or 0
        nanos = getattr(duration, "nanos", 0) or 0
        return float(seconds) + float(nanos) / 1_000_000_000


__all__ = [
    "SpeechToTextConfig",
    "SpeechToTextResult",
    "SpeechToTextService",
]
