#!/usr/bin/env python3
"""
Database Models Package
======================

Complete SQLAlchemy models for UVAI platform with multi-tenant architecture.
"""

from .base import Base, TimestampMixin, TenantMixin
from .tenant import Tenant, TenantUser, TenantSubscription
from .user import User, UserProfile, UserSession, UserActivity
from .video import Video, VideoMetadata, VideoAnalysis, VideoProcessingJob
from .learning import LearningOutcome, LearningPath, LearningProgress
from .cache import CacheEntry, CacheStats
from .audit import AuditLog, SecurityEvent
from .analytics import AnalyticsEvent, PerformanceMetric, UsageStatistic

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
    "UsageStatistic"
]