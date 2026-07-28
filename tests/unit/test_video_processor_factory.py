"""Unit tests for youtube_extension.backend.video_processor_factory."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_processor_mock(name: str = "MockProcessor") -> MagicMock:
    """Return a MagicMock that mimics a video-processor instance."""
    instance = MagicMock(name=name)
    instance.process_video = AsyncMock(return_value={"video_id": "test", "success": True})
    return instance


def _make_processor_class(name: str = "MockProcessorClass") -> MagicMock:
    instance = _make_processor_mock(name + "_instance")
    cls = MagicMock(name=name, return_value=instance)
    return cls


def _reload_factory() -> types.ModuleType:
    """Force a fresh import of the factory module, discarding cached state."""
    mod_name = "youtube_extension.backend.video_processor_factory"
    sys.modules.pop(mod_name, None)
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# "auto" mode — reads VIDEO_PROCESSOR_TYPE env var
# ---------------------------------------------------------------------------

class TestAutoMode:
    def test_auto_defaults_to_enhanced_when_no_env(self):
        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = MagicMock(EnhancedVideoProcessor=enhanced_cls)

        extra = {
            "youtube_extension.backend.enhanced_video_processor": enhanced_mod,
            "youtube_extension.backend.video_processor_factory.EnhancedVideoProcessor": enhanced_cls,
        }
        with patch.dict(sys.modules, extra):
            with patch.dict("os.environ", {}, clear=False):
                # Remove the env var if present
                import os
                os.environ.pop("VIDEO_PROCESSOR_TYPE", None)
                os.environ.pop("ENABLE_DEEP_MCP", None)

                factory = _reload_factory()

                # Patch the relative import inside the freshly loaded module
                with patch.object(factory, "get_video_processor", wraps=factory.get_video_processor):
                    with patch(
                        "youtube_extension.backend.video_processor_factory.get_video_processor",
                        wraps=factory.get_video_processor,
                    ):
                        pass

                # Directly test with a mocked enhanced processor
                with patch.dict(
                    sys.modules,
                    {
                        "youtube_extension.backend.deepmcp.deepmcp_processor": None,  # type: ignore[dict-item]
                    },
                ):
                    pass

        # Simpler approach: patch the internals via sys.modules stubs
        # and call through the module under test.
        self._assert_auto_selects_enhanced_when_no_env_var()

    def _assert_auto_selects_enhanced_when_no_env_var(self):
        """Stand-alone assertion without the noisy scaffolding above."""
        import os
        os.environ.pop("VIDEO_PROCESSOR_TYPE", None)
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            processor = factory.get_video_processor("auto")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_auto_env_var_enhanced(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        with patch.dict("os.environ", {"VIDEO_PROCESSOR_TYPE": "enhanced"}):
            with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
                factory = _reload_factory()
                processor = factory.get_video_processor("auto")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_auto_env_var_real(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        real_cls = _make_processor_class("Real")
        real_mod = types.ModuleType("youtube_extension.backend.real_video_processor")
        real_mod.RealVideoProcessor = real_cls  # type: ignore[attr-defined]

        with patch.dict("os.environ", {"VIDEO_PROCESSOR_TYPE": "real"}):
            with patch.dict(sys.modules, {
                "youtube_extension.backend.real_video_processor": real_mod,
            }):
                factory = _reload_factory()
                processor = factory.get_video_processor("auto")

        real_cls.assert_called_once()
        assert processor is real_cls.return_value


# ---------------------------------------------------------------------------
# "enhanced" processor type
# ---------------------------------------------------------------------------

class TestEnhancedProcessorType:
    def _setup_enhanced(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)
        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]
        return enhanced_cls, enhanced_mod

    def test_returns_enhanced_processor(self):
        enhanced_cls, enhanced_mod = self._setup_enhanced()

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            processor = factory.get_video_processor("enhanced")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_enhanced_falls_back_to_real_on_import_error(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        real_cls = _make_processor_class("Real")
        real_mod = types.ModuleType("youtube_extension.backend.real_video_processor")
        real_mod.RealVideoProcessor = real_cls  # type: ignore[attr-defined]

        # enhanced_video_processor module raises on instantiation
        broken_enhanced_cls = MagicMock(side_effect=ImportError("no gemini"))
        broken_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        broken_mod.EnhancedVideoProcessor = broken_enhanced_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {
            "youtube_extension.backend.enhanced_video_processor": broken_mod,
            "youtube_extension.backend.real_video_processor": real_mod,
        }):
            factory = _reload_factory()
            processor = factory.get_video_processor("enhanced")

        real_cls.assert_called_once()
        assert processor is real_cls.return_value

    def test_enhanced_import_module_missing_falls_back_to_real(self):
        """If the enhanced processor raises on instantiation, falls back to real."""
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        real_cls = _make_processor_class("Real")
        real_mod = types.ModuleType("youtube_extension.backend.real_video_processor")
        real_mod.RealVideoProcessor = real_cls  # type: ignore[attr-defined]

        # Broken enhanced: module present but class raises on instantiation
        broken_enhanced_cls = MagicMock(side_effect=RuntimeError("gpu unavailable"))
        broken_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        broken_mod.EnhancedVideoProcessor = broken_enhanced_cls  # type: ignore[attr-defined]

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if "enhanced_video_processor" in name:
                raise ImportError("stubbed out")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            with patch.dict(sys.modules, {
                "youtube_extension.backend.real_video_processor": real_mod,
            }):
                factory2 = _reload_factory()
                processor = factory2.get_video_processor("enhanced")

        real_cls.assert_called_once()
        assert processor is real_cls.return_value


# ---------------------------------------------------------------------------
# "real" processor type
# ---------------------------------------------------------------------------

class TestRealProcessorType:
    def test_returns_real_processor(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        real_cls = _make_processor_class("Real")
        real_mod = types.ModuleType("youtube_extension.backend.real_video_processor")
        real_mod.RealVideoProcessor = real_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.real_video_processor": real_mod}):
            factory = _reload_factory()
            processor = factory.get_video_processor("real")

        real_cls.assert_called_once()
        assert processor is real_cls.return_value

    def test_real_falls_back_to_enhanced_when_real_fails(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if "real_video_processor" in name:
                raise ImportError("real not available")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
                factory = _reload_factory()
                processor = factory.get_video_processor("real")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_real_raises_value_error_when_both_fail(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if "real_video_processor" in name or "enhanced_video_processor" in name:
                raise ImportError("all unavailable")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            factory = _reload_factory()
            with pytest.raises(ValueError, match="No working video processor"):
                factory.get_video_processor("real")


# ---------------------------------------------------------------------------
# "deepmcp" processor type
# ---------------------------------------------------------------------------

class TestDeepMCPProcessorType:
    def test_returns_deepmcp_processor(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        deepmcp_cls = _make_processor_class("DeepMCP")
        deepmcp_mod = types.ModuleType(
            "youtube_extension.backend.deepmcp.deepmcp_processor"
        )
        deepmcp_mod.DeepMCPAgentProcessor = deepmcp_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {
            "youtube_extension.backend.deepmcp.deepmcp_processor": deepmcp_mod,
        }):
            factory = _reload_factory()
            processor = factory.get_video_processor("deepmcp")

        deepmcp_cls.assert_called_once()
        assert processor is deepmcp_cls.return_value

    def test_deepmcp_selected_via_env_flag(self):
        """ENABLE_DEEP_MCP=true should select DeepMCP even for non-deepmcp type."""
        deepmcp_cls = _make_processor_class("DeepMCP")
        deepmcp_mod = types.ModuleType(
            "youtube_extension.backend.deepmcp.deepmcp_processor"
        )
        deepmcp_mod.DeepMCPAgentProcessor = deepmcp_cls  # type: ignore[attr-defined]

        with patch.dict("os.environ", {"ENABLE_DEEP_MCP": "true"}):
            with patch.dict(sys.modules, {
                "youtube_extension.backend.deepmcp.deepmcp_processor": deepmcp_mod,
            }):
                factory = _reload_factory()
                processor = factory.get_video_processor("enhanced")

        deepmcp_cls.assert_called_once()
        assert processor is deepmcp_cls.return_value

    def test_deepmcp_falls_back_to_enhanced_on_import_error(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if "deepmcp_processor" in name:
                raise ImportError("deepmcp not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
                factory = _reload_factory()
                processor = factory.get_video_processor("deepmcp")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_enable_deep_mcp_false_does_not_force_deepmcp(self):
        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        with patch.dict("os.environ", {"ENABLE_DEEP_MCP": "false"}):
            with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
                factory = _reload_factory()
                processor = factory.get_video_processor("enhanced")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value


# ---------------------------------------------------------------------------
# Final fallback (unknown / unhandled processor_type)
# ---------------------------------------------------------------------------

class TestFinalFallback:
    def test_unknown_type_falls_back_to_enhanced(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            processor = factory.get_video_processor("unknown_type_xyz")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_final_fallback_raises_when_enhanced_unavailable(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if "enhanced_video_processor" in name:
                raise ImportError("enhanced not available")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            factory = _reload_factory()
            with pytest.raises(ValueError, match="No working video processor"):
                factory.get_video_processor("unknown_type_xyz")


# ---------------------------------------------------------------------------
# process_video_with_best_processor helper
# ---------------------------------------------------------------------------

class TestProcessVideoWithBestProcessor:
    @pytest.mark.asyncio
    async def test_calls_process_video_and_returns_result(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)
        os.environ.pop("VIDEO_PROCESSOR_TYPE", None)

        expected = {"video_id": "abc123", "success": True}
        # Use spec to ensure 'cleanup' is NOT present (so hasattr returns False)
        mock_instance = MagicMock(spec=["process_video"])
        mock_instance.process_video = AsyncMock(return_value=expected)

        mock_cls = MagicMock(return_value=mock_instance)
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = mock_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            result = await factory.process_video_with_best_processor("https://youtube.com/watch?v=abc123")

        assert result == expected
        mock_instance.process_video.assert_awaited_once_with("https://youtube.com/watch?v=abc123")

    @pytest.mark.asyncio
    async def test_calls_cleanup_if_available(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)
        os.environ.pop("VIDEO_PROCESSOR_TYPE", None)

        mock_instance = MagicMock()
        mock_instance.process_video = AsyncMock(return_value={})
        mock_instance.cleanup = AsyncMock()

        mock_cls = MagicMock(return_value=mock_instance)
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = mock_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            await factory.process_video_with_best_processor("https://youtube.com/watch?v=abc123")

        mock_instance.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_cleanup_if_method_absent(self):
        """If processor has no cleanup method, should not raise."""
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)
        os.environ.pop("VIDEO_PROCESSOR_TYPE", None)

        mock_instance = MagicMock(spec=["process_video"])  # no cleanup attr
        mock_instance.process_video = AsyncMock(return_value={"success": True})

        mock_cls = MagicMock(return_value=mock_instance)
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = mock_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
            factory = _reload_factory()
            result = await factory.process_video_with_best_processor("https://youtube.com/watch?v=abc123")

        assert result == {"success": True}


# ---------------------------------------------------------------------------
# "hybrid" processor type
# ---------------------------------------------------------------------------

class TestHybridProcessorType:
    def test_hybrid_falls_back_to_enhanced_when_unavailable(self):
        """The hybrid path needs yt_dlp + fastvlm_gemini_hybrid; normally absent."""
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        enhanced_cls = _make_processor_class("Enhanced")
        enhanced_mod = types.ModuleType("youtube_extension.backend.enhanced_video_processor")
        enhanced_mod.EnhancedVideoProcessor = enhanced_cls  # type: ignore[attr-defined]

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name in ("yt_dlp", "fastvlm_gemini_hybrid", "fastvlm_gemini_hybrid.video_pipeline"):
                raise ImportError(f"{name} not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            with patch.dict(sys.modules, {"youtube_extension.backend.enhanced_video_processor": enhanced_mod}):
                factory = _reload_factory()
                processor = factory.get_video_processor("hybrid")

        enhanced_cls.assert_called_once()
        assert processor is enhanced_cls.return_value

    def test_hybrid_raises_when_enhanced_also_unavailable(self):
        import os
        os.environ.pop("ENABLE_DEEP_MCP", None)

        import builtins
        real_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name in ("yt_dlp", "fastvlm_gemini_hybrid", "fastvlm_gemini_hybrid.video_pipeline",
                        "youtube_extension.backend.enhanced_video_processor"):
                raise ImportError(f"{name} not installed")
            if "enhanced_video_processor" in name:
                raise ImportError("enhanced not available")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            factory = _reload_factory()
            with pytest.raises(ValueError, match="No working video processor"):
                factory.get_video_processor("hybrid")
<<<<<<< HEAD
=======

    @pytest.mark.asyncio
    async def test_hybrid_success_path(self, monkeypatch):
        # We need mock modules for fastvlm_gemini_hybrid.video_pipeline and yt_dlp
        mock_pipeline = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.process_video_hybrid.return_value = {
            "success": True,
            "response": '{"summary": "test hybrid summary", "actions": [{"name": "action1"}]}'
        }
        mock_pipeline.VideoPipeline.return_value = mock_pipeline_instance

        mock_ytdlp = MagicMock()
        mock_ytdlp_instance = MagicMock()
        mock_ytdlp_instance.extract_info.return_value = {"id": "test_vid_id"}
        mock_ytdlp_instance.prepare_filename.return_value = "filepath.mp4"
        mock_ytdlp.YoutubeDL.return_value.__enter__.return_value = mock_ytdlp_instance

        # Insert them into sys.modules
        monkeypatch.setitem(sys.modules, "fastvlm_gemini_hybrid", mock_pipeline)
        monkeypatch.setitem(sys.modules, "fastvlm_gemini_hybrid.video_pipeline", mock_pipeline)
        monkeypatch.setitem(sys.modules, "yt_dlp", mock_ytdlp)

        factory = _reload_factory()
        processor = factory.get_video_processor("hybrid")

        # Test process_video
        result = await processor.process_video("https://www.youtube.com/watch?v=auJzb1D-fag")
        assert result["video_id"] == "test_vid_id"
        assert result["success"] is True
        assert result["ai_analysis"] == {"summary": "test hybrid summary", "actions": [{"name": "action1"}]}
        assert result["actions"] == [{"name": "action1"}]

>>>>>>> origin/main
