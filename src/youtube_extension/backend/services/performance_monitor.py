#!/usr/bin/env python3
"""
Enhanced Performance Monitor for UVAI Platform
==============================================

Phase 3 Performance Optimization: Real-time performance monitoring with
comprehensive metrics, automatic alerting, and intelligent optimization
recommendations. Targets 60%+ performance improvements across all systems.

Key Features:
- Video processing pipeline performance tracking
- Database query optimization monitoring (sub-100ms targets)
- Memory management and resource monitoring
- Real-time performance alerts and optimization recommendations
- Performance benchmarking and regression detection
"""

import asyncio
import json
import logging
import time
import psutil
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import deque, defaultdict
import sqlite3
import statistics
from contextlib import asynccontextmanager
import aiofiles

# Import cleanup service for database maintenance
try:
    from .database_cleanup_service import cleanup_service
    CLEANUP_AVAILABLE = True
except ImportError:
    CLEANUP_AVAILABLE = False
    logger.warning("Database cleanup service not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric record"""
    component: str
    metric_name: str
    value: float
    timestamp: datetime
    unit: str = "ms"
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass  
class PerformanceAlert:
    """Performance alert record"""
    alert_id: str
    component: str
    metric_name: str
    threshold: float
    current_value: float
    severity: str  # "low", "medium", "high", "critical"
    message: str
    timestamp: datetime
    resolved: bool = False

class PerformanceMonitor:
    """
    Enhanced Performance Monitor for 60%+ improvement targets
    
    Monitors:
    - Video processing pipeline (target: sub-30s processing)
    - Database queries (target: 95% under 100ms)
    - Frontend load times (target: under 2s)
    - Memory usage and resource optimization
    - API costs and rate limiting
    """
    
    def __init__(self, db_path: str = "performance_monitoring.db"):
        self.db_path = db_path
        self.monitoring_enabled = True
        self.alert_thresholds = {
            'video_processing_time': {'warning': 30000, 'critical': 60000},  # 30s, 60s
            'database_query_time': {'warning': 100, 'critical': 1000},  # 100ms, 1s
            'memory_usage_percent': {'warning': 80, 'critical': 90},
            'cpu_usage_percent': {'warning': 80, 'critical': 95},
            'api_response_time': {'warning': 2000, 'critical': 5000},  # 2s, 5s
            'bundle_load_time': {'warning': 2000, 'critical': 4000}  # 2s, 4s
        }
        
        # Performance tracking
        self.metrics_buffer = deque(maxlen=10000)  # Keep last 10k metrics
        self.active_alerts = {}
        self.performance_baselines = {}
        
        # Real-time metric collections
        self.video_processing_times = deque(maxlen=100)
        self.database_query_times = deque(maxlen=1000)
        self.api_response_times = deque(maxlen=500)
        
        # Benchmarking state
        self.benchmark_results = {}
        self.optimization_history = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Start background monitoring only when an event loop is running
        self.monitoring_task = None
        try:
            asyncio.get_running_loop()
            self.start_monitoring()
        except RuntimeError:
            # No running loop at import/construction time; caller must call start_monitoring()
            logger.info("Background monitoring deferred (no running event loop)")
        
        logger.info("🔥 Enhanced Performance Monitor initialized - Target: 60%+ improvement")
    
    def _init_database(self):
        """Initialize performance monitoring database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT DEFAULT 'ms',
                    tags TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    alert_id TEXT PRIMARY KEY,
                    component TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    current_value REAL NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at DATETIME
                )
            ''')
            
            # Benchmark results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    benchmark_name TEXT NOT NULL,
                    component TEXT NOT NULL,
                    baseline_value REAL,
                    current_value REAL,
                    improvement_percent REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_component ON performance_metrics(component)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_component ON performance_alerts(component)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize performance monitoring database: {e}")
    
    def start_monitoring(self):
        """Start background performance monitoring"""
        if self.monitoring_task is None:
            try:
                # Only start monitoring if we have a running event loop
                loop = asyncio.get_running_loop()
                self.monitoring_task = asyncio.create_task(self._background_monitoring())
                logger.info("🎯 Background performance monitoring started")
            except RuntimeError:
                # No event loop running, defer monitoring
                logger.info("🎯 Performance monitoring deferred - no event loop")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("⏹️ Performance monitoring stopped")
    
    async def _background_monitoring(self):
        """Background monitoring loop"""
        while self.monitoring_enabled:
            try:
                # System resource monitoring
                await self._monitor_system_resources()
                
                # Check for performance regressions
                await self._check_performance_regressions()
                
                # Cleanup old metrics
                await self._cleanup_old_metrics()
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def record_metric(self, 
                           component: str, 
                           metric_name: str, 
                           value: float, 
                           unit: str = "ms", 
                           tags: Dict[str, str] = None) -> None:
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                component=component,
                metric_name=metric_name,
                value=value,
                timestamp=datetime.now(timezone.utc),
                unit=unit,
                tags=tags or {}
            )
            
            # Add to buffer
            with self._lock:
                self.metrics_buffer.append(metric)
                
                # Update specific collections for faster access
                if metric_name == "video_processing_time":
                    self.video_processing_times.append(value)
                elif metric_name == "database_query_time":
                    self.database_query_times.append(value)
                elif metric_name == "api_response_time":
                    self.api_response_times.append(value)
            
            # Store in database
            await self._store_metric(metric)
            
            # Check thresholds
            await self._check_alert_thresholds(metric)
            
            logger.debug(f"📊 Recorded metric: {component}.{metric_name} = {value}{unit}")
            
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    async def _store_metric(self, metric: PerformanceMetric):
        """Store metric in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (component, metric_name, value, unit, tags, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric.component,
                metric.metric_name,
                metric.value,
                metric.unit,
                json.dumps(metric.tags),
                metric.timestamp.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store metric in database: {e}")
    
    async def _check_alert_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds alert thresholds"""
        threshold_key = f"{metric.metric_name}"
        if threshold_key not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[threshold_key]
        
        # Determine severity
        severity = None
        if metric.value >= thresholds.get('critical', float('inf')):
            severity = "critical"
        elif metric.value >= thresholds.get('warning', float('inf')):
            severity = "warning"
        
        if severity:
            alert = PerformanceAlert(
                alert_id=f"{metric.component}_{metric.metric_name}_{int(time.time())}",
                component=metric.component,
                metric_name=metric.metric_name,
                threshold=thresholds[severity],
                current_value=metric.value,
                severity=severity,
                message=f"{metric.component} {metric.metric_name} ({metric.value}{metric.unit}) exceeds {severity} threshold ({thresholds[severity]}{metric.unit})",
                timestamp=metric.timestamp
            )
            
            await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: PerformanceAlert):
        """Trigger a performance alert"""
        try:
            # Store alert
            await self._store_alert(alert)

            # Log alert
            logger.warning(f"🚨 Performance Alert ({alert.severity}): {alert.message}")

            # Add to active alerts
            with self._lock:
                self.active_alerts[alert.alert_id] = alert

            # Send notification via NotificationService if available
            try:
                from .notification_service import NotificationService  # lazy import
                notification = NotificationService()
                await notification.send_alert(
                    title=f"Performance Alert: {alert.component}.{alert.metric_name}",
                    message=alert.message,
                    priority="high" if alert.severity in ("critical", "warning") else "normal",
                )
            except Exception:
                # Fallback to local placeholder to avoid crashing
                await self._send_alert_notification(alert)

        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    async def _store_alert(self, alert: PerformanceAlert):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_alerts 
                (alert_id, component, metric_name, threshold_value, current_value, severity, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.component,
                alert.metric_name,
                alert.threshold,
                alert.current_value,
                alert.severity,
                alert.message,
                alert.timestamp.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")
    
    async def _send_alert_notification(self, alert: PerformanceAlert):
        """Send alert notification (placeholder for integration)"""
        # TODO: Implement actual notification system
        pass
    
    async def _monitor_system_resources(self):
        """Monitor system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric("system", "cpu_usage_percent", cpu_percent, "%")
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self.record_metric("system", "memory_usage_percent", memory.percent, "%")
            await self.record_metric("system", "memory_available_bytes", memory.available, "bytes")
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            await self.record_metric("system", "disk_usage_percent", disk_percent, "%")
            
            # Process-specific metrics if available
            try:
                process = psutil.Process()
                await self.record_metric("process", "memory_usage_mb", process.memory_info().rss / 1024 / 1024, "MB")
                await self.record_metric("process", "cpu_percent", process.cpu_percent(), "%")
                await self.record_metric("process", "threads_count", process.num_threads(), "count")
            except Exception:
                pass  # Process monitoring is optional
                
        except Exception as e:
            logger.error(f"Error monitoring system resources: {e}")
    
    async def _check_performance_regressions(self):
        """Check for performance regressions against baselines"""
        try:
            current_metrics = await self.get_current_performance_summary()
            
            for component, metrics in current_metrics.items():
                for metric_name, current_avg in metrics.items():
                    baseline_key = f"{component}_{metric_name}"
                    
                    if baseline_key in self.performance_baselines:
                        baseline = self.performance_baselines[baseline_key]
                        regression_threshold = baseline * 1.2  # 20% degradation threshold
                        
                        if current_avg > regression_threshold:
                            await self._trigger_alert(PerformanceAlert(
                                alert_id=f"regression_{baseline_key}_{int(time.time())}",
                                component=component,
                                metric_name=metric_name,
                                threshold=regression_threshold,
                                current_value=current_avg,
                                severity="warning",
                                message=f"Performance regression detected: {metric_name} increased by {((current_avg - baseline) / baseline * 100):.1f}%",
                                timestamp=datetime.now(timezone.utc)
                            ))
                            
        except Exception as e:
            logger.error(f"Error checking performance regressions: {e}")
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent database bloat"""
        try:
            # Use the comprehensive cleanup service if available
            if CLEANUP_AVAILABLE:
                logger.info("Using comprehensive database cleanup service")
                results = cleanup_service.cleanup_database(self.db_path)

                # Log cleanup results
                for result in results:
                    if result.success:
                        logger.info(
                            f"Database cleanup: {result.table_name} - "
                            f"{result.records_deleted} records deleted, "
                            f"{result.space_freed_mb:.2f}MB freed"
                        )
                    else:
                        logger.warning(
                            f"Database cleanup failed for {result.table_name}: "
                            f"{result.error_message}"
                        )
            else:
                # Fallback to basic cleanup if service not available
                logger.info("Using basic cleanup (cleanup service not available)")
                await self._basic_cleanup()

        except Exception as e:
            logger.error(f"Error in cleanup process: {e}")

    async def _basic_cleanup(self):
        """Basic cleanup fallback when service is not available"""
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Keep only last 30 days of metrics
            cursor.execute('DELETE FROM performance_metrics WHERE timestamp < ?', (cutoff_date,))

            # Keep only unresolved alerts and alerts from last 7 days
            alert_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            cursor.execute('DELETE FROM performance_alerts WHERE resolved = 1 AND timestamp < ?', (alert_cutoff,))

            # Clean up old benchmark results (keep 90 days)
            benchmark_cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            cursor.execute('DELETE FROM benchmark_results WHERE timestamp < ?', (benchmark_cutoff,))

            conn.commit()
            conn.close()

            logger.info("Basic cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error in basic cleanup: {e}")

    async def trigger_manual_cleanup(self) -> Dict[str, Any]:
        """Manually trigger database cleanup and return results"""
        if not CLEANUP_AVAILABLE:
            return {"error": "Cleanup service not available"}

        try:
            start_time = time.time()
            results = cleanup_service.cleanup_database(self.db_path)

            cleanup_summary = {
                "database": self.db_path,
                "tables_cleaned": len(results),
                "total_records_deleted": sum(r.records_deleted for r in results),
                "total_space_freed_mb": sum(r.space_freed_mb for r in results),
                "execution_time_seconds": time.time() - start_time,
                "successful_cleanups": sum(1 for r in results if r.success),
                "failed_cleanups": sum(1 for r in results if not r.success),
                "details": [
                    {
                        "table": r.table_name,
                        "records_deleted": r.records_deleted,
                        "space_freed_mb": r.space_freed_mb,
                        "execution_time_ms": r.execution_time_ms,
                        "success": r.success,
                        "error": r.error_message if not r.success else None
                    }
                    for r in results
                ]
            }

            logger.info(f"Manual cleanup completed: {cleanup_summary}")
            return cleanup_summary

        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}")
            return {"error": str(e)}
    
    async def get_current_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get current performance summary (last hour averages)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            
            cursor.execute('''
                SELECT component, metric_name, AVG(value) as avg_value
                FROM performance_metrics 
                WHERE timestamp >= ?
                GROUP BY component, metric_name
            ''', (cutoff_time,))
            
            results = defaultdict(dict)
            for component, metric_name, avg_value in cursor.fetchall():
                results[component][metric_name] = avg_value
            
            conn.close()
            return dict(results)
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        try:
            dashboard = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_health': await self._get_system_health(),
                'performance_targets': await self._get_target_progress(),
                'active_alerts': len(self.active_alerts),
                'recent_metrics': await self._get_recent_metrics_summary(),
                'optimization_recommendations': await self._generate_optimization_recommendations()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating performance dashboard: {e}")
            return {}
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """Get system health summary"""
        with self._lock:
            # Recent video processing times
            video_times = list(self.video_processing_times)
            db_times = list(self.database_query_times)
            api_times = list(self.api_response_times)
        
        return {
            'video_processing': {
                'avg_time_ms': statistics.mean(video_times) if video_times else 0,
                'target_ms': 30000,
                'meeting_target': statistics.mean(video_times) < 30000 if video_times else False
            },
            'database_queries': {
                'avg_time_ms': statistics.mean(db_times) if db_times else 0,
                'target_ms': 100,
                'sub_100ms_percent': len([t for t in db_times if t < 100]) / len(db_times) * 100 if db_times else 0,
                'meeting_target': len([t for t in db_times if t < 100]) / len(db_times) >= 0.95 if db_times else False
            },
            'api_responses': {
                'avg_time_ms': statistics.mean(api_times) if api_times else 0,
                'target_ms': 2000,
                'meeting_target': statistics.mean(api_times) < 2000 if api_times else False
            }
        }
    
    async def _get_target_progress(self) -> Dict[str, Any]:
        """Get progress towards Phase 3 performance targets"""
        health = await self._get_system_health()
        
        # Calculate improvement percentages (assuming baseline performance)
        baseline_video_processing = 60000  # 60s baseline
        baseline_db_query = 200  # 200ms baseline
        baseline_api_response = 5000  # 5s baseline
        
        current_video = health['video_processing']['avg_time_ms']
        current_db = health['database_queries']['avg_time_ms']
        current_api = health['api_responses']['avg_time_ms']
        
        return {
            'overall_improvement_target': 60,  # 60% improvement target
            'video_processing_improvement': max(0, (baseline_video_processing - current_video) / baseline_video_processing * 100) if current_video > 0 else 0,
            'database_improvement': max(0, (baseline_db_query - current_db) / baseline_db_query * 100) if current_db > 0 else 0,
            'api_improvement': max(0, (baseline_api_response - current_api) / baseline_api_response * 100) if current_api > 0 else 0,
            'targets_met': {
                'video_processing_sub_30s': health['video_processing']['meeting_target'],
                'database_95_sub_100ms': health['database_queries']['meeting_target'],
                'api_response_sub_2s': health['api_responses']['meeting_target']
            }
        }
    
    async def _get_recent_metrics_summary(self) -> Dict[str, Any]:
        """Get recent metrics summary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Last hour metrics
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            
            cursor.execute('''
                SELECT component, COUNT(*) as metric_count, AVG(value) as avg_value
                FROM performance_metrics 
                WHERE timestamp >= ?
                GROUP BY component
                ORDER BY metric_count DESC
            ''', (cutoff_time,))
            
            metrics_summary = {}
            for component, count, avg_value in cursor.fetchall():
                metrics_summary[component] = {
                    'metric_count': count,
                    'avg_value': round(avg_value, 2)
                }
            
            conn.close()
            return metrics_summary
            
        except Exception as e:
            logger.error(f"Error getting recent metrics summary: {e}")
            return {}
    
    async def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate intelligent optimization recommendations"""
        recommendations = []
        health = await self._get_system_health()
        
        # Video processing optimization
        if not health['video_processing']['meeting_target']:
            recommendations.append({
                'component': 'video_processing',
                'priority': 'high',
                'recommendation': 'Implement parallel processing for video analysis tasks',
                'expected_improvement': '40-60%',
                'implementation_effort': 'medium'
            })
        
        # Database optimization
        if not health['database_queries']['meeting_target']:
            recommendations.append({
                'component': 'database',
                'priority': 'high',
                'recommendation': 'Add database connection pooling and query optimization',
                'expected_improvement': '30-50%',
                'implementation_effort': 'low'
            })
        
        # API optimization
        if not health['api_responses']['meeting_target']:
            recommendations.append({
                'component': 'api',
                'priority': 'medium',
                'recommendation': 'Implement intelligent caching and request batching',
                'expected_improvement': '20-40%',
                'implementation_effort': 'medium'
            })
        
        # Memory optimization
        with self._lock:
            recent_metrics = list(self.metrics_buffer)[-50:] if self.metrics_buffer else []
        
        memory_metrics = [m for m in recent_metrics if m.metric_name == "memory_usage_percent"]
        if memory_metrics and statistics.mean([m.value for m in memory_metrics]) > 75:
            recommendations.append({
                'component': 'system',
                'priority': 'medium',
                'recommendation': 'Implement memory optimization and garbage collection tuning',
                'expected_improvement': '15-25%',
                'implementation_effort': 'low'
            })
        
        return recommendations
    
    async def run_performance_benchmark(self, 
                                      component: str, 
                                      benchmark_name: str,
                                      benchmark_func,
                                      iterations: int = 10) -> Dict[str, Any]:
        """Run performance benchmark and compare against baseline"""
        try:
            logger.info(f"🏃 Running performance benchmark: {benchmark_name}")
            
            # Run benchmark
            times = []
            for i in range(iterations):
                start_time = time.time()
                await benchmark_func() if asyncio.iscoroutinefunction(benchmark_func) else benchmark_func()
                end_time = time.time()
                times.append((end_time - start_time) * 1000)  # Convert to ms
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            p95_time = sorted(times)[int(0.95 * len(times))]
            
            # Check against baseline
            baseline_key = f"{component}_{benchmark_name}"
            baseline_time = self.performance_baselines.get(baseline_key)
            
            improvement_percent = 0
            if baseline_time:
                improvement_percent = (baseline_time - avg_time) / baseline_time * 100
            else:
                # Set as new baseline
                self.performance_baselines[baseline_key] = avg_time
            
            # Store results
            result = {
                'benchmark_name': benchmark_name,
                'component': component,
                'iterations': iterations,
                'avg_time_ms': round(avg_time, 2),
                'min_time_ms': round(min_time, 2),
                'max_time_ms': round(max_time, 2),
                'p95_time_ms': round(p95_time, 2),
                'baseline_time_ms': baseline_time,
                'improvement_percent': round(improvement_percent, 1),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self._store_benchmark_result(result)
            
            logger.info(f"✅ Benchmark completed: {benchmark_name} - {avg_time:.1f}ms avg ({improvement_percent:+.1f}% vs baseline)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error running benchmark {benchmark_name}: {e}")
            return {}
    
    async def _store_benchmark_result(self, result: Dict[str, Any]):
        """Store benchmark result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO benchmark_results 
                (benchmark_name, component, baseline_value, current_value, improvement_percent, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['benchmark_name'],
                result['component'],
                result.get('baseline_time_ms'),
                result['avg_time_ms'],
                result['improvement_percent'],
                result['timestamp'],
                json.dumps({
                    'min_time': result['min_time_ms'],
                    'max_time': result['max_time_ms'],
                    'p95_time': result['p95_time_ms'],
                    'iterations': result['iterations']
                })
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store benchmark result: {e}")

# Global performance monitor instance - lazy initialized
_performance_monitor_instance = None

def _get_performance_monitor():
    """Lazy initialization of performance monitor"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance

# Convenience functions for common use cases
async def track_video_processing_time(processing_time_ms: float):
    """Track video processing time"""
    await _get_performance_monitor().record_metric("video_processor", "video_processing_time", processing_time_ms)

async def track_database_query_time(query_time_ms: float, query_type: str = "general"):
    """Track database query time"""
    await _get_performance_monitor().record_metric("database", "database_query_time", query_time_ms, tags={"query_type": query_type})

async def track_api_response_time(response_time_ms: float, endpoint: str):
    """Track API response time"""
    await _get_performance_monitor().record_metric("api", "api_response_time", response_time_ms, tags={"endpoint": endpoint})

async def track_frontend_load_time(load_time_ms: float, page: str):
    """Track frontend page load time"""
    await _get_performance_monitor().record_metric("frontend", "page_load_time", load_time_ms, tags={"page": page})

def performance_timer(component: str, metric_name: str):
    """Decorator to automatically time function execution"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            await _get_performance_monitor().record_metric(component, metric_name, execution_time)
            return result
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            # Store for async processing
            try:
                asyncio.get_running_loop()
                asyncio.create_task(performance_monitor.record_metric(component, metric_name, execution_time))
            except RuntimeError:
                # No loop: skip async record to avoid import-time errors
                pass
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

if __name__ == "__main__":
    async def test_performance_monitor():
        monitor = PerformanceMonitor()
        
        # Test metric recording
        await monitor.record_metric("test_component", "test_metric", 150.5, "ms")
        
        # Test benchmark
        async def dummy_benchmark():
            await asyncio.sleep(0.1)  # 100ms simulation
        
        result = await monitor.run_performance_benchmark("test", "dummy_test", dummy_benchmark, 5)
        print(f"Benchmark result: {result}")
        
        # Get dashboard
        dashboard = await monitor.get_performance_dashboard()
        print(f"Dashboard: {json.dumps(dashboard, indent=2, default=str)}")
        
        await monitor.stop_monitoring()
    
    asyncio.run(test_performance_monitor())