"""Domain model: events and the event taxonomy (SC3).

The taxonomy `<domain>.<entity>.<action>` is the salvageable spine asset —
the 10 SQLAlchemy platform tables built around it are not ported.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

# Three lowercase, snake-friendly segments: e.g. "youtube.video.captured".
EVENT_NAME_RE = re.compile(
    r"^[a-z0-9]+(?:_[a-z0-9]+)*"
    r"\.[a-z0-9]+(?:_[a-z0-9]+)*"
    r"\.[a-z0-9]+(?:_[a-z0-9]+)*$"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """A typed, schema-validated event extracted from a transcript (SC3)."""

    type: str = Field(description="Event name as <domain>.<entity>.<action>")
    ts: datetime = Field(default_factory=_utcnow)
    payload: dict = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not EVENT_NAME_RE.match(v):
            raise ValueError(
                f"event type {v!r} must match <domain>.<entity>.<action> "
                "(lowercase, dot-separated)"
            )
        return v
