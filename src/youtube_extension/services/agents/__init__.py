"""
AI Agent Services
=================

Extracted AI agent services with clean APIs and proper dependency injection.
Provides specialized AI agents for different video processing tasks.
"""

try:
    from .adapters.action_implementer_agent import ActionImplementerAgent
except ImportError:
    ActionImplementerAgent = None

try:
    from .adapters.agent_orchestrator import AgentOrchestrator
except ImportError:
    AgentOrchestrator = None

try:
    from .adapters.hybrid_vision_agent import HybridVisionAgent
except ImportError:
    HybridVisionAgent = None

try:
    from .adapters.personality_agent import PersonalityAgent
except ImportError:
    PersonalityAgent = None

try:
    from .adapters.strategy_agent import StrategyAgent
except ImportError:
    StrategyAgent = None

try:
    from .adapters.transcript_action_agent import TranscriptActionAgent
except ImportError:
    TranscriptActionAgent = None

try:
    from .adapters.video_master_agent import VideoMasterAgent
except ImportError:
    VideoMasterAgent = None

try:
    from .base_agent import BaseAgent
except ImportError:
    BaseAgent = None

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
