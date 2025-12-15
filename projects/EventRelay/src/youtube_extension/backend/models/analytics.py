#!/usr/bin/env python3
"""
Analytics and Metrics Models
============================

Models for analytics events, performance metrics, and usage statistics.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, ForeignKey, Index, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel

class EventCategory(PyEnum):
    """Analytics event categories"""
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_PERFORMANCE = "system_performance"
    BUSINESS_METRIC = "business_metric"
    ERROR_TRACKING = "error_tracking"
    CONVERSION = "conversion"
    ENGAGEMENT = "engagement"

class MetricType(PyEnum):
    """Performance metric types"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    AVAILABILITY = "availability"
    CAPACITY = "capacity"

class AnalyticsEvent(BaseModel):
    """
    Analytics events for user behavior and system tracking
    """
    __tablename__ = "analytics_events"
    
    # Event identification
    event_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Name of the analytics event"
    )
    
    category: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory),
        nullable=False,
        index=True,
        doc="Event category"
    )
    
    # User context
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        doc="Associated user ID"
    )
    
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Session identifier"
    )
    
    # Event data
    properties: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Event properties and data"
    )
    
    # Numeric values for aggregation
    value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Numeric value associated with event"
    )
    
    count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Event count (for aggregated events)"
    )
    
    # Context information
    page_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Page URL where event occurred"
    )
    
    referrer: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Referrer URL"
    )
    
    # Device and browser info
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Device type (desktop, mobile, tablet)"
    )
    
    browser: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Browser name and version"
    )
    
    os: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Operating system"
    )
    
    screen_resolution: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Screen resolution"
    )
    
    # Geographic information
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User country"
    )
    
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User region/state"
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User city"
    )
    
    # A/B testing
    experiments: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Active A/B test experiments"
    )
    
    # Cohort information
    user_cohort: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="User cohort identifier"
    )
    
    # Event timing
    event_timestamp: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="When the event actually occurred"
    )
    
    # Relationships
    user = relationship("User")
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Get event property value"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any) -> None:
        """Set event property value"""
        if self.properties is None:
            self.properties = {}
        self.properties[key] = value
    
    def is_conversion_event(self) -> bool:
        """Check if this is a conversion event"""
        conversion_events = [
            'user_signup', 'subscription_started', 'payment_completed',
            'video_processed', 'learning_completed'
        ]
        return self.event_name in conversion_events
    
    def __repr__(self) -> str:
        return f"<AnalyticsEvent(name='{self.event_name}', category='{self.category}', user_id='{self.user_id}')>"

class PerformanceMetric(BaseModel):
    """
    System performance metrics and monitoring data
    """
    __tablename__ = "performance_metrics"
    
    # Metric identification
    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Name of the performance metric"
    )
    
    metric_type: Mapped[MetricType] = mapped_column(
        Enum(MetricType),
        nullable=False,
        index=True,
        doc="Type of performance metric"
    )
    
    # Service/component information
    service_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Service or component name"
    )
    
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="API endpoint or resource path"
    )
    
    # Metric values
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Metric value"
    )
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Metric unit (ms, %, bytes, rps, etc.)"
    )
    
    # Statistical data
    min_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Minimum value in sampling period"
    )
    
    max_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Maximum value in sampling period"
    )
    
    avg_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average value in sampling period"
    )
    
    p50_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="50th percentile value"
    )
    
    p95_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="95th percentile value"
    )
    
    p99_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="99th percentile value"
    )
    
    # Sampling information
    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Number of samples aggregated"
    )
    
    sampling_period_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
        doc="Sampling period in seconds"
    )
    
    # Context data
    tags: Mapped[Dict[str, str]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Metric tags and labels"
    )
    
    # Alerting thresholds
    warning_threshold: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Warning threshold value"
    )
    
    critical_threshold: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Critical threshold value"
    )
    
    # Status indicators
    is_healthy: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Whether metric indicates healthy state"
    )
    
    def is_above_threshold(self, threshold_type: str = 'warning') -> bool:
        """Check if metric is above threshold"""
        if threshold_type == 'warning' and self.warning_threshold:
            return self.value > self.warning_threshold
        elif threshold_type == 'critical' and self.critical_threshold:
            return self.value > self.critical_threshold
        return False
    
    def get_health_status(self) -> str:
        """Get health status based on thresholds"""
        if self.critical_threshold and self.value > self.critical_threshold:
            return "critical"
        elif self.warning_threshold and self.value > self.warning_threshold:
            return "warning"
        else:
            return "healthy"
    
    def __repr__(self) -> str:
        return f"<PerformanceMetric(name='{self.metric_name}', service='{self.service_name}', value={self.value})>"

