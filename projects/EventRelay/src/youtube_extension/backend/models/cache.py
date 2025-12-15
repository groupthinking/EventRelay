#!/usr/bin/env python3
"""
Cache Management Models
======================

Models for intelligent caching, cache statistics, and performance optimization.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Integer, Text, Float, Index, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel

class CacheType(PyEnum):
    """Types of cached content"""
    VIDEO_METADATA = "video_metadata"
    TRANSCRIPT = "transcript"
    ANALYSIS_RESULT = "analysis_result"
    LEARNING_EXTRACTION = "learning_extraction"
    API_RESPONSE = "api_response"
    THUMBNAIL = "thumbnail"
    USER_SESSION = "user_session"
    SEARCH_RESULT = "search_result"

class CacheStatus(PyEnum):
    """Cache entry status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    WARMING = "warming"
    ERROR = "error"

class CacheEntry(BaseModel):
    """
    Intelligent cache entries with automatic expiration and warming
    """
    __tablename__ = "cache_entries"
    
    # Cache identification
    cache_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique cache key"
    )
    
    cache_type: Mapped[CacheType] = mapped_column(
        Enum(CacheType),
        nullable=False,
        index=True,
        doc="Type of cached content"
    )
    
    # Cache content
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Cached content (for text data)"
    )
    
    structured_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Structured cached data"
    )
    
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA256 hash of content for integrity"
    )
    
    # Size and metadata
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Cache entry size in bytes"
    )
    
    content_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="MIME type of cached content"
    )
    
    compression_ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Compression ratio if content is compressed"
    )
    
    # Cache lifecycle
    status: Mapped[CacheStatus] = mapped_column(
        Enum(CacheStatus),
        default=CacheStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Cache entry status"
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="Cache expiration timestamp"
    )
    
    # Usage tracking
    hit_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of cache hits"
    )
    
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True,
        doc="Last access timestamp"
    )
    
    access_frequency: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Access frequency (hits per day)"
    )
    
    # Source information
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Original source URL"
    )
    
    source_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Source version or etag"
    )
    
    generation_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Time taken to generate content (ms)"
    )
    
    generation_cost: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Cost to generate this content"
    )
    
    # Cache warming and maintenance
    warm_after: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When to start warming this cache entry"
    )
    
    warming_priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        doc="Cache warming priority (1=highest)"
    )
    
    auto_refresh: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to auto-refresh before expiration"
    )
    
    # Error tracking
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of errors accessing this entry"
    )
    
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Last error message"
    )
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_near_expiry(self, minutes: int = 30) -> bool:
        """Check if cache entry is near expiry"""
        threshold = datetime.utcnow() + timedelta(minutes=minutes)
        return self.expires_at <= threshold
    
    def record_hit(self) -> None:
        """Record a cache hit"""
        self.hit_count += 1
        self.last_accessed_at = datetime.utcnow()
        self._update_access_frequency()
    
    def _update_access_frequency(self) -> None:
        """Update access frequency calculation"""
        if not self.created_at or not self.hit_count:
            self.access_frequency = 0.0
            return
        
        age_days = (datetime.utcnow() - self.created_at).days
        if age_days == 0:
            age_days = 1  # Prevent division by zero
        
        self.access_frequency = self.hit_count / age_days
    
    def extend_expiry(self, hours: int = 24) -> None:
        """Extend cache expiry time"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
    
    def invalidate(self) -> None:
        """Mark cache entry as invalidated"""
        self.status = CacheStatus.INVALIDATED
    
    def get_efficiency_score(self) -> float:
        """Calculate cache efficiency score"""
        if not self.generation_time_ms or self.hit_count == 0:
            return 0.0
        
        # Score based on hits vs generation time
        time_saved = (self.hit_count - 1) * self.generation_time_ms
        efficiency = min(100.0, time_saved / 1000)  # Cap at 100
        
        return efficiency
    
    def __repr__(self) -> str:
        return f"<CacheEntry(key='{self.cache_key[:50]}...', type='{self.cache_type}', hits={self.hit_count})>"

class CacheStats(BaseModel):
    """
    Cache statistics and performance metrics
    """
    __tablename__ = "cache_stats"
    
    # Time period
    stats_date: Mapped[datetime] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        doc="Date for these statistics"
    )
    
    # Cache metrics
    total_entries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total cache entries"
    )
    
    active_entries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Active cache entries"
    )
    
    expired_entries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Expired cache entries"
    )
    
    # Size metrics
    total_size_bytes: Mapped[BigInteger] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Total cache size in bytes"
    )
    
    average_entry_size: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average cache entry size"
    )
    
    largest_entry_size: Mapped[BigInteger] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Largest cache entry size"
    )
    
    # Performance metrics
    hit_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Cache hit rate percentage"
    )
    
    miss_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Cache miss rate percentage"
    )
    
    total_hits: Mapped[BigInteger] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Total cache hits"
    )
    
    total_misses: Mapped[BigInteger] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Total cache misses"
    )
    
    # Timing metrics
    average_response_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average cache response time"
    )
    
    time_saved_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Estimated time saved by caching"
    )
    
    # Cost metrics
    generation_cost_saved: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Cost saved through caching"
    )
    
    storage_cost: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Cost of cache storage"
    )
    
    # Cache type breakdown
    type_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Statistics by cache type"
    )
    
    # Top performing caches
    top_entries: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Top performing cache entries"
    )
    
    # Cleanup metrics
    entries_cleaned: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Cache entries cleaned up"
    )
    
    cleanup_size_freed: Mapped[BigInteger] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Space freed by cleanup"
    )
    
    def calculate_efficiency(self) -> float:
        """Calculate overall cache efficiency"""
        if self.total_hits + self.total_misses == 0:
            return 0.0
        
        return (self.total_hits / (self.total_hits + self.total_misses)) * 100
    
    def get_storage_efficiency(self) -> float:
        """Calculate storage efficiency"""
        if self.storage_cost == 0:
            return 0.0
        
        return self.generation_cost_saved / self.storage_cost
    
    def get_size_summary(self) -> Dict[str, str]:
        """Get human-readable size summary"""
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} TB"
        
        return {
            "total_size": format_bytes(self.total_size_bytes),
            "average_entry": format_bytes(self.average_entry_size),
            "largest_entry": format_bytes(self.largest_entry_size)
        }
    
    @classmethod
    def create_daily_stats(cls) -> 'CacheStats':
        """Create daily statistics entry"""
        # This would be implemented with actual statistics calculation
        return cls(
            stats_date=datetime.utcnow().date(),
            tenant_id="system"  # System-level stats
        )
    
    def __repr__(self) -> str:
        return f"<CacheStats(date='{self.stats_date}', hit_rate={self.hit_rate:.1f}%)>"

# Create performance indexes
Index("ix_cache_entries_type_status", CacheEntry.cache_type, CacheEntry.status)
Index("ix_cache_entries_expires_status", CacheEntry.expires_at, CacheEntry.status)
Index("ix_cache_entries_frequency_hits", CacheEntry.access_frequency, CacheEntry.hit_count)
Index("ix_cache_entries_warm_priority", CacheEntry.warm_after, CacheEntry.warming_priority)
Index("ix_cache_stats_date_tenant", CacheStats.stats_date, CacheStats.tenant_id)