#!/usr/bin/env python3
"""
Service Container
=================

Dependency injection container for managing service lifecycle and dependencies.
Implements IoC (Inversion of Control) pattern for better testability and modularity.
"""

import asyncio
import inspect
import logging
import os
from typing import Any, Callable, Optional, TypeVar

from youtube_extension.services.ai.gemini_service import GeminiConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """
    Dependency injection container for managing services and their dependencies.
    Provides singleton and factory patterns for service instantiation.
    """

    def __init__(self):
        """Initialize service container"""
        self._services: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._config: dict[str, Any] = {}

        # Load configuration from environment
        self._load_configuration()

        # Register core services
        self._register_core_services()

    def _load_configuration(self):
        """Load configuration from environment variables"""
        self._config = {
            # Cache configuration
            # Use /tmp for Cloud Run compatibility (read-only root filesystem)
            "cache_dir": os.getenv("CACHE_DIR", "/tmp/uvai_cache/markdown_analysis"),
            "enhanced_analysis_dir": os.getenv(
                "ENHANCED_ANALYSIS_DIR", "/tmp/uvai_cache/enhanced_analysis"
            ),
            "feedback_dir": os.getenv("FEEDBACK_DIR", "/tmp/uvai_cache/feedback"),
            "knowledge_dir": os.getenv("KNOWLEDGE_DIR", "/tmp/uvai_cache/knowledge"),
            # Rate limiting
            "rate_limit_rps": int(os.getenv("RATE_LIMIT_RPS", "5")),
            "max_recent_requests": int(os.getenv("MAX_RECENT_REQUESTS", "1000")),
            # Video processing
            "video_processor_type": os.getenv("VIDEO_PROCESSOR_TYPE", "auto"),
            "use_langextract_fallback": os.getenv(
                "USE_LANGEXTRACT_FALLBACK", "false"
            ).lower()
            in ("1", "true", "yes"),
            # External services
            "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
            "mozilla_ai_url": os.getenv("MOZILLA_AI_URL", ""),
            # API keys (validation only, not storage)
            "gemini_api_key_present": bool(
                os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            ),
            "youtube_api_key_present": bool(os.getenv("YOUTUBE_API_KEY")),
        }

        logger.info("Configuration loaded from environment")

    def _register_core_services(self):
        """Register core service factories"""

        # Cache Service
        self.register_singleton("cache_service", self._create_cache_service)

        # Health Monitoring Service
        self.register_singleton(
            "health_monitoring_service", self._create_health_monitoring_service
        )

        # Data Service
        self.register_singleton("data_service", self._create_data_service)

        # Video Processor Factory
        self.register_singleton(
            "video_processor_factory", self._create_video_processor_factory
        )

        # Video Processing Service
        self.register_singleton(
            "video_processing_service", self._create_video_processing_service
        )

        # Hybrid Processor Service (Gemini/FastVLM orchestration)
        self.register_singleton(
            "hybrid_processor_service", self._create_hybrid_processor_service
        )

        # Notification Service
        self.register_singleton(
            "notification_service", self._create_notification_service
        )

        # Metrics Service
        self.register_singleton("metrics_service", self._create_metrics_service)

        # WebSocket Connection Manager
        self.register_singleton(
            "websocket_connection_manager", self._create_websocket_connection_manager
        )

        # WebSocket Service
        self.register_singleton("websocket_service", self._create_websocket_service)

        # AI Agent Orchestrator
        self.register_singleton("agent_orchestrator", self._create_agent_orchestrator)

        # Pub/Sub Service
        self.register_singleton("pubsub_service", self._create_pubsub_service)

        # MCP Orchestrator (Unified Model Context Protocol)
        self.register_singleton("mcp_orchestrator", self._create_mcp_orchestrator)

        # Register aliases for skill dependencies
        self._register_skill_dependency_aliases()

        logger.info("Core services registered")

    def _register_skill_dependency_aliases(self):
        """Register aliases for services used as skill dependencies.

        Only services backed by a real implementation are aliased here.
        Dependencies without an implementation (e.g. ``openai_service``,
        ``social_api_service``) are intentionally left unregistered: resolving
        them raises ``ValueError``, which ``SkillRegistry._load_skill_instance``
        catches and degrades to no injection, so a skill's ``if self.social_api:``
        availability check correctly reports the service as unavailable. This
        avoids registering truthy placeholder objects that would masquerade as
        real services (and violate REAL_MODE_ONLY).
        """
        # AI Services
        self.register_singleton("gemini_service", lambda: self.get_service("hybrid_processor_service"))

        # Data & Analytics
        self.register_singleton("database_service", lambda: self.get_service("data_service"))
        self.register_singleton("analytics_service", lambda: self.get_service("metrics_service"))

        # External Integration
        self.register_singleton("email_service", lambda: self.get_service("notification_service"))

    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a singleton service.

        Args:
            name: Service name/identifier
            factory: Factory function to create service instance
        """
        self._factories[name] = factory
        logger.debug(f"Singleton service registered: {name}")

    def register_transient(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a transient service (new instance each time).

        Args:
            name: Service name/identifier
            factory: Factory function to create service instance
        """
        self._services[name] = factory
        logger.debug(f"Transient service registered: {name}")

    def get_service(self, name: str) -> Any:
        """
        Get service instance by name.

        Args:
            name: Service name/identifier

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered
        """
        # Check if it's a singleton
        if name in self._factories:
            if name not in self._singletons:
                logger.debug(f"Creating singleton service: {name}")
                self._singletons[name] = self._factories[name]()
            return self._singletons[name]

        # Check if it's a transient service
        if name in self._services:
            logger.debug(f"Creating transient service: {name}")
            return self._services[name]()

        raise ValueError(f"Service not registered: {name}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def update_config(self, config_updates: dict[str, Any]) -> None:
        """
        Update configuration values.

        Args:
            config_updates: Dictionary of configuration updates
        """
        self._config.update(config_updates)
        logger.info(f"Configuration updated: {list(config_updates.keys())}")

    # Service factory methods

    def _create_cache_service(self):
        """Create cache service instance"""
        from ..services.cache_service import CacheService

        return CacheService(cache_dir=self._config["cache_dir"])

    def _create_health_monitoring_service(self):
        """Create health monitoring service instance"""
        from ..services.health_monitoring_service import HealthMonitoringService

        # HealthMonitoringService now accepts an optional config dict only.
        # Use defaults; tuning can be passed via env or future config mapping.
        return HealthMonitoringService()

    def _create_data_service(self):
        """Create data service instance"""
        from ..services.data_service import DataService

        return DataService(
            enhanced_analysis_dir=self._config["enhanced_analysis_dir"],
            feedback_dir=self._config["feedback_dir"],
            knowledge_dir=self._config["knowledge_dir"],
        )

    def _create_video_processor_factory(self):
        """Create video processor factory instance"""
        from ..video_processor_factory import get_video_processor

        class VideoProcessorFactory:
            def create_processor(self, processor_type: str = "auto"):
                return get_video_processor(processor_type)

        return VideoProcessorFactory()

    def _create_video_processing_service(self):
        """Create video processing service instance"""
        from ..services.video_processing_service import VideoProcessingService

        video_processor_factory = self.get_service("video_processor_factory")
        cache_service = self.get_service("cache_service")

        return VideoProcessingService(
            video_processor_factory=video_processor_factory, cache_service=cache_service
        )

    def _create_hybrid_processor_service(self):
        """Create hybrid processor service instance for Gemini orchestration."""
        from youtube_extension.services.ai import HybridConfig, HybridProcessorService

        gemini_cfg = GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GEMINI_LOCATION", "us-central1"),
        )
        hybrid_config = HybridConfig(gemini=gemini_cfg)
        return HybridProcessorService(hybrid_config)

    def _create_websocket_connection_manager(self):
        """Create WebSocket connection manager instance"""
        from ..services.websocket_service import WebSocketConnectionManager

        return WebSocketConnectionManager()

    def _create_websocket_service(self):
        """Create WebSocket service instance"""
        from ..services.websocket_service import WebSocketService

        connection_manager = self.get_service("websocket_connection_manager")
        video_processing_service = self.get_service("video_processing_service")

        return WebSocketService(
            connection_manager=connection_manager,
            video_processing_service=video_processing_service,
            chat_service=None,  # Can be added later
        )

    def _create_notification_service(self):
        """Create notification service instance"""
        from ..services.notification_service import NotificationService

        # In the future, map SMTP or other settings from self._config
        return NotificationService()

    def _create_metrics_service(self):
        """Create metrics service instance"""
        from ..services.metrics_service import MetricsService

        return MetricsService()

    def _create_pubsub_service(self):
        """Create Pub/Sub service instance"""
        from ..services.pubsub_service import PubSubService

        return PubSubService(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            topic_name=os.getenv("PUBSUB_TOPIC_NAME", "uvai-processing-events"),
        )

    def _create_agent_orchestrator(self):
        """Create AI agent orchestrator instance"""
        from ...services.agents import (
            ActionImplementerAgent,
            AgentOrchestrator,
            HybridVisionAgent,
            TranscriptActionAgent,
            VideoMasterAgent,
        )

        orchestrator = AgentOrchestrator()

        # Register agent types for lazy instantiation
        orchestrator.register_agent_type("video_master", VideoMasterAgent)
        orchestrator.register_agent_type("action_implementer", ActionImplementerAgent)
        orchestrator.register_agent_type("hybrid_vision", HybridVisionAgent)
        orchestrator.register_agent_type("transcript_action", TranscriptActionAgent)

        # Add new task mappings for vision processing
        orchestrator.add_task_mapping("vision_analysis", ["hybrid_vision"])
        orchestrator.add_task_mapping(
            "multi_modal_analysis", ["hybrid_vision", "video_master"]
        )
        orchestrator.add_task_mapping("intelligent_vision", ["hybrid_vision"])
        orchestrator.add_task_mapping("transcript_action", ["transcript_action"])
        orchestrator.add_task_mapping("chat_assistance", ["transcript_action"])

        logger.info(
            "Agent orchestrator created with registered agent types including hybrid vision and chat support"
        )
        return orchestrator

    def _create_mcp_orchestrator(self):
        """Create MCP orchestrator instance"""
        from ...services.mcp import MCPOrchestrator, get_registry

        # Get or create the global registry
        registry = get_registry()

        # Create orchestrator with the registry
        orchestrator = MCPOrchestrator(registry=registry)

        logger.info("MCP Orchestrator created for unified protocol coordination")
        return orchestrator

    def get_all_services(self) -> dict[str, Any]:
        """
        Get all currently instantiated services.

        Returns:
            Dictionary of service name -> service instance
        """
        services = {}

        # Get singletons
        for name, service in self._singletons.items():
            services[name] = service

        # Add registered but not instantiated services
        for name in self._factories.keys():
            if name not in services:
                services[name] = "Not instantiated"

        for name in self._services.keys():
            if name not in services:
                services[name] = "Transient (not instantiated)"

        return services

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all services.

        Returns:
            Health status of all services
        """
        health_status = {
            "container": "healthy",
            "timestamp": (
                logger.handlers[0].formatter.formatTime(
                    logging.LogRecord("", 0, "", 0, "", (), None)
                )
                if logger.handlers
                else "unknown"
            ),
            "services": {},
            "configuration": {
                "loaded_keys": len(self._config),
                "api_keys_present": {
                    "gemini": self._config["gemini_api_key_present"],
                    "youtube": self._config["youtube_api_key_present"],
                },
            },
        }

        # Check instantiated singletons
        for name, service in self._singletons.items():
            try:
                # Try to call a health method if available
                if hasattr(service, "health_check"):
                    service_health = service.health_check()
                elif hasattr(service, "__class__"):
                    service_health = {
                        "status": "healthy",
                        "class": service.__class__.__name__,
                    }
                else:
                    service_health = {"status": "unknown"}

                health_status["services"][name] = service_health

            except Exception as e:
                health_status["services"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["container"] = "degraded"

        return health_status

    @staticmethod
    async def _shutdown_service(name: str, service: Any) -> None:
        """Run a single service's teardown hook.

        Prefers ``cleanup()`` and falls back to ``close()``. Either hook may be
        synchronous or a coroutine function, so the result is awaited only when
        it is actually awaitable.
        """
        closer: Optional[Callable[[], Any]] = None
        completion = ""

        cleanup = getattr(service, "cleanup", None)
        if callable(cleanup):
            closer, completion = cleanup, "cleanup completed"
        else:
            close = getattr(service, "close", None)
            if callable(close):
                closer, completion = close, "closed"

        if closer is None:
            return

        result = closer()
        if inspect.isawaitable(result):
            await result

        logger.info(f"Service {completion}: {name}")

    async def shutdown(self):
        """
        Gracefully shutdown all services.
        """
        logger.info("Shutting down service container...")

        shutdown_errors = []

        # Skill-dependency aliases (e.g. ``gemini_service`` ->
        # ``hybrid_processor_service``) resolve to the *same* instance, so the
        # singleton map can hold one object under several names. Deduplicate by
        # identity to avoid tearing the same service down more than once.
        targets: list[tuple[str, Any]] = []
        seen: set[int] = set()
        for name, service in self._singletons.items():
            if id(service) in seen:
                logger.debug(f"Skipping duplicate service alias: {name}")
                continue
            seen.add(id(service))
            targets.append((name, service))

        # Services are independent, so tear them down concurrently: shutdown runs
        # inside the SIGTERM grace window, where serial teardown costs the sum of
        # every close() round-trip instead of the slowest one.
        results = await asyncio.gather(
            *(self._shutdown_service(name, service) for name, service in targets),
            return_exceptions=True,
        )

        for (name, _), result in zip(targets, results):
            if isinstance(result, BaseException):
                logger.warning(f"Error during {name} service shutdown: {result}")
                shutdown_errors.append(f"{name}: {result}")

        # Clear service instances
        self._singletons.clear()

        if shutdown_errors:
            logger.warning(f"Shutdown completed with errors: {shutdown_errors}")
        else:
            logger.info("Service container shutdown completed successfully")


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """
    Get or create global service container instance.

    Returns:
        Global service container
    """
    global _service_container

    if _service_container is None:
        _service_container = ServiceContainer()
        logger.info("Global service container initialized")

    return _service_container


def get_service(service_name: str) -> Any:
    """
    Convenience function to get service from global container.

    Args:
        service_name: Name of service to retrieve

    Returns:
        Service instance
    """
    return get_service_container().get_service(service_name)
