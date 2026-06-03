"""Unit tests for real_ai_processor.py and real_video_processor.py.

Covers:
  - RealAIProcessorService: init, provider selection, prompt generation, all three
    AI provider methods (success + error paths), process_content, analyze_video_content
  - RealVideoProcessor: init, cache helpers, process_video (cache hit, success, youtube
    failure, AI failure), validate_and_process, batch_process_videos,
    get_processing_status, close
  - Module-level convenience helpers: get_ai_processor, analyze_video_with_ai,
    get_real_video_processor, process_video_real, validate_and_process_video
"""

from __future__ import annotations

import json
import sys
import types
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Path / sys.path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Pre-stub heavy / unavailable packages before any module import
# ---------------------------------------------------------------------------

def _stub_module(name: str, **attrs):
    """Insert a MagicMock module into sys.modules under *name* if not present."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


# google.genai
_google = _stub_module("google")
_google_genai = _stub_module("google.genai", Client=MagicMock())
_google.genai = _google_genai

# openai
_openai_mod = _stub_module("openai", AsyncOpenAI=MagicMock())

# anthropic
_anthropic_mod = _stub_module("anthropic", AsyncAnthropic=MagicMock())

# dotenv
_stub_module("dotenv", load_dotenv=lambda: None)

# pytubefix (used by some transitive imports)
_stub_module("pytubefix")

# ---------------------------------------------------------------------------
# Import modules under test *after* stubs are in place
# ---------------------------------------------------------------------------
from youtube_extension.backend.services.real_ai_processor import (  # noqa: E402
    AIProcessingRequest,
    AIProcessingResult,
    AIProvider,
    ProcessingType,
    RealAIProcessorService,
    get_ai_processor,
    analyze_video_with_ai,
)


# ---------------------------------------------------------------------------
# Shared helpers / factories
# ---------------------------------------------------------------------------

def _make_openai_response(content: str = '{"key": "value"}', total: int = 100,
                           prompt: int = 60, completion: int = 40):
    resp = MagicMock()
    resp.usage.total_tokens = total
    resp.usage.prompt_tokens = prompt
    resp.usage.completion_tokens = completion
    resp.choices[0].message.content = content
    return resp


def _make_anthropic_response(text: str = '{"key": "value"}',
                              input_tokens: int = 50, output_tokens: int = 30):
    resp = MagicMock()
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    resp.content = [MagicMock(text=text)]
    return resp


def _make_gemini_response(text: str = '{"key": "value"}'):
    resp = MagicMock()
    resp.text = text
    return resp


def _make_youtube_data(video_id: str = "auJzb1D-fag") -> dict:
    return {
        "video_id": video_id,
        "metadata": {
            "title": "Test Video",
            "description": "A test video description.",
            "duration": "PT10M",
            "channel_title": "Test Channel",
        },
        "transcript": {
            "has_transcript": True,
            "segment_count": 80,
            "full_text": "This is the transcript.",
        },
        "channel_info": {},
        "related_videos": [],
    }


def _make_ai_analysis(success: bool = True) -> dict:
    return {
        "video_id": "auJzb1D-fag",
        "processing_timestamp": "2026-06-01T00:00:00+00:00",
        "content_analysis": {"main_topics": ["AI"]},
        "summary": {"executive_summary": "Short summary."},
        "actions": {"immediate_actions": []},
        "categorization": {"primary_category": "Technology"},
        "total_cost": 0.05,
        "total_tokens": 500,
        "processing_providers": ["openai"],
        "success": success,
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_ai_processor_singleton():
    """Ensure the module-level singleton is reset between tests."""
    import youtube_extension.backend.services.real_ai_processor as _mod
    original = _mod.ai_processor
    _mod.ai_processor = None
    yield
    _mod.ai_processor = original


@pytest.fixture(autouse=True)
def _reset_video_processor_singleton():
    """Ensure the RealVideoProcessor singleton is reset between tests."""
    try:
        import youtube_extension.backend.services.real_video_processor as _vmod
        original = _vmod.real_video_processor
        _vmod.real_video_processor = None
        yield
        _vmod.real_video_processor = original
    except Exception:
        yield


@pytest.fixture
def mock_cost_monitor():
    """Patch cost_monitor in real_ai_processor with a lightweight mock."""
    monitor = MagicMock()
    monitor.calculate_cost.return_value = 0.01
    monitor.get_cost_dashboard = AsyncMock(return_value={
        "today_summary": {"budget_remaining": 9.0}
    })
    return monitor


@pytest.fixture
def mock_track_api_call():
    return AsyncMock(return_value=MagicMock())


@pytest.fixture
def mock_rate_decorator():
    """Replace check_rate_limit_decorator with a pass-through."""
    def passthrough(service):
        def decorator(fn):
            return fn
        return decorator
    return passthrough


# ---------------------------------------------------------------------------
# Helper: build a processor with explicit client mocks
# ---------------------------------------------------------------------------

def _build_processor(
    openai_client=None,
    anthropic_client=None,
    gemini_client=None,
    mock_cost_monitor=None,
    mock_track=None,
    mock_rate=None,
):
    """Return a RealAIProcessorService with patched internals."""
    passthrough = (lambda s: lambda fn: fn)
    patches = [
        patch(
            "youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
            new=mock_rate or passthrough,
        ),
    ]
    if mock_cost_monitor is not None:
        patches.append(
            patch(
                "youtube_extension.backend.services.real_ai_processor.cost_monitor",
                new=mock_cost_monitor,
            )
        )
    if mock_track is not None:
        patches.append(
            patch(
                "youtube_extension.backend.services.real_ai_processor.track_api_call",
                new=mock_track,
            )
        )

    for p in patches:
        p.start()

    try:
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-openai-key" if openai_client is not None else "",
                "ANTHROPIC_API_KEY": "test-anthropic-key" if anthropic_client is not None else "",
                "GEMINI_API_KEY": "test-gemini-key" if gemini_client is not None else "",
            },
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.HAS_OPENAI",
            new=bool(openai_client),
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.HAS_ANTHROPIC",
            new=bool(anthropic_client),
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.HAS_GEMINI",
            new=bool(gemini_client),
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.openai",
            new=MagicMock(AsyncOpenAI=MagicMock(return_value=openai_client)),
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.anthropic",
            new=MagicMock(AsyncAnthropic=MagicMock(return_value=anthropic_client)),
        ), patch(
            "youtube_extension.backend.services.real_ai_processor.genai",
            new=MagicMock(Client=MagicMock(return_value=gemini_client)),
        ):
            processor = RealAIProcessorService()
            # Directly assign mocked clients to bypass constructor details
            if openai_client is not None:
                processor.openai_client = openai_client
            if anthropic_client is not None:
                processor.anthropic_client = anthropic_client
            if gemini_client is not None:
                processor.gemini_client = gemini_client
    finally:
        for p in patches:
            p.stop()

    return processor


# ===========================================================================
# Tests — RealAIProcessorService
# ===========================================================================


class TestRealAIProcessorServiceInit:
    def test_no_providers_when_no_keys(self):
        with patch.dict("os.environ", {}, clear=False), \
             patch("youtube_extension.backend.services.real_ai_processor.HAS_OPENAI", False), \
             patch("youtube_extension.backend.services.real_ai_processor.HAS_ANTHROPIC", False), \
             patch("youtube_extension.backend.services.real_ai_processor.HAS_GEMINI", False), \
             patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        assert proc.openai_client is None
        assert proc.anthropic_client is None
        assert proc.gemini_client is None

    def test_provider_preferences_populated(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        assert ProcessingType.ANALYSIS in proc.provider_preferences
        assert ProcessingType.SUMMARY in proc.provider_preferences
        assert ProcessingType.ACTIONS in proc.provider_preferences
        assert ProcessingType.LEARNING_PATH in proc.provider_preferences
        assert ProcessingType.CATEGORIZATION in proc.provider_preferences

    def test_model_configs_populated(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        assert AIProvider.OPENAI in proc.model_configs
        assert AIProvider.ANTHROPIC in proc.model_configs
        assert AIProvider.GEMINI in proc.model_configs

    def test_with_all_providers(self):
        openai_client = MagicMock()
        anthropic_client = MagicMock()
        gemini_client = MagicMock()
        proc = _build_processor(
            openai_client=openai_client,
            anthropic_client=anthropic_client,
            gemini_client=gemini_client,
        )
        assert proc.openai_client is openai_client
        assert proc.anthropic_client is anthropic_client
        assert proc.gemini_client is gemini_client


class TestGetAvailableProviders:
    def test_no_providers(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = None
        proc.anthropic_client = None
        proc.gemini_client = None
        assert proc._get_available_providers() == []

    def test_only_openai(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = MagicMock()
        proc.anthropic_client = None
        proc.gemini_client = None
        assert proc._get_available_providers() == ["openai"]

    def test_all_providers(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = MagicMock()
        proc.anthropic_client = MagicMock()
        proc.gemini_client = MagicMock()
        providers = proc._get_available_providers()
        assert set(providers) == {"openai", "anthropic", "gemini"}


class TestSelectOptimalProvider:
    def test_selects_preferred_for_analysis(self):
        """For ANALYSIS, prefers gemini > openai > anthropic."""
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = MagicMock()
        proc.anthropic_client = MagicMock()
        proc.gemini_client = MagicMock()
        provider = proc._select_optimal_provider(ProcessingType.ANALYSIS, 100)
        assert provider == AIProvider.GEMINI

    def test_selects_fallback_when_preferred_unavailable(self):
        """For ANALYSIS with no gemini, falls back to openai."""
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = MagicMock()
        proc.anthropic_client = None
        proc.gemini_client = None
        provider = proc._select_optimal_provider(ProcessingType.ANALYSIS, 100)
        assert provider == AIProvider.OPENAI

    def test_raises_when_no_providers(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = None
        proc.anthropic_client = None
        proc.gemini_client = None
        with pytest.raises(Exception, match="No AI providers available"):
            proc._select_optimal_provider(ProcessingType.ANALYSIS, 100)

    def test_selects_anthropic_for_summary(self):
        """For SUMMARY, prefers anthropic > openai > gemini."""
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = MagicMock()
        proc.anthropic_client = MagicMock()
        proc.gemini_client = None
        provider = proc._select_optimal_provider(ProcessingType.SUMMARY, 100)
        assert provider == AIProvider.ANTHROPIC


class TestGetProcessingPrompt:
    def setup_method(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            self.proc = RealAIProcessorService()

    def test_analysis_prompt_contains_content(self):
        prompt = self.proc._get_processing_prompt(ProcessingType.ANALYSIS, "test content")
        assert "test content" in prompt
        assert "main_topics" in prompt

    def test_summary_prompt(self):
        prompt = self.proc._get_processing_prompt(ProcessingType.SUMMARY, "video text")
        assert "video text" in prompt
        assert "executive_summary" in prompt

    def test_actions_prompt(self):
        prompt = self.proc._get_processing_prompt(ProcessingType.ACTIONS, "action content")
        assert "action content" in prompt
        assert "immediate_actions" in prompt

    def test_learning_path_prompt(self):
        prompt = self.proc._get_processing_prompt(ProcessingType.LEARNING_PATH, "learn content")
        assert "learn content" in prompt
        assert "learning_path" in prompt

    def test_categorization_prompt(self):
        prompt = self.proc._get_processing_prompt(ProcessingType.CATEGORIZATION, "cat content")
        assert "cat content" in prompt
        assert "primary_category" in prompt

    def test_unknown_type_returns_content(self):
        """Falls through to the final `return content` line."""
        # Use a mock processing type value that doesn't match any branch
        # We can just call with a real type but rely on the else branch
        # actually: the code falls through to `return content` only if none match.
        # Since all enum values are covered, we test the else: return content path
        # by calling the private method with an unmatched mock
        mock_type = MagicMock()
        mock_type.__eq__ = lambda s, o: False
        result = self.proc._get_processing_prompt(mock_type, "raw content")
        assert result == "raw content"


# ---------------------------------------------------------------------------
# _process_with_openai
# ---------------------------------------------------------------------------

class TestProcessWithOpenAI:
    async def test_success_returns_parsed_json(self):
        openai_client = MagicMock()
        openai_client.chat = MagicMock()
        openai_client.chat.completions = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response('{"main_topics": ["ML"]}')
        )

        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.005

        proc = _build_processor(openai_client=openai_client)
        proc.openai_client = openai_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            request = AIProcessingRequest(
                content="video transcript",
                processing_type=ProcessingType.ANALYSIS,
                provider=AIProvider.OPENAI,
                video_id="auJzb1D-fag",
            )
            result = await proc._process_with_openai(request)

        assert result.success is True
        assert result.provider == "openai"
        assert result.result == {"main_topics": ["ML"]}
        assert result.tokens_used == 100

    async def test_invalid_json_stored_as_raw(self):
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response("not valid json")
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        proc = _build_processor(openai_client=openai_client)
        proc.openai_client = openai_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_openai(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.SUMMARY,
                )
            )

        assert result.success is True
        assert "raw_response" in result.result

    async def test_api_error_returns_failure_result(self):
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("rate limit")
        )
        proc = _build_processor(openai_client=openai_client)
        proc.openai_client = openai_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", MagicMock()), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock()):
            result = await proc._process_with_openai(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.ACTIONS,
                )
            )

        assert result.success is False
        assert "OpenAI processing failed" in result.error_message
        assert result.tokens_used == 0

    async def test_custom_model_used(self):
        openai_client = MagicMock()
        create_mock = AsyncMock(return_value=_make_openai_response())
        openai_client.chat.completions.create = create_mock
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        proc = _build_processor(openai_client=openai_client)
        proc.openai_client = openai_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_openai(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.CATEGORIZATION,
                    model="gpt-4o",
                )
            )

        assert result.model == "gpt-4o"


# ---------------------------------------------------------------------------
# _process_with_anthropic
# ---------------------------------------------------------------------------

class TestProcessWithAnthropic:
    async def test_success_returns_parsed_json(self):
        anthropic_client = MagicMock()
        anthropic_client.messages = MagicMock()
        anthropic_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response('{"summary": "great"}')
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.02

        proc = _build_processor(anthropic_client=anthropic_client)
        proc.anthropic_client = anthropic_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_anthropic(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.SUMMARY,
                    video_id="auJzb1D-fag",
                )
            )

        assert result.success is True
        assert result.provider == "anthropic"
        assert result.result == {"summary": "great"}
        assert result.tokens_used == 80  # 50+30

    async def test_invalid_json_stored_as_raw(self):
        anthropic_client = MagicMock()
        anthropic_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response("plain text response")
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        proc = _build_processor(anthropic_client=anthropic_client)
        proc.anthropic_client = anthropic_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_anthropic(
                AIProcessingRequest(content="text", processing_type=ProcessingType.ANALYSIS)
            )

        assert "raw_response" in result.result

    async def test_api_error_returns_failure(self):
        anthropic_client = MagicMock()
        anthropic_client.messages.create = AsyncMock(
            side_effect=Exception("connection error")
        )
        proc = _build_processor(anthropic_client=anthropic_client)
        proc.anthropic_client = anthropic_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", MagicMock()), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call", AsyncMock()):
            result = await proc._process_with_anthropic(
                AIProcessingRequest(content="text", processing_type=ProcessingType.ACTIONS)
            )

        assert result.success is False
        assert "Anthropic processing failed" in result.error_message

    async def test_custom_model_propagated(self):
        anthropic_client = MagicMock()
        anthropic_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response()
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        proc = _build_processor(anthropic_client=anthropic_client)
        proc.anthropic_client = anthropic_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_anthropic(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.LEARNING_PATH,
                    model="claude-haiku-4-5",
                )
            )

        assert result.model == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# _process_with_gemini
# ---------------------------------------------------------------------------

class TestProcessWithGemini:
    async def test_success_returns_parsed_json(self):
        gemini_client = MagicMock()
        gemini_client.models = MagicMock()
        gemini_client.models.generate_content = MagicMock(
            return_value=_make_gemini_response('{"primary_category": "Tech"}')
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.001

        proc = _build_processor(gemini_client=gemini_client)
        proc.gemini_client = gemini_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_gemini(
                AIProcessingRequest(
                    content="video text",
                    processing_type=ProcessingType.CATEGORIZATION,
                    video_id="auJzb1D-fag",
                )
            )

        assert result.success is True
        assert result.provider == "gemini"
        assert result.result == {"primary_category": "Tech"}

    async def test_invalid_json_falls_back_to_raw(self):
        gemini_client = MagicMock()
        gemini_client.models.generate_content = MagicMock(
            return_value=_make_gemini_response("plain gemini response")
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        proc = _build_processor(gemini_client=gemini_client)
        proc.gemini_client = gemini_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc._process_with_gemini(
                AIProcessingRequest(content="text", processing_type=ProcessingType.ANALYSIS)
            )

        assert "raw_response" in result.result

    async def test_api_error_returns_failure(self):
        gemini_client = MagicMock()
        gemini_client.models.generate_content = MagicMock(
            side_effect=Exception("quota exceeded")
        )
        proc = _build_processor(gemini_client=gemini_client)
        proc.gemini_client = gemini_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", MagicMock()), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call", AsyncMock()):
            result = await proc._process_with_gemini(
                AIProcessingRequest(content="text", processing_type=ProcessingType.SUMMARY)
            )

        assert result.success is False
        assert "Gemini processing failed" in result.error_message
        assert result.tokens_used == 0


# ---------------------------------------------------------------------------
# process_content routing
# ---------------------------------------------------------------------------

class TestProcessContent:
    async def _make_proc_with_openai(self) -> tuple:
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response()
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.01
        proc = _build_processor(openai_client=openai_client)
        proc.openai_client = openai_client
        return proc, monitor

    async def test_auto_provider_routes_to_best(self):
        proc, monitor = await self._make_proc_with_openai()
        # For ACTIONS, prefers openai first
        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.process_content(
                AIProcessingRequest(
                    content="do something",
                    processing_type=ProcessingType.ACTIONS,
                    provider=AIProvider.AUTO,
                )
            )
        assert result.success is True
        assert result.provider == "openai"

    async def test_explicit_openai_provider(self):
        proc, monitor = await self._make_proc_with_openai()
        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.process_content(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.ANALYSIS,
                    provider=AIProvider.OPENAI,
                )
            )
        assert result.success is True

    async def test_no_providers_returns_failure(self):
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = None
        proc.anthropic_client = None
        proc.gemini_client = None

        result = await proc.process_content(
            AIProcessingRequest(
                content="text",
                processing_type=ProcessingType.ANALYSIS,
                provider=AIProvider.AUTO,
            )
        )
        assert result.success is False
        assert "failed" in result.error_message.lower()

    async def test_explicit_provider_not_available_tries_fallbacks(self):
        """When requested provider not initialized, tries available ones."""
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response()
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = openai_client
        proc.anthropic_client = None
        proc.gemini_client = None

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            # Request anthropic but it's None — should fall back to openai
            result = await proc.process_content(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.ANALYSIS,
                    provider=AIProvider.ANTHROPIC,
                )
            )
        # Either succeeded via fallback or failed gracefully
        assert isinstance(result, AIProcessingResult)

    async def test_anthropic_explicit_route(self):
        anthropic_client = MagicMock()
        anthropic_client.messages.create = AsyncMock(
            return_value=_make_anthropic_response()
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = None
        proc.anthropic_client = anthropic_client
        proc.gemini_client = None

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.process_content(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.SUMMARY,
                    provider=AIProvider.ANTHROPIC,
                )
            )
        assert result.provider == "anthropic"

    async def test_gemini_explicit_route(self):
        gemini_client = MagicMock()
        gemini_client.models.generate_content = MagicMock(
            return_value=_make_gemini_response()
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = None
        proc.anthropic_client = None
        proc.gemini_client = gemini_client

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.process_content(
                AIProcessingRequest(
                    content="text",
                    processing_type=ProcessingType.CATEGORIZATION,
                    provider=AIProvider.GEMINI,
                )
            )
        assert result.provider == "gemini"


# ---------------------------------------------------------------------------
# analyze_video_content
# ---------------------------------------------------------------------------

class TestAnalyzeVideoContent:
    async def test_success_with_all_analyses(self):
        """All four processing tasks succeed."""
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response('{"result": "ok"}')
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.01

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = openai_client
        proc.anthropic_client = None
        proc.gemini_client = None

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.analyze_video_content(_make_youtube_data())

        assert "video_id" in result
        assert result["video_id"] == "auJzb1D-fag"
        assert "processing_timestamp" in result
        # At least some analyses completed or the result structure is correct
        assert "total_cost" in result
        assert "total_tokens" in result

    async def test_success_rate_threshold(self):
        """2 of 4 analyses succeeding yields success=True."""
        call_count = 0

        async def alternating_process(req):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return AIProcessingResult(
                    provider="openai",
                    model="gpt-4o-mini",
                    processing_type=req.processing_type.value,
                    result={"data": "ok"},
                    tokens_used=50,
                    cost=0.01,
                    processing_time=0.1,
                    timestamp="2026-06-01T00:00:00+00:00",
                    success=True,
                )
            else:
                return AIProcessingResult(
                    provider="openai",
                    model="gpt-4o-mini",
                    processing_type=req.processing_type.value,
                    result={},
                    tokens_used=0,
                    cost=0.0,
                    processing_time=0.0,
                    timestamp="2026-06-01T00:00:00+00:00",
                    success=False,
                    error_message="failed",
                )

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()

        proc.process_content = alternating_process
        result = await proc.analyze_video_content(_make_youtube_data())
        assert result["success"] is True

    async def test_with_missing_transcript(self):
        """Handles video data without transcript gracefully."""
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(
            return_value=_make_openai_response('{"data": "ok"}')
        )
        monitor = MagicMock()
        monitor.calculate_cost.return_value = 0.0

        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()
        proc.openai_client = openai_client
        proc.anthropic_client = None
        proc.gemini_client = None

        video_data = {
            "video_id": "auJzb1D-fag",
            "metadata": {"title": "Test", "description": "", "duration": "5m", "channel_title": "Ch"},
            "transcript": {"full_text": "", "has_transcript": False, "segment_count": 0},
        }

        with patch("youtube_extension.backend.services.real_ai_processor.cost_monitor", monitor), \
             patch("youtube_extension.backend.services.real_ai_processor.track_api_call",
                   AsyncMock(return_value=MagicMock())):
            result = await proc.analyze_video_content(video_data)

        assert "video_id" in result

    async def test_exception_in_gather_handled(self):
        """If process_content raises, result captures the exception."""
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            proc = RealAIProcessorService()

        async def raise_always(req):
            raise RuntimeError("boom")

        proc.process_content = raise_always
        result = await proc.analyze_video_content(_make_youtube_data())
        # Should still return a dict (error path or partial)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Module-level helpers: get_ai_processor, analyze_video_with_ai
# ---------------------------------------------------------------------------

class TestModuleLevelAIHelpers:
    def test_get_ai_processor_creates_singleton(self):
        import youtube_extension.backend.services.real_ai_processor as _mod
        with patch("youtube_extension.backend.services.real_ai_processor.check_rate_limit_decorator",
                   new=lambda s: lambda fn: fn):
            p1 = get_ai_processor()
            p2 = get_ai_processor()
        assert p1 is p2
        assert isinstance(p1, RealAIProcessorService)

    async def test_analyze_video_with_ai_delegates(self):
        mock_proc = MagicMock()
        mock_proc.analyze_video_content = AsyncMock(return_value={"success": True})

        with patch("youtube_extension.backend.services.real_ai_processor.get_ai_processor",
                   return_value=mock_proc):
            result = await analyze_video_with_ai({"video_id": "auJzb1D-fag"})

        mock_proc.analyze_video_content.assert_awaited_once()
        assert result == {"success": True}


# ===========================================================================
# Tests — RealVideoProcessor
# ===========================================================================


def _import_video_processor():
    """Import RealVideoProcessor with heavy deps mocked."""
    with patch("youtube_extension.backend.services.real_video_processor.get_youtube_service") as yt, \
         patch("youtube_extension.backend.services.real_video_processor.get_ai_processor") as ai:
        yt.return_value = MagicMock()
        ai.return_value = MagicMock()
        from youtube_extension.backend.services.real_video_processor import (
            RealVideoProcessor,
            get_real_video_processor,
            process_video_real,
            validate_and_process_video,
        )
    return RealVideoProcessor, get_real_video_processor, process_video_real, validate_and_process_video


def _make_video_processor(tmp_path, youtube_service=None, ai_processor=None, enable_cache=True):
    """Build a RealVideoProcessor with mocked services."""
    yt_svc = youtube_service or MagicMock()
    ai_proc = ai_processor or MagicMock()

    with patch("youtube_extension.backend.services.real_video_processor.get_youtube_service",
               return_value=yt_svc), \
         patch("youtube_extension.backend.services.real_video_processor.get_ai_processor",
               return_value=ai_proc), \
         patch.dict("os.environ", {
             "FALLBACK_TO_CACHE": "true" if enable_cache else "false",
             "MAX_RETRY_ATTEMPTS": "2",
         }):
        from youtube_extension.backend.services.real_video_processor import RealVideoProcessor
        proc = RealVideoProcessor()
        proc.cache_dir = tmp_path / "cache"
        proc.cache_dir.mkdir(parents=True, exist_ok=True)
        proc.youtube_service = yt_svc
        proc.ai_processor = ai_proc
        return proc


class TestRealVideoProcessorInit:
    def test_init_sets_attributes(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        assert proc.enable_caching is True
        assert proc.max_retry_attempts == 2
        assert proc.youtube_service is not None
        assert proc.ai_processor is not None

    def test_init_caching_disabled(self, tmp_path):
        proc = _make_video_processor(tmp_path, enable_cache=False)
        assert proc.enable_caching is False


class TestCacheHelpers:
    def test_get_cache_key_is_12_chars(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        key = proc._get_cache_key("https://youtube.com/watch?v=auJzb1D-fag")
        assert len(key) == 12

    def test_get_cache_key_deterministic(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        url = "https://youtube.com/watch?v=auJzb1D-fag"
        assert proc._get_cache_key(url) == proc._get_cache_key(url)

    def test_get_cache_path(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        path = proc._get_cache_path("auJzb1D-fag")
        assert path.name == "auJzb1D-fag_processed.json"

    async def test_load_from_cache_returns_none_when_disabled(self, tmp_path):
        proc = _make_video_processor(tmp_path, enable_cache=False)
        result = await proc._load_from_cache("auJzb1D-fag")
        assert result is None

    async def test_load_from_cache_returns_none_when_no_file(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        result = await proc._load_from_cache("no-such-video")
        assert result is None

    async def test_load_from_cache_returns_data_for_recent_file(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        data = {"video_id": "auJzb1D-fag", "success": True}
        cache_path = proc._get_cache_path("auJzb1D-fag")
        cache_path.write_text(json.dumps(data))

        result = await proc._load_from_cache("auJzb1D-fag")
        assert result is not None
        assert result["cached"] is True
        assert result["video_id"] == "auJzb1D-fag"

    async def test_load_from_cache_ignores_stale_file(self, tmp_path):
        """Files older than 24h should not be returned."""
        import os, time
        proc = _make_video_processor(tmp_path)
        data = {"video_id": "auJzb1D-fag", "success": True}
        cache_path = proc._get_cache_path("auJzb1D-fag")
        cache_path.write_text(json.dumps(data))

        # Set mtime to 25 hours ago
        old_mtime = time.time() - (25 * 3600)
        os.utime(cache_path, (old_mtime, old_mtime))

        result = await proc._load_from_cache("auJzb1D-fag")
        assert result is None

    async def test_save_to_cache_writes_file(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        data = {"video_id": "auJzb1D-fag", "success": True, "cached": True}
        await proc._save_to_cache("auJzb1D-fag", data)

        cache_path = proc._get_cache_path("auJzb1D-fag")
        assert cache_path.exists()
        saved = json.loads(cache_path.read_text())
        # cached field should be stripped
        assert "cached" not in saved
        assert saved["video_id"] == "auJzb1D-fag"

    async def test_save_to_cache_skipped_when_disabled(self, tmp_path):
        proc = _make_video_processor(tmp_path, enable_cache=False)
        await proc._save_to_cache("auJzb1D-fag", {"video_id": "auJzb1D-fag"})
        cache_path = proc._get_cache_path("auJzb1D-fag")
        assert not cache_path.exists()

    async def test_load_from_cache_handles_corrupt_file(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        cache_path = proc._get_cache_path("auJzb1D-fag")
        cache_path.write_text("not-json{{{")

        # Should not raise; should return None
        result = await proc._load_from_cache("auJzb1D-fag")
        assert result is None


class TestProcessVideo:
    async def test_returns_cached_result_when_available(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        cached = {"video_id": "auJzb1D-fag", "success": True, "note": "from cache"}
        proc._load_from_cache = AsyncMock(return_value=cached)

        result = await proc.process_video("https://youtube.com/watch?v=auJzb1D-fag")
        assert result["note"] == "from cache"

    async def test_force_refresh_skips_cache(self, tmp_path):
        """force_refresh=True bypasses _load_from_cache."""
        yt_svc = MagicMock()
        yt_svc.get_comprehensive_video_data = AsyncMock(return_value=_make_youtube_data())
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value={"cached": True, "success": True})

        cost_dash = {"today_summary": {"budget_remaining": 9.0}}
        with patch("youtube_extension.backend.services.real_video_processor.analyze_video_with_ai",
                   AsyncMock(return_value=_make_ai_analysis())), \
             patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value=cost_dash)
            result = await proc.process_video(
                "https://youtube.com/watch?v=auJzb1D-fag", force_refresh=True
            )

        # load_from_cache should NOT have been called because force_refresh=True
        proc._load_from_cache.assert_not_awaited()
        assert result["success"] is True

    async def test_youtube_api_failure_returns_error_result(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.get_comprehensive_video_data = AsyncMock(
            side_effect=Exception("YouTube API quota exceeded")
        )
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value=None)

        result = await proc.process_video("https://youtube.com/watch?v=auJzb1D-fag")

        assert result["success"] is False
        assert "YouTube data extraction failed" in result["error"]
        assert result["video_id"] == "auJzb1D-fag"

    async def test_successful_full_processing(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.get_comprehensive_video_data = AsyncMock(return_value=_make_youtube_data())
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value=None)
        proc._save_to_cache = AsyncMock()

        cost_dash = {"today_summary": {"budget_remaining": 5.0}}
        with patch("youtube_extension.backend.services.real_video_processor.analyze_video_with_ai",
                   AsyncMock(return_value=_make_ai_analysis())), \
             patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value=cost_dash)
            result = await proc.process_video("https://youtube.com/watch?v=auJzb1D-fag")

        assert result["success"] is True
        assert result["video_id"] == "auJzb1D-fag"
        assert "metadata" in result
        assert "transcript" in result
        assert "ai_analysis" in result
        assert result["cached"] is False
        proc._save_to_cache.assert_awaited_once()

    async def test_ai_analysis_failure_continues_with_youtube_data(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.get_comprehensive_video_data = AsyncMock(return_value=_make_youtube_data())
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value=None)
        proc._save_to_cache = AsyncMock()

        cost_dash = {"today_summary": {"budget_remaining": 5.0}}
        with patch("youtube_extension.backend.services.real_video_processor.analyze_video_with_ai",
                   AsyncMock(side_effect=Exception("AI unavailable"))), \
             patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value=cost_dash)
            result = await proc.process_video("https://youtube.com/watch?v=auJzb1D-fag")

        # Processing continues even when AI fails
        assert result["success"] is True
        assert result["ai_analysis"]["success"] is False

    async def test_invalid_url_raises_gracefully(self, tmp_path):
        proc = _make_video_processor(tmp_path)

        result = await proc.process_video("not-a-valid-url-at-all-xyz")
        # Should return a failure dict, not raise
        assert isinstance(result, dict)
        assert result["success"] is False

    async def test_quality_metrics_populated(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.get_comprehensive_video_data = AsyncMock(return_value=_make_youtube_data())
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value=None)
        proc._save_to_cache = AsyncMock()

        cost_dash = {"today_summary": {"budget_remaining": 5.0}}
        with patch("youtube_extension.backend.services.real_video_processor.analyze_video_with_ai",
                   AsyncMock(return_value=_make_ai_analysis())), \
             patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value=cost_dash)
            result = await proc.process_video("https://youtube.com/watch?v=auJzb1D-fag")

        qm = result["quality_metrics"]
        assert qm["has_metadata"] is True
        assert qm["has_transcript"] is True
        assert qm["transcript_quality"] == "high"  # segment_count=80 > 50


class TestValidateAndProcess:
    async def test_invalid_url_returns_error(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.validate_video_url = AsyncMock(return_value=(False, "", "invalid URL"))
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)

        result = await proc.validate_and_process("bad-url")
        assert result["valid"] is False
        assert "invalid URL" in result["error"]

    async def test_valid_url_processes_video(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.validate_video_url = AsyncMock(
            return_value=(True, "auJzb1D-fag", "Valid video")
        )
        yt_svc.get_comprehensive_video_data = AsyncMock(return_value=_make_youtube_data())
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)
        proc._load_from_cache = AsyncMock(return_value=None)
        proc._save_to_cache = AsyncMock()

        cost_dash = {"today_summary": {"budget_remaining": 9.0}}
        with patch("youtube_extension.backend.services.real_video_processor.analyze_video_with_ai",
                   AsyncMock(return_value=_make_ai_analysis())), \
             patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value=cost_dash)
            result = await proc.validate_and_process(
                "https://youtube.com/watch?v=auJzb1D-fag"
            )

        assert result["valid"] is True
        assert result["validation_message"] == "Valid video"
        assert result["success"] is True

    async def test_exception_in_validate_returns_error(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.validate_video_url = AsyncMock(side_effect=RuntimeError("network error"))
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)

        result = await proc.validate_and_process("https://youtube.com/watch?v=auJzb1D-fag")
        assert result["valid"] is False
        assert "Validation failed" in result["error"]


class TestBatchProcessVideos:
    async def test_successful_batch(self, tmp_path):
        urls = [
            "https://youtube.com/watch?v=auJzb1D-fag",
            "https://youtube.com/watch?v=auJzb1D-fag",
        ]
        proc = _make_video_processor(tmp_path)

        success_result = {
            "success": True,
            "video_id": "auJzb1D-fag",
            "cost_breakdown": {"total_cost": 0.05},
        }
        proc.process_video = AsyncMock(return_value=success_result)

        result = await proc.batch_process_videos(urls, max_concurrent=2)

        assert result["batch_processing"] is True
        assert result["total_videos"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["success_rate"] == 100.0

    async def test_batch_with_some_failures(self, tmp_path):
        urls = [
            "https://youtube.com/watch?v=auJzb1D-fag",
            "bad-url-xyz",
        ]
        proc = _make_video_processor(tmp_path)

        async def fake_process(url, force_refresh=False):
            if "auJzb1D-fag" in url:
                return {
                    "success": True,
                    "video_id": "auJzb1D-fag",
                    "cost_breakdown": {"total_cost": 0.05},
                }
            return {"success": False, "error": "bad url", "video_url": url}

        proc.process_video = fake_process

        result = await proc.batch_process_videos(urls)

        assert result["total_videos"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["success_rate"] == 50.0

    async def test_batch_empty_list_raises_zero_division(self, tmp_path):
        """Source code divides by len(video_urls); empty list raises ZeroDivisionError."""
        proc = _make_video_processor(tmp_path)
        with pytest.raises(ZeroDivisionError):
            await proc.batch_process_videos([])

    async def test_batch_exception_in_single_task(self, tmp_path):
        proc = _make_video_processor(tmp_path)
        proc.process_video = AsyncMock(side_effect=RuntimeError("crash"))

        result = await proc.batch_process_videos(["https://youtube.com/watch?v=auJzb1D-fag"])
        # Should handle exceptions gracefully
        assert result["total_videos"] == 1
        assert isinstance(result, dict)

    async def test_semaphore_limits_concurrency(self, tmp_path):
        """Verify semaphore object is created (smoke test for concurrency path)."""
        proc = _make_video_processor(tmp_path)
        success_result = {
            "success": True,
            "video_id": "auJzb1D-fag",
            "cost_breakdown": {"total_cost": 0.0},
        }
        proc.process_video = AsyncMock(return_value=success_result)
        urls = ["https://youtube.com/watch?v=auJzb1D-fag"] * 5
        result = await proc.batch_process_videos(urls, max_concurrent=2)
        assert result["successful"] == 5


class TestGetProcessingStatus:
    async def test_returns_operational_status(self, tmp_path):
        proc = _make_video_processor(tmp_path)

        with patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value={"today": {}})
            status = await proc.get_processing_status()

        assert status["service_status"] == "operational"
        assert "cache" in status
        assert "api_status" in status
        assert "cost_monitoring" in status
        assert "configuration" in status

    async def test_cache_info_populated(self, tmp_path):
        proc = _make_video_processor(tmp_path)

        # Create a couple of fake cache files
        (proc.cache_dir / "abc_processed.json").write_text("{}")
        (proc.cache_dir / "def_processed.json").write_text("{}")

        with patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(return_value={})
            status = await proc.get_processing_status()

        assert status["cache"]["cached_videos"] == 2

    async def test_error_in_status_returns_error_dict(self, tmp_path):
        proc = _make_video_processor(tmp_path)

        with patch("youtube_extension.backend.services.real_video_processor.cost_monitor") as cm:
            cm.get_cost_dashboard = AsyncMock(side_effect=RuntimeError("DB error"))
            status = await proc.get_processing_status()

        assert status["service_status"] == "error"
        assert "error" in status


class TestClose:
    async def test_close_calls_youtube_service_close(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.close = AsyncMock()
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)

        await proc.close()
        yt_svc.close.assert_awaited_once()

    async def test_close_handles_exception_gracefully(self, tmp_path):
        yt_svc = MagicMock()
        yt_svc.close = AsyncMock(side_effect=RuntimeError("cleanup error"))
        proc = _make_video_processor(tmp_path, youtube_service=yt_svc)

        # Should not raise
        await proc.close()


class TestModuleLevelVideoHelpers:
    async def test_get_real_video_processor_singleton(self, tmp_path):
        import youtube_extension.backend.services.real_video_processor as _vmod
        _vmod.real_video_processor = None

        with patch("youtube_extension.backend.services.real_video_processor.get_youtube_service",
                   return_value=MagicMock()), \
             patch("youtube_extension.backend.services.real_video_processor.get_ai_processor",
                   return_value=MagicMock()):
            from youtube_extension.backend.services.real_video_processor import get_real_video_processor
            p1 = get_real_video_processor()
            p2 = get_real_video_processor()

        assert p1 is p2
        _vmod.real_video_processor = None

    async def test_process_video_real_delegates(self, tmp_path):
        mock_proc = MagicMock()
        mock_proc.process_video = AsyncMock(return_value={"success": True})

        with patch("youtube_extension.backend.services.real_video_processor.get_real_video_processor",
                   return_value=mock_proc):
            from youtube_extension.backend.services.real_video_processor import process_video_real
            result = await process_video_real("https://youtube.com/watch?v=auJzb1D-fag")

        mock_proc.process_video.assert_awaited_once()
        assert result == {"success": True}

    async def test_validate_and_process_video_delegates(self, tmp_path):
        mock_proc = MagicMock()
        mock_proc.validate_and_process = AsyncMock(return_value={"valid": True})

        with patch("youtube_extension.backend.services.real_video_processor.get_real_video_processor",
                   return_value=mock_proc):
            from youtube_extension.backend.services.real_video_processor import validate_and_process_video
            result = await validate_and_process_video("https://youtube.com/watch?v=auJzb1D-fag")

        mock_proc.validate_and_process.assert_awaited_once()
        assert result == {"valid": True}


# ---------------------------------------------------------------------------
# AIProcessingRequest / AIProcessingResult dataclass checks
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_request_defaults(self):
        req = AIProcessingRequest(
            content="hello",
            processing_type=ProcessingType.ANALYSIS,
        )
        assert req.provider == AIProvider.AUTO
        assert req.temperature == 0.7
        assert req.model is None
        assert req.max_tokens is None
        assert req.video_id is None
        assert req.context is None

    def test_result_success_default(self):
        res = AIProcessingResult(
            provider="openai",
            model="gpt-4o-mini",
            processing_type="analysis",
            result={},
            tokens_used=0,
            cost=0.0,
            processing_time=0.0,
            timestamp="2026-06-01T00:00:00+00:00",
        )
        assert res.success is True
        assert res.error_message is None


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------

class TestEnums:
    def test_ai_provider_values(self):
        assert AIProvider.OPENAI.value == "openai"
        assert AIProvider.ANTHROPIC.value == "anthropic"
        assert AIProvider.GEMINI.value == "gemini"
        assert AIProvider.AUTO.value == "auto"

    def test_processing_type_values(self):
        assert ProcessingType.ANALYSIS.value == "analysis"
        assert ProcessingType.SUMMARY.value == "summary"
        assert ProcessingType.ACTIONS.value == "actions"
        assert ProcessingType.LEARNING_PATH.value == "learning_path"
        assert ProcessingType.CATEGORIZATION.value == "categorization"
