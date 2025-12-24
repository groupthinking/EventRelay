#!/usr/bin/env python3
"""
Memory Management and Resource Monitoring
=========================================

Phase 3 Performance Optimization: Advanced memory management and resource
monitoring targeting efficient memory usage, automatic cleanup, and 
prevention of memory leaks for sustained performance.

Key Features:
- Real-time memory usage monitoring and alerting
- Automatic garbage collection optimization
- Memory leak detection and prevention
- Resource pool management
- Smart cleanup scheduling
- Memory profiling and analysis
- Process isolation and resource limits
"""

import asyncio
import gc
import logging
import os
import psutil
import resource
import sys
import threading
import time
import tracemalloc
import weakref
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable
import ctypes

# Import performance monitoring
try:
    from .performance_monitor import performance_monitor
except ImportError:
    performance_monitor = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    percent: float  # Memory percentage
    available_mb: float
    cached_mb: float
    buffers_mb: float
    heap_size_mb: float
    gc_collections: int
    gc_objects: int

@dataclass
class MemoryAlert:
    """Memory alert information"""
    alert_type: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    current_usage_mb: float
    threshold_mb: float
    timestamp: datetime
    process_info: Dict[str, Any]

@dataclass
class ResourceLimit:
    """Resource limit configuration"""
    memory_limit_mb: int
    cpu_limit_percent: float
    file_descriptor_limit: int
    thread_limit: int
    connection_limit: int

class MemoryProfiler:
    """Advanced memory profiling and leak detection"""
    
    def __init__(self):
        self.snapshots = deque(maxlen=1000)
        self.tracking_enabled = False
        self.baseline_snapshot = None
        
    def start_tracking(self):
        """Start memory tracking"""
        tracemalloc.start()
        self.tracking_enabled = True
        self.baseline_snapshot = tracemalloc.take_snapshot()
        logger.info("🔍 Memory tracking started")
    
    def stop_tracking(self):
        """Stop memory tracking"""
        if self.tracking_enabled:
            tracemalloc.stop()
            self.tracking_enabled = False
            logger.info("⏹️ Memory tracking stopped")
    
    def take_snapshot(self) -> Dict[str, Any]:
        """Take current memory snapshot"""
        if not self.tracking_enabled:
            return {}
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_size_mb': sum(stat.size for stat in top_stats) / 1024 / 1024,
            'total_count': sum(stat.count for stat in top_stats),
            'top_allocations': [
                {
                    'filename': stat.traceback.format()[0],
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }
                for stat in top_stats[:10]
            ]
        }
    
    def detect_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        if not self.tracking_enabled or not self.baseline_snapshot:
            return []
        
        current_snapshot = tracemalloc.take_snapshot()
        top_stats = current_snapshot.compare_to(self.baseline_snapshot, 'lineno')
        
        leaks = []
        for stat in top_stats[:10]:
            if stat.size_diff > 1024 * 1024:  # > 1MB difference
                leaks.append({
                    'filename': stat.traceback.format()[0],
                    'size_diff_mb': stat.size_diff / 1024 / 1024,
                    'count_diff': stat.count_diff,
                    'current_size_mb': stat.size / 1024 / 1024
                })
        
        return leaks

