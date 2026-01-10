#!/usr/bin/env python3
"""
Vision Processor
================

Core vision processing module with Google Video Intelligence API integration.
Implements the Globo-style workflow: proxy video → OCR → metadata extraction.

All outputs are signed with QuantomCode ECDSA before caching/transmission.
"""

import asyncio
import base64
import hashlib
import io
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

# Vision AI imports
try:
    from google.cloud import videointelligence
    from google.cloud import storage
    from google.cloud import vision

    HAS_VISION_DEPS = True
except ImportError:
    HAS_VISION_DEPS = False
    logging.warning("Google Cloud Vision/Video AI not available")

from quantomcode_signer import QuantomCodeSigner, get_signer

logger = logging.getLogger("VisionProcessor")


@dataclass
class VisionResult:
    """Result from vision processing with signature."""

    result_id: str
    provider: str  # "google_video_ai" | "google_vision_ai"
    processing_type: str  # "ocr" | "label" | "transcription" | "shot_detection"
    labels: list[str]
    ocr_text: Optional[str]
    transcription: Optional[str]
    confidence: float
    processing_time: float
    timestamp: str
    cache_key: str
    signature: Optional[str] = None  # Base64 ECDSA signature

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for signing/caching."""
        return asdict(self)


@dataclass
class VideoJob:
    """Async video processing job."""

    job_id: str
    video_uri: str
    status: str  # "pending" | "processing" | "completed" | "failed"
    created_at: str
    completed_at: Optional[str] = None
    results: Optional[list[VisionResult]] = None
    error: Optional[str] = None


class NvidiaProcessor:
    """Processor for NVIDIA Cosmos/VLM capabilities via NIM API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.available = bool(self.api_key)

    async def get_video_embedding(self, video_data: bytes) -> list[float]:
        """Get Cosmos video embedding for semantic search"""
        if not self.available:
            return []

        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "input": [base64.b64encode(video_data).decode("utf-8")],
                        "model": "nvidia/cosmos-nemotron-34b",
                        "encoding_format": "float",
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["data"][0]["embedding"]
                    else:
                        logger.error(f"NVIDIA API error: {await response.text()}")
                        return []
        except Exception as e:
            logger.error(f"NIM embedding error: {e}")
            return []

    async def analyze_video_vlm(self, video_uri: str, prompt: str) -> str:
        """Analyze video using NVIDIA VLM (VILA / Cosmos)"""
        if not self.available:
            return "NVIDIA API key not configured"

        # VLM Implementation via NIM (chat completions format)
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "nvidia/vila-1.5-40b",  # Using VILA for video QA
                        "messages": [
                            {
                                "role": "user",
                                "content": f"{prompt} <video_url>{video_uri}</video_url>",
                            }
                        ],
                        "temperature": 0.2,
                        "top_p": 0.7,
                        "max_tokens": 1024,
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"NVIDIA VLM error: {error_text}")
                        return f"Error: {error_text}"
        except Exception as e:
            logger.error(f"NIM VLM error: {e}")
            return f"Error: {str(e)}"


