#!/usr/bin/env python3
"""
Audit and Security Models
=========================

Models for audit logging, security events, and compliance tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel

class AuditAction(PyEnum):
    """Types of auditable actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    PROCESS = "process"
    EXPORT = "export"
    IMPORT = "import"
    CONFIGURE = "configure"

class AuditLevel(PyEnum):
    """Audit log levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SecurityEventType(PyEnum):
    """Types of security events"""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    UNUSUAL_ACCESS_PATTERN = "unusual_access_pattern"
    MALICIOUS_REQUEST = "malicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"

class SeverityLevel(PyEnum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLog(BaseModel):
    """
    Comprehensive audit logging for compliance and security
    """
    __tablename__ = "audit_logs"
    
    # User and session information
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        doc="User who performed the action"
    )
    
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Session identifier"
    )
    
    # Action details
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
        index=True,
        doc="Type of action performed"
    )
    
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type of resource affected"
    )
    
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="ID of resource affected"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable description of action"
    )
    
    # Request details
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="API endpoint or URL accessed"
    )
    
    http_method: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="HTTP method used"
    )
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        index=True,
        doc="Client IP address"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Client user agent string"
    )
    
    # Geographic information
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Country based on IP"
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="City based on IP"
    )
    
    # Change tracking
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Previous values (for updates)"
    )
    
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="New values (for updates)"
    )
    
    # Context information
    level: Mapped[AuditLevel] = mapped_column(
        Enum(AuditLevel),
        default=AuditLevel.INFO,
        nullable=False,
        index=True,
        doc="Log level"
    )
    
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether action was successful"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if action failed"
    )
    
    # Performance metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Response time in milliseconds"
    )
    
    # Additional context
    additional_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Additional contextual data"
    )
    
    # Compliance fields
    compliance_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Compliance-related tags (GDPR, HIPAA, etc.)"
    )
    
    # Relationships
    user = relationship("User")
    
    def is_sensitive_action(self) -> bool:
        """Check if this is a sensitive action requiring special attention"""
        sensitive_actions = [
            AuditAction.DELETE,
            AuditAction.EXPORT,
            AuditAction.CONFIGURE
        ]
        return self.action in sensitive_actions
    
    def get_change_summary(self) -> Optional[str]:
        """Get a summary of what changed"""
        if not self.old_values or not self.new_values:
            return None
        
        changes = []
        for key in self.new_values.keys():
            old_val = self.old_values.get(key)
            new_val = self.new_values.get(key)
            if old_val != new_val:
                changes.append(f"{key}: {old_val} → {new_val}")
        
        return "; ".join(changes)
    
    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}', user_id='{self.user_id}')>"

class SecurityEvent(BaseModel):
    """
    Security events and threat detection
    """
    __tablename__ = "security_events"
    
    # Event classification
    event_type: Mapped[SecurityEventType] = mapped_column(
        Enum(SecurityEventType),
        nullable=False,
        index=True,
        doc="Type of security event"
    )
    
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel),
        default=SeverityLevel.MEDIUM,
        nullable=False,
        index=True,
        doc="Event severity level"
    )
    
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Event title/summary"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed event description"
    )
    
    # Source information
    source_ip: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        index=True,
        doc="Source IP address"
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        doc="Associated user (if known)"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User agent string"
    )
    
    # Attack details
    attack_vector: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Attack vector or method used"
    )
    
    payload: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Attack payload (sanitized)"
    )
    
    # Request details
    request_method: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="HTTP method"
    )
    
    request_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Requested URL"
    )
    
    request_headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Request headers (filtered)"
    )
    
    # Geographic information
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Country of origin"
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="City of origin"
    )
    
    # Response and mitigation
    blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the request was blocked"
    )
    
    mitigation_action: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Mitigation action taken"
    )
    
    # Status tracking
    investigated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether event has been investigated"
    )
    
    false_positive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether event is a false positive"
    )
    
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether event is resolved"
    )
    
    # Investigation details
    investigated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Who investigated the event"
    )
    
    investigation_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Investigation findings and notes"
    )
    
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When event was resolved"
    )
    
    # Additional data
    event_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Additional event data"
    )
    
    # Pattern matching
    rule_matched: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Security rule that triggered this event"
    )
    
    pattern_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Pattern matching confidence score"
    )
    
    # Relationships
    user = relationship("User")
    
    def is_critical(self) -> bool:
        """Check if this is a critical security event"""
        return self.severity == SeverityLevel.CRITICAL
    
    def needs_immediate_attention(self) -> bool:
        """Check if event needs immediate attention"""
        return (self.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL] and 
                not self.investigated and not self.false_positive)
    
    def get_threat_summary(self) -> Dict[str, Any]:
        """Get threat summary for dashboards"""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "blocked": self.blocked,
            "source_ip": str(self.source_ip) if self.source_ip else None,
            "country": self.country,
            "investigated": self.investigated,
            "resolved": self.resolved
        }
    
    def __repr__(self) -> str:
        return f"<SecurityEvent(type='{self.event_type}', severity='{self.severity}', resolved={self.resolved})>"

# Create performance indexes
Index("ix_audit_logs_tenant_created", AuditLog.tenant_id, AuditLog.created_at)
Index("ix_audit_logs_user_action_created", AuditLog.user_id, AuditLog.action, AuditLog.created_at)
Index("ix_audit_logs_resource_created", AuditLog.resource_type, AuditLog.resource_id, AuditLog.created_at)
Index("ix_audit_logs_ip_created", AuditLog.ip_address, AuditLog.created_at)
Index("ix_security_events_severity_created", SecurityEvent.severity, SecurityEvent.created_at)
Index("ix_security_events_type_resolved", SecurityEvent.event_type, SecurityEvent.resolved)
Index("ix_security_events_source_created", SecurityEvent.source_ip, SecurityEvent.created_at)