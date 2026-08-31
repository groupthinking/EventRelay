#!/usr/bin/env python3
"""
Database Models Package
======================

Complete SQLAlchemy models for UVAI platform with multi-tenant architecture.
"""

from .analytics import AnalyticsEvent, PerformanceMetric, UsageStatistic
from .api_cost import APIUsage, DailyBudget, WebhookOutbox
from .audit import AuditLog, SecurityEvent
from .base import Base, TenantMixin, TimestampMixin
from .cache import CacheEntry, CacheStats
from .learning import LearningOutcome, LearningPath, LearningProgress
from .tenant import Tenant, TenantSubscription, TenantUser
from .user import User, UserActivity, UserProfile, UserSession
from .video import Video, VideoAnalysis, VideoMetadata, VideoProcessingJob

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "TenantMixin",
    # Tenant models
    "Tenant",
    "TenantUser",
    "TenantSubscription",
    # User models
    "User",
    "UserProfile",
    "UserSession",
    "UserActivity",
    # Video models
    "Video",
    "VideoMetadata",
    "VideoAnalysis",
    "VideoProcessingJob",
    # Learning models
    "LearningOutcome",
    "LearningPath",
    "LearningProgress",
    # Cache models
    "CacheEntry",
    "CacheStats",
    # Audit models
    "AuditLog",
    "SecurityEvent",
    # Analytics models
    "AnalyticsEvent",
    "PerformanceMetric",
    "UsageStatistic",
    # API cost and durable alert delivery
    "APIUsage",
    "DailyBudget",
    "WebhookOutbox",
]
