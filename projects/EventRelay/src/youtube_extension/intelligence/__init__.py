"""
UVAI Intelligence Layer

This module contains advanced AI capabilities and specialized intelligence components.
All AI operations are modular, interchangeable, and integrate through the MCP protocol.

Available Intelligence Components:
- Gemini: Cloud AI capabilities and complex analysis
- Agents: Specialized AI agents for medical, surveillance, content analysis
- Multi-Modal: Unified processing for video, image, and text content

Architecture:
- Modular AI components with clean interfaces
- Intelligent routing between local and cloud processing
- Performance optimization for different hardware platforms
- Comprehensive error handling and fallback mechanisms
"""

from .gemini import GeminiProcessor
from .agents import SpecializedAgentRegistry
from .multimodal import MultiModalProcessor

__all__ = [
    "GeminiProcessor",
    "SpecializedAgentRegistry",
    "MultiModalProcessor"
]
