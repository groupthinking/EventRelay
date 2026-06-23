"""SC4 — derived artifacts (summary, tasks, insights).

Pure function over (transcript, events, model seam) -> Artifacts. The legacy
three-Gemini-agent orchestration is reduced to one structured call; the agents'
prompt intent is carried as data here, not as orchestration classes.
"""

from __future__ import annotations

import logging

from ..api.v1.schemas import Artifacts
from ..domain.events import Event
from ..llm.base import LLMClient

logger = logging.getLogger(__name__)

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


async def derive_artifacts(
    transcript: str, events: list[Event], llm: LLMClient
) -> Artifacts:
    logger.info(
        "derive_artifacts: calling LLMClient",
        extra={"transcript_length": len(transcript), "event_count": len(events)},
    )
    try:
        data = await llm.generate_json(
            system=_SYSTEM, prompt=_prompt(transcript, events), schema=_SCHEMA
        )
        summary_length = len(data.get("summary", ""))
        tasks_count = len(data.get("tasks", []))
        insights_count = len(data.get("insights", {}))
        logger.info(
            "derive_artifacts: Artifacts generated",
            extra={
                "summary_length": summary_length,
                "tasks_count": tasks_count,
                "insights_count": insights_count,
            },
        )
        return Artifacts(
            summary=data["summary"],
            tasks=list(data.get("tasks", [])),
            insights=dict(data.get("insights", {})),
        )
    except Exception as exc:
        logger.error(
            "derive_artifacts: failed",
            extra={
                "transcript_length": len(transcript),
                "event_count": len(events),
                "error": str(exc),
            },
            exc_info=True,
        )
        raise
