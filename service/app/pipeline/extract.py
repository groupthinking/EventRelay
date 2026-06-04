"""SC3 — typed event extraction.

Pure function: transcript -> list[Event]. Events are validated against the
taxonomy at construction time (domain/events.py). The agent frameworks and MCP
implementations are NOT required to satisfy this criterion.
"""
from __future__ import annotations

from ..domain.events import Event


async def extract_events(transcript: str) -> list[Event]:
    """Extract schema-validated <domain>.<entity>.<action> events.

    Acceptance test (SC3): golden transcript -> expected event set; every event
    validates against the taxonomy regex.
    """
    raise NotImplementedError(
        "SC3 event extraction not yet ported — see docs/PORTING_PARAMETERS.md"
    )
