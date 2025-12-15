#!/usr/bin/env python3
"""
Gemini Service
==============

Cloud-based vision-language processing using Google Gemini.
Extracted from fastvlm_gemini_hybrid with clean service architecture.
"""

import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

from PIL import Image

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False
    logging.warning("Google Gemini not available - install: pip install google-generativeai")

try:
    from google.generativeai import types as genai_types
except ImportError:
    genai_types = None

try:
    from vertexai.generative_models import GenerativeModel, Part
    import vertexai
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False
    logging.warning("Vertex AI not available - install: pip install google-cloud-aiplatform")

TRANSFORMERS_DISABLE_FLAG = os.getenv("YOUTUBE_EXTENSION_DISABLE_TRANSFORMERS", "0").lower() in {"1", "true", "yes"}

try:
    if TRANSFORMERS_DISABLE_FLAG:
        raise ImportError("Transformers import disabled via YOUTUBE_EXTENSION_DISABLE_TRANSFORMERS")
    from transformers import pipeline as hf_pipeline  # type: ignore
    TRANSFORMERS_AVAILABLE = True
except Exception as exc:  # pragma: no cover - optional dependency
    hf_pipeline = None
    TRANSFORMERS_AVAILABLE = False
    logging.warning(
        "Transformers unavailable for Gemma support: %s", exc
    )


class _TextOnlyResponse(SimpleNamespace):
    """Simple response container mimicking google.generativeai responses."""

    def __init__(self, text: str, **kwargs):  # pragma: no cover - trivial container
        super().__init__(text=text, **kwargs)