class UsageStatistic(BaseModel):
    """
    Usage statistics and business metrics
    """
    __tablename__ = "usage_statistics"
    
    # Statistic identification
    stat_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Name of the statistic"
    )
    
    stat_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Category of statistic"
    )
    
    # Time period
    period_start: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="Start of reporting period"
    )
    
    period_end: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="End of reporting period"
    )
    
    period_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Period type (hourly, daily, weekly, monthly)"
    )
    
    # Statistic values
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Statistic value"
    )
    
    count: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Count value (for count-based statistics)"
    )
    
    # Change tracking
    previous_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Previous period value"
    )
    
    change_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Absolute change from previous period"
    )
    
    change_percentage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Percentage change from previous period"
    )
    
    # Breakdown data
    breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Detailed breakdown of statistic"
    )
    
    # Dimensions
    dimensions: Mapped[Dict[str, str]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Statistic dimensions (tenant, user_type, etc.)"
    )
    
    # Data quality
    sample_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Sample size for statistic calculation"
    )
    
    confidence_interval: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence interval percentage"
    )
    
    # Targets and goals
    target_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Target or goal value"
    )
    
    target_achievement: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Percentage of target achieved"
    )
    
    def calculate_growth_rate(self) -> Optional[float]:
        """Calculate growth rate from previous period"""
        if not self.previous_value or self.previous_value == 0:
            return None
        
        return ((self.value - self.previous_value) / self.previous_value) * 100
    
    def is_trending_up(self) -> bool:
        """Check if statistic is trending upward"""
        return self.change_value is not None and self.change_value > 0
    
    def get_target_status(self) -> str:
        """Get target achievement status"""
        if not self.target_value:
            return "no_target"
        
        achievement = (self.value / self.target_value) * 100
        
        if achievement >= 100:
            return "exceeded"
        elif achievement >= 90:
            return "on_track"
        elif achievement >= 70:
            return "behind"
        else:
            return "at_risk"
    
    def __repr__(self) -> str:
        return f"<UsageStatistic(name='{self.stat_name}', period='{self.period_type}', value={self.value})>"

# Create performance indexes
Index("ix_analytics_events_name_tenant_timestamp", 
      AnalyticsEvent.event_name, AnalyticsEvent.tenant_id, AnalyticsEvent.event_timestamp)
Index("ix_analytics_events_user_category_timestamp", 
      AnalyticsEvent.user_id, AnalyticsEvent.category, AnalyticsEvent.event_timestamp)
Index("ix_analytics_events_session_timestamp", 
      AnalyticsEvent.session_id, AnalyticsEvent.event_timestamp)

Index("ix_performance_metrics_service_metric_created", 
      PerformanceMetric.service_name, PerformanceMetric.metric_name, PerformanceMetric.created_at)
Index("ix_performance_metrics_type_healthy_created", 
      PerformanceMetric.metric_type, PerformanceMetric.is_healthy, PerformanceMetric.created_at)

Index("ix_usage_statistics_category_period_start", 
      UsageStatistic.stat_category, UsageStatistic.period_start)
Index("ix_usage_statistics_name_period_type_start", 
      UsageStatistic.stat_name, UsageStatistic.period_type, UsageStatistic.period_start)