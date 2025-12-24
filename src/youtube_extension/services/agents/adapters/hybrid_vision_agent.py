#!/usr/bin/env python3
"""
Hybrid Vision Agent
===================

Multi-modal vision agent backed by Gemini. Previously routed between
FastVLM and Gemini, but now relies solely on cloud processing while
retaining the same interface for callers.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from PIL import Image

from ..base_agent import BaseAgent, AgentResult
from ...ai import (
    HybridProcessorService,
    HybridConfig,
    HybridResult,
    ProcessingMode,
    TaskType,
    GeminiConfig
)


@dataclass
class VisionAnalysisResult:
    """Structured result from vision analysis"""
    description: str
    objects_detected: List[str]
    scene_analysis: str
    text_content: List[str]
    confidence_score: float
    processing_mode: str
    local_latency: Optional[float] = None
    cloud_latency: Optional[float] = None


from ..registry import register
from ..dto import AgentRequest, AgentResult

@register
class HybridVisionAgent(BaseAgent):
    name = "hybrid_vision"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Hybrid Vision Agent.

        Args:
            config: Configuration including API keys and model settings
        """
        self._hybrid_processor = None
        self._setup_hybrid_processor()

    def _setup_hybrid_processor(self) -> None:
        """Initialise the Gemini-only hybrid processor."""
        gemini_cfg = GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GEMINI_LOCATION", "us-central1"),
        )

        try:
            self._hybrid_processor = HybridProcessorService(HybridConfig(gemini=gemini_cfg))
            self.logger.info("Hybrid vision agent initialised with Gemini backend")
        except Exception as exc:
            self.logger.error(f"Failed to initialise hybrid processor: {exc}")
            self._hybrid_processor = None

    async def run(self, req: AgentRequest) -> AgentResult:
        """
        Process vision data using hybrid system.

        Args:
            req: AgentRequest with 'image' or 'video' and 'prompt' in params

        Returns:
            AgentResult with vision analysis
        """
        start_time = asyncio.get_event_loop().time()
        action = req.params.get('action') or req.params.get('command')

        if not self._hybrid_processor:
            return AgentResult(
                status="error",
                output={},
                logs=["Hybrid processor not available"],
            )

        if action:
            return await self._handle_special_action(action, req.params, start_time)

        # Validate input
        if not any(key in req.params for key in ['image', 'video', 'image_path', 'video_path']):
            return AgentResult(
                status="error",
                output={},
                logs=["Missing required image or video data"],
            )

        if 'prompt' not in req.params:
            # Use default prompt for general analysis
            req.params['prompt'] = "Describe this image in detail, including objects, scenes, and any text you can see."

        try:
            # Extract processing parameters
            image_data = self._extract_image_data(req.params)
            prompt = req.params['prompt']
            task_type = self._determine_task_type(req.params)
            force_mode = self._get_processing_mode(req.params)

            # Process with hybrid system
            hybrid_result = await self._hybrid_processor.process(
                input_data=image_data,
                prompt=prompt,
                task_type=task_type,
                force_mode=force_mode,
                metadata=req.params.get('metadata', {}),
                **req.params.get('generation_params', {})
            )

            # Parse results
            vision_analysis = self._parse_hybrid_result(hybrid_result)

            processing_time = asyncio.get_event_loop().time() - start_time

            return AgentResult(
                status="ok" if hybrid_result.success else "error",
                output={
                    "vision_analysis": vision_analysis,
                    "raw_result": hybrid_result,
                    "processing_mode": hybrid_result.mode_used.value,
                    "routing_decision": hybrid_result.routing_decision,
                    "metrics": self._hybrid_processor.get_metrics()
                },
                logs=[hybrid_result.error] if hybrid_result.error else [f"Processing time: {processing_time:.2f}s"],
            )

        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Vision analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            return AgentResult(
                status="error",
                output={},
                logs=[error_msg, f"Processing time: {processing_time:.2f}s"],
            )

    async def _handle_special_action(
        self,
        action: str,
        input_data: Dict[str, Any],
        start_time: float,
    ) -> AgentResult:
        """Handle auxiliary hybrid operations such as caching, batch jobs, and tokens."""

        def _failure(message: str) -> AgentResult:
            processing_time = asyncio.get_event_loop().time() - start_time
            return AgentResult(
                success=False,
                data={"action": action},
                errors=[message],
                processing_time=processing_time,
                agent_name=self.name,
                timestamp=datetime.now()
            )

        try:
            if action == "create_ephemeral_token":
                token_kwargs = dict(input_data.get("token_params", {}) or {})
                model_name = token_kwargs.pop("model_name", input_data.get("model_name"))
                audience = token_kwargs.pop("audience", input_data.get("audience"))
                ttl_seconds = token_kwargs.pop("ttl_seconds", input_data.get("ttl_seconds"))

                result = await self._hybrid_processor.create_ephemeral_token(
                    model_name=model_name,
                    audience=audience,
                    ttl_seconds=ttl_seconds,
                    **token_kwargs,
                )

            elif action == "start_cached_session":
                contents = input_data.get("contents")
                if contents is None:
                    return _failure("start_cached_session requires 'contents'")

                session_kwargs = dict(input_data.get("generation_params", {}) or {})
                model_name = session_kwargs.pop("model_name", input_data.get("model_name"))
                display_name = session_kwargs.pop("display_name", input_data.get("display_name"))
                ttl_seconds = session_kwargs.pop("ttl_seconds", input_data.get("ttl_seconds", 3600))

                try:
                    ttl_seconds = int(ttl_seconds)
                except (TypeError, ValueError):
                    return _failure("ttl_seconds must be an integer value")

                result = await self._hybrid_processor.start_cached_session(
                    contents=contents,
                    model_name=model_name,
                    ttl_seconds=ttl_seconds,
                    display_name=display_name,
                    **session_kwargs,
                )

            elif action == "submit_batch_job":
                requests = input_data.get("requests")
                if not requests:
                    return _failure("submit_batch_job requires a non-empty 'requests' list")

                batch_kwargs = dict(input_data.get("batch_params", {}) or {})
                model_name = batch_kwargs.pop("model_name", input_data.get("model_name"))
                wait_flag = batch_kwargs.pop("wait", input_data.get("wait", False))
                poll_interval = batch_kwargs.pop("poll_interval", input_data.get("poll_interval", 5.0))
                timeout = batch_kwargs.pop("timeout", input_data.get("timeout", 600.0))

                result = await self._hybrid_processor.submit_batch_job(
                    requests,
                    model_name=model_name,
                    wait=wait_flag,
                    poll_interval=poll_interval,
                    timeout=timeout,
                    **batch_kwargs,
                )

            else:
                return _failure(f"Unknown hybrid action: {action}")

            success = bool(result.get("success"))
            processing_time = asyncio.get_event_loop().time() - start_time
            metrics = self._safe_get_metrics()

            data_payload = {
                "action": action,
                "result": result,
                "metrics": metrics,
            }

            if action == "create_ephemeral_token":
                data_payload["token"] = result.get("token")
            elif action == "start_cached_session":
                data_payload["cache"] = result.get("cache")
            elif action == "submit_batch_job":
                data_payload["operation"] = result.get("operation")
                data_payload["batch_completed"] = result.get("completed")

            error_message = result.get("error")
            errors = [] if success else [error_message or f"{action} failed"]

            return AgentResult(
                success=success,
                data=data_payload,
                errors=errors,
                processing_time=processing_time,
                agent_name=self.name,
                timestamp=datetime.now()
            )

        except Exception as exc:
            processing_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"{action} action failed: {str(exc)}"
            self.logger.error(error_msg, exc_info=True)
            return AgentResult(
                success=False,
                data={"action": action},
                errors=[error_msg],
                processing_time=processing_time,
                agent_name=self.name,
                timestamp=datetime.now()
            )

    def _safe_get_metrics(self) -> Dict[str, Any]:
        """Safely fetch metrics from the hybrid processor if available."""
        try:
            if self._hybrid_processor and hasattr(self._hybrid_processor, "get_metrics"):
                return self._hybrid_processor.get_metrics()
        except Exception as exc:
            self.logger.debug("Failed to retrieve hybrid metrics: %s", exc)
        return {}

    def _extract_image_data(self, input_data: Dict[str, Any]) -> Union[str, Path, Image.Image]:
        """Extract image data from input"""
        if 'image' in input_data:
            return input_data['image']
        elif 'image_path' in input_data:
            return Path(input_data['image_path'])
        elif 'video_path' in input_data:
            return Path(input_data['video_path'])
        elif 'video' in input_data:
            return input_data['video']
        else:
            raise ValueError("No image or video data found")

    def _determine_task_type(self, input_data: Dict[str, Any]) -> Optional[TaskType]:
        """Determine task type from input data"""
        # Check explicit task type
        if 'task_type' in input_data:
            task_type_str = input_data['task_type']
            try:
                return TaskType(task_type_str)
            except ValueError:
                self.logger.warning(f"Unknown task type: {task_type_str}")

        # Analyze prompt for task classification
        prompt = input_data.get('prompt', '').lower()

        if any(word in prompt for word in ['real-time', 'live', 'instant']):
            return TaskType.REAL_TIME_CAPTION
        elif any(word in prompt for word in ['youtube', 'video summary']):
            return TaskType.YOUTUBE_ANALYSIS
        elif any(word in prompt for word in ['complex', 'detailed analysis', 'reasoning']):
            return TaskType.COMPLEX_REASONING
        elif any(word in prompt for word in ['technical', 'documentation', 'code']):
            return TaskType.TECHNICAL_DOCUMENT
        elif any(word in prompt for word in ['private', 'confidential', 'sensitive']):
            return TaskType.PRIVACY_SENSITIVE

        return TaskType.GENERAL_QA

    def _get_processing_mode(self, input_data: Dict[str, Any]) -> Optional[ProcessingMode]:
        """Get processing mode from input data"""
        if 'processing_mode' in input_data:
            mode_str = input_data['processing_mode']
            try:
                return ProcessingMode(mode_str)
            except ValueError:
                self.logger.warning(f"Unknown processing mode: {mode_str}")

        return None

    def _parse_hybrid_result(self, hybrid_result: HybridResult) -> VisionAnalysisResult:
        """Parse hybrid result into structured vision analysis"""
        if not hybrid_result.success or not hybrid_result.response:
            return VisionAnalysisResult(
                description="Analysis failed",
                objects_detected=[],
                scene_analysis="Could not analyze scene",
                text_content=[],
                confidence_score=0.0,
                processing_mode=hybrid_result.mode_used.value
            )

        response = hybrid_result.response

        # Parse response for structured information
        # This is a simple parser - in production, you might use more sophisticated NLP
        description = response

        # Extract potential objects (simple keyword extraction)
        objects_detected = self._extract_objects(response)

        # Extract text content mentions
        text_content = self._extract_text_mentions(response)

        # Scene analysis
        scene_analysis = self._extract_scene_analysis(response)

        # Calculate confidence based on response quality and processing mode
        confidence_score = self._calculate_confidence(hybrid_result)

        return VisionAnalysisResult(
            description=description,
            objects_detected=objects_detected,
            scene_analysis=scene_analysis,
            text_content=text_content,
            confidence_score=confidence_score,
            processing_mode=hybrid_result.mode_used.value,
            local_latency=hybrid_result.local_result.latency if hybrid_result.local_result else None,
            cloud_latency=hybrid_result.cloud_result.latency if hybrid_result.cloud_result else None
        )

    def _extract_objects(self, response: str) -> List[str]:
        """Extract object mentions from response"""
        # Simple object detection based on common nouns
        common_objects = [
            'person', 'people', 'man', 'woman', 'child', 'car', 'vehicle', 'building',
            'tree', 'house', 'dog', 'cat', 'table', 'chair', 'computer', 'phone',
            'book', 'window', 'door', 'sky', 'water', 'mountain', 'road', 'sign'
        ]

        response_lower = response.lower()
        detected = []

        for obj in common_objects:
            if obj in response_lower:
                detected.append(obj)

        return detected[:10]  # Limit to top 10

    def _extract_text_mentions(self, response: str) -> List[str]:
        """Extract text content mentions"""
        text_indicators = ['text', 'words', 'writing', 'sign says', 'reads', 'written']
        text_content = []

        response_lower = response.lower()
        for indicator in text_indicators:
            if indicator in response_lower:
                # Try to extract what comes after the indicator
                start_idx = response_lower.find(indicator)
                context = response[start_idx:start_idx + 100]
                text_content.append(context)

        return text_content

    def _extract_scene_analysis(self, response: str) -> str:
        """Extract scene analysis from response"""
        # Look for scene description keywords
        scene_keywords = ['scene', 'setting', 'environment', 'location', 'background']

        for keyword in scene_keywords:
            if keyword in response.lower():
                # Extract sentence containing the keyword
                sentences = response.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return sentence.strip()

        # Fallback to first sentence if no scene keywords found
        sentences = response.split('.')
        return sentences[0].strip() if sentences else "Scene analysis not available"

    def _calculate_confidence(self, hybrid_result: HybridResult) -> float:
        """Calculate confidence score based on result quality"""
        if not hybrid_result.success:
            return 0.0

        base_confidence = 0.7

        # Boost confidence if Gemini succeeded with a response
        if hybrid_result.cloud_result and hybrid_result.cloud_result.success:
            base_confidence += 0.2

        # Boost confidence for low latency
        if hybrid_result.latency < 2.0:
            base_confidence += 0.1

        # Response quality indicators
        response_length = len(hybrid_result.response) if hybrid_result.response else 0
        if response_length > 100:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def is_available(self) -> bool:
        """Check if agent is available for processing"""
        return self._hybrid_processor is not None and self._hybrid_processor.is_available()

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        if not self._hybrid_processor:
            return {"available": False, "services": []}

        return {
            "available": True,
            "services": {
                "gemini": self._hybrid_processor.gemini.get_model_info()
            },
            "processing_modes": [mode.value for mode in ProcessingMode],
            "task_types": [task.value for task in TaskType],
            "metrics": self._hybrid_processor.get_metrics()
        }

    async def cleanup(self):
        """Cleanup hybrid processor resources"""
        if self._hybrid_processor:
            await self._hybrid_processor.cleanup()
            self._hybrid_processor = None
            self.logger.info("Hybrid vision agent cleaned up")
