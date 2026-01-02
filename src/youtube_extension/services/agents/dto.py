from typing import Any, Optional

from pydantic import BaseModel


class AgentRequest(BaseModel):
    task: str
    params: dict[str, Any] = {}
    video_pack_id: Optional[str] = None

class AgentResult(BaseModel):
    status: str  # "ok"|"error"
    output: dict[str, Any] = {}
    logs: list[str] = []
