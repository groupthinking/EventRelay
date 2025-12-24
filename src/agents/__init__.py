"""Agent entry points exposed at the repository root.

The legacy test harness expects ``process_video_with_mcp`` to live under the
``agents`` namespace, so we keep the package lightweight and re-export the
modern implementation.
"""

from .process_video_with_mcp import RealVideoProcessor, SimulationDetectionError

# Export consolidated agents
from .gemini_video_master_agent import GeminiVideoMasterAgent
from .grok4_video_subagent import Grok4VideoSubagent
from .mcp_enhanced_video_processor import MCPEnhancedVideoProcessor
from .multi_llm_video_processor import MultiLLMVideoProcessor
from .openai_dev_task_manager import OpenAIDevTaskManager

__all__ = [
    "RealVideoProcessor", 
    "SimulationDetectionError",
    "GeminiVideoMasterAgent",
    "Grok4VideoSubagent",
    "MCPEnhancedVideoProcessor",
    "MultiLLMVideoProcessor",
    "OpenAIDevTaskManager"
]

