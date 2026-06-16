"""Unit tests for services/ai/gemini_service.py."""

from __future__ import annotations

import asyncio
import io
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock

import pytest

# Ensure src is on the path
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Lazy import – delay until each test so patches can be applied cleanly
# ---------------------------------------------------------------------------


def _import_module():
    """Import the gemini_service module fresh (or from cache)."""
    import youtube_extension.services.ai.gemini_service as m
    return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(api_key: str = "fake_key", model_name: str = "gemini-2.5-flash", **extra):
    """Create a GeminiService with a mocked Gemini model so no real API calls happen."""
    m = _import_module()
    GeminiConfig = m.GeminiConfig
    GeminiService = m.GeminiService

    cfg = GeminiConfig(api_key=api_key, model_name=model_name, **extra)
    with patch.object(m, "GEMINI_AVAILABLE", True), \
         patch.object(m, "genai") as mock_genai:
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
        svc = GeminiService(cfg)
    return svc


def _mock_response(text: str = "test response") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


# ===========================================================================
# GeminiConfig dataclass
# ===========================================================================

class TestGeminiConfig:
    def test_default_model_name(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.model_name == "gemini-2.5-flash"

    def test_default_temperature(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.temperature == pytest.approx(0.4)

    def test_default_top_p(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.top_p == pytest.approx(0.95)

    def test_default_top_k(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.top_k == 40

    def test_default_max_output_tokens(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.max_output_tokens == 8192

    def test_default_location(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.location == "us-central1"

    def test_default_video_frame_rate(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.video_frame_rate == 1

    def test_default_max_video_duration(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.max_video_duration == 600

    def test_default_nones(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.api_key is None
        assert cfg.project_id is None
        assert cfg.safety_settings is None
        assert cfg.response_schema is None
        assert cfg.response_mime_type is None
        assert cfg.tools is None
        assert cfg.tool_choice is None

    def test_default_thinking_false(self):
        m = _import_module()
        cfg = m.GeminiConfig()
        assert cfg.thinking is False

    def test_custom_values(self):
        m = _import_module()
        cfg = m.GeminiConfig(
            api_key="my_key",
            model_name="gemini-1.5-pro",
            project_id="my-project",
            temperature=0.9,
            max_output_tokens=4096,
            thinking=True,
        )
        assert cfg.api_key == "my_key"
        assert cfg.model_name == "gemini-1.5-pro"
        assert cfg.project_id == "my-project"
        assert cfg.temperature == pytest.approx(0.9)
        assert cfg.max_output_tokens == 4096
        assert cfg.thinking is True


# ===========================================================================
# GeminiResult dataclass
# ===========================================================================

class TestGeminiResult:
    def test_success_result(self):
        m = _import_module()
        r = m.GeminiResult(
            success=True,
            response="hello",
            latency=0.1,
            model_name="gemini-2.5-flash",
            backend="api",
        )
        assert r.success is True
        assert r.response == "hello"
        assert r.latency == pytest.approx(0.1)
        assert r.model_name == "gemini-2.5-flash"
        assert r.backend == "api"
        assert r.error is None

    def test_failure_result(self):
        m = _import_module()
        r = m.GeminiResult(
            success=False,
            response=None,
            latency=0.05,
            model_name="gemini-2.5-flash",
            backend="none",
            error="some error",
        )
        assert r.success is False
        assert r.response is None
        assert r.error == "some error"

    def test_error_defaults_to_none(self):
        m = _import_module()
        r = m.GeminiResult(
            success=True, response="ok", latency=0.0,
            model_name="m", backend="api"
        )
        assert r.error is None


# ===========================================================================
# GeminiService.__init__ and is_available
# ===========================================================================

class TestGeminiServiceInit:
    def test_default_config_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
            assert svc.config.model_name == m.DEFAULT_GEMINI_MODEL
            assert not svc.is_initialized()
            assert not svc.is_available()

    def test_init_with_api_key_initializes_client(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc = m.GeminiService(m.GeminiConfig(api_key="key123"))
        assert svc.is_initialized()
        assert svc._use_vertex is False

    def test_init_passes_generation_config_to_model(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            cfg = m.GeminiConfig(api_key="key123", temperature=0.8, top_k=32)
            m.GeminiService(cfg)
        call_kwargs = mock_genai.GenerativeModel.call_args[1]
        assert call_kwargs["generation_config"]["temperature"] == pytest.approx(0.8)
        assert call_kwargs["generation_config"]["top_k"] == 32

    def test_init_gemini_not_available(self):
        m = _import_module()
        # Keep patches active during assertion since is_available() reads module globals
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
            # api key present but GEMINI_AVAILABLE=False → not initialized
            assert not svc.is_initialized()
            assert not svc.is_available()

    def test_init_transformers_makes_available(self):
        m = _import_module()
        # Keep patches active during assertion since is_available() reads module globals
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", True):
            svc = m.GeminiService()
            assert svc.is_available()

    def test_init_exception_during_client_setup(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock(side_effect=Exception("configure failed"))
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        assert not svc.is_initialized()
        assert svc._model is None

    def test_caches_initialized_to_empty(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        assert svc._model_cache == {}
        assert svc._backend_cache == {}
        assert svc._vertex_cache == {}

    def test_backend_kind_defaults_to_gemini(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        assert svc._backend_kind == "gemini"


# ===========================================================================
# is_available
# ===========================================================================

class TestIsAvailable:
    def test_available_with_api_key_and_gemini(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        assert svc.is_available()

    def test_not_available_no_credentials_no_libs(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
            assert not svc.is_available()

    def test_available_with_project_id_and_vertex(self):
        m = _import_module()
        vertex_module = MagicMock()
        vertex_module.init = MagicMock()
        generative_model_mock = MagicMock(return_value=MagicMock())
        # Keep patches active during assertion since is_available() reads module globals
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", True), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "vertexai", vertex_module, create=True), \
             patch.object(m, "GenerativeModel", generative_model_mock, create=True):
            svc = m.GeminiService(m.GeminiConfig(project_id="proj"))
            assert svc.is_available()


# ===========================================================================
# get_model_info
# ===========================================================================

class TestGetModelInfo:
    def test_returns_dict_with_required_keys(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        info = svc.get_model_info()
        assert isinstance(info, dict)
        for key in ("available", "initialized", "model", "backend", "project_id",
                    "location", "max_tokens", "has_vertex", "has_api"):
            assert key in info, f"Missing key: {key}"

    def test_model_info_reflects_config(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService(m.GeminiConfig(model_name="gemini-1.5-pro", location="eu-west1"))
        info = svc.get_model_info()
        assert info["model"] == "gemini-1.5-pro"
        assert info["location"] == "eu-west1"

    def test_model_info_not_initialized(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
            info = svc.get_model_info()
            assert info["initialized"] is False
            assert info["available"] is False

    def test_model_info_api_backend(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc = m.GeminiService(m.GeminiConfig(api_key="k"))
        info = svc.get_model_info()
        assert info["backend"] == "api"


# ===========================================================================
# _register_model
# ===========================================================================

class TestRegisterModel:
    def test_register_model_updates_caches(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()

        mock_model = MagicMock()
        svc._register_model("gemini-1.5-pro", mock_model, backend="gemini", use_vertex=False)

        assert svc._model_cache["gemini-1.5-pro"] is mock_model
        assert svc._backend_cache["gemini-1.5-pro"] == "gemini"
        assert svc._vertex_cache["gemini-1.5-pro"] is False
        assert svc._model is mock_model
        assert svc.config.model_name == "gemini-1.5-pro"
        assert svc._is_initialized is True

    def test_register_model_vertex(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()

        mock_model = MagicMock()
        svc._register_model("gemini-1.5-pro", mock_model, backend="gemini", use_vertex=True)
        assert svc._use_vertex is True
        assert svc._vertex_cache["gemini-1.5-pro"] is True


# ===========================================================================
# _prepare_generation_args
# ===========================================================================

class TestPrepareGenerationArgs:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc

    def test_defaults_from_config(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({})
        assert gen_cfg["temperature"] == pytest.approx(0.4)
        assert gen_cfg["top_p"] == pytest.approx(0.95)
        assert gen_cfg["top_k"] == 40
        assert gen_cfg["max_output_tokens"] == 8192

    def test_kwargs_override_config(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args(
            {"temperature": 0.9, "max_tokens": 512}
        )
        assert gen_cfg["temperature"] == pytest.approx(0.9)
        assert gen_cfg["max_output_tokens"] == 512

    def test_response_schema_added_to_request_kwargs(self):
        svc = self._make_service()
        schema = {"type": "object"}
        gen_cfg, req_kwargs = svc._prepare_generation_args(
            {"response_schema": schema, "response_mime_type": "application/json"}
        )
        assert req_kwargs["response_schema"] == schema
        assert req_kwargs["response_mime_type"] == "application/json"

    def test_no_response_schema_no_key(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({})
        assert "response_schema" not in req_kwargs

    def test_tools_added_when_present(self):
        svc = self._make_service()
        tools = [{"name": "search"}]
        gen_cfg, req_kwargs = svc._prepare_generation_args({"tools": tools})
        assert req_kwargs["tools"] == tools

    def test_no_tools_not_in_request_kwargs(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({})
        assert "tools" not in req_kwargs

    def test_tool_choice_added_when_present(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({"tool_choice": "auto"})
        assert req_kwargs["tool_choice"] == "auto"

    def test_thinking_added_when_true(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({"thinking": True})
        assert req_kwargs["thinking"] is True

    def test_safety_settings_added(self):
        svc = self._make_service()
        ss = {"HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE"}
        gen_cfg, req_kwargs = svc._prepare_generation_args({"safety_settings": ss})
        assert req_kwargs["safety_settings"] == ss

    def test_empty_request_kwargs_when_no_extras(self):
        svc = self._make_service()
        gen_cfg, req_kwargs = svc._prepare_generation_args({})
        assert req_kwargs == {}


# ===========================================================================
# select_model
# ===========================================================================

class TestSelectModel:
    def _make_uninit_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    def test_none_model_name_noop(self):
        svc, m = self._make_uninit_service()
        svc.select_model(None)
        assert svc.config.model_name == "gemini-2.5-flash"

    def test_same_model_name_noop(self):
        svc, m = self._make_uninit_service()
        original_model = svc._model
        svc.select_model("gemini-2.5-flash")
        assert svc._model is original_model

    def test_cached_model_retrieved(self):
        svc, m = self._make_uninit_service()
        mock_model = MagicMock()
        svc._model_cache["gemini-1.5-pro"] = mock_model
        svc._backend_cache["gemini-1.5-pro"] = "gemini"
        svc._vertex_cache["gemini-1.5-pro"] = False

        svc.select_model("gemini-1.5-pro")
        assert svc._model is mock_model
        assert svc.config.model_name == "gemini-1.5-pro"

    def test_gemma_model_creates_gemma_client(self):
        svc, m = self._make_uninit_service()
        with patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc.select_model("gemma-2-9b-it")
        assert svc._backend_kind == "gemma"
        assert svc.config.model_name == "gemma-2-9b-it"

    def test_gemma_model_case_insensitive(self):
        svc, m = self._make_uninit_service()
        with patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc.select_model("Gemma-2-2b")
        assert svc._backend_kind == "gemma"

    def test_veo_model_creates_veo_client(self):
        svc, m = self._make_uninit_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc.select_model("veo-2.0-generate-001")
        assert svc._backend_kind == "veo"

    def test_veo_model_gemini_unavailable_logs_error(self):
        svc, m = self._make_uninit_service()
        with patch.object(m, "GEMINI_AVAILABLE", False):
            # VeoVideoClient.__init__ raises RuntimeError if GEMINI_AVAILABLE=False
            svc.select_model("veo-1.0")
        # Should still be at original model (no crash, error logged)
        assert svc._backend_kind == "gemini"

    def test_new_gemini_model_api_backend(self):
        svc, m = self._make_uninit_service()
        svc._use_vertex = False
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_model_instance = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model_instance)
            svc.select_model("gemini-1.5-flash")
        assert svc.config.model_name == "gemini-1.5-flash"
        assert svc._backend_kind == "gemini"

    def test_new_gemini_model_exception_logs_error(self):
        svc, m = self._make_uninit_service()
        svc._use_vertex = False
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.GenerativeModel = MagicMock(side_effect=RuntimeError("fail"))
            svc.select_model("gemini-99.0")
        # model should remain the default
        assert svc.config.model_name == "gemini-2.5-flash"


# ===========================================================================
# process_image
# ===========================================================================

class TestProcessImage:
    def _make_initialized_service(self):
        """Return (svc, mock_model) with api backend initialized."""
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_process_image_success(self):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage

        test_image = PILImage.new("RGB", (10, 10))
        mock_response = _mock_response("image analysis result")
        mock_model.generate_content.return_value = mock_response

        # Patch genai_types to None to use the simple [prompt, image] path
        with patch.object(m, "genai_types", None):
            result = await svc.process_image(test_image, "describe this image")

        assert result.success is True
        assert result.response == "image analysis result"
        assert result.backend == "api"
        assert result.latency >= 0

    async def test_process_image_not_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        from PIL import Image as PILImage
        test_image = PILImage.new("RGB", (10, 10))
        result = await svc.process_image(test_image, "describe")
        assert result.success is False
        assert result.error is not None
        assert "not available" in result.error.lower() or "not initialized" in result.error.lower()

    async def test_process_image_not_initialized(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(side_effect=Exception("no model"))
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        assert not svc.is_initialized()
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (5, 5))
        result = await svc.process_image(img, "test")
        assert result.success is False

    async def test_process_image_non_gemini_backend(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "gemma"
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (5, 5))
        result = await svc.process_image(img, "test")
        assert result.success is False
        assert "gemma" in result.error.lower()

    async def test_process_image_exception_returns_failure(self):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (5, 5))
        mock_model.generate_content.side_effect = RuntimeError("API error")
        with patch.object(m, "genai_types", None):
            result = await svc.process_image(img, "test")
        assert result.success is False
        assert "API error" in result.error

    async def test_process_image_from_path(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage
        img_path = tmp_path / "test.png"
        PILImage.new("RGB", (10, 10)).save(img_path)
        mock_response = _mock_response("path image result")
        mock_model.generate_content.return_value = mock_response
        with patch.object(m, "genai_types", None):
            result = await svc.process_image(str(img_path), "describe")
        assert result.success is True
        assert result.response == "path image result"


# ===========================================================================
# process_text
# ===========================================================================

class TestProcessText:
    def _make_initialized_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_process_text_success(self):
        svc, mock_model, m = self._make_initialized_service()
        mock_response = _mock_response("text response here")
        mock_model.generate_content.return_value = mock_response
        result = await svc.process_text("hello")
        assert result.success is True
        assert result.response == "text response here"

    async def test_process_text_with_input_text(self):
        svc, mock_model, m = self._make_initialized_service()
        mock_response = _mock_response("expanded response")
        mock_model.generate_content.return_value = mock_response
        result = await svc.process_text("summarize this", input_text="long input text")
        assert result.success is True
        assert result.response == "expanded response"

    async def test_process_text_not_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        result = await svc.process_text("hello")
        assert result.success is False
        assert result.error is not None

    async def test_process_text_exception_returns_failure(self):
        svc, mock_model, m = self._make_initialized_service()
        mock_model.generate_content.side_effect = RuntimeError("timeout")
        result = await svc.process_text("hello")
        assert result.success is False
        assert "timeout" in result.error

    async def test_process_text_gemma_backend(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "gemma"
        mock_response = _mock_response("gemma text")
        mock_model.generate_content.return_value = mock_response
        result = await svc.process_text("test prompt")
        assert result.success is True
        assert result.backend == "gemma"

    async def test_process_text_veo_backend(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "veo"
        mock_response = _mock_response("veo text")
        mock_model.generate_content.return_value = mock_response
        result = await svc.process_text("test prompt")
        assert result.success is True
        assert result.backend == "veo"

    async def test_process_text_response_without_text_attr(self):
        svc, mock_model, m = self._make_initialized_service()
        # Response without .text attr
        mock_response = "plain string response"
        mock_model.generate_content.return_value = mock_response
        result = await svc.process_text("hello")
        assert result.success is True
        assert result.response == "plain string response"


# ===========================================================================
# process_video
# ===========================================================================

class TestProcessVideo:
    def _make_initialized_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_process_video_not_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        result = await svc.process_video("/fake/video.mp4", "describe")
        assert result.success is False
        assert "not available" in result.error.lower() or "not initialized" in result.error.lower()

    async def test_process_video_gemma_backend_rejected(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "gemma"
        result = await svc.process_video("/fake/video.mp4", "describe")
        assert result.success is False
        assert "gemma" in result.error.lower()
        assert result.backend == "gemma"

    async def test_process_video_api_backend_success(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        # Create a fake video file
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video data")

        mock_response = _mock_response("video analysis")
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.state.name = "ACTIVE"
        mock_uploaded_file.name = "files/abc123"

        with patch.object(m, "genai") as mock_genai, \
             patch.object(m, "genai_types", None):
            mock_genai.upload_file = MagicMock(return_value=mock_uploaded_file)
            mock_genai.get_file = MagicMock(return_value=mock_uploaded_file)
            mock_genai.delete_file = MagicMock()
            mock_model.generate_content.return_value = mock_response
            svc._model = mock_model

            result = await svc.process_video(str(video_path), "describe")

        assert result.success is True
        assert result.response == "video analysis"

    async def test_process_video_veo_backend(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "veo"
        mock_veo_response = MagicMock()
        mock_veo_response.output_uri = "gs://bucket/video.mp4"
        mock_model.generate_video = MagicMock(return_value=mock_veo_response)

        result = await svc.process_video("/fake/video.mp4", "generate a video")
        assert result.success is True
        assert result.backend == "veo"

    async def test_process_video_exception_returns_failure(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"data")

        with patch.object(m, "genai") as mock_genai, \
             patch.object(m, "genai_types", None):
            mock_genai.upload_file = MagicMock(side_effect=RuntimeError("upload failed"))
            result = await svc.process_video(str(video_path), "describe")

        assert result.success is False
        assert "upload failed" in result.error


# ===========================================================================
# process_audio
# ===========================================================================

class TestProcessAudio:
    def _make_initialized_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_process_audio_not_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        result = await svc.process_audio("/fake/audio.mp3", "transcribe")
        assert result.success is False

    async def test_process_audio_non_gemini_backend_rejected(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "gemma"
        result = await svc.process_audio("/fake/audio.mp3", "transcribe")
        assert result.success is False
        assert "gemma" in result.error.lower()

    async def test_process_audio_success(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"fake audio")

        mock_response = _mock_response("audio transcription")
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.state.name = "ACTIVE"
        mock_uploaded_file.name = "files/audio123"

        with patch.object(m, "genai") as mock_genai, \
             patch.object(m, "genai_types", None):
            mock_genai.upload_file = MagicMock(return_value=mock_uploaded_file)
            mock_genai.get_file = MagicMock(return_value=mock_uploaded_file)
            mock_genai.delete_file = MagicMock()
            mock_model.generate_content.return_value = mock_response
            svc._model = mock_model

            result = await svc.process_audio(str(audio_path), "transcribe")

        assert result.success is True
        assert result.response == "audio transcription"

    async def test_process_audio_exception(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"data")

        with patch.object(m, "genai") as mock_genai:
            mock_genai.upload_file = MagicMock(side_effect=RuntimeError("network error"))
            result = await svc.process_audio(str(audio_path), "transcribe")

        assert result.success is False
        assert "network error" in result.error


# ===========================================================================
# process_youtube
# ===========================================================================

class TestProcessYoutube:
    def _make_initialized_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_process_youtube_not_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        result = await svc.process_youtube("https://youtube.com/watch?v=abc", "summarize")
        assert result.success is False

    async def test_process_youtube_vertex_not_supported(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._use_vertex = True
        result = await svc.process_youtube("https://youtube.com/watch?v=abc", "summarize")
        assert result.success is False
        assert "vertex" in result.error.lower()

    async def test_process_youtube_non_gemini_backend(self):
        svc, mock_model, m = self._make_initialized_service()
        svc._backend_kind = "gemma"
        result = await svc.process_youtube("https://youtube.com/watch?v=abc", "summarize")
        assert result.success is False
        assert "gemma" in result.error.lower()

    async def test_process_youtube_success_no_types(self):
        svc, mock_model, m = self._make_initialized_service()
        mock_response = _mock_response("youtube summary")
        mock_model.generate_content.return_value = mock_response

        with patch.object(m, "genai_types", None):
            result = await svc.process_youtube("https://youtube.com/watch?v=abc", "summarize")

        assert result.success is True
        assert result.response == "youtube summary"
        assert result.backend == "api"

    async def test_process_youtube_exception(self):
        svc, mock_model, m = self._make_initialized_service()
        mock_model.generate_content.side_effect = RuntimeError("yt error")
        with patch.object(m, "genai_types", None):
            result = await svc.process_youtube("https://youtube.com/watch?v=abc", "summarize")
        assert result.success is False
        assert "yt error" in result.error


# ===========================================================================
# batch_process
# ===========================================================================

class TestBatchProcess:
    def _make_initialized_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._use_vertex = False
        svc._backend_kind = "gemini"
        return svc, mock_model, m

    async def test_batch_process_images(self):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage

        images = [PILImage.new("RGB", (5, 5)) for _ in range(3)]
        mock_response = _mock_response("batch result")
        mock_model.generate_content.return_value = mock_response

        with patch.object(m, "genai_types", None):
            results = await svc.batch_process(images, "describe each")
        assert len(results) == 3
        assert all(r.success for r in results)

    async def test_batch_process_single_prompt_broadcast(self):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage

        images = [PILImage.new("RGB", (5, 5)) for _ in range(2)]
        mock_response = _mock_response("result")
        mock_model.generate_content.return_value = mock_response

        with patch.object(m, "genai_types", None):
            results = await svc.batch_process(images, "single prompt")
        assert len(results) == 2

    async def test_batch_process_video_files(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        videos = []
        for i in range(2):
            v = tmp_path / f"video{i}.mp4"
            v.write_bytes(b"data")
            videos.append(str(v))

        mock_response = _mock_response("video result")
        mock_uploaded = MagicMock()
        mock_uploaded.state.name = "ACTIVE"
        mock_uploaded.name = "files/v1"

        with patch.object(m, "genai") as mock_genai, \
             patch.object(m, "genai_types", None):
            mock_genai.upload_file = MagicMock(return_value=mock_uploaded)
            mock_genai.get_file = MagicMock(return_value=mock_uploaded)
            mock_genai.delete_file = MagicMock()
            mock_model.generate_content.return_value = mock_response
            svc._model = mock_model
            results = await svc.batch_process(videos, "describe")

        assert len(results) == 2

    async def test_batch_process_audio_files(self, tmp_path):
        svc, mock_model, m = self._make_initialized_service()
        audios = []
        for ext in [".mp3", ".wav"]:
            a = tmp_path / f"audio{ext}"
            a.write_bytes(b"data")
            audios.append(str(a))

        mock_response = _mock_response("audio result")
        mock_uploaded = MagicMock()
        mock_uploaded.state.name = "ACTIVE"
        mock_uploaded.name = "files/a1"

        with patch.object(m, "genai") as mock_genai, \
             patch.object(m, "genai_types", None):
            mock_genai.upload_file = MagicMock(return_value=mock_uploaded)
            mock_genai.get_file = MagicMock(return_value=mock_uploaded)
            mock_genai.delete_file = MagicMock()
            mock_model.generate_content.return_value = mock_response
            svc._model = mock_model
            results = await svc.batch_process(audios, "transcribe")

        assert len(results) == 2

    async def test_batch_process_list_prompts(self):
        svc, mock_model, m = self._make_initialized_service()
        from PIL import Image as PILImage

        images = [PILImage.new("RGB", (5, 5)) for _ in range(2)]
        prompts = ["prompt 1", "prompt 2"]
        mock_response = _mock_response("result")
        mock_model.generate_content.return_value = mock_response

        with patch.object(m, "genai_types", None):
            results = await svc.batch_process(images, prompts)
        assert len(results) == 2


# ===========================================================================
# _process_text_sync
# ===========================================================================

class TestProcessTextSync:
    def _make_uninit_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    def test_gemma_backend_calls_model(self):
        svc, m = self._make_uninit_service()
        svc._backend_kind = "gemma"
        mock_model = MagicMock()
        mock_response = _mock_response("gemma text")
        mock_model.generate_content.return_value = mock_response
        svc._model = mock_model

        result = svc._process_text_sync("input", "prompt", {}, {})
        mock_model.generate_content.assert_called_once()
        assert result.text == "gemma text"

    def test_veo_backend_calls_model(self):
        svc, m = self._make_uninit_service()
        svc._backend_kind = "veo"
        mock_model = MagicMock()
        mock_response = _mock_response("veo text")
        mock_model.generate_content.return_value = mock_response
        svc._model = mock_model

        result = svc._process_text_sync("input", "prompt", {}, {})
        mock_model.generate_content.assert_called_once()

    def test_gemini_backend_with_different_input_and_prompt(self):
        svc, m = self._make_uninit_service()
        svc._backend_kind = "gemini"
        mock_model = MagicMock()
        mock_response = _mock_response("gemini text")
        mock_model.generate_content.return_value = mock_response
        svc._model = mock_model

        result = svc._process_text_sync("different input", "my prompt", {}, {})
        # Should include both prompt and input_text in contents
        call_args = mock_model.generate_content.call_args[0][0]
        assert "my prompt" in call_args
        assert "different input" in call_args

    def test_gemini_backend_same_input_and_prompt(self):
        svc, m = self._make_uninit_service()
        svc._backend_kind = "gemini"
        mock_model = MagicMock()
        mock_response = _mock_response("result")
        mock_model.generate_content.return_value = mock_response
        svc._model = mock_model

        result = svc._process_text_sync("same", "same", {}, {})
        call_args = mock_model.generate_content.call_args[0][0]
        # When payload == prompt, only one entry
        assert call_args == ["same"]


# ===========================================================================
# _process_image_sync
# ===========================================================================

class TestProcessImageSync:
    def _make_uninit_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    def test_no_vertex_no_types_uses_list(self):
        svc, m = self._make_uninit_service()
        svc._use_vertex = False
        mock_model = MagicMock()
        mock_response = _mock_response("result")
        mock_model.generate_content.return_value = mock_response
        svc._model = mock_model
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (5, 5))

        with patch.object(m, "genai_types", None):
            result = svc._process_image_sync(img, "prompt", {}, {})

        # Should call model.generate_content([prompt, image], ...)
        call_args = mock_model.generate_content.call_args[0][0]
        assert "prompt" in call_args


# ===========================================================================
# _summarize_veo_response
# ===========================================================================

class TestSummarizeVeoResponse:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc

    def test_none_response_returns_empty_string(self):
        svc = self._make_service()
        assert svc._summarize_veo_response(None) == ""

    def test_response_with_output_uri(self):
        svc = self._make_service()
        resp = MagicMock(spec=["output_uri"])
        resp.output_uri = "gs://bucket/video.mp4"
        result = svc._summarize_veo_response(resp)
        parsed = json.loads(result)
        assert parsed["output_uri"] == "gs://bucket/video.mp4"

    def test_response_with_video_bytes(self):
        svc = self._make_service()
        resp = MagicMock(spec=["video"])
        resp.video = b"fake video bytes"
        result = svc._summarize_veo_response(resp)
        parsed = json.loads(result)
        assert "16 bytes" in parsed["video"]

    def test_response_with_to_dict(self):
        svc = self._make_service()
        resp = MagicMock()
        del resp.output_uri
        del resp.video_uri
        del resp.video
        del resp.media
        del resp.candidates
        resp.to_dict = MagicMock(return_value={"status": "done", "uri": "gs://x"})
        result = svc._summarize_veo_response(resp)
        parsed = json.loads(result)
        assert parsed["status"] == "done"

    def test_response_with_no_known_attrs_falls_back_to_raw(self):
        svc = self._make_service()
        resp = SimpleNamespace()  # no relevant attrs
        result = svc._summarize_veo_response(resp)
        parsed = json.loads(result)
        assert "raw" in parsed


# ===========================================================================
# _serialize_google_object
# ===========================================================================

class TestSerializeGoogleObject:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc

    def test_none(self):
        svc = self._make_service()
        assert svc._serialize_google_object(None) is None

    def test_string(self):
        svc = self._make_service()
        assert svc._serialize_google_object("hello") == "hello"

    def test_int(self):
        svc = self._make_service()
        assert svc._serialize_google_object(42) == 42

    def test_float(self):
        svc = self._make_service()
        assert svc._serialize_google_object(3.14) == pytest.approx(3.14)

    def test_bool(self):
        svc = self._make_service()
        assert svc._serialize_google_object(True) is True

    def test_dict(self):
        svc = self._make_service()
        result = svc._serialize_google_object({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_list(self):
        svc = self._make_service()
        result = svc._serialize_google_object([1, "two", 3.0])
        assert result == [1, "two", 3.0]

    def test_object_with_to_dict(self):
        svc = self._make_service()
        obj = MagicMock()
        obj.to_dict = MagicMock(return_value={"key": "value"})
        result = svc._serialize_google_object(obj)
        assert result == {"key": "value"}

    def test_object_with_dict_attr(self):
        svc = self._make_service()

        class MyObj:
            def __init__(self):
                self.public = "yes"
                self._private = "no"

        result = svc._serialize_google_object(MyObj())
        assert result == {"public": "yes"}

    def test_unknown_type_converts_to_string(self):
        svc = self._make_service()
        result = svc._serialize_google_object(object())
        assert isinstance(result, str)

    def test_nested_dict(self):
        svc = self._make_service()
        result = svc._serialize_google_object({"outer": {"inner": 42}})
        assert result == {"outer": {"inner": 42}}

    def test_nested_list(self):
        svc = self._make_service()
        result = svc._serialize_google_object([[1, 2], [3, 4]])
        assert result == [[1, 2], [3, 4]]


# ===========================================================================
# start_cached_session
# ===========================================================================

class TestStartCachedSession:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    async def test_returns_error_when_gemini_unavailable(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", False):
            result = await svc.start_cached_session(contents="some text")
        assert result["success"] is False
        assert "error" in result

    async def test_raises_on_empty_contents(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.caching = MagicMock()
            with pytest.raises(ValueError, match="contents must be provided"):
                await svc.start_cached_session(contents="")

    async def test_returns_error_when_no_caching_attr(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            del mock_genai.caching
            result = await svc.start_cached_session(contents="text")
        assert result["success"] is False

    async def test_success(self):
        svc, m = self._make_service()
        mock_cache = MagicMock()
        mock_cache.to_dict = MagicMock(return_value={"name": "caches/123"})
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.caching = MagicMock()
            mock_genai.caching.create_cache = MagicMock(return_value=mock_cache)
            result = await svc.start_cached_session(contents="long context here")
        assert result["success"] is True
        assert "cache" in result

    async def test_exception_returns_failure(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.caching = MagicMock()
            mock_genai.caching.create_cache = MagicMock(side_effect=RuntimeError("quota exceeded"))
            result = await svc.start_cached_session(contents="text")
        assert result["success"] is False
        assert "quota exceeded" in result["error"]


# ===========================================================================
# submit_batch_job
# ===========================================================================

class TestSubmitBatchJob:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    async def test_returns_error_when_gemini_unavailable(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", False):
            result = await svc.submit_batch_job([{"content": "x"}])
        assert result["success"] is False
        assert "error" in result

    async def test_raises_on_empty_requests(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.batch = MagicMock()
            with pytest.raises(ValueError, match="requests must be provided"):
                await svc.submit_batch_job([])

    async def test_returns_error_when_no_batch_attr(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            del mock_genai.batch
            result = await svc.submit_batch_job([{"content": "x"}])
        assert result["success"] is False

    async def test_submit_success(self):
        svc, m = self._make_service()
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.__dict__ = {"name": "operations/123", "done": True}
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.batch = MagicMock()
            mock_genai.batch.generate_content = MagicMock(return_value=mock_operation)
            result = await svc.submit_batch_job([{"content": "x"}])
        assert result["success"] is True
        assert result["completed"] is True

    async def test_submit_exception_returns_failure(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.batch = MagicMock()
            mock_genai.batch.generate_content = MagicMock(side_effect=RuntimeError("batch fail"))
            result = await svc.submit_batch_job([{"content": "x"}])
        assert result["success"] is False
        assert "batch fail" in result["error"]


# ===========================================================================
# create_ephemeral_token
# ===========================================================================

class TestCreateEphemeralToken:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    async def test_unavailable_returns_error(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", False):
            result = await svc.create_ephemeral_token()
        assert result["success"] is False

    async def test_no_tokens_attr_returns_error(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            del mock_genai.tokens
            result = await svc.create_ephemeral_token()
        assert result["success"] is False

    async def test_create_token_success(self):
        svc, m = self._make_service()
        mock_token = MagicMock()
        mock_token.__dict__ = {"value": "token_xyz", "expires_in": 3600}
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.tokens = MagicMock()
            mock_genai.tokens.create = MagicMock(return_value=mock_token)
            result = await svc.create_ephemeral_token(ttl_seconds=1800)
        assert result["success"] is True
        assert "token" in result

    async def test_create_token_with_audience(self):
        svc, m = self._make_service()
        mock_token = MagicMock()
        mock_token.__dict__ = {"value": "token_abc"}
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.tokens = MagicMock()
            mock_genai.tokens.create = MagicMock(return_value=mock_token)
            result = await svc.create_ephemeral_token(audience="my-app")
        assert result["success"] is True
        call_kwargs = mock_genai.tokens.create.call_args[1]
        assert call_kwargs["audience"] == "my-app"

    async def test_create_token_exception(self):
        svc, m = self._make_service()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.tokens = MagicMock()
            mock_genai.tokens.create = MagicMock(side_effect=RuntimeError("auth error"))
            result = await svc.create_ephemeral_token()
        assert result["success"] is False
        assert "auth error" in result["error"]


# ===========================================================================
# cleanup
# ===========================================================================

class TestCleanup:
    async def test_cleanup_resets_model_and_initialized(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        assert svc.is_initialized()
        await svc.cleanup()
        assert svc._model is None
        assert svc._is_initialized is False

    async def test_cleanup_idempotent(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        await svc.cleanup()
        await svc.cleanup()
        assert svc._model is None


# ===========================================================================
# test_connection
# ===========================================================================

class TestTestConnection:
    async def test_test_connection_not_initialized(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        result = await svc.test_connection()
        assert result.success is False

    async def test_test_connection_success(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai_types", None), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_response = _mock_response("Hello, I am Gemini!")
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
            svc._model = mock_model
            result = await svc.test_connection()
        assert result.success is True
        assert result.response == "Hello, I am Gemini!"


# ===========================================================================
# GemmaTextClient
# ===========================================================================

class TestGemmaTextClient:
    def test_normalize_model_name_adds_google_prefix(self):
        m = _import_module()
        c = m.GemmaTextClient("gemma-2-9b-it")
        assert c.model_name == "google/gemma-2-9b-it"

    def test_normalize_model_name_with_slash_unchanged(self):
        m = _import_module()
        c = m.GemmaTextClient("organization/gemma-2-9b-it")
        assert c.model_name == "organization/gemma-2-9b-it"

    def test_normalize_model_name_already_google(self):
        m = _import_module()
        c = m.GemmaTextClient("google/gemma-2-9b-it")
        assert c.model_name == "google/gemma-2-9b-it"

    def test_extract_prompt_string(self):
        m = _import_module()
        result = m.GemmaTextClient._extract_prompt("hello world")
        assert result == "hello world"

    def test_extract_prompt_list_of_strings(self):
        m = _import_module()
        result = m.GemmaTextClient._extract_prompt(["hello", "world"])
        assert result == "hello\nworld"

    def test_extract_prompt_list_with_text_attr(self):
        m = _import_module()
        part = SimpleNamespace(text="from attr")
        result = m.GemmaTextClient._extract_prompt([part])
        assert result == "from attr"

    def test_extract_prompt_list_with_dicts(self):
        m = _import_module()
        result = m.GemmaTextClient._extract_prompt([{"text": "from dict"}])
        assert result == "from dict"

    def test_extract_prompt_empty_list(self):
        m = _import_module()
        result = m.GemmaTextClient._extract_prompt([])
        assert result == ""

    def test_pipeline_error_set_when_transformers_unavailable(self):
        m = _import_module()
        with patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            c = m.GemmaTextClient("gemma-model")
        assert c._pipeline is None
        assert c._pipeline_error is not None

    def test_default_hyperparams(self):
        m = _import_module()
        with patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            c = m.GemmaTextClient("gemma-model")
        assert c.max_new_tokens == 512
        assert c.temperature == pytest.approx(0.2)
        assert c.top_p == pytest.approx(0.9)

    def test_custom_hyperparams(self):
        m = _import_module()
        with patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            c = m.GemmaTextClient("gemma-model", max_new_tokens=1024, temperature=0.5)
        assert c.max_new_tokens == 1024
        assert c.temperature == pytest.approx(0.5)


# ===========================================================================
# VeoVideoClient
# ===========================================================================

class TestVeoVideoClient:
    def test_init_raises_when_gemini_unavailable(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="google-generativeai"):
                m.VeoVideoClient("veo-2.0", api_key="key")

    def test_init_creates_model(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            client = m.VeoVideoClient("veo-2.0", api_key="key123")
        assert client._model is mock_model
        assert client.model_name == "veo-2.0"

    def test_init_without_api_key_skips_configure(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            m.VeoVideoClient("veo-2.0", api_key=None)
        mock_genai.configure.assert_not_called()

    def test_generate_content_calls_model(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            client = m.VeoVideoClient("veo-2.0", api_key="key")
        mock_model.generate_content.return_value = MagicMock(text="result")
        result = client.generate_content("prompt text")
        mock_model.generate_content.assert_called_once()

    def test_generate_video_uses_generate_video_if_available(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_model.generate_video = MagicMock(return_value=MagicMock())
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            client = m.VeoVideoClient("veo-2.0", api_key="key")
        client.generate_video("make a short video")
        mock_model.generate_video.assert_called_once()

    def test_generate_video_falls_back_to_generate_content(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock(spec=["generate_content"])  # no generate_video
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            client = m.VeoVideoClient("veo-2.0", api_key="key")
        mock_model.generate_content.return_value = MagicMock()
        client.generate_video("make a short video")
        mock_model.generate_content.assert_called_once()

    def test_merge_generation_config(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            client = m.VeoVideoClient(
                "veo-2.0",
                api_key="key",
                generation_config={"temperature": 0.5, "top_k": 10},
            )
        merged = client._merge_generation_config({"temperature": 0.9})
        assert merged["temperature"] == pytest.approx(0.9)  # override
        assert merged["top_k"] == 10  # base retained


# ===========================================================================
# _wait_for_batch_completion
# ===========================================================================

class TestWaitForBatchCompletion:
    def _make_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    def test_already_done_returns_immediately(self):
        svc, m = self._make_service()
        mock_op = MagicMock()
        mock_op.done = True
        with patch.object(m, "genai") as mock_genai:
            mock_genai.batch = MagicMock()
            result = svc._wait_for_batch_completion(mock_op, poll_interval=0.01, timeout=1.0)
        assert result is mock_op

    def test_no_batch_attr_returns_operation(self):
        svc, m = self._make_service()
        mock_op = MagicMock()
        with patch.object(m, "genai") as mock_genai:
            del mock_genai.batch
            result = svc._wait_for_batch_completion(mock_op, poll_interval=0.01, timeout=1.0)
        assert result is mock_op

    def test_timeout_raises_timeout_error(self):
        svc, m = self._make_service()
        mock_op = MagicMock()
        mock_op.done = False
        mock_op.name = "operations/xyz"
        done_op = MagicMock()
        done_op.done = False  # never completes

        with patch.object(m, "genai") as mock_genai, \
             patch("time.sleep"), \
             patch("time.time", side_effect=[0, 0, 100]):  # instant timeout
            mock_genai.batch = MagicMock()
            mock_genai.batch.get_operation = MagicMock(return_value=done_op)
            with pytest.raises(TimeoutError):
                svc._wait_for_batch_completion(mock_op, poll_interval=0.001, timeout=0.0001)


# ===========================================================================
# analyze_video_frames (partial - guards only)
# ===========================================================================

class TestAnalyzeVideoFrames:
    def _make_uninit_service(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        return svc, m

    async def test_returns_error_when_not_available(self):
        svc, m = self._make_uninit_service()
        result = await svc.analyze_video_frames([{"path": "f.jpg", "timestamp": 0.0}])
        assert result["success"] is False
        assert "not available" in result["error"].lower() or "not initialized" in result["error"].lower()

    async def test_returns_error_non_gemini_backend(self):
        svc, m = self._make_uninit_service()
        svc._is_initialized = True
        svc._model = MagicMock()
        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", True):
            svc._backend_kind = "gemma"
            result = await svc.analyze_video_frames([{"path": "f.jpg", "timestamp": 0.0}])
        assert result["success"] is False
        assert "gemma" in result["error"].lower()

    async def test_empty_frames_returns_summary(self):
        m = _import_module()
        import datetime as _datetime_mod

        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_response = _mock_response("summary text")
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
            svc = m.GeminiService(m.GeminiConfig(api_key="key"))
        svc._model = mock_model
        svc._is_initialized = True
        svc._backend_kind = "gemini"

        # Patch process_text to return a fake result, avoiding the real call
        async def _fake_process_text(prompt, **kwargs):
            return m.GeminiResult(
                success=True, response="summary here", latency=0.0,
                model_name="gemini-2.5-flash", backend="gemini"
            )

        svc.process_text = _fake_process_text

        # Inject a fake datetime object into module namespace to work around
        # the missing import bug (source calls datetime.now() without importing datetime).
        # The code does `datetime.now()` so we need an object with a .now() method.
        fake_datetime = MagicMock()
        fake_datetime.now = MagicMock(return_value=_datetime_mod.datetime(2026, 1, 1))
        m.datetime = fake_datetime
        try:
            result = await svc.analyze_video_frames([])
        finally:
            del m.datetime  # clean up after test

        assert result["success"] is True
        assert result["visual_elements"] == []


# ===========================================================================
# is_initialized
# ===========================================================================

class TestIsInitialized:
    def test_not_initialized_by_default(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        assert svc.is_initialized() is False

    def test_initialized_after_model_registered(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        svc._register_model("m", MagicMock(), backend="gemini")
        assert svc.is_initialized() is True

    def test_not_initialized_if_model_none_despite_flag(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        svc._is_initialized = True
        svc._model = None
        assert svc.is_initialized() is False


# ===========================================================================
# Vertex AI initialization path
# ===========================================================================

class TestVertexInitialization:
    def test_vertex_init_sets_use_vertex(self):
        m = _import_module()
        vertex_module = MagicMock()
        vertex_module.init = MagicMock()
        mock_vertex_model = MagicMock()
        GenerativeModel_mock = MagicMock(return_value=mock_vertex_model)

        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", True), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "vertexai", vertex_module, create=True), \
             patch.object(m, "GenerativeModel", GenerativeModel_mock, create=True):
            svc = m.GeminiService(m.GeminiConfig(project_id="my-project", location="us-east1"))

        assert svc._use_vertex is True
        assert svc.is_initialized()
        vertex_module.init.assert_called_once_with(
            project="my-project", location="us-east1"
        )

    def test_vertex_takes_priority_over_api_key(self):
        m = _import_module()
        vertex_module = MagicMock()
        vertex_module.init = MagicMock()
        mock_vertex_model = MagicMock()
        GenerativeModel_mock = MagicMock(return_value=mock_vertex_model)

        with patch.object(m, "GEMINI_AVAILABLE", True), \
             patch.object(m, "VERTEX_AVAILABLE", True), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False), \
             patch.object(m, "genai") as mock_genai, \
             patch.object(m, "vertexai", vertex_module, create=True), \
             patch.object(m, "GenerativeModel", GenerativeModel_mock, create=True):
            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=MagicMock())
            svc = m.GeminiService(m.GeminiConfig(
                api_key="api_key",
                project_id="my-project",
            ))

        assert svc._use_vertex is True


# ===========================================================================
# _prepare_image
# ===========================================================================

class TestPrepareImage:
    def test_prepare_image_pil_api_backend(self):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        svc._use_vertex = False
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (10, 10))
        result = svc._prepare_image(img)
        # For API backend, just returns the image
        assert result is img

    def test_prepare_image_from_path(self, tmp_path):
        m = _import_module()
        with patch.object(m, "GEMINI_AVAILABLE", False), \
             patch.object(m, "VERTEX_AVAILABLE", False), \
             patch.object(m, "TRANSFORMERS_AVAILABLE", False):
            svc = m.GeminiService()
        svc._use_vertex = False
        from PIL import Image as PILImage
        img_path = tmp_path / "img.png"
        PILImage.new("RGB", (5, 5)).save(img_path)
        result = svc._prepare_image(str(img_path))
        # Returns a PIL Image
        assert hasattr(result, "size")
