from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class AgentRequest(BaseModel):
    task: str
    params: Dict[str, Any] = {}
    video_pack_id: Optional[str] = None

class AgentResult(BaseModel):
    status: str  # "ok"|"error"
    output: Dict[str, Any] = {}
    logs: List[str] = []
