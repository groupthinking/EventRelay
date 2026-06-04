"""SC4 — derived artifacts (summary, tasks, insights).

Pure functions over transcript + events. Port the *prompt content* of the three
legacy Gemini agents here as data — not the agent orchestration classes.
"""
from __future__ import annotations

from ..api.v1.schemas import Artifacts
from ..domain.events import Event


async def derive_artifacts(transcript: str, events: list[Event]) -> Artifacts:
    """Produce summary + tasks + insights.

    Acceptance test (SC4): golden transcript -> non-empty summary, >=1 typed
    task, insights validating against schema.
    """
    raise NotImplementedError(
        "SC4 artifact derivation not yet ported — see docs/PORTING_PARAMETERS.md"
    )