class ResourcePool:
    """Generic resource pool with automatic cleanup"""
    
    def __init__(self, 
                 name: str,
                 create_resource: Callable,
                 cleanup_resource: Callable,
                 max_size: int = 100,
                 idle_timeout: int = 300):  # 5 minutes
        
        self.name = name
        self.create_resource = create_resource
        self.cleanup_resource = cleanup_resource
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        
        self.pool = []
        self.in_use = set()
        self.creation_times = {}
        self._lock = threading.RLock()
        
        # Start cleanup task
        self.cleanup_task = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_task.start()
        
        logger.info(f"📦 Resource pool '{name}' initialized (max_size: {max_size})")
    
    @contextmanager
    def get_resource(self):
        """Get resource from pool with automatic cleanup"""
        resource = None
        try:
            resource = self._acquire_resource()
            yield resource
        finally:
            if resource:
                self._release_resource(resource)
    
    def _acquire_resource(self):
        """Acquire resource from pool"""
        with self._lock:
            # Try to get existing resource from pool
            if self.pool:
                resource = self.pool.pop()
                self.in_use.add(resource)
                logger.debug(f"♻️ Reused resource from pool '{self.name}'")
                return resource
            
            # Create new resource if pool is not at max capacity
            if len(self.in_use) < self.max_size:
                resource = self.create_resource()
                self.in_use.add(resource)
                self.creation_times[id(resource)] = time.time()
                logger.debug(f"🆕 Created new resource for pool '{self.name}'")
                return resource
            
            # Pool is full, wait or raise exception
            raise RuntimeError(f"Resource pool '{self.name}' exhausted")
    
    def _release_resource(self, resource):
        """Release resource back to pool"""
        with self._lock:
            if resource in self.in_use:
                self.in_use.remove(resource)
                self.pool.append(resource)
                logger.debug(f"🔄 Released resource to pool '{self.name}'")
    
    def _cleanup_worker(self):
        """Background worker to cleanup idle resources"""
        while True:
            try:
                time.sleep(60)  # Check every minute
                
                with self._lock:
                    current_time = time.time()
                    resources_to_cleanup = []
                    
                    # Find idle resources
                    for resource in list(self.pool):
                        resource_id = id(resource)
                        if resource_id in self.creation_times:
                            age = current_time - self.creation_times[resource_id]
                            if age > self.idle_timeout:
                                resources_to_cleanup.append(resource)
                    
                    # Cleanup idle resources
                    for resource in resources_to_cleanup:
                        try:
                            self.pool.remove(resource)
                            self.cleanup_resource(resource)
                            resource_id = id(resource)
                            if resource_id in self.creation_times:
                                del self.creation_times[resource_id]
                            
                            logger.debug(f"🗑️ Cleaned up idle resource from pool '{self.name}'")
                        except Exception as e:
                            logger.error(f"Error cleaning up resource: {e}")
                
            except Exception as e:
                logger.error(f"Error in cleanup worker for pool '{self.name}': {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                'name': self.name,
                'pool_size': len(self.pool),
                'in_use': len(self.in_use),
                'max_size': self.max_size,
                'utilization_percent': (len(self.in_use) / self.max_size) * 100,
                'total_created': len(self.creation_times)
            }

