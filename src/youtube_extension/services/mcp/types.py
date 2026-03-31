"""
MCP Types - Unified type definitions for MCP services

Provides consistent type definitions across all MCP components.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class ServerStatus(str, Enum):
    """MCP Server Status"""

    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MCPCapability(str, Enum):
    """MCP Server Capabilities"""

    # Video Processing
    VIDEO_TRANSCRIPTION = "video_transcription"
    VIDEO_ANALYSIS = "video_analysis"
    VIDEO_PROCESSING = "video_processing"

    # AI & Analysis
    AI_INFERENCE = "ai_inference"
    AI_REASONING = "ai_reasoning"
    SEMANTIC_SEARCH = "semantic_search"

    # Data Processing
    DATA_PROCESSING = "data_processing"
    TEXT_EXTRACTION = "text_extraction"
    EVENT_EXTRACTION = "event_extraction"

    # System Operations
    FILE_OPERATIONS = "file_operations"
    CONTEXT_MANAGEMENT = "context_management"
    STATE_COORDINATION = "state_coordination"

    # Networking & Integration
    NETWORKING = "networking"
    API_PROXY = "api_proxy"
    MONITORING = "monitoring"


class MCPTaskStatus(str, Enum):
    """MCP Task Status"""

    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MCPServerConfig(BaseModel):
    """MCP Server Configuration"""

    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Human-readable server name")
    endpoint: str = Field(..., description="Server endpoint URL (must start with http:// or https://)")
    capabilities: list[MCPCapability] = Field(
        default_factory=list, description="Server capabilities"
    )

    # Connection details
    protocol: str = Field(default="http", description="Communication protocol")
    port: Optional[int] = Field(default=None, description="Server port", ge=1, le=65535)
    auth_token: Optional[str] = Field(default=None, description="Authentication token")

    # Health monitoring
    health_check_interval: int = Field(
        default=30, ge=1, description="Health check interval in seconds"
    )
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")

    # Priority and load
    priority: int = Field(
        default=3, ge=1, le=5, description="Server priority (1=critical, 5=low)"
    )
    max_concurrent_tasks: int = Field(
        default=10, ge=1, description="Maximum concurrent tasks"
    )

    # Metadata
    version: str = Field(default="1.0.0", description="Server version")
    tags: list[str] = Field(default_factory=list, description="Server tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @model_validator(mode="after")
    def validate_endpoint_scheme(self) -> "MCPServerConfig":
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                f"endpoint must be a valid http:// or https:// URL, got: {self.endpoint!r}"
            )
        return self


class MCPTask(BaseModel):
    """MCP Task Definition"""

    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Task type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Task payload")
    requirements: list[MCPCapability] = Field(
        default_factory=list, description="Required capabilities"
    )

    # Execution details
    priority: int = Field(
        default=3, ge=1, le=5, description="Task priority (1=critical, 5=low)"
    )
    timeout: int = Field(default=300, description="Task timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")

    # Status tracking
    status: MCPTaskStatus = Field(
        default=MCPTaskStatus.PENDING, description="Task status"
    )
    assigned_server: Optional[str] = Field(
        default=None, description="Assigned server ID"
    )
    result: Optional[dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list, description="Task dependencies (other task IDs)"
    )
    depends_on_completion: bool = Field(
        default=True, description="Must wait for dependencies to complete"
    )


class MCPServerState(BaseModel):
    """MCP Server Runtime State"""

    server_id: str
    status: ServerStatus
    current_tasks: int = Field(default=0, description="Number of active tasks")
    total_tasks_completed: int = Field(
        default=0, description="Total tasks completed"
    )
    total_tasks_failed: int = Field(default=0, description="Total tasks failed")

    # Performance metrics
    average_response_time: float = Field(
        default=0.0, description="Average response time in seconds"
    )
    load_factor: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Current load (0.0-1.0)"
    )
    error_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Error rate (0.0-1.0)"
    )

    # Health tracking
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = Field(
        default=0, description="Consecutive health check failures"
    )
    uptime_seconds: int = Field(default=0, description="Server uptime in seconds")
    last_online_time: Optional[datetime] = Field(
        default=None, description="Timestamp when server last came online"
    )

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
