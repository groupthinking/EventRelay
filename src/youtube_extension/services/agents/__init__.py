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
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    ActionImplementerAgent = None
    logger.warning("ActionImplementerAgent unavailable: %s", exc)

try:
    from .adapters.agent_orchestrator import AgentOrchestrator
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    AgentOrchestrator = None
    logger.warning("AgentOrchestrator unavailable: %s", exc)

try:
    from .adapters.hybrid_vision_agent import HybridVisionAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    HybridVisionAgent = None
    logger.warning("HybridVisionAgent unavailable: %s", exc)

try:
    from .adapters.personality_agent import PersonalityAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    PersonalityAgent = None
    logger.warning("PersonalityAgent unavailable: %s", exc)

try:
    from .adapters.strategy_agent import StrategyAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    StrategyAgent = None
    logger.warning("StrategyAgent unavailable: %s", exc)

try:
    from .adapters.transcript_action_agent import TranscriptActionAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    TranscriptActionAgent = None
    logger.warning("TranscriptActionAgent unavailable: %s", exc)

try:
    from .adapters.video_master_agent import VideoMasterAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
    VideoMasterAgent = None
    logger.warning("VideoMasterAgent unavailable: %s", exc)

try:
    from .base_agent import BaseAgent
<<<<<<< HEAD
except ImportError as exc:
=======
except ImportError as exc:  # pragma: no cover
>>>>>>> origin/main
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
