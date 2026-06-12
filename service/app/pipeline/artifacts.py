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
    """
    Builds the user prompt sent to the language model by embedding the transcript and a bullet list of extracted event types.
    
    Parameters:
        transcript (str): The raw video transcript text to include in the prompt.
        events (list[Event]): Extracted events; only each event's `type` is included as a bullet. If the list is empty, the literal "(none)" is inserted.
    
    Returns:
        prompt (str): The formatted prompt containing the transcript, the "Extracted events" section, and an instruction to produce the artifacts.
    """
    event_lines = "\n".join(f"- {e.type}" for e in events) or "(none)"
    return f"Transcript:\n\n{transcript}\n\nExtracted events:\n{event_lines}\n\nProduce the artifacts."


async def derive_artifacts(transcript: str, events: list[Event], llm: LLMClient) -> Artifacts:
    """
    Generate structured Artifacts from a video transcript and extracted event list using the provided LLM client.
    
    Parameters:
        transcript (str): Full video transcript text to summarize and analyze.
        events (list[Event]): Extracted events associated with the transcript; used to inform artifact generation.
        llm (LLMClient): Language model client used to generate and validate a JSON response against the expected schema.
    
    Returns:
        Artifacts: An Artifacts instance containing:
            - summary (str): Model-produced concise summary (required).
            - tasks (list[str]): List of concrete viewer-action tasks (empty list if absent).
            - insights (dict): Insights object with strategic observations (empty dict if absent).
    """
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
            extra={"transcript_length": len(transcript), "event_count": len(events), "error": str(exc)},
            exc_info=True,
        )
        raise