class MemoryManager:
    """
    Advanced memory management system
    
    Features:
    - Real-time memory monitoring and alerting
    - Automatic garbage collection optimization
    - Memory leak detection and prevention
    - Resource pool management
    - Smart cleanup scheduling
    """
    
    def __init__(self):
        self.monitoring_enabled = True
        self.alert_thresholds = {
            'memory_usage_mb': 1024,      # 1GB warning
            'memory_percent': 80,          # 80% of system memory
            'memory_growth_rate': 50,      # 50MB/minute growth
            'gc_frequency': 10             # GC more than 10 times per minute
        }
        
        # Monitoring state
        self.memory_history = deque(maxlen=1440)  # 24 hours of minute data
        self.gc_stats = {'collections': 0, 'objects': 0}
        self.resource_pools = {}
        self.active_alerts = {}
        
        # Memory profiler
        self.profiler = MemoryProfiler()
        
        # Threading
        self._lock = threading.RLock()
        self.monitoring_task = None
        
        # Resource limits
        self.resource_limits = ResourceLimit(
            memory_limit_mb=2048,    # 2GB memory limit
            cpu_limit_percent=80,     # 80% CPU usage limit
            file_descriptor_limit=1024,
            thread_limit=100,
            connection_limit=200
        )
        
        logger.info("🧠 Memory Manager initialized")
    
    def start_monitoring(self):
        """Start memory monitoring"""
        if self.monitoring_task is None:
            self.monitoring_task = threading.Thread(target=self._monitoring_worker, daemon=True)
            self.monitoring_task.start()
            self.profiler.start_tracking()
            logger.info("✅ Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring_enabled = False
        self.profiler.stop_tracking()
        logger.info("⏹️ Memory monitoring stopped")
    
    def _monitoring_worker(self):
        """Background monitoring worker"""
        while self.monitoring_enabled:
            try:
                # Take memory snapshot
                snapshot = self._take_system_snapshot()
                self._process_snapshot(snapshot)
                
                # Check for alerts
                self._check_memory_alerts(snapshot)
                
                # Optimize garbage collection if needed
                self._optimize_garbage_collection(snapshot)
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring worker: {e}")
                time.sleep(60)
    
    def _take_system_snapshot(self) -> MemorySnapshot:
        """Take system memory snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        
        # Get GC stats
        gc_stats = {
            'collections': sum(gc.get_stats()),
            'objects': len(gc.get_objects())
        }
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=system_memory.percent,
            available_mb=system_memory.available / 1024 / 1024,
            cached_mb=getattr(system_memory, 'cached', 0) / 1024 / 1024,
            buffers_mb=getattr(system_memory, 'buffers', 0) / 1024 / 1024,
            heap_size_mb=self._get_heap_size_mb(),
            gc_collections=gc_stats['collections'],
            gc_objects=gc_stats['objects']
        )
        
        return snapshot
    
    def _get_heap_size_mb(self) -> float:
        """Get approximate heap size"""
        try:
            # This is a rough estimation
            return sys.getsizeof(gc.get_objects()) / 1024 / 1024
        except Exception:
            return 0.0
    
    def _process_snapshot(self, snapshot: MemorySnapshot):
        """Process memory snapshot"""
        with self._lock:
            self.memory_history.append(snapshot)
        
        # Log to performance monitor if available
        if performance_monitor:
            asyncio.create_task(performance_monitor.record_metric(
                "system", "memory_usage_mb", snapshot.rss_mb, "MB"
            ))
            asyncio.create_task(performance_monitor.record_metric(
                "system", "memory_percent", snapshot.percent, "%"
            ))
    
    def _check_memory_alerts(self, snapshot: MemorySnapshot):
        """Check for memory-related alerts"""
        alerts = []
        
        # Check absolute memory usage
        if snapshot.rss_mb > self.alert_thresholds['memory_usage_mb']:
            alerts.append(MemoryAlert(
                alert_type="high_memory_usage",
                severity="high" if snapshot.rss_mb > self.alert_thresholds['memory_usage_mb'] * 1.5 else "medium",
                message=f"High memory usage: {snapshot.rss_mb:.1f}MB",
                current_usage_mb=snapshot.rss_mb,
                threshold_mb=self.alert_thresholds['memory_usage_mb'],
                timestamp=snapshot.timestamp,
                process_info=self._get_process_info()
            ))
        
        # Check system memory percentage
        if snapshot.percent > self.alert_thresholds['memory_percent']:
            alerts.append(MemoryAlert(
                alert_type="high_system_memory",
                severity="critical" if snapshot.percent > 95 else "high",
                message=f"High system memory usage: {snapshot.percent:.1f}%",
                current_usage_mb=0,  # System-wide metric
                threshold_mb=0,
                timestamp=snapshot.timestamp,
                process_info=self._get_process_info()
            ))
        
        # Check memory growth rate
        growth_rate = self._calculate_memory_growth_rate()
        if growth_rate > self.alert_thresholds['memory_growth_rate']:
            alerts.append(MemoryAlert(
                alert_type="memory_growth",
                severity="high",
                message=f"High memory growth rate: {growth_rate:.1f}MB/min",
                current_usage_mb=snapshot.rss_mb,
                threshold_mb=0,
                timestamp=snapshot.timestamp,
                process_info=self._get_process_info()
            ))
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _calculate_memory_growth_rate(self) -> float:
        """Calculate memory growth rate in MB/minute"""
        if len(self.memory_history) < 2:
            return 0.0
        
        # Look at last 10 minutes if available
        lookback_minutes = min(10, len(self.memory_history) - 1)
        recent_snapshots = list(self.memory_history)[-lookback_minutes:]
        
        if len(recent_snapshots) < 2:
            return 0.0
        
        start_memory = recent_snapshots[0].rss_mb
        end_memory = recent_snapshots[-1].rss_mb
        time_diff = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds() / 60
        
        return (end_memory - start_memory) / time_diff if time_diff > 0 else 0.0
    
    def _process_alert(self, alert: MemoryAlert):
        """Process memory alert"""
        alert_key = f"{alert.alert_type}_{alert.severity}"
        
        # Avoid duplicate alerts
        if alert_key in self.active_alerts:
            last_alert = self.active_alerts[alert_key]
            time_diff = (alert.timestamp - last_alert.timestamp).total_seconds()
            if time_diff < 300:  # Don't repeat same alert within 5 minutes
                return
        
        self.active_alerts[alert_key] = alert
        
        # Log alert
        logger.warning(f"🚨 Memory Alert ({alert.severity}): {alert.message}")
        
        # Take corrective action based on severity
        if alert.severity in ["high", "critical"]:
            self._take_corrective_action(alert)
    
    def _take_corrective_action(self, alert: MemoryAlert):
        """Take corrective action for memory alerts"""
        logger.info(f"🛠️ Taking corrective action for {alert.alert_type}")
        
        if alert.alert_type == "high_memory_usage":
            # Force garbage collection
            self.force_garbage_collection()
            
            # Clear resource pools
            self._cleanup_resource_pools()
            
            # Detect and log memory leaks
            leaks = self.profiler.detect_leaks()
            if leaks:
                logger.warning(f"🔍 Detected {len(leaks)} potential memory leaks")
                for leak in leaks[:5]:  # Log top 5
                    logger.warning(f"  - {leak['filename']}: +{leak['size_diff_mb']:.1f}MB")
        
        elif alert.alert_type == "high_system_memory":
            # More aggressive cleanup
            self.emergency_cleanup()
    
    def _get_process_info(self) -> Dict[str, Any]:
        """Get current process information"""
        try:
            process = psutil.Process()
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds(),
                'connections': len(process.connections())
            }
        except Exception:
            return {}
    
    def _optimize_garbage_collection(self, snapshot: MemorySnapshot):
        """Optimize garbage collection based on current state"""
        # Calculate GC frequency
        if len(self.memory_history) > 1:
            prev_collections = self.memory_history[-2].gc_collections if len(self.memory_history) > 1 else 0
            gc_frequency = snapshot.gc_collections - prev_collections
            
            # If memory is high and GC frequency is low, force collection
            if snapshot.rss_mb > 512 and gc_frequency < 2:
                logger.info("🗑️ Forcing garbage collection due to high memory usage")
                self.force_garbage_collection()
    
    def force_garbage_collection(self):
        """Force garbage collection for all generations"""
        collected = gc.collect()
        logger.info(f"🗑️ Garbage collection completed - collected {collected} objects")
        
        # Also run collection for each generation
        for generation in range(3):
            gen_collected = gc.collect(generation)
            logger.debug(f"  Generation {generation}: {gen_collected} objects collected")
    
    def _cleanup_resource_pools(self):
        """Cleanup resource pools to free memory"""
        for pool_name, pool in self.resource_pools.items():
            try:
                # Force cleanup of idle resources
                with pool._lock:
                    resources_to_cleanup = list(pool.pool)
                    pool.pool.clear()
                    
                    for resource in resources_to_cleanup:
                        pool.cleanup_resource(resource)
                
                logger.info(f"🧹 Cleaned up resource pool '{pool_name}': {len(resources_to_cleanup)} resources")
                
            except Exception as e:
                logger.error(f"Error cleaning up resource pool '{pool_name}': {e}")
    
    def emergency_cleanup(self):
        """Emergency cleanup procedure for critical memory situations"""
        logger.warning("🚨 Initiating emergency cleanup procedure")
        
        # Force multiple garbage collections
        for _ in range(3):
            self.force_garbage_collection()
        
        # Clear all resource pools
        self._cleanup_resource_pools()
        
        # Clear internal caches
        self._clear_internal_caches()
        
        # Log memory usage after cleanup
        process = psutil.Process()
        memory_after = process.memory_info().rss / 1024 / 1024
        logger.info(f"🧹 Emergency cleanup completed - memory usage: {memory_after:.1f}MB")
    
    def _clear_internal_caches(self):
        """Clear internal caches to free memory"""
        # Clear memory history (keep last 100 entries)
        with self._lock:
            if len(self.memory_history) > 100:
                recent_history = list(self.memory_history)[-100:]
                self.memory_history.clear()
                self.memory_history.extend(recent_history)
        
        # Clear old alerts
        current_time = datetime.now(timezone.utc)
        expired_alerts = [
            key for key, alert in self.active_alerts.items()
            if (current_time - alert.timestamp).total_seconds() > 3600  # 1 hour
        ]
        
        for key in expired_alerts:
            del self.active_alerts[key]
        
        logger.info("🧹 Cleared internal caches")
    
    def create_resource_pool(self, 
                           name: str,
                           create_fn: Callable,
                           cleanup_fn: Callable,
                           max_size: int = 100) -> ResourcePool:
        """Create a managed resource pool"""
        pool = ResourcePool(name, create_fn, cleanup_fn, max_size)
        self.resource_pools[name] = pool
        logger.info(f"📦 Created resource pool: {name}")
        return pool
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        if not self.memory_history:
            return {}
        
        latest = self.memory_history[-1]
        
        # Calculate averages over last hour
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_snapshots = [s for s in self.memory_history if s.timestamp >= hour_ago]
        
        if recent_snapshots:
            avg_memory = sum(s.rss_mb for s in recent_snapshots) / len(recent_snapshots)
            peak_memory = max(s.rss_mb for s in recent_snapshots)
            min_memory = min(s.rss_mb for s in recent_snapshots)
        else:
            avg_memory = peak_memory = min_memory = latest.rss_mb
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current': asdict(latest),
            'last_hour': {
                'avg_memory_mb': round(avg_memory, 1),
                'peak_memory_mb': round(peak_memory, 1),
                'min_memory_mb': round(min_memory, 1),
                'samples': len(recent_snapshots)
            },
            'growth_rate_mb_per_min': self._calculate_memory_growth_rate(),
            'active_alerts': len(self.active_alerts),
            'resource_pools': {
                name: pool.get_stats() 
                for name, pool in self.resource_pools.items()
            },
            'profiler_snapshot': self.profiler.take_snapshot(),
            'gc_stats': {
                'total_objects': len(gc.get_objects()),
                'garbage_count': len(gc.garbage),
                'thresholds': gc.get_threshold()
            }
        }
    
    def set_resource_limits(self, limits: ResourceLimit):
        """Set resource limits"""
        self.resource_limits = limits
        
        # Apply memory limit if possible
        try:
            resource.setrlimit(resource.RLIMIT_AS, (limits.memory_limit_mb * 1024 * 1024, -1))
            logger.info(f"🔒 Set memory limit: {limits.memory_limit_mb}MB")
        except Exception as e:
            logger.warning(f"Could not set memory limit: {e}")
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get memory optimization recommendations"""
        recommendations = []
        
        if not self.memory_history:
            return recommendations
        
        latest = self.memory_history[-1]
        growth_rate = self._calculate_memory_growth_rate()
        
        # High memory usage
        if latest.rss_mb > 1024:
            recommendations.append({
                'type': 'high_memory_usage',
                'priority': 'high',
                'message': f'High memory usage: {latest.rss_mb:.1f}MB',
                'suggestions': [
                    'Implement more aggressive garbage collection',
                    'Review and optimize data structures',
                    'Consider using memory-mapped files for large datasets',
                    'Implement object pooling for frequently created objects'
                ]
            })
        
        # Memory growth
        if growth_rate > 10:
            recommendations.append({
                'type': 'memory_growth',
                'priority': 'high',
                'message': f'High memory growth rate: {growth_rate:.1f}MB/min',
                'suggestions': [
                    'Check for memory leaks in long-running processes',
                    'Implement periodic cleanup routines',
                    'Review caching strategies and TTL settings',
                    'Consider using weak references for caches'
                ]
            })
        
        # High GC activity
        if len(self.memory_history) > 1:
            gc_activity = latest.gc_collections - self.memory_history[-2].gc_collections
            if gc_activity > 5:
                recommendations.append({
                    'type': 'high_gc_activity',
                    'priority': 'medium',
                    'message': 'High garbage collection activity detected',
                    'suggestions': [
                        'Optimize object creation patterns',
                        'Use object pools for frequently created objects',
                        'Tune garbage collection parameters',
                        'Consider using generators for large datasets'
                    ]
                })
        
        return recommendations

# Global memory manager instance
memory_manager = MemoryManager()

# Convenience functions
def start_memory_monitoring():
    """Start global memory monitoring"""
    memory_manager.start_monitoring()

def get_memory_stats() -> Dict[str, Any]:
    """Get global memory statistics"""
    return memory_manager.get_memory_stats()

def force_cleanup():
    """Force memory cleanup"""
    memory_manager.force_garbage_collection()

@contextmanager
def memory_limit(limit_mb: int):
    """Context manager for temporary memory limits"""
    old_limit = resource.getrlimit(resource.RLIMIT_AS)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit_mb * 1024 * 1024, old_limit[1]))
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_AS, old_limit)

def memory_profiler(func):
    """Decorator to profile memory usage of functions"""
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        mem_before = process.memory_info().rss
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        mem_after = process.memory_info().rss
        mem_diff = (mem_after - mem_before) / 1024 / 1024
        
        logger.info(f"🔍 Memory profile {func.__name__}: {mem_diff:+.1f}MB in {(end_time - start_time) * 1000:.1f}ms")
        
        return result
    return wrapper

if __name__ == "__main__":
    # Test memory manager
    memory_manager.start_monitoring()
    
    try:
        # Simulate some memory usage
        data = []
        for i in range(1000):
            data.append([0] * 1000)  # Allocate some memory
            time.sleep(0.01)
        
        # Get stats
        stats = memory_manager.get_memory_stats()
        print(f"Memory stats: {stats}")
        
        # Force cleanup
        memory_manager.force_garbage_collection()
        
    finally:
        memory_manager.stop_monitoring()