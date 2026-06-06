"""SC3 — typed event extraction.

Pure function over (transcript, model seam) -> list[Event]. Every returned
event is validated against the taxonomy at construction (domain/events.py); a
malformed event raises and the runner records the job as failed rather than
emitting an untyped event.
"""
from __future__ import annotations

from ..domain.events import Event
from ..llm.base import LLMClient

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
    return f"Transcript:\n\n{transcript}\n\nExtract the events."


async def extract_events(transcript: str, llm: LLMClient) -> list[Event]:
    data = await llm.generate_json(system=_SYSTEM, prompt=_prompt(transcript), schema=_SCHEMA)
    raw = data.get("events", [])
    return [Event(type=item["type"], payload=item.get("payload", {})) for item in raw]
