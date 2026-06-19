"""SC3 — typed event extraction.

Pure function over (transcript, model seam) -> list[Event]. Every returned
event is validated against the taxonomy at construction (domain/events.py); a
malformed event raises and the runner records the job as failed rather than
emitting an untyped event.
"""
from __future__ import annotations

import logging

from ..domain.events import Event
from ..llm.base import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You extract structured events from a video transcript. "
    "Each event name MUST be lowercase and of the form <domain>.<entity>.<action> "
    "(three dot-separated segments), e.g. youtube.video.captured. "
    "Return only events that are clearly supported by the transcript."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["type"],
            },
        }
    },
    "required": ["events"],
}


def _prompt(transcript: str) -> str:
    """
    Builds the LLM user prompt by embedding the transcript and instructing the model to extract events.
    
    Parameters:
        transcript (str): The transcript text to include in the prompt.
    
    Returns:
        str: A formatted prompt containing the transcript followed by an instruction to extract events.
    """
    return f"Transcript:\n\n{transcript}\n\nExtract the events."


async def extract_events(transcript: str, llm: LLMClient) -> list[Event]:
    """
    Extracts typed Event objects from a transcript by calling the provided LLM with a JSON schema.
    
    Parameters:
    	transcript (str): Transcript text to extract events from.
    	llm (LLMClient): LLM client used to generate schema-constrained JSON (omitted for services in param docs only when not necessary, included here for clarity).
    
    Returns:
    	events (list[Event]): List of extracted Event instances; each event has a `type` string and a `payload` dict (defaults to an empty dict if absent).
    """
    logger.info("extract_events: calling LLMClient", extra={"transcript_length": len(transcript)})
    try:
        data = await llm.generate_json(system=_SYSTEM, prompt=_prompt(transcript), schema=_SCHEMA)
        raw = data.get("events", [])
        events = [Event(type=item["type"], payload=item.get("payload", {})) for item in raw]
        event_types = [e.type for e in events]
        logger.info(
            "extract_events: events extracted",
            extra={"transcript_length": len(transcript), "event_count": len(events), "event_types": event_types},
        )
        return events
    except Exception as exc:
        logger.error(
            "extract_events: failed",
            extra={"transcript_length": len(transcript), "error": str(exc)},
            exc_info=True,
        )
        raise
