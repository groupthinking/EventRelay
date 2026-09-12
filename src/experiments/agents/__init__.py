"""Agent scaffolding for hypotheses h1, h2, and h3."""

from __future__ import annotations

from .base import HypothesisAgent
from .h1 import H1Agent
from .h2 import H2Agent
from .h3 import H3Agent

HYPOTHESIS_AGENTS: dict[str, type[HypothesisAgent]] = {
    "h1": H1Agent,
    "h2": H2Agent,
    "h3": H3Agent,
}

__all__ = [
    "HYPOTHESIS_AGENTS",
    "HypothesisAgent",
    "H1Agent",
    "H2Agent",
    "H3Agent",
    "build_agent",
]


def build_agent(name: str) -> HypothesisAgent:
    """Instantiate the agent for a given hypothesis identifier."""
    normalized = (name or "").strip().lower()
    if normalized not in HYPOTHESIS_AGENTS:
        raise ValueError(f"Unknown hypothesis agent: {name!r}")
    return HYPOTHESIS_AGENTS[normalized]()
