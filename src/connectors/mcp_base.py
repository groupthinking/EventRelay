"""MCP Base Classes - Model Context Protocol support."""

from typing import Dict, Any, List
from datetime import datetime


class MCPContext:
    """
    Model Context Protocol context for semantic understanding.
    Provides context for agent operations and decision-making.
    """
    
    def __init__(self):
        self.task: Dict[str, Any] = {}
        self.intent: Dict[str, Any] = {}
        self.env: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "task": self.task,
            "intent": self.intent,
            "env": self.env,
            "history": self.history,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPContext":
        """Create context from dictionary."""
        context = cls()
        context.task = data.get("task", {})
        context.intent = data.get("intent", {})
        context.env = data.get("env", {})
        context.history = data.get("history", [])
        context.created_at = data.get("created_at", context.created_at)
        return context
