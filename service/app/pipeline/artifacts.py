"""SC4 — derived artifacts (summary, tasks, insights).

Pure function over (transcript, events, model seam) -> Artifacts. The legacy
three-Gemini-agent orchestration is reduced to one structured call; the agents'
prompt intent is carried as data here, not as orchestration classes.
"""
from __future__ import annotations

from ..api.v1.schemas import Artifacts
from ..domain.events import Event
from ..llm.base import LLMClient

_SYSTEM = (
    "You turn a video transcript and its extracted events into actionable output. "
    "Produce a concise summary, a list of concrete tasks a viewer could act on, "
    "and an insights object with any strategic observations."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "tasks": {"type": "array", "items": {"type": "string"}},
        "insights": {"type": "object"},
    },
    "required": ["summary"],
}


def _prompt(transcript: str, events: list[Event]) -> str:
    event_lines = "\n".join(f"- {e.type}" for e in events) or "(none)"
    return f"Transcript:\n\n{transcript}\n\nExtracted events:\n{event_lines}\n\nProduce the artifacts."


async def derive_artifacts(transcript: str, events: list[Event], llm: LLMClient) -> Artifacts:
    data = await llm.generate_json(
        system=_SYSTEM, prompt=_prompt(transcript, events), schema=_SCHEMA
    )
    return Artifacts(
        summary=data["summary"],
        tasks=list(data.get("tasks", [])),
        insights=dict(data.get("insights", {})),
    )
