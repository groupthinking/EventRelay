import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


class EventPayload(BaseModel):
    """
    Generic event payload model.
    Accepts arbitrary fields with 'type' being a key field for filtering.
    """

    type: str = Field(..., description="The type of the event, e.g., 'user_login'")
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Event data payload"
    )
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="Event timestamp"
    )

    class Config:
        extra = "allow"  # Allow other fields


@router.post("/", status_code=200)
async def ingest_event(event: EventPayload):
    """
    Accepts incoming events, filters them, and processes valid ones.
    """
    try:
        # 1. Log receipt
        event_logger.info(f"Received event: {event.dict()}")

        # 2. Filter
        # For this requirement: "only process events where the 'type' field is 'user_login'"
        ACCEPTED_TYPES = {"user_login"}

        if event.type not in ACCEPTED_TYPES:
            msg = f"Event type '{event.type}' ignored. Filter matched only: {ACCEPTED_TYPES}"
            event_logger.info(msg)
            return {"status": "ignored", "message": msg}

        # 3. Process (Single Handler)
        # "process them through a single handler, and output the result"
        # "Use a simple JSON payload for events and a console logger for output."
        process_event(event)

        return {"status": "processed", "type": event.type}

    except Exception as e:
        # 4. Error Handling & Logging
        # "Log any exceptions ... to a separate log file."
        import traceback

        error_details = traceback.format_exc()
        event_logger.error(f"Error processing event: {str(e)}\n{error_details}")

        # We might want to return 500, but often event ingestion endpoints return 200 to acknowledge receipt
        # unless it's a client error. I'll return 500 to signal failure to the caller.
        raise HTTPException(
            status_code=500, detail="Internal Server Error processing event"
        )


def process_event(event: EventPayload):
    """
    The single handler that processes the event.
    Outputs the result to console logger.
    """
    # Console output as requested
    print(f"[{datetime.now()}] PROCESSING EVENT: Type={event.type}, Data={event.data}")
    # Simulating some logic
    if event.type == "user_login":
        user_id = event.data.get("user_id", "unknown")
        print(f"User {user_id} logged in successfully.")
