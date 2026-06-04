"""SC3 — typed event extraction.

Pure function: transcript -> list[Event]. Events are validated against the
taxonomy at construction time (domain/events.py). The agent frameworks and MCP
implementations are NOT required to satisfy this criterion.
"""
from __future__ import annotations

from ..domain.events import Event


async def extract_events(transcript: str) -> list[Event]:
    """
    Extract schema-validated events in the form `<domain>.<entity>.<action>` from a transcript.
    
    Each returned Event must validate against the event taxonomy's regex; as an acceptance test, a golden transcript should produce the expected event set with every event matching the taxonomy.
    
    Parameters:
        transcript (str): Raw transcript text to extract events from.
    
    Returns:
        list[Event]: A list of validated events extracted from the transcript.
    
    Raises:
        NotImplementedError: Extraction is not implemented in this module (see docs/PORTING_PARAMETERS.md).
    """
    raise NotImplementedError(
        "SC3 event extraction not yet ported — see docs/PORTING_PARAMETERS.md"
    )
