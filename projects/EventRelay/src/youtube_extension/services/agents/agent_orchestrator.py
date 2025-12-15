#!/usr/bin/env python3
"""
Compatibility shim for the AgentOrchestrator.

Delegates to ``services.agents.adapters.agent_orchestrator`` so legacy imports
resolve to the modern implementation.
"""

from src.youtube_extension.services.agents.adapters.agent_orchestrator import (
    AgentOrchestrator,
)

__all__ = ["AgentOrchestrator"]
