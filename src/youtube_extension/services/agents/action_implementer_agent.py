#!/usr/bin/env python3
"""
Compatibility shim for the Action Implementer agent (F4).

Canonical implementation:
``youtube_extension.services.agents.adapters.action_implementer_agent``.

There is only one registered agent class. Do not import
``src.agents.action_implementer.ActionImplementer`` for orchestrator work —
that module is the offline plan builder only.
"""

from .adapters.action_implementer_agent import (
    ActionImplementerAgent,
    ActionPlan,
)

__all__ = [
    "ActionImplementerAgent",
    "ActionPlan",
]
