#!/usr/bin/env python3
"""Comprehensive unit tests for service_container.py."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_extension.backend.containers.service_container import (
    ServiceContainer,
    get_service,
    get_service_container,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bare_container() -> ServiceContainer:
    """Create a ServiceContainer without calling __init__ (skips lazy service setup)."""
    sc = ServiceContainer.__new__(ServiceContainer)
    sc._services = {}
    sc._singletons = {}
    sc._factories = {}
    sc._config = {}
    return sc


# ---------------------------------------------------------------------------
# _load_configuration
# ---------------------------------------------------------------------------

class TestLoadConfiguration:
    def test_defaults_set_without_env(self, monkeypatch):
        for key in [
            "CACHE_DIR", "ENHANCED_ANALYSIS_DIR", "FEEDBACK_DIR",
            "RATE_LIMIT_RPS", "MAX_RECENT_REQUESTS", "VIDEO_PROCESSOR_TYPE",
            "USE_LANGEXTRACT_FALLBACK", "LIVEKIT_URL", "MOZILLA_AI_URL",
            "GEMINI_API_KEY", "GOOGLE_API_KEY", "YOUTUBE_API_KEY",
        ]:
            monkeypatch.delenv(key, raising=False)

        sc = _bare_container()
        sc._load_configuration()

        assert sc._config["cache_dir"] == "/tmp/uvai_cache/markdown_analysis"
        assert sc._config["enhanced_analysis_dir"] == "/tmp/uvai_cache/enhanced_analysis"
        assert sc._config["feedback_dir"] == "/tmp/uvai_cache/feedback"
        assert sc._config["rate_limit_rps"] == 5
        assert sc._config["max_recent_requests"] == 1000
        assert sc._config["video_processor_type"] == "auto"
        assert sc._config["use_langextract_fallback"] is False
        assert sc._config["livekit_url"] == "ws://localhost:7880"
        assert sc._config["mozilla_ai_url"] == ""
        assert sc._config["gemini_api_key_present"] is False
        assert sc._config["youtube_api_key_present"] is False

    def test_env_overrides_cache_dir(self, monkeypatch):
        monkeypatch.setenv("CACHE_DIR", "/custom/cache")
        sc = _bare_container()
        sc._load_configuration()
        assert sc._config["cache_dir"] == "/custom/cache"

    def test_env_overrides_rate_limit_rps(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_RPS", "20")
        sc = _bare_container()
        sc._load_configuration()
        assert sc._config["rate_limit_rps"] == 20

    def test_gemini_api_key_present_true_via_gemini_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        sc = _bare_container()
        sc._load_configuration()
        assert sc._config["gemini_api_key_present"] is True

    def test_gemini_api_key_present_true_via_google_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        sc = _bare_container()
        sc._load_configuration()
        assert sc._config["gemini_api_key_present"] is True

    def test_youtube_api_key_present(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "yt-key")
        sc = _bare_container()
        sc._load_configuration()
        assert sc._config["youtube_api_key_present"] is True

    def test_use_langextract_fallback_truthy_values(self, monkeypatch):
        for val in ("1", "true", "yes"):
            monkeypatch.setenv("USE_LANGEXTRACT_FALLBACK", val)
            sc = _bare_container()
            sc._load_configuration()
            assert sc._config["use_langextract_fallback"] is True, f"Failed for {val!r}"

    def test_use_langextract_fallback_falsy_values(self, monkeypatch):
        for val in ("0", "false", "no", ""):
            monkeypatch.setenv("USE_LANGEXTRACT_FALLBACK", val)
            sc = _bare_container()
            sc._load_configuration()
            assert sc._config["use_langextract_fallback"] is False, f"Failed for {val!r}"


# ---------------------------------------------------------------------------
# register_singleton / register_transient
# ---------------------------------------------------------------------------

class TestRegisterSingleton:
    def test_registers_factory(self):
        sc = _bare_container()
        factory = lambda: object()
        sc.register_singleton("my_service", factory)
        assert "my_service" in sc._factories
        assert sc._factories["my_service"] is factory

    def test_singleton_not_instantiated_on_register(self):
        sc = _bare_container()
        sc.register_singleton("lazy", lambda: object())
        assert "lazy" not in sc._singletons


class TestRegisterTransient:
    def test_registers_factory(self):
        sc = _bare_container()
        factory = lambda: object()
        sc.register_transient("trans_service", factory)
        assert "trans_service" in sc._services
        assert sc._services["trans_service"] is factory


# ---------------------------------------------------------------------------
# get_service
# ---------------------------------------------------------------------------

class TestGetService:
    def test_raises_for_unknown_service(self):
        sc = _bare_container()
        with pytest.raises(ValueError, match="Service not registered: unknown"):
            sc.get_service("unknown")

    def test_singleton_created_on_first_access(self):
        sc = _bare_container()
        created = []
        def factory():
            obj = object()
            created.append(obj)
            return obj

        sc.register_singleton("singleton", factory)
        result = sc.get_service("singleton")
        assert result is created[0]

    def test_singleton_same_instance_on_second_access(self):
        sc = _bare_container()
        sc.register_singleton("singleton", lambda: object())
        first = sc.get_service("singleton")
        second = sc.get_service("singleton")
        assert first is second

    def test_singleton_factory_called_exactly_once(self):
        sc = _bare_container()
        call_count = [0]

        def factory():
            call_count[0] += 1
            return object()

        sc.register_singleton("once", factory)
        sc.get_service("once")
        sc.get_service("once")
        assert call_count[0] == 1

    def test_transient_creates_new_instance_each_time(self):
        sc = _bare_container()
        sc.register_transient("transient", lambda: object())
        first = sc.get_service("transient")
        second = sc.get_service("transient")
        assert first is not second

    def test_singleton_takes_priority_over_transient(self):
        sc = _bare_container()
        singleton_obj = object()
        sc.register_singleton("both", lambda: singleton_obj)
        sc._services["both"] = lambda: object()  # also in transient dict
        result = sc.get_service("both")
        assert result is singleton_obj


# ---------------------------------------------------------------------------
# get_config / update_config
# ---------------------------------------------------------------------------

class TestGetConfig:
    def test_get_existing_key(self):
        sc = _bare_container()
        sc._config["rate_limit_rps"] = 10
        assert sc.get_config("rate_limit_rps") == 10

    def test_get_missing_key_returns_default(self):
        sc = _bare_container()
        assert sc.get_config("nonexistent", default="fallback") == "fallback"

    def test_get_missing_key_returns_none_by_default(self):
        sc = _bare_container()
        assert sc.get_config("missing") is None


class TestUpdateConfig:
    def test_updates_existing_key(self):
        sc = _bare_container()
        sc._config["rate_limit_rps"] = 5
        sc.update_config({"rate_limit_rps": 99})
        assert sc._config["rate_limit_rps"] == 99

    def test_adds_new_key(self):
        sc = _bare_container()
        sc.update_config({"new_key": "new_value"})
        assert sc._config["new_key"] == "new_value"

    def test_updates_multiple_keys(self):
        sc = _bare_container()
        sc.update_config({"a": 1, "b": 2})
        assert sc._config["a"] == 1
        assert sc._config["b"] == 2


# ---------------------------------------------------------------------------
# get_all_services
# ---------------------------------------------------------------------------

class TestGetAllServices:
    def test_instantiated_singletons_shown(self):
        sc = _bare_container()
        real_obj = object()
        sc._singletons["inst"] = real_obj
        services = sc.get_all_services()
        assert services["inst"] is real_obj

    def test_non_instantiated_factories_shown_as_not_instantiated(self):
        sc = _bare_container()
        sc.register_singleton("lazy", lambda: object())
        services = sc.get_all_services()
        assert services["lazy"] == "Not instantiated"

    def test_transients_shown_as_transient(self):
        sc = _bare_container()
        sc.register_transient("trans", lambda: object())
        services = sc.get_all_services()
        assert services["trans"] == "Transient (not instantiated)"

    def test_instantiated_singleton_overrides_not_instantiated_label(self):
        sc = _bare_container()
        real_obj = object()
        sc.register_singleton("svc", lambda: real_obj)
        sc._singletons["svc"] = real_obj
        services = sc.get_all_services()
        assert services["svc"] is real_obj


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_returns_healthy_with_no_services(self):
        sc = _bare_container()
        sc._config = {"gemini_api_key_present": False, "youtube_api_key_present": False}
        result = sc.health_check()
        assert result["container"] == "healthy"
        assert "services" in result
        assert "configuration" in result

    def test_reports_api_key_config(self):
        sc = _bare_container()
        sc._config = {
            "gemini_api_key_present": True,
            "youtube_api_key_present": False,
        }
        result = sc.health_check()
        assert result["configuration"]["api_keys_present"]["gemini"] is True
        assert result["configuration"]["api_keys_present"]["youtube"] is False

    def test_reports_loaded_config_keys_count(self):
        sc = _bare_container()
        sc._config = {"key1": 1, "key2": 2, "gemini_api_key_present": False, "youtube_api_key_present": False}
        result = sc.health_check()
        assert result["configuration"]["loaded_keys"] == 4

    def test_service_with_health_check_method_called(self):
        sc = _bare_container()
        mock_svc = MagicMock()
        mock_svc.health_check.return_value = {"status": "healthy", "class": "MockService"}
        sc._singletons["mock_svc"] = mock_svc
        sc._config = {"gemini_api_key_present": False, "youtube_api_key_present": False}

        result = sc.health_check()

        mock_svc.health_check.assert_called_once()
        assert result["services"]["mock_svc"]["status"] == "healthy"

    def test_service_without_health_check_reported_as_healthy(self):
        sc = _bare_container()

        class SimpleSvc:
            pass

        sc._singletons["simple"] = SimpleSvc()
        sc._config = {"gemini_api_key_present": False, "youtube_api_key_present": False}
        result = sc.health_check()
        assert result["services"]["simple"]["status"] == "healthy"
        assert result["services"]["simple"]["class"] == "SimpleSvc"

    def test_unhealthy_service_degrades_container(self):
        sc = _bare_container()
        bad_svc = MagicMock()
        bad_svc.health_check.side_effect = RuntimeError("service dead")
        sc._singletons["bad_svc"] = bad_svc
        sc._config = {"gemini_api_key_present": False, "youtube_api_key_present": False}

        result = sc.health_check()

        assert result["container"] == "degraded"
        assert result["services"]["bad_svc"]["status"] == "unhealthy"
        assert "service dead" in result["services"]["bad_svc"]["error"]


# ---------------------------------------------------------------------------
# shutdown
# ---------------------------------------------------------------------------

class TestShutdown:
    async def test_shutdown_clears_singletons(self):
        sc = _bare_container()
        sc._singletons["svc"] = object()
        await sc.shutdown()
        assert sc._singletons == {}

    async def test_shutdown_calls_cleanup_method(self):
        sc = _bare_container()
        mock_svc = MagicMock()
        mock_svc.cleanup = AsyncMock()
        sc._singletons["svc"] = mock_svc

        await sc.shutdown()

        mock_svc.cleanup.assert_called_once()

    async def test_shutdown_calls_close_when_no_cleanup(self):
        sc = _bare_container()
        mock_svc = MagicMock(spec=["close"])
        mock_svc.close = AsyncMock()
        sc._singletons["svc"] = mock_svc

        await sc.shutdown()

        mock_svc.close.assert_called_once()

    async def test_shutdown_swallows_service_errors(self):
        sc = _bare_container()
        bad_svc = MagicMock()
        bad_svc.cleanup = AsyncMock(side_effect=RuntimeError("cleanup failed"))
        sc._singletons["bad"] = bad_svc

        # Must not raise
        await sc.shutdown()

        assert sc._singletons == {}

    async def test_shutdown_skips_services_without_cleanup_or_close(self):
        sc = _bare_container()

        class PlainSvc:
            pass

        sc._singletons["plain"] = PlainSvc()
        # Must not raise
        await sc.shutdown()
        assert sc._singletons == {}


# ---------------------------------------------------------------------------
# _register_core_services
# ---------------------------------------------------------------------------

class TestRegisterCoreServices:
    def test_all_core_services_registered(self):
        sc = _bare_container()
        sc._register_core_services()

        expected = [
            "cache_service",
            "health_monitoring_service",
            "data_service",
            "video_processor_factory",
            "video_processing_service",
            "hybrid_processor_service",
            "notification_service",
            "metrics_service",
            "websocket_connection_manager",
            "websocket_service",
            "agent_orchestrator",
            "pubsub_service",
            "mcp_orchestrator",
        ]
        for name in expected:
            assert name in sc._factories, f"Service {name!r} not registered"

    def test_register_does_not_instantiate(self):
        sc = _bare_container()
        sc._register_core_services()
        assert sc._singletons == {}


# ---------------------------------------------------------------------------
# Service factory methods (lazy-load testing)
# ---------------------------------------------------------------------------

class TestServiceFactories:
    def test_create_metrics_service(self):
        sc = _bare_container()
        sc._config = {"gemini_api_key_present": False, "youtube_api_key_present": False}
        service = sc._create_metrics_service()
        from youtube_extension.backend.services.metrics_service import MetricsService
        assert isinstance(service, MetricsService)

    def test_create_notification_service(self):
        sc = _bare_container()
        sc._config = {}
        service = sc._create_notification_service()
        from youtube_extension.backend.services.notification_service import NotificationService
        assert isinstance(service, NotificationService)

    def test_create_health_monitoring_service(self):
        sc = _bare_container()
        sc._config = {}
        service = sc._create_health_monitoring_service()
        from youtube_extension.backend.services.health_monitoring_service import HealthMonitoringService
        assert isinstance(service, HealthMonitoringService)

    def test_create_cache_service(self):
        sc = _bare_container()
        sc._config = {"cache_dir": "/tmp/test_cache"}
        service = sc._create_cache_service()
        from youtube_extension.backend.services.cache_service import CacheService
        assert isinstance(service, CacheService)

    def test_create_data_service(self):
        sc = _bare_container()
        sc._config = {
            "enhanced_analysis_dir": "/tmp/test_enhanced",
            "feedback_dir": "/tmp/test_feedback",
            "knowledge_dir": "/tmp/test_knowledge",
        }
        service = sc._create_data_service()
        from youtube_extension.backend.services.data_service import DataService
        assert isinstance(service, DataService)

    def test_create_video_processor_factory(self):
        sc = _bare_container()
        sc._config = {}
        factory = sc._create_video_processor_factory()
        assert hasattr(factory, "create_processor")

    def test_create_websocket_connection_manager(self):
        sc = _bare_container()
        sc._config = {}
        manager = sc._create_websocket_connection_manager()
        from youtube_extension.backend.services.websocket_service import WebSocketConnectionManager
        assert isinstance(manager, WebSocketConnectionManager)

    def test_create_hybrid_processor_service(self, monkeypatch):
        import sys
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        # Remove stale stubs so the real module is (re)imported
        for key in list(sys.modules):
            if key.startswith("youtube_extension.services.ai"):
                sys.modules.pop(key, None)
        sc = _bare_container()
        sc._config = {}
        service = sc._create_hybrid_processor_service()
        from youtube_extension.services.ai.hybrid_processor_service import HybridProcessorService
        assert isinstance(service, HybridProcessorService)

    def test_create_pubsub_service(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        import sys
        import types as _types

        # google.cloud.pubsub_v1 is not installed in test env — provide a stub
        stub_pubsub = _types.ModuleType("google.cloud.pubsub_v1")
        stub_pubsub.PublisherClient = MagicMock
        google_cloud = sys.modules.get("google.cloud")
        original = getattr(google_cloud, "pubsub_v1", None)

        monkeypatch.setattr("sys.modules", {**sys.modules, "google.cloud.pubsub_v1": stub_pubsub})
        if google_cloud is not None:
            google_cloud.pubsub_v1 = stub_pubsub

        try:
            sc = _bare_container()
            sc._config = {}
            service = sc._create_pubsub_service()
            from youtube_extension.backend.services.pubsub_service import PubSubService
            assert isinstance(service, PubSubService)
        finally:
            if google_cloud is not None and original is None:
                try:
                    del google_cloud.pubsub_v1
                except AttributeError:
                    pass

    def test_create_video_processing_service(self):
        sc = _bare_container()
        sc._config = {"cache_dir": "/tmp/cache"}
        # Need video_processor_factory and cache_service registered
        sc.register_singleton("video_processor_factory", sc._create_video_processor_factory)
        sc.register_singleton("cache_service", lambda: sc._create_cache_service())
        service = sc._create_video_processing_service()
        from youtube_extension.backend.services.video_processing_service import VideoProcessingService
        assert isinstance(service, VideoProcessingService)

    def test_create_websocket_service(self):
        sc = _bare_container()
        sc._config = {"cache_dir": "/tmp/cache"}
        sc.register_singleton("video_processor_factory", sc._create_video_processor_factory)
        sc.register_singleton("cache_service", lambda: sc._create_cache_service())
        sc.register_singleton("video_processing_service", sc._create_video_processing_service)
        sc.register_singleton("websocket_connection_manager", sc._create_websocket_connection_manager)
        service = sc._create_websocket_service()
        from youtube_extension.backend.services.websocket_service import WebSocketService
        assert isinstance(service, WebSocketService)

    def test_create_agent_orchestrator(self):
        import sys
        # Remove stale stubs so the real agents package is (re)imported
        for key in list(sys.modules):
            if key.startswith("youtube_extension.services.agents"):
                sys.modules.pop(key, None)
        sc = _bare_container()
        sc._config = {}
        orchestrator = sc._create_agent_orchestrator()
        from youtube_extension.services.agents.adapters.agent_orchestrator import AgentOrchestrator
        assert isinstance(orchestrator, AgentOrchestrator)

    def test_create_mcp_orchestrator(self):
        sc = _bare_container()
        sc._config = {}
        orchestrator = sc._create_mcp_orchestrator()
        from youtube_extension.services.mcp.orchestrator import MCPOrchestrator
        assert isinstance(orchestrator, MCPOrchestrator)


# ---------------------------------------------------------------------------
# get_service_container (module-level singleton)
# ---------------------------------------------------------------------------

class TestGetServiceContainer:
    def test_returns_service_container_instance(self):
        import youtube_extension.backend.containers.service_container as sc_module
        # Reset global state
        original = sc_module._service_container
        sc_module._service_container = None
        try:
            container = get_service_container()
            assert isinstance(container, ServiceContainer)
        finally:
            sc_module._service_container = original

    def test_returns_same_instance_on_subsequent_calls(self):
        import youtube_extension.backend.containers.service_container as sc_module
        original = sc_module._service_container
        sc_module._service_container = None
        try:
            first = get_service_container()
            second = get_service_container()
            assert first is second
        finally:
            sc_module._service_container = original

    def test_existing_container_returned_without_reinit(self):
        import youtube_extension.backend.containers.service_container as sc_module
        original = sc_module._service_container
        sentinel = ServiceContainer.__new__(ServiceContainer)
        sentinel._services = {}
        sentinel._singletons = {}
        sentinel._factories = {}
        sentinel._config = {}
        sc_module._service_container = sentinel
        try:
            result = get_service_container()
            assert result is sentinel
        finally:
            sc_module._service_container = original


# ---------------------------------------------------------------------------
# get_service convenience function
# ---------------------------------------------------------------------------

class TestGetServiceConvenienceFunction:
    def test_get_service_metrics(self):
        import youtube_extension.backend.containers.service_container as sc_module
        original = sc_module._service_container
        sc_module._service_container = None
        try:
            from youtube_extension.backend.services.metrics_service import MetricsService
            result = get_service("metrics_service")
            assert isinstance(result, MetricsService)
        finally:
            sc_module._service_container = original

    def test_get_service_raises_for_unknown(self):
        import youtube_extension.backend.containers.service_container as sc_module
        original = sc_module._service_container
        sc_module._service_container = None
        try:
            with pytest.raises(ValueError, match="Service not registered"):
                get_service("nonexistent_service_xyz")
        finally:
            sc_module._service_container = original