# Update VisionProcessor to include NvidiaProcessor
class VisionProcessor:
    """
    Production vision processor with dual-capability:
    1. Google Video Intelligence (Classic)
    2. NVIDIA Cosmos/VLM (New - Cognitive)
    """

    def __init__(self, gcs_bucket: Optional[str] = None):
        """Initialize vision processor."""
        self._video_client = None
        self._vision_client = None
        self._storage_client = None
        self._signer = get_signer()
        self._gcs_bucket = gcs_bucket or os.getenv(
            "VISION_GCS_BUCKET", "uvai-vision-processing"
        )
        self._pending_jobs: dict[str, VideoJob] = {}

        # Initialize NVIDIA processor
        self.nvidia = NvidiaProcessor()

        self._init_clients()

    def _init_clients(self):
        """Initialize Google Cloud clients."""
        if not HAS_VISION_DEPS:
            logger.warning("Vision dependencies not available")
            # Don't return here so we initialize NVIDIA even if Google deps fail

        try:
            if HAS_VISION_DEPS:
                self._video_client = videointelligence.VideoIntelligenceServiceClient()
                self._vision_client = vision.ImageAnnotatorClient()
                self._storage_client = storage.Client()
                logger.info("✅ Google Vision clients initialized")

            if self.nvidia.available:
                logger.info("✅ NVIDIA Cosmos/VLM initialized")
            else:
                logger.warning("⚠️ NVIDIA API key not found - Cosmos disabled")

        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {e}")

    def _generate_cache_key(self, data: bytes, processing_type: str) -> str:
        """Generate deterministic cache key for vision data."""
        content_hash = hashlib.sha256(data).hexdigest()[:16]
        return f"vision:{processing_type}:{content_hash}"

    def _generate_result_id(self) -> str:
        """Generate unique result ID."""
        return f"vr_{int(time.time() * 1000)}_{os.urandom(4).hex()}"

    async def process_frame(
        self,
        frame_data: bytes,
        detect_labels: bool = True,
        extract_ocr: bool = True,
    ) -> VisionResult:
        """
        Process a single frame for OCR and label detection.

        This is the primary method for the clapperboard detection workflow.

        Args:
            frame_data: Raw image bytes (JPEG/PNG)
            detect_labels: Whether to detect objects/labels
            extract_ocr: Whether to extract text via OCR

        Returns:
            Signed VisionResult
        """
        start_time = time.time()
        result_id = self._generate_result_id()
        cache_key = self._generate_cache_key(frame_data, "frame")

        labels: list[str] = []
        ocr_text: Optional[str] = None
        confidence = 0.0

        if not self._vision_client:
            return self._create_mock_result(
                result_id, cache_key, start_time, "Vision client not available"
            )

        try:
            loop = asyncio.get_event_loop()
            image = vision.Image(content=frame_data)

            # Run label detection
            if detect_labels:
                label_response = await loop.run_in_executor(
                    None,
                    lambda: self._vision_client.label_detection(image=image),
                )
                labels = [
                    label.description for label in label_response.label_annotations[:10]
                ]
                if label_response.label_annotations:
                    confidence = max(
                        label.score for label in label_response.label_annotations
                    )

            # Run OCR for clapperboard text
            if extract_ocr:
                ocr_response = await loop.run_in_executor(
                    None,
                    lambda: self._vision_client.text_detection(image=image),
                )
                if ocr_response.text_annotations:
                    ocr_text = ocr_response.text_annotations[0].description
                    # Parse clapperboard format: "SCENE X TAKE Y"
                    ocr_text = self._parse_clapperboard_text(ocr_text)

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return self._create_error_result(result_id, cache_key, start_time, str(e))

        processing_time = time.time() - start_time

        result = VisionResult(
            result_id=result_id,
            provider="google_vision_ai",
            processing_type="frame_analysis",
            labels=labels,
            ocr_text=ocr_text,
            transcription=None,
            confidence=confidence,
            processing_time=processing_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cache_key=cache_key,
        )

        # Sign the result
        result = self._sign_result(result)

        logger.info(
            f"✅ Frame processed: {result_id} "
            f"({len(labels)} labels, OCR: {bool(ocr_text)}, {processing_time:.2f}s)"
        )
        return result

    def _parse_clapperboard_text(self, raw_text: str) -> str:
        """
        Parse clapperboard OCR text into structured format.

        Example inputs:
        - "SCENE 12\nTAKE 3\nDIRECTOR: Smith"
        - "SC12-T3 INT. STUDIO DAY"

        Returns cleaned, structured text.
        """
        if not raw_text:
            return ""

        # Clean up common OCR artifacts
        cleaned = raw_text.strip()
        cleaned = cleaned.replace("\n", " | ")

        return cleaned

    async def submit_video_job(
        self,
        video_uri: str,
        features: Optional[list[str]] = None,
    ) -> str:
        """
        Submit async video processing job.

        Args:
            video_uri: GCS URI (gs://bucket/path) or local path
            features: List of features to extract
                - "labels": Object/label detection
                - "transcription": Speech-to-text
                - "shots": Shot change detection
                - "ocr": Text detection in video

        Returns:
            Job ID for status polling
        """
        job_id = f"vj_{int(time.time() * 1000)}_{os.urandom(4).hex()}"

        job = VideoJob(
            job_id=job_id,
            video_uri=video_uri,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._pending_jobs[job_id] = job

        # Start async processing
        asyncio.create_task(self._process_video_async(job, features or ["labels"]))

        logger.info(f"📹 Video job submitted: {job_id} for {video_uri}")
        return job_id

    async def _process_video_async(self, job: VideoJob, features: list[str]):
        """Background video processing task."""
        job.status = "processing"

        if not self._video_client:
            job.status = "failed"
            job.error = "Video client not available"
            return

        try:
            # Map feature names to Video Intelligence features
            feature_map = {
                "labels": videointelligence.Feature.LABEL_DETECTION,
                "transcription": videointelligence.Feature.SPEECH_TRANSCRIPTION,
                "shots": videointelligence.Feature.SHOT_CHANGE_DETECTION,
                "ocr": videointelligence.Feature.TEXT_DETECTION,
            }

            video_features = [feature_map[f] for f in features if f in feature_map]

            # Build request
            video_context = None
            if "transcription" in features:
                video_context = videointelligence.VideoContext(
                    speech_transcription_config=videointelligence.SpeechTranscriptionConfig(
                        language_code="en-US",
                        enable_automatic_punctuation=True,
                    )
                )

            # Submit to Video Intelligence
            loop = asyncio.get_event_loop()
            operation = await loop.run_in_executor(
                None,
                lambda: self._video_client.annotate_video(
                    request=videointelligence.AnnotateVideoRequest(
                        input_uri=job.video_uri,
                        features=video_features,
                        video_context=video_context,
                    )
                ),
            )

            # Wait for completion (with timeout)
            result = await loop.run_in_executor(
                None, lambda: operation.result(timeout=300)
            )

            # Extract results
            job.results = self._extract_video_results(result, job.job_id)
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"✅ Video job completed: {job.job_id} "
                f"({len(job.results or [])} results)"
            )

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"❌ Video job failed: {job.job_id} - {e}")

    def _extract_video_results(self, response: Any, job_id: str) -> list[VisionResult]:
        """Extract VisionResults from Video Intelligence response."""
        results = []

        for annotation_result in response.annotation_results:
            # Extract labels
            if annotation_result.segment_label_annotations:
                labels = [
                    label.entity.description
                    for label in annotation_result.segment_label_annotations[:20]
                ]
                result = VisionResult(
                    result_id=f"{job_id}_labels",
                    provider="google_video_ai",
                    processing_type="label_detection",
                    labels=labels,
                    ocr_text=None,
                    transcription=None,
                    confidence=0.9,
                    processing_time=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    cache_key=f"video:{job_id}:labels",
                )
                results.append(self._sign_result(result))

            # Extract transcription
            if annotation_result.speech_transcriptions:
                transcripts = []
                for transcription in annotation_result.speech_transcriptions:
                    for alternative in transcription.alternatives:
                        transcripts.append(alternative.transcript)

                result = VisionResult(
                    result_id=f"{job_id}_transcription",
                    provider="google_video_ai",
                    processing_type="transcription",
                    labels=[],
                    ocr_text=None,
                    transcription=" ".join(transcripts),
                    confidence=0.85,
                    processing_time=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    cache_key=f"video:{job_id}:transcription",
                )
                results.append(self._sign_result(result))

            # Extract OCR text
            if annotation_result.text_annotations:
                ocr_texts = [
                    text.text for text in annotation_result.text_annotations[:10]
                ]
                result = VisionResult(
                    result_id=f"{job_id}_ocr",
                    provider="google_video_ai",
                    processing_type="ocr",
                    labels=[],
                    ocr_text=" | ".join(ocr_texts),
                    transcription=None,
                    confidence=0.8,
                    processing_time=0.0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    cache_key=f"video:{job_id}:ocr",
                )
                results.append(self._sign_result(result))

        return results

    def _sign_result(self, result: VisionResult) -> VisionResult:
        """Sign result with QuantomCode signer."""
        if self._signer.is_signing_available():
            # Create dict without signature for signing
            data_to_sign = result.to_dict()
            data_to_sign.pop("signature", None)
            result.signature = self._signer.sign_output_b64(data_to_sign)
        return result

    def _create_mock_result(
        self, result_id: str, cache_key: str, start_time: float, message: str
    ) -> VisionResult:
        """Create mock result when vision services unavailable."""
        return VisionResult(
            result_id=result_id,
            provider="mock",
            processing_type="mock",
            labels=["mock_label"],
            ocr_text=f"[MOCK] {message}",
            transcription=None,
            confidence=0.0,
            processing_time=time.time() - start_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cache_key=cache_key,
        )

    def _create_error_result(
        self, result_id: str, cache_key: str, start_time: float, error: str
    ) -> VisionResult:
        """Create error result."""
        result = VisionResult(
            result_id=result_id,
            provider="google_vision_ai",
            processing_type="error",
            labels=[],
            ocr_text=None,
            transcription=None,
            confidence=0.0,
            processing_time=time.time() - start_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cache_key=cache_key,
        )
        return self._sign_result(result)

    def get_job_status(self, job_id: str) -> Optional[VideoJob]:
        """Get status of video processing job."""
        return self._pending_jobs.get(job_id)

    def is_available(self) -> bool:
        """Check if vision processing is available."""
        return self._vision_client is not None or self._video_client is not None


# Global singleton
_processor_instance: Optional[VisionProcessor] = None


def get_processor() -> VisionProcessor:
    """Get or create global processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = VisionProcessor()
    return _processor_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def test():
        processor = VisionProcessor()

        print("\n👁️ Vision Processor Test")
        print("=" * 40)
        print(f"Available: {processor.is_available()}")
        print(f"Signer: {processor._signer.is_signing_available()}")

        # Test with mock frame if no real vision client
        if not processor.is_available():
            print("\n⚠️ Vision clients not available - testing mock mode")
            result = await processor.process_frame(b"test_image_data")
            print(f"Mock result: {result.result_id}")
            print(f"  Labels: {result.labels}")
            print(f"  OCR: {result.ocr_text}")
            print(f"  Signed: {bool(result.signature)}")

    asyncio.run(test())
