#!/usr/bin/env python3
"""
Event Classification Taxonomy

Defines the 4-type event classification system used across EventRelay.
Events extracted from videos are classified into one of these types
during extraction (not post-processing), enabling filtered views,
color-coded displays, and smarter routing.

    ACTION — Concrete step the viewer should take ("Install Docker", "Run the build")
    TOPIC  — Subject or concept discussed ("Kubernetes architecture", "OAuth flow")
    CODE   — Code snippet, command, or technical artifact ("git clone ...", "npm install")
    ALERT  — Warning, caveat, or risk ("Don't use in production", "Deprecated API")
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Classified event types for video extraction."""

    ACTION = "action"
    TOPIC = "topic"
    CODE = "code"
    ALERT = "alert"


# Visual metadata for each event type (used by both backend and frontend)
EVENT_TYPE_METADATA = {
    EventType.ACTION: {
        "color": "#3b82f6",      # blue
        "bg": "rgba(59, 130, 246, 0.1)",
        "icon": "⚡",
        "label": "Action",
        "description": "Concrete step the viewer should take",
    },
    EventType.TOPIC: {
        "color": "#a855f7",      # purple
        "bg": "rgba(168, 85, 247, 0.1)",
        "icon": "📌",
        "label": "Topic",
        "description": "Subject or concept discussed",
    },
    EventType.CODE: {
        "color": "#22c55e",      # green
        "bg": "rgba(34, 197, 94, 0.1)",
        "icon": "💻",
        "label": "Code",
        "description": "Code snippet, command, or technical artifact",
    },
    EventType.ALERT: {
        "color": "#ef4444",      # red
        "bg": "rgba(239, 68, 68, 0.1)",
        "icon": "⚠️",
        "label": "Alert",
        "description": "Warning, caveat, or risk",
    },
}


class ClassifiedEvent(BaseModel):
    """A video event classified with the 4-type taxonomy."""

    id: str
    type: EventType
    title: str
    description: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Optional[str] = Field(
        None,
        description="For ALERT type: low, medium, high, critical",
    )
    source_segment: Optional[str] = Field(
        None,
        description="The transcript segment this event was extracted from",
    )


def classify_event_type(text: str) -> EventType:
    """
    Heuristic classification of an event based on its text content.
    Used as a fallback when AI classification is unavailable.

    This is a lightweight classifier — the primary classification happens
    in the extraction prompts sent to the AI model.
    """
    text_lower = text.lower()

    # Code indicators
    code_indicators = [
        "```", "import ", "npm ", "pip ", "git ", "docker ",
        "curl ", "wget ", "sudo ", "apt ", "brew ", "./",
        "mkdir ", "cd ", "ls ", "cat ", "echo ",
    ]
    if any(indicator in text_lower for indicator in code_indicators):
        return EventType.CODE

    # Alert indicators
    alert_indicators = [
        "warning", "caution", "don't", "do not", "avoid",
        "deprecated", "breaking change", "security", "vulnerability",
        "risk", "careful", "bug", "issue", "problem",
    ]
    if any(indicator in text_lower for indicator in alert_indicators):
        return EventType.ALERT

    # Action indicators (imperative verbs at start)
    action_starters = [
        "install", "create", "build", "deploy", "run", "configure",
        "setup", "set up", "implement", "add", "remove", "update",
        "test", "write", "download", "open", "navigate", "click",
        "start", "stop", "enable", "disable",
    ]
    first_word = text_lower.split()[0] if text_lower.split() else ""
    if first_word in action_starters:
        return EventType.ACTION

    # Default to topic
    return EventType.TOPIC


# Mapping from legacy types to new taxonomy
LEGACY_TYPE_MAP = {
    "action": EventType.ACTION,
    "mention": EventType.TOPIC,    # 'mention' maps to TOPIC
    "topic": EventType.TOPIC,
    "insight": EventType.ALERT,    # 'insight' maps closest to ALERT
    "code": EventType.CODE,
    "alert": EventType.ALERT,
}


def migrate_legacy_type(legacy_type: str) -> EventType:
    """Convert legacy event type strings to the new taxonomy."""
    return LEGACY_TYPE_MAP.get(legacy_type.lower(), EventType.TOPIC)
