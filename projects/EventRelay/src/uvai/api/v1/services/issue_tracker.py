#!/usr/bin/env python3
"""
Issue Tracker Service
=====================

Persistent JSON-based issue tracker with recurrence detection, severity escalation,
and optional MCP session correlation for enhanced debugging and monitoring.
"""

import json
import hashlib
import logging
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback if pydantic not available
    class BaseModel:
        pass

    def Field(default=None, description=""):
        return default

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """Issue severity levels with escalation logic"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Issue categories for classification and routing"""
    INFRASTRUCTURE = "infrastructure"
    API_ERROR = "api_error"
    PROCESSING_ERROR = "processing_error"
    MCP_ERROR = "mcp_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    NETWORK_ERROR = "network_error"
    PERFORMANCE_ERROR = "performance_error"
    SECURITY_ERROR = "security_error"
    UNKNOWN = "unknown"


class IssueStatus(Enum):
    """Issue status tracking"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class IssueRecurrencePattern(BaseModel):
    """Tracks recurrence patterns for issue escalation"""
    first_occurrence: str
    occurrence_count: int = Field(default=1, description="Number of times this issue has occurred")
    last_occurrence: str
    average_interval_hours: float = Field(default=0.0, description="Average hours between occurrences")
    peak_hour: Optional[int] = Field(default=None, description="Hour of day when issue most frequently occurs")
    affected_components: List[str] = Field(default_factory=list, description="Components affected by this issue")


class MCPContext(BaseModel):
    """MCP session correlation context"""
    session_id: Optional[str] = Field(default=None, description="MCP session ID")
    provider: Optional[str] = Field(default=None, description="MCP provider used")
    operation: Optional[str] = Field(default=None, description="MCP operation being performed")
    correlation_id: Optional[str] = Field(default=None, description="MCP correlation ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional MCP context")


class IssueEntry(BaseModel):
    """Comprehensive issue tracking entry"""
    issue_id: str = Field(description="Unique issue identifier")
    title: str
    description: str
    severity: IssueSeverity
    category: IssueCategory
    status: IssueStatus = Field(default=IssueStatus.OPEN)

    # Timing
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None

    # Context
    component: str = Field(description="Component where issue occurred")
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    # Error details
    error_type: Optional[str] = None
    error_message: str
    stack_trace: Optional[str] = None
    error_code: Optional[str] = None

    # Recurrence tracking
    recurrence_pattern: IssueRecurrencePattern

    # MCP correlation
    mcp_context: MCPContext = Field(default_factory=MCPContext)

    # Additional metadata
    tags: List[str] = Field(default_factory=list)
    environment: str = Field(default="production")
    version: str = Field(default="1.0.0")

    # Resolution
    resolution_notes: Optional[str] = None
    assigned_to: Optional[str] = None
    priority_score: float = Field(default=0.0, description="Calculated priority score")


class IssueTrackerConfig:
    """Configuration for issue tracker"""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/issue_tracker.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_issues = 10000
        self.auto_escalation_threshold = 5  # occurrences before auto-escalation
        self.escalation_window_hours = 24  # window for recurrence counting
        self.cleanup_interval_hours = 168  # 1 week
        self.enable_mcp_correlation = True


class IssueTracker:
    """
    Persistent JSON issue tracker with recurrence detection and MCP correlation.

    Features:
    - JSON-based persistence with atomic writes
    - Automatic recurrence detection and severity escalation
    - MCP session correlation for enhanced debugging
    - Priority scoring and intelligent routing
    - Thread-safe operations with async support
    """

    def __init__(self, config: Optional[IssueTrackerConfig] = None):
        self.config = config or IssueTrackerConfig()
        self.issues: Dict[str, IssueEntry] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._load_issues()

    def _load_issues(self) -> None:
        """Load issues from persistent storage"""
        try:
            if self.config.storage_path.exists():
                with open(self.config.storage_path, 'r') as f:
                    data = json.load(f)
                    for issue_data in data.get('issues', []):
                        try:
                            issue = IssueEntry(**issue_data)
                            self.issues[issue.issue_id] = issue
                        except Exception as e:
                            logger.warning(f"Failed to load issue: {e}")
                logger.info(f"Loaded {len(self.issues)} issues from storage")
        except Exception as e:
            logger.error(f"Failed to load issues from storage: {e}")
            self.issues = {}

    def _save_issues(self) -> None:
        """Atomically save issues to persistent storage"""
        try:
            # Prepare data for serialization
            data = {
                'metadata': {
                    'total_issues': len(self.issues),
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'version': '1.0'
                },
                'issues': [issue.dict() if hasattr(issue, 'dict') else asdict(issue) for issue in self.issues.values()]
            }

            # Atomic write using temporary file
            temp_path = self.config.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic move
            temp_path.replace(self.config.storage_path)
            logger.debug(f"Saved {len(self.issues)} issues to storage")

        except Exception as e:
            logger.error(f"Failed to save issues to storage: {e}")

    def _generate_issue_id(self, error_signature: str, component: str) -> str:
        """Generate unique issue ID from error signature"""
        signature = f"{error_signature}:{component}:{time.time()}"
        return hashlib.sha256(signature.encode()).hexdigest()[:16]

    def _detect_recurrence(self, error_signature: str, component: str) -> Optional[IssueEntry]:
        """Detect if this is a recurring issue and return existing entry if found"""
        current_time = time.time()
        cutoff_time = current_time - (self.config.escalation_window_hours * 3600)

        for issue in self.issues.values():
            if (issue.recurrence_pattern.occurrence_count > 1 and
                issue.component == component and
                issue.error_type == error_signature and
                issue.status in [IssueStatus.OPEN, IssueStatus.INVESTIGATING]):

                # Check if within escalation window
                last_occurrence = datetime.fromisoformat(issue.recurrence_pattern.last_occurrence.replace('Z', '+00:00')).timestamp()
                if last_occurrence > cutoff_time:
                    return issue

        return None

    def _calculate_priority_score(self, issue: IssueEntry) -> float:
        """Calculate priority score based on severity, recurrence, and impact"""
        base_score = {
            IssueSeverity.LOW: 1.0,
            IssueSeverity.MEDIUM: 2.0,
            IssueSeverity.HIGH: 3.0,
            IssueSeverity.CRITICAL: 5.0
        }[issue.severity]

        # Recurrence multiplier
        recurrence_multiplier = min(issue.recurrence_pattern.occurrence_count * 0.5, 3.0)

        # MCP correlation bonus (if MCP-related)
        mcp_bonus = 1.5 if issue.category == IssueCategory.MCP_ERROR else 1.0

        return base_score * recurrence_multiplier * mcp_bonus

    def _escalate_severity(self, issue: IssueEntry) -> None:
        """Auto-escalate severity based on recurrence patterns"""
        if issue.recurrence_pattern.occurrence_count >= self.config.auto_escalation_threshold:
            if issue.severity == IssueSeverity.LOW:
                issue.severity = IssueSeverity.MEDIUM
            elif issue.severity == IssueSeverity.MEDIUM:
                issue.severity = IssueSeverity.HIGH
            elif issue.severity == IssueSeverity.HIGH:
                issue.severity = IssueSeverity.CRITICAL

            logger.info(f"Auto-escalated issue {issue.issue_id} to {issue.severity.value}")

    def _update_recurrence_pattern(self, issue: IssueEntry) -> None:
        """Update recurrence pattern statistics"""
        current_time = datetime.now(timezone.utc)
        pattern = issue.recurrence_pattern

        pattern.occurrence_count += 1
        pattern.last_occurrence = current_time.isoformat()

        # Calculate average interval
        first_time = datetime.fromisoformat(pattern.first_occurrence.replace('Z', '+00:00'))
        total_hours = (current_time - first_time).total_seconds() / 3600
        pattern.average_interval_hours = total_hours / pattern.occurrence_count

        # Update peak hour
        current_hour = current_time.hour
        if pattern.peak_hour is None:
            pattern.peak_hour = current_hour
        elif current_hour == pattern.peak_hour:
            # Strengthen the pattern
            pass

    async def track_issue(
        self,
        title: str,
        description: str,
        error_message: str,
        component: str,
        severity: IssueSeverity = IssueSeverity.MEDIUM,
        category: IssueCategory = IssueCategory.UNKNOWN,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        function_name: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        mcp_session_id: Optional[str] = None,
        mcp_provider: Optional[str] = None,
        mcp_operation: Optional[str] = None,
        mcp_correlation_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: str = "production",
        version: str = "1.0.0"
    ) -> str:
        """
        Track a new issue or update existing recurring issue.

        Returns the issue ID.
        """
        async with self._lock:
            error_signature = error_type or hashlib.md5(error_message.encode()).hexdigest()[:12]

            # Check for recurrence
            existing_issue = self._detect_recurrence(error_signature, component)

            current_time = datetime.now(timezone.utc).isoformat()

            if existing_issue:
                # Update existing issue
                issue = existing_issue
                issue.updated_at = current_time
                issue.recurrence_pattern.last_occurrence = current_time
                self._update_recurrence_pattern(issue)
                self._escalate_severity(issue)

                # Update MCP context if provided
                if mcp_session_id:
                    issue.mcp_context.session_id = mcp_session_id
                if mcp_provider:
                    issue.mcp_context.provider = mcp_provider
                if mcp_operation:
                    issue.mcp_context.operation = mcp_operation
                if mcp_correlation_id:
                    issue.mcp_context.correlation_id = mcp_correlation_id

                logger.info(f"Updated recurring issue {issue.issue_id} (count: {issue.recurrence_pattern.occurrence_count})")

            else:
                # Create new issue
                issue_id = self._generate_issue_id(error_signature, component)

                issue = IssueEntry(
                    issue_id=issue_id,
                    title=title,
                    description=description,
                    severity=severity,
                    category=category,
                    created_at=current_time,
                    updated_at=current_time,
                    component=component,
                    function_name=function_name,
                    file_path=file_path,
                    line_number=line_number,
                    error_type=error_type,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    recurrence_pattern=IssueRecurrencePattern(
                        first_occurrence=current_time,
                        last_occurrence=current_time
                    ),
                    mcp_context=MCPContext(
                        session_id=mcp_session_id,
                        provider=mcp_provider,
                        operation=mcp_operation,
                        correlation_id=mcp_correlation_id
                    ),
                    tags=tags or [],
                    environment=environment,
                    version=version
                )

                self.issues[issue_id] = issue
                logger.info(f"Created new issue {issue_id} in category {category.value}")

            # Update priority score
            issue.priority_score = self._calculate_priority_score(issue)

            # Cleanup old issues periodically
            if time.time() - self._last_cleanup > (self.config.cleanup_interval_hours * 3600):
                await self._cleanup_old_issues()

            # Save to storage
            self._save_issues()

            return issue.issue_id

    async def resolve_issue(self, issue_id: str, resolution_notes: str) -> bool:
        """Mark an issue as resolved"""
        async with self._lock:
            if issue_id not in self.issues:
                return False

            issue = self.issues[issue_id]
            issue.status = IssueStatus.RESOLVED
            issue.resolved_at = datetime.now(timezone.utc).isoformat()
            issue.resolution_notes = resolution_notes
            issue.updated_at = datetime.now(timezone.utc).isoformat()

            self._save_issues()
            logger.info(f"Resolved issue {issue_id}")
            return True

    async def close_issue(self, issue_id: str) -> bool:
        """Close an issue"""
        async with self._lock:
            if issue_id not in self.issues:
                return False

            issue = self.issues[issue_id]
            issue.status = IssueStatus.CLOSED
            issue.updated_at = datetime.now(timezone.utc).isoformat()

            self._save_issues()
            logger.info(f"Closed issue {issue_id}")
            return True

    async def get_issue(self, issue_id: str) -> Optional[IssueEntry]:
        """Get issue by ID"""
        return self.issues.get(issue_id)

    async def get_issues_by_component(self, component: str) -> List[IssueEntry]:
        """Get all issues for a specific component"""
        return [issue for issue in self.issues.values() if issue.component == component]

    async def get_issues_by_severity(self, severity: IssueSeverity) -> List[IssueEntry]:
        """Get all issues with specific severity"""
        return [issue for issue in self.issues.values() if issue.severity == severity]

    async def get_issues_by_category(self, category: IssueCategory) -> List[IssueEntry]:
        """Get all issues in specific category"""
        return [issue for issue in self.issues.values() if issue.category == category]

    async def get_recurring_issues(self, min_occurrences: int = 2) -> List[IssueEntry]:
        """Get issues that have recurred multiple times"""
        return [issue for issue in self.issues.values()
                if issue.recurrence_pattern.occurrence_count >= min_occurrences]

    async def get_mcp_correlated_issues(self) -> List[IssueEntry]:
        """Get issues that have MCP session correlation"""
        return [issue for issue in self.issues.values()
                if issue.mcp_context.session_id is not None]

    def get_issue_summary(self) -> Dict[str, Any]:
        """Get comprehensive issue tracking summary"""
        total_issues = len(self.issues)
        open_issues = len([i for i in self.issues.values() if i.status == IssueStatus.OPEN])
        resolved_issues = len([i for i in self.issues.values() if i.status == IssueStatus.RESOLVED])
        critical_issues = len([i for i in self.issues.values() if i.severity == IssueSeverity.CRITICAL])

        # Category breakdown
        category_counts = {}
        for category in IssueCategory:
            category_counts[category.value] = len([i for i in self.issues.values() if i.category == category])

        # Recurring issues
        recurring_issues = len([i for i in self.issues.values() if i.recurrence_pattern.occurrence_count > 1])

        # MCP correlated
        mcp_issues = len([i for i in self.issues.values() if i.mcp_context.session_id])

        return {
            'total_issues': total_issues,
            'open_issues': open_issues,
            'resolved_issues': resolved_issues,
            'critical_issues': critical_issues,
            'recurring_issues': recurring_issues,
            'mcp_correlated_issues': mcp_issues,
            'category_breakdown': category_counts,
            'top_components': self._get_top_components(),
            'severity_distribution': self._get_severity_distribution()
        }

    def _get_top_components(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most problematic components"""
        component_counts = {}
        for issue in self.issues.values():
            component_counts[issue.component] = component_counts.get(issue.component, 0) + 1

        return [{'component': comp, 'count': count}
                for comp, count in sorted(component_counts.items(), key=lambda x: x[1], reverse=True)][:limit]

    def _get_severity_distribution(self) -> Dict[str, int]:
        """Get severity distribution"""
        severity_counts = {}
        for severity in IssueSeverity:
            severity_counts[severity.value] = len([i for i in self.issues.values() if i.severity == severity])
        return severity_counts

    async def _cleanup_old_issues(self) -> None:
        """Clean up old resolved/closed issues"""
        cutoff_time = time.time() - (self.config.cleanup_interval_hours * 3600)
        to_remove = []

        for issue_id, issue in self.issues.items():
            if issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]:
                resolved_time = datetime.fromisoformat(issue.resolved_at.replace('Z', '+00:00')).timestamp()
                if resolved_time < cutoff_time:
                    to_remove.append(issue_id)

        for issue_id in to_remove:
            del self.issues[issue_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old issues")
            self._save_issues()

        self._last_cleanup = time.time()

    async def export_issues(self, file_path: str) -> None:
        """Export all issues to JSON file"""
        data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': self.get_issue_summary(),
            'issues': [asdict(issue) for issue in self.issues.values()]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)


