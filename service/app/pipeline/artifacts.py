"""SC4 — derived artifacts (summary, tasks, insights).

Pure functions over transcript + events. Port the *prompt content* of the three
legacy Gemini agents here as data — not the agent orchestration classes.
"""
from __future__ import annotations

from ..api.v1.schemas import Artifacts
from ..domain.events import Event


async def derive_artifacts(transcript: str, events: list[Event]) -> Artifacts:
    """
    Derive a summary, a set of typed tasks, and insights from a conversation transcript and its events.
    
    Parameters:
        transcript (str): Full conversation transcript to analyze.
        events (list[Event]): Chronological events related to the transcript used to inform derivation.
    
    Returns:
        Artifacts: An object containing a non-empty summary, one or more typed tasks, and insights that conform to the Artifacts schema.
    
    Raises:
        NotImplementedError: If the SC4 artifact derivation has not been implemented.
    """
    raise NotImplementedError(
        "SC4 artifact derivation not yet ported — see docs/PORTING_PARAMETERS.md"
    )
