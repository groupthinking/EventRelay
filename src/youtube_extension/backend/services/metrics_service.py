#!/usr/bin/env python3
"""
Metrics Service
==============

Collects, analyzes, and reports system metrics and performance data.
Provides comprehensive monitoring and analytics capabilities.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import psutil
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Represents a single metric measurement"""
    name: str
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSeries:
    """Represents a time series of metric points"""
    name: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    aggregation_window: int = 300  # 5 minutes in seconds

    def add_point(self, value: Union[int, float], timestamp: Optional[datetime] = None,
                  tags: Optional[Dict[str, str]] = None) -> None:
        """Add a metric point to the series"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=timestamp,
            tags=tags or {}
        )
        self.points.append(point)

    def get_recent_points(self, seconds: int = 300) -> List[MetricPoint]:
        """Get points from the last N seconds"""
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        return [p for p in self.points if p.timestamp >= cutoff]

    def get_aggregated_stats(self, seconds: int = 300) -> Dict[str, Any]:
        """Get aggregated statistics for recent points"""
        recent_points = self.get_recent_points(seconds)

        if not recent_points:
            return {"count": 0, "mean": 0, "min": 0, "max": 0}

        values = [p.value for p in recent_points]

        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1],
            "oldest": values[0]
        }

class MetricsService:
    """
    Service for collecting, analyzing, and reporting system metrics.
    Provides real-time monitoring and historical analytics.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics service.

        Args:
            config: Configuration dictionary with metrics settings
        """
        self.config = config or {}
        self.metrics: Dict[str, MetricSeries] = {}
        self.collection_interval = self.config.get("collection_interval", 60)  # seconds
        self.retention_period = self.config.get("retention_period", 3600)  # 1 hour
        self.metrics_file = Path("logs/metrics.json")

        # Create logs directory
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Start background collection
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("Metrics service initialized")

    async def start_collection(self) -> None:
        """Start background metric collection"""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._background_collection())
        logger.info("Metrics collection started")

    async def stop_collection(self) -> None:
        """Stop background metric collection"""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collection stopped")

    async def record_metric(self, name: str, value: Union[int, float],
                          tags: Optional[Dict[str, str]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for categorization
            metadata: Optional additional metadata
        """
        if name not in self.metrics:
            self.metrics[name] = MetricSeries(name)

        self.metrics[name].add_point(value, tags=tags)

        # Persist to disk periodically
        if len(self.metrics[name].points) % 10 == 0:
            await self._persist_metrics()

    async def get_metric_stats(self, name: str, time_window: int = 300) -> Dict[str, Any]:
        """
        Get statistics for a metric over a time window.

        Args:
            name: Metric name
            time_window: Time window in seconds

        Returns:
            Statistics dictionary
        """
        if name not in self.metrics:
            return {"error": f"Metric '{name}' not found"}

        series = self.metrics[name]
        stats = series.get_aggregated_stats(time_window)

        return {
            "metric_name": name,
            "time_window_seconds": time_window,
            "stats": stats,
            "point_count": len(series.points)
        }

    async def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get overview of all metrics.

        Returns:
            Metrics overview dictionary
        """
        overview = {
            "total_metrics": len(self.metrics),
            "collection_status": "running" if self._running else "stopped",
            "collection_interval": self.collection_interval,
            "metrics": {}
        }

        for name, series in self.metrics.items():
            overview["metrics"][name] = {
                "point_count": len(series.points),
                "latest_timestamp": series.points[-1].timestamp.isoformat() if series.points else None,
                "recent_stats": series.get_aggregated_stats(300)
            }

        return overview

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.

        Returns:
            System metrics dictionary
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_total = memory.total

            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used
            disk_total = disk.total

            # Network metrics (basic)
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent
            bytes_recv = network.bytes_recv

            system_metrics = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "percent": memory_percent,
                    "used_bytes": memory_used,
                    "total_bytes": memory_total,
                    "used_gb": round(memory_used / (1024**3), 2),
                    "total_gb": round(memory_total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk_percent,
                    "used_bytes": disk_used,
                    "total_bytes": disk_total,
                    "used_gb": round(disk_used / (1024**3), 2),
                    "total_gb": round(disk_total / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": bytes_sent,
                    "bytes_recv": bytes_recv,
                    "total_mb": round((bytes_sent + bytes_recv) / (1024**2), 2)
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            # Record these as metrics
            await self.record_metric("system.cpu_percent", cpu_percent, tags={"type": "system"})
            await self.record_metric("system.memory_percent", memory_percent, tags={"type": "system"})
            await self.record_metric("system.disk_percent", disk_percent, tags={"type": "system"})

            return system_metrics

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {"error": str(e)}

    async def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics data.

        Args:
            format: Export format ("json" or "prometheus")

        Returns:
            Exported metrics string
        """
        if format == "json":
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "metrics": {}
            }

            for name, series in self.metrics.items():
                export_data["metrics"][name] = {
                    "points": [
                        {
                            "timestamp": p.timestamp.isoformat(),
                            "value": p.value,
                            "tags": p.tags
                        }
                        for p in series.points
                    ]
                }

            return json.dumps(export_data, indent=2, default=str)

        elif format == "prometheus":
            lines = []
            for name, series in self.metrics.items():
                if series.points:
                    latest_point = series.points[-1]
                    lines.append(f"{name} {latest_point.value}")

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _background_collection(self) -> None:
        """Background task for periodic metric collection"""
        while self._running:
            try:
                await self.get_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background collection: {e}")
                await asyncio.sleep(self.collection_interval)

    async def _persist_metrics(self) -> None:
        """Persist metrics to disk"""
        try:
            export_data = await self.export_metrics("json")

            with open(self.metrics_file, 'w') as f:
                f.write(export_data)

        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")

    async def load_persisted_metrics(self) -> bool:
        """
        Load previously persisted metrics.

        Returns:
            Success status
        """
        try:
            if not self.metrics_file.exists():
                return False

            with open(self.metrics_file, 'r') as f:
                data = json.load(f)

            # Restore metrics (simplified - would need more complex logic for full restoration)
            logger.info(f"Loaded persisted metrics from {self.metrics_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load persisted metrics: {e}")
            return False

    async def clear_old_metrics(self, retention_seconds: Optional[int] = None) -> int:
        """
        Clear metrics older than retention period.

        Args:
            retention_seconds: Override default retention period

        Returns:
            Number of points cleared
        """
        if retention_seconds is None:
            retention_seconds = self.retention_period

        cutoff = datetime.utcnow() - timedelta(seconds=retention_seconds)
        cleared_count = 0

        for series in self.metrics.values():
            original_count = len(series.points)
            series.points = deque([p for p in series.points if p.timestamp >= cutoff])
            cleared_count += original_count - len(series.points)

        logger.info(f"Cleared {cleared_count} old metric points")
        return cleared_count

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for metrics service.

        Returns:
            Health status dictionary
        """
        health = {
            "service": "metrics_service",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "collection_running": self._running,
                "total_metrics": len(self.metrics),
                "collection_interval": self.collection_interval,
                "persistence_file_exists": self.metrics_file.exists()
            }
        }

        # Test metric recording
        try:
            await self.record_metric("health_check.test", 1.0, tags={"test": "health"})
            health["metrics"]["recording_works"] = True
        except Exception as e:
            health["metrics"]["recording_works"] = False
            health["status"] = "degraded"
            health["error"] = str(e)

        # Test system metrics collection
        try:
            system_metrics = await self.get_system_metrics()
            health["metrics"]["system_collection_works"] = "error" not in system_metrics
        except Exception as e:
            health["metrics"]["system_collection_works"] = False
            health["status"] = "degraded"

        return health