class GemmaTextClient:
    """Lightweight wrapper around Hugging Face Gemma models for text tasks."""

    def __init__(
        self,
        model_name: str,
        *,
        max_new_tokens: int = 512,
        temperature: float = 1.0,  # Gemini 3 requires temp=1.0
        top_p: float = 0.9,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.model_name = self._normalize_model_name(model_name)
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.logger = logger or logging.getLogger(__name__)
        self._pipeline = None
        self._pipeline_error: Optional[str] = None

        if not TRANSFORMERS_AVAILABLE:
            self._pipeline_error = "transformers library not installed"
            return

        try:
            # Delay heavy model loads until explicitly requested.
            self._pipeline = hf_pipeline(  # pragma: no cover - depends on local weights
                task="text-generation",
                model=self.model_name,
                device_map="auto",
                torch_dtype="auto",
            )
        except Exception as exc:  # pragma: no cover - environment specific
            self._pipeline = None
            self._pipeline_error = str(exc)
            self.logger.warning(
                "Failed to initialize Gemma pipeline (%s): %s", self.model_name, exc
            )

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """Translate aliases like 'gemma-2-9b-it' to HuggingFace identifiers."""

        normalized = model_name.strip()
        if "/" in normalized:
            return normalized
        if not normalized.startswith("google/"):
            return f"google/{normalized}"
        return normalized

    @staticmethod
    def _extract_prompt(contents: Union[str, List[Any]]) -> str:
        """Flatten google-style content payload into a plain text prompt."""

        if isinstance(contents, str):
            return contents

        parts: List[str] = []
        for item in contents or []:
            if isinstance(item, str):
                parts.append(item)
                continue

            text = getattr(item, "text", None)
            if text:
                parts.append(text)
                continue

            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)

        return "\n".join(parts).strip()

    def generate_content(  # pragma: no cover - relies on model availability
        self,
        contents: Union[str, List[Any]],
        *,
        generation_config: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> _TextOnlyResponse:
        """Mimic the GenerativeModel.generate_content interface."""

        prompt = self._extract_prompt(contents)
        if not prompt:
            return _TextOnlyResponse(text="")

        if self._pipeline is None:
            fallback = (
                "[Gemma pipeline unavailable] "
                "Install transformers weights to enable offline responses."
            )
            if self._pipeline_error:
                fallback += f" Details: {self._pipeline_error}"
            return _TextOnlyResponse(text=fallback)

        cfg = generation_config or {}
        max_tokens = int(cfg.get("max_output_tokens", self.max_new_tokens))
        temperature = float(cfg.get("temperature", self.temperature))
        top_p = float(cfg.get("top_p", self.top_p))

        outputs = self._pipeline(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
        )

        # Hugging Face pipelines return a list[dict]
        generated = outputs[0].get("generated_text", "") if outputs else ""
        return _TextOnlyResponse(text=generated)


class VeoVideoClient:
    """Wrapper for Google's Veo generative video endpoint."""

    def __init__(
        self,
        model_name: str,
        *,
        api_key: Optional[str],
        generation_config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if not GEMINI_AVAILABLE:
            raise RuntimeError(
                "google-generativeai is required for Veo models. Install google-generativeai."
            )

        self.logger = logger or logging.getLogger(__name__)
        self.model_name = model_name
        self._generation_config = generation_config or {}

        if api_key:
            genai.configure(api_key=api_key)

        self._model = genai.GenerativeModel(model_name=model_name)

    def generate_content(
        self,
        contents: Union[str, List[Any]],
        *,
        generation_config: Optional[Dict[str, Any]] = None,
        **request_kwargs: Any,
    ):
        """Proxy to Veo's content generation (text or structured control)."""

        cfg = self._merge_generation_config(generation_config)
        return self._model.generate_content(contents, generation_config=cfg, **request_kwargs)

    def generate_video(
        self,
        prompt: str,
        *,
        generation_config: Optional[Dict[str, Any]] = None,
        **request_kwargs: Any,
    ):
        """Invoke Veo's video generation endpoint when available."""

        cfg = self._merge_generation_config(generation_config)

        if hasattr(self._model, "generate_video"):
            return self._model.generate_video(
                prompt=prompt,
                generation_config=cfg,
                **request_kwargs,
            )

        self.logger.debug("Veo client falling back to generate_content for video prompt")
        return self._model.generate_content(prompt, generation_config=cfg, **request_kwargs)

    def _merge_generation_config(
        self,
        overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        base = dict(self._generation_config)
        if overrides:
            base.update(overrides)
        return base


@dataclass
class GeminiConfig:
    """Configuration for Gemini service"""
    api_key: Optional[str] = None
    model_name: str = "gemini-3-pro-preview"
    project_id: Optional[str] = None
    location: str = "us-central1"
    max_output_tokens: int = 8192
    temperature: float = 1.0  # Gemini 3 requires temp=1.0
    top_p: float = 0.95
    top_k: int = 40
    safety_settings: Optional[dict] = None
    video_frame_rate: int = 1
    max_video_duration: int = 600
    response_schema: Optional[Any] = None
    response_mime_type: Optional[str] = None
    tools: Optional[List[Any]] = None
    tool_choice: Optional[str] = None
    thinking: bool = False


@dataclass
class GeminiResult:
    """Result from Gemini processing"""
    success: bool
    response: Optional[str]
    latency: float
    model_name: str
    backend: str  # "api" or "vertex"
    error: Optional[str] = None


class GeminiService:
    """
    Service for cloud-based vision-language processing using Google Gemini.
    Supports both direct API and Vertex AI backends with async interface.
    """

    def __init__(self, config: Optional[GeminiConfig] = None):
        """
        Initialize Gemini service.

        Args:
            config: Gemini configuration
        """
        self.config = config or GeminiConfig()
        self.logger = logging.getLogger(__name__)
        self._model = None
        self._use_vertex = False
        self._is_initialized = False
        self._model_cache: Dict[str, Any] = {}
        self._backend_cache: Dict[str, str] = {}
        self._vertex_cache: Dict[str, bool] = {}
        self._backend_kind: str = "gemini"

        # Initialize client on startup if credentials available
        if self.is_available():
            self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client"""
        try:
            if self.config.project_id and VERTEX_AVAILABLE:
                # Use Vertex AI
                self.logger.info("Initializing Gemini via Vertex AI")
                vertexai.init(project=self.config.project_id, location=self.config.location)
                self._model = GenerativeModel(self.config.model_name)
                self._use_vertex = True

            elif self.config.api_key and GEMINI_AVAILABLE:
                # Use direct API
                self.logger.info("Initializing Gemini via API key")
                genai.configure(api_key=self.config.api_key)
                self._model = genai.GenerativeModel(
                    model_name=self.config.model_name,
                    generation_config={
                        "temperature": self.config.temperature,
                        "top_p": self.config.top_p,
                        "top_k": self.config.top_k,
                        "max_output_tokens": self.config.max_output_tokens,
                    },
                    safety_settings=self.config.safety_settings
                )
                self._use_vertex = False
            else:
                self.logger.warning("Gemini API key or project ID not configured")
                return

            self._is_initialized = True
            self.logger.info(f"Gemini service initialized with {self.config.model_name}")

            if self._model:
                self._register_model(
                    self.config.model_name,
                    self._model,
                    backend="gemini",
                    use_vertex=self._use_vertex,
                )

        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {e}")
            self._model = None
            self._is_initialized = False

    def _register_model(
        self,
        model_name: str,
        model_obj: Any,
        *,
        backend: str,
        use_vertex: bool = False,
    ) -> None:
        """Track model instances across backends for quick switching."""

        self._model_cache[model_name] = model_obj
        self._backend_cache[model_name] = backend
        self._vertex_cache[model_name] = use_vertex
        self._model = model_obj
        self.config.model_name = model_name
        self._backend_kind = backend
        self._use_vertex = use_vertex
        self._is_initialized = True

    def _prepare_generation_args(self, kwargs: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Split kwargs into generation_config and request kwargs."""

        generation_config = {
            "temperature": kwargs.pop('temperature', self.config.temperature),
            "top_p": kwargs.pop('top_p', self.config.top_p),
            "top_k": kwargs.pop('top_k', self.config.top_k),
            "max_output_tokens": kwargs.pop('max_tokens', self.config.max_output_tokens),
        }

        request_kwargs: Dict[str, Any] = {}

        response_schema = kwargs.pop('response_schema', self.config.response_schema)
        if response_schema is not None:
            request_kwargs['response_schema'] = response_schema
            mime_type = kwargs.pop('response_mime_type', self.config.response_mime_type)
            if mime_type:
                request_kwargs['response_mime_type'] = mime_type

        tools = kwargs.pop('tools', self.config.tools)
        if tools:
            request_kwargs['tools'] = tools

        tool_choice = kwargs.pop('tool_choice', self.config.tool_choice)
        if tool_choice:
            request_kwargs['tool_choice'] = tool_choice

        thinking = kwargs.pop('thinking', self.config.thinking)
        if thinking:
            request_kwargs['thinking'] = thinking

        safety_settings = kwargs.pop('safety_settings', self.config.safety_settings)
        if safety_settings:
            request_kwargs['safety_settings'] = safety_settings

        return generation_config, request_kwargs

    def select_model(self, model_name: Optional[str]) -> None:
        """Ensure the requested Gemini model is ready for the next call."""

        if not model_name or model_name == self.config.model_name:
            return

        if model_name in self._model_cache:
            self._register_model(
                model_name,
                self._model_cache[model_name],
                backend=self._backend_cache.get(model_name, "gemini"),
                use_vertex=self._vertex_cache.get(model_name, False),
            )
            return

        normalized = model_name.lower()

        if normalized.startswith("gemma"):
            gemma_client = GemmaTextClient(
                model_name=model_name,
                max_new_tokens=self.config.max_output_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                logger=self.logger,
            )
            self._register_model(model_name, gemma_client, backend="gemma", use_vertex=False)
            self.logger.info("Switched to Gemma model %s", model_name)
            return

        if normalized.startswith("veo"):
            try:
                veo_client = VeoVideoClient(
                    model_name=model_name,
                    api_key=self.config.api_key,
                    generation_config={
                        "temperature": self.config.temperature,
                        "top_p": self.config.top_p,
                        "top_k": self.config.top_k,
                        "max_output_tokens": self.config.max_output_tokens,
                    },
                    logger=self.logger,
                )
            except Exception as exc:
                self.logger.error("Failed to initialize Veo client %s: %s", model_name, exc)
                return

            self._register_model(model_name, veo_client, backend="veo", use_vertex=False)
            self.logger.info("Switched to Veo model %s", model_name)
            return

        try:
            if self._use_vertex:
                model = GenerativeModel(model_name)
                backend = "gemini"
                use_vertex = True
            else:
                generation_config = {
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                    "max_output_tokens": self.config.max_output_tokens,
                }
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    safety_settings=self.config.safety_settings,
                )
                backend = "gemini"
                use_vertex = False

            self._register_model(model_name, model, backend=backend, use_vertex=use_vertex)
            self.logger.info("Switched Gemini model to %s", model_name)

        except Exception as exc:
            self.logger.error("Failed to switch to model %s: %s", model_name, exc)

    def _prepare_image(self, image: Union[str, Path, Image.Image]) -> Any:
        """Prepare image for Gemini API"""
        if isinstance(image, (str, Path)):
            image = Image.open(image).convert('RGB')

        if self._use_vertex:
            # Vertex AI format
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return Part.from_data(buffer.getvalue(), mime_type="image/png")
        else:
            # Direct API format
            return image

    async def process_image(
        self,
        image: Union[str, Path, Image.Image],
        prompt: str,
        **kwargs
    ) -> GeminiResult:
        """
        Process an image with Gemini.

        Args:
            image: Image path or PIL Image
            prompt: Text prompt for analysis
            **kwargs: Additional generation parameters

        Returns:
            GeminiResult with analysis results
        """
        start_time = time.time()

        if not self.is_available() or not self._is_initialized:
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="none",
                error="Gemini not available or not initialized"
            )

        if self._backend_kind != "gemini":
            error = f"{self._backend_kind} backend does not support image processing"
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend=self._backend_kind,
                error=error,
            )

        try:
            # Prepare image
            prepared_image = self._prepare_image(image)
            loop = asyncio.get_event_loop()
            temp_kwargs = dict(kwargs)
            generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

            response = await loop.run_in_executor(
                None,
                self._process_image_sync,
                prepared_image,
                prompt,
                generation_config,
                request_kwargs,
            )

            latency = time.time() - start_time

            return GeminiResult(
                success=True,
                response=response.text,
                latency=latency,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api"
            )

        except Exception as e:
            self.logger.error(f"Error processing image with Gemini: {e}")
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api",
                error=str(e)
            )

    def _process_image_sync(
        self,
        prepared_image: Any,
        prompt: str,
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Synchronous image processing in executor"""
        if self._use_vertex:
            return self._model.generate_content(
                [prompt, prepared_image],
                generation_config=generation_config,
                **request_kwargs,
            )

        if genai_types:
            prompt_part = genai_types.Part(text=prompt)
            image_part = genai_types.Part(image=prepared_image)
            content = genai_types.Content(role="user", parts=[image_part, prompt_part])
            return self._model.generate_content(
                [content],
                generation_config=generation_config,
                **request_kwargs,
            )

        return self._model.generate_content(
            [prompt, prepared_image],
            generation_config=generation_config,
            **request_kwargs,
        )

    async def process_text(
        self,
        prompt: str,
        *,
        input_text: Optional[str] = None,
        **kwargs,
    ) -> GeminiResult:
        """Process pure text requests across Gemini/Gemma/Veo backends."""

        start_time = time.time()

        if not self.is_available():
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="none",
                error="Text backend not available",
            )

        text_payload = input_text or prompt

        try:
            loop = asyncio.get_event_loop()
            temp_kwargs = dict(kwargs)
            generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

            response = await loop.run_in_executor(
                None,
                self._process_text_sync,
                text_payload,
                prompt,
                generation_config,
                request_kwargs,
            )

            return GeminiResult(
                success=True,
                response=response.text if hasattr(response, "text") else str(response),
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend=self._backend_kind,
            )

        except Exception as exc:
            self.logger.error("Error processing text with %s backend: %s", self._backend_kind, exc)
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend=self._backend_kind,
                error=str(exc),
            )

    def _process_text_sync(
        self,
        text_payload: str,
        prompt: str,
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Synchronous helper for text-only requests."""

        backend = self._backend_kind

        if backend == "gemma":
            return self._model.generate_content(
                text_payload,
                generation_config=generation_config,
                **request_kwargs,
            )

        if backend == "veo":
            # Veo supports prompt engineering for planning scripts; use generate_content.
            return self._model.generate_content(
                text_payload,
                generation_config=generation_config,
                **request_kwargs,
            )

        # Default Gemini path
        contents: List[Any] = [prompt]
        if text_payload and text_payload != prompt:
            contents.append(text_payload)

        return self._model.generate_content(
            contents,
            generation_config=generation_config,
            **request_kwargs,
        )

    async def process_video(
        self,
        video_path: Union[str, Path],
        prompt: str,
        *,
        video_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> GeminiResult:
        """
        Process a video with Gemini.

        Args:
            video_path: Path to video file
            prompt: Text prompt
            **kwargs: Additional parameters

        Returns:
            GeminiResult with analysis
        """
        start_time = time.time()

        if not self.is_available() or not self._is_initialized:
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="none",
                error="Gemini not available or not initialized"
            )

        if self._backend_kind == "gemma":
            error = "Gemma backend does not support video processing"
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="gemma",
                error=error,
            )

        if self._backend_kind == "veo":
            try:
                loop = asyncio.get_event_loop()
                temp_kwargs = dict(kwargs)
                generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

                response = await loop.run_in_executor(
                    None,
                    self._process_veo_video_sync,
                    prompt,
                    generation_config,
                    request_kwargs,
                )

                payload = self._summarize_veo_response(response)

                return GeminiResult(
                    success=True,
                    response=payload,
                    latency=time.time() - start_time,
                    model_name=self.config.model_name,
                    backend="veo",
                )

            except Exception as exc:
                self.logger.error("Error generating video with Veo: %s", exc)
                return GeminiResult(
                    success=False,
                    response=None,
                    latency=time.time() - start_time,
                    model_name=self.config.model_name,
                    backend="veo",
                    error=str(exc),
                )

        try:
            loop = asyncio.get_event_loop()
            temp_kwargs = dict(kwargs)
            generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

            response = await loop.run_in_executor(
                None,
                self._process_video_sync,
                video_path,
                prompt,
                video_metadata,
                generation_config,
                request_kwargs,
            )

            latency = time.time() - start_time

            return GeminiResult(
                success=True,
                response=response.text,
                latency=latency,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api"
            )

        except Exception as e:
            self.logger.error(f"Error processing video with Gemini: {e}")
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api",
                error=str(e)
            )

    async def process_audio(
        self,
        audio_path: Union[str, Path],
        prompt: str,
        **kwargs,
    ) -> GeminiResult:
        """Process an audio file with Gemini."""

        start_time = time.time()

        if not self.is_available() or not self._is_initialized:
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="none",
                error="Gemini not available or not initialized",
            )

        if self._backend_kind != "gemini":
            error = f"{self._backend_kind} backend does not support audio processing"
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend=self._backend_kind,
                error=error,
            )

        try:
            loop = asyncio.get_event_loop()
            temp_kwargs = dict(kwargs)
            generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

            response = await loop.run_in_executor(
                None,
                self._process_audio_sync,
                audio_path,
                prompt,
                generation_config,
                request_kwargs,
            )

            latency = time.time() - start_time

            return GeminiResult(
                success=True,
                response=response.text,
                latency=latency,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api",
            )

        except Exception as e:
            self.logger.error(f"Error processing audio with Gemini: {e}")
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="vertex" if self._use_vertex else "api",
                error=str(e),
            )

    def _process_video_sync(
        self,
        video_path: Union[str, Path],
        prompt: str,
        video_metadata: Optional[Dict[str, Any]],
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Synchronous video processing in executor"""
        video_path = Path(video_path)
        mime_type, _ = mimetypes.guess_type(str(video_path))
        if not mime_type or not mime_type.startswith('video/'):
            mime_type = "video/mp4"  # Default fallback

        if self._use_vertex:
            with open(video_path, 'rb') as f:
                video_part = Part.from_data(f.read(), mime_type=mime_type)

            if video_metadata:
                return self._model.generate_content(
                    [prompt, video_part],
                    generation_config=generation_config,
                    video_metadata=video_metadata,
                    **request_kwargs,
                )

            return self._model.generate_content(
                [prompt, video_part],
                generation_config=generation_config,
                **request_kwargs,
            )
        else:
            video_file = genai.upload_file(path=str(video_path), mime_type=mime_type)

            # Wait for processing (up to 5 minutes)
            max_wait = 300  # 5 minutes
            waited = 0
            while video_file.state.name == "PROCESSING" and waited < max_wait:
                time.sleep(2)
                waited += 2
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise Exception(f"Video processing failed: {video_file.error}")
            if video_file.state.name == "PROCESSING":
                raise Exception("Video processing timeout")

            metadata_obj = None
            if genai_types and video_metadata:
                try:
                    metadata_obj = genai_types.VideoMetadata(**video_metadata)
                except Exception as exc:
                    self.logger.warning("Invalid video metadata supplied: %s", exc)

            if genai_types and metadata_obj:
                video_part = genai_types.Part(
                    file_data=genai_types.FileData(file_uri=getattr(video_file, 'uri', video_file.name)),
                    video_metadata=metadata_obj,
                )
                prompt_part = genai_types.Part(text=prompt)
                content = genai_types.Content(role="user", parts=[video_part, prompt_part])
                response = self._model.generate_content(
                    [content],
                    generation_config=generation_config,
                    **request_kwargs,
                )
            else:
                response = self._model.generate_content(
                    [video_file, prompt],
                    generation_config=generation_config,
                    **request_kwargs,
                )

            # Clean up
            genai.delete_file(video_file.name)

            return response

    def _process_audio_sync(
        self,
        audio_path: Union[str, Path],
        prompt: str,
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Synchronous audio processing in executor."""

        audio_path = Path(audio_path)
        mime_type, _ = mimetypes.guess_type(str(audio_path))
        if not mime_type or not mime_type.startswith('audio/'):
            mime_type = "audio/mpeg"

        if self._use_vertex:
            with open(audio_path, 'rb') as f:
                audio_part = Part.from_data(f.read(), mime_type=mime_type)

            return self._model.generate_content(
                [prompt, audio_part],
                generation_config=generation_config,
                **request_kwargs,
            )

        audio_file = genai.upload_file(path=str(audio_path), mime_type=mime_type)

        max_wait = 300
        waited = 0
        while audio_file.state.name == "PROCESSING" and waited < max_wait:
            time.sleep(2)
            waited += 2
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name == "FAILED":
            raise Exception(f"Audio processing failed: {audio_file.error}")
        if audio_file.state.name == "PROCESSING":
            raise Exception("Audio processing timeout")

        if genai_types:
            audio_part = genai_types.Part(
                file_data=genai_types.FileData(file_uri=getattr(audio_file, 'uri', audio_file.name))
            )
            prompt_part = genai_types.Part(text=prompt)
            content = genai_types.Content(role="user", parts=[audio_part, prompt_part])
            response = self._model.generate_content(
                [content],
                generation_config=generation_config,
                **request_kwargs,
            )
        else:
            response = self._model.generate_content(
                [audio_file, prompt],
                generation_config=generation_config,
                **request_kwargs,
            )

        genai.delete_file(audio_file.name)

        return response

    def _process_veo_video_sync(
        self,
        prompt: str,
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Invoke Veo client in a worker thread."""

        client = self._model
        if hasattr(client, "generate_video"):
            return client.generate_video(
                prompt,
                generation_config=generation_config,
                **request_kwargs,
            )

        return client.generate_content(
            prompt,
            generation_config=generation_config,
            **request_kwargs,
        )

    def _summarize_veo_response(self, response: Any) -> str:
        """Extract human-readable information from Veo responses."""

        if response is None:
            return ""

        summary: Dict[str, Any] = {}

        for attr in ("output_uri", "video_uri", "video", "media", "candidates"):
            if hasattr(response, attr):
                value = getattr(response, attr)
                if attr == "video" and isinstance(value, (bytes, bytearray)):
                    summary[attr] = f"{len(value)} bytes"
                else:
                    summary[attr] = value

        if hasattr(response, "to_dict"):
            try:
                converted = response.to_dict()
                if isinstance(converted, dict):
                    summary.update(converted)
            except Exception:  # pragma: no cover - defensive
                pass

        if not summary:
            summary["raw"] = str(response)

        return json.dumps(summary, default=str)

    async def process_youtube(
        self,
        youtube_url: str,
        prompt: str,
        *,
        video_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> GeminiResult:
        """
        Process a YouTube video directly (preview feature).

        Args:
            youtube_url: YouTube video URL
            prompt: Text prompt
            **kwargs: Additional parameters

        Returns:
            GeminiResult with analysis
        """
        start_time = time.time()

        if not self.is_available() or not self._is_initialized:
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="none",
                error="Gemini not available or not initialized"
            )

        if self._use_vertex:
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="vertex",
                error="YouTube URL processing not supported in Vertex AI"
            )

        if self._backend_kind != "gemini":
            error = f"{self._backend_kind} backend does not handle YouTube ingestion"
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend=self._backend_kind,
                error=error,
            )

        try:
            loop = asyncio.get_event_loop()
            temp_kwargs = dict(kwargs)
            generation_config, request_kwargs = self._prepare_generation_args(temp_kwargs)

            response = await loop.run_in_executor(
                None,
                self._process_youtube_sync,
                youtube_url,
                prompt,
                video_metadata,
                generation_config,
                request_kwargs,
            )

            latency = time.time() - start_time

            return GeminiResult(
                success=True,
                response=response.text,
                latency=latency,
                model_name=self.config.model_name,
                backend="api"
            )

        except Exception as e:
            self.logger.error(f"Error processing YouTube video with Gemini: {e}")
            return GeminiResult(
                success=False,
                response=None,
                latency=time.time() - start_time,
                model_name=self.config.model_name,
                backend="api",
                error=str(e)
            )

    def _process_youtube_sync(
        self,
        youtube_url: str,
        prompt: str,
        video_metadata: Optional[Dict[str, Any]],
        generation_config: Dict[str, Any],
        request_kwargs: Dict[str, Any],
    ):
        """Synchronous YouTube processing in executor"""
        if genai_types:
            metadata_obj = None
            if video_metadata:
                try:
                    metadata_obj = genai_types.VideoMetadata(**video_metadata)
                except Exception as exc:
                    self.logger.warning("Invalid YouTube video metadata supplied: %s", exc)

            youtube_part = genai_types.Part(
                file_data=genai_types.FileData(file_uri=youtube_url),
                video_metadata=metadata_obj,
            )
            prompt_part = genai_types.Part(text=prompt)
            content = genai_types.Content(role="user", parts=[youtube_part, prompt_part])
            return self._model.generate_content(
                [content],
                generation_config=generation_config,
                **request_kwargs,
            )

        # Fallback to inline_data preview format if types module unavailable
        youtube_part = {
            "inline_data": {
                "mime_type": "video/youtube",
                "data": youtube_url
            }
        }
        return self._model.generate_content(
            [prompt, youtube_part],
            generation_config=generation_config,
            **request_kwargs,
        )

    async def start_cached_session(
        self,
        *,
        contents: Union[str, List[Any]],
        model_name: Optional[str] = None,
        ttl_seconds: int = 3600,
        display_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a reusable cache for repeated prompts via Google's caching API."""

        start_time = time.time()

        if not (GEMINI_AVAILABLE and genai and hasattr(genai, "caching")):
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": "Gemini caching requires google-generativeai with caching support",
            }

        if not contents:
            raise ValueError("contents must be provided to create a cache")

        if isinstance(contents, str):
            contents_payload: Union[str, List[Any]] = [contents]
        else:
            contents_payload = contents

        chosen_model = model_name or self.config.model_name

        def _create_cache():
            request_kwargs = {
                "model": chosen_model,
                "contents": contents_payload,
                "ttl_seconds": ttl_seconds,
            }
            if display_name:
                request_kwargs["display_name"] = display_name
            request_kwargs.update(kwargs)
            return genai.caching.create_cache(**request_kwargs)

        loop = asyncio.get_event_loop()

        try:
            cache_obj = await loop.run_in_executor(None, _create_cache)
            return {
                "success": True,
                "latency": time.time() - start_time,
                "cache": self._serialize_google_object(cache_obj),
            }
        except Exception as exc:
            self.logger.error("Failed to create Gemini cache: %s", exc)
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": str(exc),
            }

    async def submit_batch_job(
        self,
        requests: List[Dict[str, Any]],
        *,
        model_name: Optional[str] = None,
        wait: bool = False,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Submit a batch generateContent job, optionally waiting for completion."""

        start_time = time.time()

        if not (GEMINI_AVAILABLE and genai and hasattr(genai, "batch")):
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": "Gemini batch processing requires google-generativeai batch support",
            }

        if not requests:
            raise ValueError("requests must be provided for batch submission")

        default_model = model_name or self.config.model_name
        normalized_requests = []
        for request in requests:
            req = dict(request)
            req.setdefault("model", default_model)
            normalized_requests.append(req)

        def _start_batch():
            return genai.batch.generate_content(requests=normalized_requests, **kwargs)

        loop = asyncio.get_event_loop()

        try:
            operation = await loop.run_in_executor(None, _start_batch)
            op_serialized = self._serialize_google_object(operation)
            result_payload = None
            completed = bool(getattr(operation, "done", False))

            if wait and not completed:
                def _wait_for_completion():
                    return self._wait_for_batch_completion(operation, poll_interval, timeout)

                final_operation = await loop.run_in_executor(None, _wait_for_completion)
                op_serialized = self._serialize_google_object(final_operation)
                result_payload = self._serialize_google_object(getattr(final_operation, "result", None))
                completed = True

            return {
                "success": True,
                "latency": time.time() - start_time,
                "operation": op_serialized,
                "result": result_payload,
                "completed": completed,
            }

        except TimeoutError as exc:
            self.logger.error("Batch operation timeout: %s", exc)
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": str(exc),
                "completed": False,
            }
        except Exception as exc:
            self.logger.error("Failed to submit Gemini batch job: %s", exc)
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": str(exc),
            }

    def _wait_for_batch_completion(
        self,
        initial_operation: Any,
        poll_interval: float,
        timeout: float,
    ):
        """Synchronously poll the batch API until completion or timeout."""

        if not (genai and hasattr(genai, "batch")):
            return initial_operation

        deadline = time.time() + timeout
        operation = initial_operation

        while not getattr(operation, "done", False):
            if time.time() > deadline:
                raise TimeoutError("Gemini batch operation timed out")
            time.sleep(poll_interval)
            operation = genai.batch.get_operation(getattr(operation, "name", ""))

        return operation

    async def create_ephemeral_token(
        self,
        *,
        model_name: Optional[str] = None,
        audience: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Request an ephemeral auth token for client-side uploads."""

        start_time = time.time()

        if not (GEMINI_AVAILABLE and genai and hasattr(genai, "tokens")):
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": "Gemini tokens API unavailable; install google-generativeai >= 0.6.0",
            }

        request_kwargs: Dict[str, Any] = dict(kwargs)
        request_kwargs.setdefault("model", model_name or self.config.model_name)
        if audience:
            request_kwargs["audience"] = audience
        if ttl_seconds is not None:
            request_kwargs["ttl"] = ttl_seconds

        loop = asyncio.get_event_loop()

        def _create_token():
            return genai.tokens.create(**request_kwargs)

        try:
            token_obj = await loop.run_in_executor(None, _create_token)
            return {
                "success": True,
                "latency": time.time() - start_time,
                "token": self._serialize_google_object(token_obj),
            }
        except Exception as exc:
            self.logger.error("Failed to create Gemini ephemeral token: %s", exc)
            return {
                "success": False,
                "latency": time.time() - start_time,
                "error": str(exc),
            }

    def _serialize_google_object(self, value: Any) -> Any:
        """Best-effort conversion of Google client objects to JSON-safe data."""

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {
                key: self._serialize_google_object(val)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [self._serialize_google_object(item) for item in value]

        if hasattr(value, "to_dict"):
            try:
                return value.to_dict()
            except Exception:  # pragma: no cover - defensive
                pass

        if hasattr(value, "__dict__"):
            return {
                key: self._serialize_google_object(val)
                for key, val in value.__dict__.items()
                if not key.startswith("_")
            }

        return str(value)

    async def batch_process(
        self,
        items: List[Union[str, Path, Image.Image]],
        prompts: Union[str, List[str]],
        **kwargs
    ) -> List[GeminiResult]:
        """
        Process multiple items.

        Args:
            items: List of images or videos
            prompts: Single prompt or list of prompts
            **kwargs: Additional parameters

        Returns:
            List of GeminiResults
        """
        if isinstance(prompts, str):
            prompts = [prompts] * len(items)

        # Process concurrently with rate limiting
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

        async def process_one(item, prompt):
            async with semaphore:
                # Determine if video or image
                if isinstance(item, (str, Path)):
                    lower_item = str(item).lower()
                    if lower_item.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.mpg', '.mpeg', '.wmv', '.3gp')):
                        return await self.process_video(item, prompt, **kwargs)
                    if lower_item.endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.opus')):
                        return await self.process_audio(item, prompt, **kwargs)
                else:
                    return await self.process_image(item, prompt, **kwargs)

        tasks = [process_one(item, prompt) for item, prompt in zip(items, prompts)]
        return await asyncio.gather(*tasks)

    def is_available(self) -> bool:
        """Check if Gemini service is available"""
        has_vertex = self.config.project_id and VERTEX_AVAILABLE
        has_api = self.config.api_key and GEMINI_AVAILABLE
        gemma_ready = TRANSFORMERS_AVAILABLE
        return bool(has_vertex or has_api or gemma_ready)

    def is_initialized(self) -> bool:
        """Check if service is initialized and ready"""
        return self._is_initialized and self._model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "available": self.is_available(),
            "initialized": self.is_initialized(),
            "model": self.config.model_name,
            "backend": "vertex" if self._use_vertex else "api",
            "project_id": self.config.project_id,
            "location": self.config.location,
            "max_tokens": self.config.max_output_tokens,
            "has_vertex": VERTEX_AVAILABLE,
            "has_api": GEMINI_AVAILABLE
        }

    async def test_connection(self) -> GeminiResult:
        """Test Gemini connection with a simple request"""
        test_prompt = "Say 'Hello, I am Gemini and I am working correctly!'"

        # Create a simple test image (1x1 pixel)
        test_image = Image.new('RGB', (1, 1), color='white')

        return await self.process_image(test_image, test_prompt)

    async def cleanup(self):
        """Cleanup resources"""
        self._model = None
        self._is_initialized = False
        self.logger.info("Gemini service cleaned up")
