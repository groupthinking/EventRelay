#!/usr/bin/env python3
"""
Data Access Layer - Repository Pattern
=====================================

Repository pattern implementation for data access abstraction and testing.
"""

# Base repository always available
from .base import BaseRepository

# Initialize __all__ with base repository
__all__ = ["BaseRepository"]

# Try to import user repositories
try:
    from .user import UserRepository, UserProfileRepository, UserSessionRepository
    __all__.extend(["UserRepository", "UserProfileRepository", "UserSessionRepository"])
except ImportError:
    # Optional user repositories not available; safe to ignore
    pass

# Try to import tenant repositories
try:
    from .tenant import TenantRepository, TenantUserRepository, TenantSubscriptionRepository
    __all__.extend(["TenantRepository", "TenantUserRepository", "TenantSubscriptionRepository"])
    # Optional user repositories not available; safe to ignore.
    pass
    # Optional user repositories not available; safe to ignore.

# Try to import tenant repositories
try:
    from .tenant import TenantRepository, TenantUserRepository, TenantSubscriptionRepository
    __all__.extend(["TenantRepository", "TenantUserRepository", "TenantSubscriptionRepository"])
except ImportError:
    # Optional tenant repositories not available; safe to ignore.

# Try to import video repositories
try:
    from .video import VideoRepository, VideoMetadataRepository, VideoAnalysisRepository, VideoProcessingJobRepository
    __all__.extend(["VideoRepository", "VideoMetadataRepository", "VideoAnalysisRepository", "VideoProcessingJobRepository"])
except ImportError:
    # Optional video repositories not available; safe to ignore.

# Try to import learning repositories
try:
    from .learning import LearningOutcomeRepository, LearningPathRepository, LearningProgressRepository
    __all__.extend(["LearningOutcomeRepository", "LearningPathRepository", "LearningProgressRepository"])
except ImportError:
    # Optional learning repositories not available; safe to ignore.

# Try to import cache repositories
try:
    from .cache import CacheRepository, CacheStatsRepository
    __all__.extend(["CacheRepository", "CacheStatsRepository"])
except ImportError:
    # Optional cache repositories not available; safe to ignore.

# Try to import audit repositories
try:
    from .audit import AuditLogRepository, SecurityEventRepository
    __all__.extend(["AuditLogRepository", "SecurityEventRepository"])
except ImportError:
    # Optional audit repositories not available; safe to ignore.

# Try to import analytics repositories
try:
    from .analytics import AnalyticsEventRepository, PerformanceMetricRepository, UsageStatisticRepository
    __all__.extend(["AnalyticsEventRepository", "PerformanceMetricRepository", "UsageStatisticRepository"])
except ImportError:
    # Optional analytics repositories not available; safe to ignore.

# Try to import unit of work
try:
    from .unit_of_work import UnitOfWork
    __all__.append("UnitOfWork")
except ImportError:
    # Optional unit of work not available; safe to ignore.