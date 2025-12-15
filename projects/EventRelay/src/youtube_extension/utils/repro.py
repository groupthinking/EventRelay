import os
import uuid
from typing import Dict, Optional


def get_repro_id(default: Optional[str] = None) -> str:
    """Return the repro-id.

    Order of precedence:
    1) REPRO_ID environment variable
    2) provided default value
    3) generated uuid4
    """
    env_value = os.getenv("REPRO_ID")
    if env_value and env_value.strip():
        return env_value.strip()
    if default and default.strip():
        return default.strip()
    return str(uuid.uuid4())


def attach_repro_id_to_payload(payload: Dict[str, object], repro_id: Optional[str] = None) -> Dict[str, object]:
    """Return a copy of payload including a 'repro-id' field.

    If repro_id is not provided, it is resolved via get_repro_id().
    """
    resolved = repro_id or get_repro_id()
    merged: Dict[str, object] = dict(payload)
    merged["repro-id"] = resolved
    return merged
