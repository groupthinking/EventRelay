"""MCP Base Context and Utilities"""

from typing import Dict, Any, List
from datetime import datetime


class MCPContext:
    """Model Context Protocol Context Object"""
    
    def __init__(self):
        self.task = {}
        self.intent = {}
        self.env = {}
        self.history = []
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "intent": self.intent,
            "env": self.env,
            "history": self.history,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPContext":
        context = cls()
        context.task = data.get("task", {})
        context.intent = data.get("intent", {})
        context.env = data.get("env", {})
        context.history = data.get("history", [])
        context.timestamp = data.get("timestamp", context.timestamp)
        return context
