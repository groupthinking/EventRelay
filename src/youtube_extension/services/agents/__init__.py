"""
AI Agent Services
=================

Extracted AI agent services with clean APIs and proper dependency injection.
Provides specialized AI agents for different video processing tasks.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from .adapters.action_implementer_agent import ActionImplementerAgent
except ImportError as exc:  # pragma: no cover
    ActionImplementerAgent = None
    logger.warning("ActionImplementerAgent unavailable: %s", exc)

try:
    from .adapters.agent_orchestrator import AgentOrchestrator
except ImportError as exc:  # pragma: no cover
    AgentOrchestrator = None
    logger.warning("AgentOrchestrator unavailable: %s", exc)

try:
    from .adapters.hybrid_vision_agent import HybridVisionAgent
except ImportError as exc:  # pragma: no cover
    HybridVisionAgent = None
    logger.warning("HybridVisionAgent unavailable: %s", exc)

try:
    from .adapters.personality_agent import PersonalityAgent
except ImportError as exc:  # pragma: no cover
    PersonalityAgent = None
    logger.warning("PersonalityAgent unavailable: %s", exc)

try:
    from .adapters.strategy_agent import StrategyAgent
except ImportError as exc:  # pragma: no cover
    StrategyAgent = None
    logger.warning("StrategyAgent unavailable: %s", exc)

try:
    from .adapters.transcript_action_agent import TranscriptActionAgent
except ImportError as exc:  # pragma: no cover
    TranscriptActionAgent = None
    logger.warning("TranscriptActionAgent unavailable: %s", exc)

try:
    from .adapters.video_master_agent import VideoMasterAgent
except ImportError as exc:  # pragma: no cover
    VideoMasterAgent = None
    logger.warning("VideoMasterAgent unavailable: %s", exc)

try:
    from .base_agent import BaseAgent
except ImportError as exc:  # pragma: no cover
    BaseAgent = None
    logger.warning("BaseAgent unavailable: %s", exc)

__all__ = [
    'AgentOrchestrator',
    'VideoMasterAgent',
    'ActionImplementerAgent',
    'HybridVisionAgent',
    'TranscriptActionAgent',
    'PersonalityAgent',
    'StrategyAgent',
    'BaseAgent'
]
