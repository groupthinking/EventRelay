import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.event_types import (
    EVENT_TYPE_METADATA,
    EventType,
    classify_event_type,
    migrate_legacy_type,
)

# Configure a separate logger for event processing
event_logger = logging.getLogger("event_relay")
event_logger.setLevel(logging.INFO)

# Use StreamHandler for Cloud Run compatibility (stdout-based logging)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
event_logger.addHandler(log_handler)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# Accepted event types for the classified taxonomy
CLASSIFIED_EVENT_TYPES = {t.value for t in EventType}

# Legacy types still accepted for backward compatibility
LEGACY_EVENT_TYPES = {"user_login", "mention", "insight"}

ACCEPTED_TYPES = CLASSIFIED_EVENT_TYPES | LEGACY_EVENT_TYPES


class EventPayload(BaseModel):
    """
    Event payload with classified type taxonomy.

    Accepts the 4-type classification (ACTION, TOPIC, CODE, ALERT)
    plus legacy types for backward compatibility.
    """

    type: str = Field(
        ...,
        description=(
            "Event type. Classified taxonomy: action, topic, code, alert. "
            "Legacy types (user_login, mention, insight) accepted for backward compat."
        ),
    )
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Event data payload"
    )
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Classification confidence score",
    )
    severity: Optional[str] = Field(
        None,
        description="For alert type: low, medium, high, critical",
    )

    class Config:
        extra = "allow"  # Allow other fields


class ClassifiedEventResponse(BaseModel):
    """Response with classified event metadata."""

    status: str
    type: str
    classified_type: str
    metadata: Dict[str, Any]


@router.post("/", status_code=200, response_model=ClassifiedEventResponse)
async def ingest_event(event: EventPayload):
    """
    Accepts incoming events, classifies them using the 4-type taxonomy,
    and processes valid ones.
    """
    try:
        event_logger.info(f"Received event: {event.dict()}")

        # Classify the event type
        if event.type in CLASSIFIED_EVENT_TYPES:
            classified_type = EventType(event.type)
        elif event.type in LEGACY_EVENT_TYPES:
            classified_type = migrate_legacy_type(event.type)
            event_logger.info(
                f"Migrated legacy type '{event.type}' → '{classified_type.value}'"
            )
        else:
            # Auto-classify from content if available
            title = (event.data or {}).get("title", "")
            if title:
                classified_type = classify_event_type(title)
                event_logger.info(
                    f"Auto-classified '{event.type}' → '{classified_type.value}' from content"
                )
            else:
                msg = f"Event type '{event.type}' not recognized. Valid: {sorted(ACCEPTED_TYPES)}"
                event_logger.info(msg)
                return ClassifiedEventResponse(
                    status="ignored",
                    type=event.type,
                    classified_type="unknown",
                    metadata={"message": msg},
                )

        # Get type metadata for response
        type_meta = EVENT_TYPE_METADATA.get(classified_type, {})

        # Process the classified event
        process_event(event, classified_type)

        return ClassifiedEventResponse(
            status="processed",
            type=event.type,
            classified_type=classified_type.value,
            metadata={
                "label": type_meta.get("label", classified_type.value),
                "color": type_meta.get("color", "#ffffff"),
                "icon": type_meta.get("icon", "📋"),
            },
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        event_logger.error(f"Error processing event: {str(e)}\n{error_details}")

        raise HTTPException(
            status_code=500, detail="Internal Server Error processing event"
        )


@router.get("/types", status_code=200)
async def list_event_types():
    """Return the event type taxonomy with metadata."""
    return {
        "types": {
            t.value: EVENT_TYPE_METADATA[t]
            for t in EventType
        }
    }


def process_event(event: EventPayload, classified_type: EventType):
    """
    Process a classified event.
    Outputs the result to console logger.
    """
    print(
        f"[{datetime.now()}] PROCESSING EVENT: "
        f"Type={classified_type.value} (original={event.type}), "
        f"Data={event.data}"
    )
    if classified_type == EventType.ACTION:
        title = (event.data or {}).get("title", "untitled")
        print(f"  → ACTION: {title}")
    elif classified_type == EventType.ALERT:
        severity = event.severity or "medium"
        print(f"  → ALERT [{severity}]: {(event.data or {}).get('title', '')}")
    elif classified_type == EventType.CODE:
        print(f"  → CODE snippet captured")
    elif classified_type == EventType.TOPIC:
        print(f"  → TOPIC logged")