# Global singleton instance
_issue_tracker: Optional[IssueTracker] = None


async def get_issue_tracker() -> IssueTracker:
    """Get or create global issue tracker instance"""
    global _issue_tracker
    if _issue_tracker is None:
        _issue_tracker = IssueTracker()
    return _issue_tracker


# Convenience functions for easy usage
async def track_error(
    error: Exception,
    component: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    severity: IssueSeverity = IssueSeverity.MEDIUM,
    category: IssueCategory = IssueCategory.UNKNOWN,
    mcp_session_id: Optional[str] = None,
    mcp_provider: Optional[str] = None,
    **kwargs
) -> str:
    """Convenience function to track exceptions"""
    tracker = await get_issue_tracker()

    title = title or f"{error.__class__.__name__} in {component}"
    description = description or str(error)

    return await tracker.track_issue(
        title=title,
        description=description,
        error_message=str(error),
        component=component,
        severity=severity,
        category=category,
        error_type=error.__class__.__name__,
        mcp_session_id=mcp_session_id,
        mcp_provider=mcp_provider,
        **kwargs
    )


async def track_api_error(
    status_code: int,
    endpoint: str,
    error_message: str,
    component: str = "api",
    mcp_session_id: Optional[str] = None,
    **kwargs
) -> str:
    """Convenience function to track API errors"""
    tracker = await get_issue_tracker()

    severity = IssueSeverity.HIGH if status_code >= 500 else IssueSeverity.MEDIUM
    category = IssueCategory.API_ERROR

    title = f"API Error {status_code}: {endpoint}"

    return await tracker.track_issue(
        title=title,
        description=f"HTTP {status_code} error on {endpoint}",
        error_message=error_message,
        component=component,
        severity=severity,
        category=category,
        mcp_session_id=mcp_session_id,
        **kwargs
    )


async def track_mcp_error(
    error: Exception,
    operation: str,
    provider: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> str:
    """Convenience function to track MCP-related errors"""
    tracker = await get_issue_tracker()

    return await tracker.track_issue(
        title=f"MCP Error in {operation}",
        description=f"MCP operation '{operation}' failed",
        error_message=str(error),
        component="mcp",
        severity=IssueSeverity.HIGH,
        category=IssueCategory.MCP_ERROR,
        error_type=error.__class__.__name__,
        mcp_session_id=session_id,
        mcp_provider=provider,
        mcp_operation=operation,
        **kwargs
    )


@asynccontextmanager
async def issue_tracking_context(component: str, operation: str, **context):
    """Context manager for automatic issue tracking on exceptions"""
    try:
        yield
    except Exception as e:
        await track_error(
            error=e,
            component=component,
            title=f"Exception in {operation}",
            description=f"Exception occurred during {operation}",
            **context
        )
        raise
