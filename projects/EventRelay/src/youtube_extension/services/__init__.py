"""Lightweight service namespace for the current codebase."""

from __future__ import annotations

__all__ = []

try:  # pragma: no cover - optional service
    from .deployment_manager import DeploymentManager, validate_deployment_environment

    __all__.extend([
        "DeploymentManager",
        "validate_deployment_environment",
    ])
except ImportError:  # Legacy modules were removed in recent refactors
    pass

try:  # pragma: no cover - optional service
    from .video_subagent import VideoSubAgent

    __all__.append("VideoSubAgent")
except ImportError:
    pass

try:  # pragma: no cover - AI agent services
    from .agents import AgentOrchestrator, VideoMasterAgent, ActionImplementerAgent, BaseAgent

    __all__.extend([
        "AgentOrchestrator",
        "VideoMasterAgent",
        "ActionImplementerAgent",
        "BaseAgent"
    ])
except ImportError:
    pass
