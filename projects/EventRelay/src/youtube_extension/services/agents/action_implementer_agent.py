#!/usr/bin/env python3
"""
Compatibility shim for the Action Implementer agent.

The refactored implementation resides in
``src.youtube_extension.services.agents.adapters.action_implementer_agent``.
This module simply re-exports the public class so older imports remain valid.
"""

from src.youtube_extension.services.agents.adapters.action_implementer_agent import (
    ActionImplementerAgent,
    ActionPlan,
)

__all__ = [
    "ActionImplementerAgent",
    "ActionPlan",
]
