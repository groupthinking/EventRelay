"""Agent entry points exposed at the repository root.

The legacy test harness expects ``process_video_with_mcp`` to live under the
``agents`` namespace, so we keep the package lightweight and re-export the
modern implementation.
"""

from __future__ import annotations


__all__ = []

try:
    from .gemini_video_master_agent import GeminiVideoMasterAgent

    __all__.append("GeminiVideoMasterAgent")
except ImportError:
    pass

try:
    from .grok4_video_subagent import Grok4VideoSubagent

    __all__.append("Grok4VideoSubagent")
except ImportError:
    pass

try:
    from .mcp_agent_network import MCPAgentNetwork, get_agent_network

    __all__.extend(["MCPAgentNetwork", "get_agent_network"])
except ImportError:
    pass

try:
    from .mcp_enhanced_video_processor import MCPEnhancedVideoProcessor

    __all__.append("MCPEnhancedVideoProcessor")
except ImportError:
    pass

try:
    from .multi_llm_video_processor import MultiLLMVideoProcessor

    __all__.append("MultiLLMVideoProcessor")
except ImportError:
    pass

try:
    from .openai_dev_task_manager import OpenAIDevTaskManager

    __all__.append("OpenAIDevTaskManager")
except ImportError:
    pass

try:
    from .pipeline_orchestrator import VideoPipelineOrchestrator

    __all__.append("VideoPipelineOrchestrator")
except ImportError:
    pass

try:
    from .process_video_with_mcp import RealVideoProcessor, SimulationDetectionError

    __all__.extend(["RealVideoProcessor", "SimulationDetectionError"])
except ImportError:
    pass

try:
    from .skill_monitor_emitter import get_emitter

    __all__.append("get_emitter")
except ImportError:
    pass
