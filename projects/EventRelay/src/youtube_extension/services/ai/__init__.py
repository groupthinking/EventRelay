"""
AI Services
===========

AI processing services including local and cloud-based models.
Provides clean interfaces for multi-modal AI capabilities.
"""

from .gemini_service import GeminiService, GeminiConfig, GeminiResult
from .hybrid_processor_service import (
    HybridProcessorService,
    HybridConfig,
    HybridResult,
    ProcessingMode,
    TaskType,
    RoutingDecision,
)
from .speech_to_text_service import (
    SpeechToTextService,
    SpeechToTextConfig,
    SpeechToTextResult,
)

__all__ = [
    'GeminiService',
    'GeminiConfig',
    'GeminiResult',
    'HybridProcessorService',
    'HybridConfig',
    'HybridResult',
    'ProcessingMode',
    'TaskType',
    'RoutingDecision',
    'SpeechToTextService',
    'SpeechToTextConfig',
    'SpeechToTextResult',
]
