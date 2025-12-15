"""
MCP Context Manager - Core Context Protocol Implementation

This module implements the Model Context Protocol (MCP) context management system,
providing structured context sharing across all UVAI components.

Key Responsibilities:
- Context lifecycle management (create, update, destroy)
- Context persistence and recovery
- Context validation and integrity
- Cross-component context sharing
- Context metadata management
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from pydantic import BaseModel, Field, validator

# Configure logging
logger = logging.getLogger(__name__)


class ContextStatus(Enum):
    """MCP Context Status Enumeration"""

    ACTIVE = "active"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ContextPriority(Enum):
    """Context Priority Levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MCPContext(BaseModel):
    """
    MCP Context Model - Core context data structure

    Represents a single context instance in the MCP system with full
    lifecycle management and validation.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user: str = Field(..., description="User or system identifier")
    task: str = Field(..., description="Task or operation identifier")
    intent: str = Field(..., description="User intent or goal")
    env: str = Field(default="development", description="Environment context")
    code_state: Dict[str, Any] = Field(
        default_factory=dict, description="Code/file state"
    )

    # Optional context fields
    subtask: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # System fields
    status: ContextStatus = Field(default=ContextStatus.ACTIVE)
    priority: ContextPriority = Field(default=ContextPriority.NORMAL)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    checksum: Optional[str] = None

    @validator("expires_at", always=True)
    def set_default_expiry(cls, value):
        """Set default expiration to 24 hours from creation"""
        return value or (datetime.utcnow() + timedelta(hours=24))

    def update_checksum(self) -> None:
        """Update context checksum for integrity validation"""
        context_dict = self.dict(exclude={"checksum", "updated_at"})
        context_str = json.dumps(context_dict, sort_keys=True, default=str)
        self.checksum = hashlib.sha256(context_str.encode()).hexdigest()

    def validate_integrity(self) -> bool:
        """Validate context integrity using checksum"""
        if not self.checksum:
            return False

        current_dict = self.dict(exclude={"checksum", "updated_at"})
        current_str = json.dumps(current_dict, sort_keys=True, default=str)
        current_checksum = hashlib.sha256(current_str.encode()).hexdigest()

        return current_checksum == self.checksum

    def add_history_entry(self, action: str, details: Dict[str, Any]) -> None:
        """Add an entry to the context history"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details,
        }
        self.history.append(entry)
        self.updated_at = datetime.utcnow()
        self.update_checksum()

    def update_status(
        self, status: ContextStatus, reason: Optional[str] = None
    ) -> None:
        """Update context status with optional reason"""
        old_status = self.status
        self.status = status
        self.updated_at = datetime.utcnow()

        if reason:
            self.add_history_entry(
                "status_change",
                {"from": old_status.value, "to": status.value, "reason": reason},
            )
        else:
            self.add_history_entry(
                "status_change", {"from": old_status.value, "to": status.value}
            )

    def is_expired(self) -> bool:
        """Check if context has expired"""
        return datetime.utcnow() > self.expires_at

    def extend_expiry(self, hours: int = 24) -> None:
        """Extend context expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.add_history_entry("expiry_extended", {"hours": hours})


class MCPContextManager:
    """
    MCP Context Manager - Central context lifecycle management

    Manages the complete lifecycle of MCP contexts across the system,
    providing persistence, recovery, and coordination capabilities.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the MCP Context Manager

        Args:
            storage_path: Optional path for context persistence
        """
        self.storage_path = storage_path or "./data/mcp_contexts/"
        self.active_contexts: Dict[str, MCPContext] = {}
        self.context_cache: Dict[str, MCPContext] = {}

        # Ensure storage directory exists
        import os

        os.makedirs(self.storage_path, exist_ok=True)

        logger.info(
            f"MCP Context Manager initialized with storage: {self.storage_path}"
        )

    def create_context(
        self,
        user: str,
        task: str,
        intent: str,
        env: str = "development",
        priority: ContextPriority = ContextPriority.NORMAL,
        **kwargs,
    ) -> MCPContext:
        """
        Create a new MCP context

        Args:
            user: User or system identifier
            task: Task identifier
            intent: User intent/goal
            env: Environment context
            priority: Context priority level
            **kwargs: Additional context fields

        Returns:
            New MCPContext instance
        """
        context = MCPContext(
            user=user, task=task, intent=intent, env=env, priority=priority, **kwargs
        )

        context.update_checksum()

        # Store in active contexts
        self.active_contexts[context.id] = context

        # Persist to storage
        self._persist_context(context)

        logger.info(f"Created MCP context: {context.id} for task: {task}")

        return context

    def get_context(self, context_id: str) -> Optional[MCPContext]:
        """
        Retrieve a context by ID

        Args:
            context_id: Context identifier

        Returns:
            MCPContext if found, None otherwise
        """
        # Check active contexts first
        if context_id in self.active_contexts:
            return self.active_contexts[context_id]

        # Check cache
        if context_id in self.context_cache:
            return self.context_cache[context_id]

        # Try to load from storage
        context = self._load_context(context_id)
        if context:
            self.context_cache[context_id] = context
            return context

        return None

    def update_context(
        self, context_id: str, updates: Dict[str, Any]
    ) -> Optional[MCPContext]:
        """
        Update an existing context

        Args:
            context_id: Context identifier
            updates: Fields to update

        Returns:
            Updated context if successful, None if not found
        """
        context = self.get_context(context_id)
        if not context:
            logger.warning(f"Context not found for update: {context_id}")
            return None

        # Update context fields
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)

        context.updated_at = datetime.utcnow()
        context.update_checksum()

        # Update active contexts if present
        if context_id in self.active_contexts:
            self.active_contexts[context_id] = context

        # Persist changes
        self._persist_context(context)

        logger.info(f"Updated context: {context_id}")

        return context

    def delete_context(self, context_id: str) -> bool:
        """
        Delete a context

        Args:
            context_id: Context identifier

        Returns:
            True if deleted, False if not found
        """
        context = self.get_context(context_id)
        if not context:
            return False

        # Remove from active contexts
        if context_id in self.active_contexts:
            del self.active_contexts[context_id]

        # Remove from cache
        if context_id in self.context_cache:
            del self.context_cache[context_id]

        # Remove from storage
        self._delete_persisted_context(context_id)

        logger.info(f"Deleted context: {context_id}")

        return True

    def list_contexts(
        self,
        user: Optional[str] = None,
        status: Optional[ContextStatus] = None,
        limit: int = 50,
    ) -> List[MCPContext]:
        """
        List contexts with optional filtering

        Args:
            user: Filter by user
            status: Filter by status
            limit: Maximum number of contexts to return

        Returns:
            List of matching contexts
        """
        contexts = list(self.active_contexts.values())

        # Apply filters
        if user:
            contexts = [c for c in contexts if c.user == user]
        if status:
            contexts = [c for c in contexts if c.status == status]

        # Sort by creation time (newest first)
        contexts.sort(key=lambda c: c.created_at, reverse=True)

        return contexts[:limit]

    def cleanup_expired_contexts(self) -> int:
        """
        Clean up expired contexts

        Returns:
            Number of contexts cleaned up
        """
        expired_ids = []
        for context_id, context in self.active_contexts.items():
            if context.is_expired():
                expired_ids.append(context_id)

        for context_id in expired_ids:
            context = self.active_contexts[context_id]
            context.update_status(ContextStatus.EXPIRED, "Expired by cleanup")
            self.delete_context(context_id)

        logger.info(f"Cleaned up {len(expired_ids)} expired contexts")

        return len(expired_ids)

    def _persist_context(self, context: MCPContext) -> None:
        """Persist context to storage"""
        try:
            import os

            file_path = os.path.join(self.storage_path, f"{context.id}.json")

            with open(file_path, "w") as f:
                json.dump(context.dict(), f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to persist context {context.id}: {e}")

    def _load_context(self, context_id: str) -> Optional[MCPContext]:
        """Load context from storage"""
        try:
            import os

            file_path = os.path.join(self.storage_path, f"{context_id}.json")

            if not os.path.exists(file_path):
                return None

            with open(file_path, "r") as f:
                data = json.load(f)

            context = MCPContext(**data)
            return context

        except Exception as e:
            logger.error(f"Failed to load context {context_id}: {e}")
            return None

    def _delete_persisted_context(self, context_id: str) -> None:
        """Delete persisted context"""
        try:
            import os

            file_path = os.path.join(self.storage_path, f"{context_id}.json")

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            logger.error(f"Failed to delete persisted context {context_id}: {e}")


# Global context manager instance
_context_manager = None


def get_context_manager() -> MCPContextManager:
    """Get the global MCP context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = MCPContextManager()
    return _context_manager


def create_context(*args, **kwargs) -> MCPContext:
    """Convenience function to create a new context"""
    return get_context_manager().create_context(*args, **kwargs)


def get_context(context_id: str) -> Optional[MCPContext]:
    """Convenience function to get a context"""
    return get_context_manager().get_context(context_id)
