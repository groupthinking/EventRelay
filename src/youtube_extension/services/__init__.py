"""Lightweight service namespace for the current codebase."""

from __future__ import annotations

__all__ = []

try:  # pragma: no cover - optional service
    from .video_subagent import VideoSubAgent

    __all__.append("VideoSubAgent")
except ImportError:
    pass

try:  # pragma: no cover - AI agent services
    from .agents import (
        ActionImplementerAgent,
        AgentOrchestrator,
        BaseAgent,
        VideoMasterAgent,
    )

    __all__.extend([
        "AgentOrchestrator",
        "VideoMasterAgent",
        "ActionImplementerAgent",
        "BaseAgent"
    ])
except ImportError:
    pass
