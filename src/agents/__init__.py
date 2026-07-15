"""Agent entry points exposed at the repository root.

The legacy test harness expects ``process_video_with_mcp`` to live under the
``agents`` namespace, so we keep the package lightweight and re-export the
modern implementation.
"""

# Export consolidated agents
from .gemini_video_master_agent import GeminiVideoMasterAgent
from .grok4_video_subagent import Grok4VideoSubagent
from .mcp_agent_network import MCPAgentNetwork, get_agent_network
from .mcp_enhanced_video_processor import MCPEnhancedVideoProcessor
from .multi_llm_video_processor import MultiLLMVideoProcessor
from .openai_dev_task_manager import OpenAIDevTaskManager
from .pipeline_orchestrator import VideoPipelineOrchestrator
from .process_video_with_mcp import RealVideoProcessor, SimulationDetectionError
from .skill_monitor_emitter import get_emitter

__all__ = [
    "RealVideoProcessor",
    "SimulationDetectionError",
    "GeminiVideoMasterAgent",
    "Grok4VideoSubagent",
    "MCPAgentNetwork",
    "MCPEnhancedVideoProcessor",
    "MultiLLMVideoProcessor",
    "OpenAIDevTaskManager",
    "VideoPipelineOrchestrator",
    "get_agent_network",
    "get_emitter",
]

