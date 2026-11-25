"""
Inter-Agent Handoff Protocol for EventRelay.
Provides strongly-typed handoff envelopes, lineage tracking, and delivery validation.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class AgentHandoffEnvelope(BaseModel):
    """
    Standardized inter-agent handoff envelope carrying task context,
    state payloads, and lineage trace across agent handoffs.
    """

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_agent: str
    recipient_agent: str
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)
    lineage: list[str] = Field(default_factory=list)
    contract_version: str = "1.0.0"
    created_at: float = Field(default_factory=time.time)
    acknowledged: bool = False

    def forward(self, next_recipient: str, next_intent: str, updated_payload: dict[str, Any] | None = None) -> AgentHandoffEnvelope:
        """Forward envelope to the next agent in the execution graph, updating lineage."""
        new_lineage = list(self.lineage)
        if self.recipient_agent and self.recipient_agent not in new_lineage:
            new_lineage.append(self.recipient_agent)

        merged_payload = dict(self.payload)
        if updated_payload:
            merged_payload.update(updated_payload)

        return AgentHandoffEnvelope(
            trace_id=self.trace_id,
            sender_agent=self.recipient_agent,
            recipient_agent=next_recipient,
            intent=next_intent,
            payload=merged_payload,
            lineage=new_lineage,
            contract_version=self.contract_version,
            created_at=time.time(),
            acknowledged=False,
        )

    def acknowledge(self) -> None:
        """Acknowledge receipt and acceptance of handoff by target agent."""
        self.acknowledged = True
