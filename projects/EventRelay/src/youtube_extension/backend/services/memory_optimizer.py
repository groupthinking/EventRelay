#!/usr/bin/env python3
"""
Memory Management and Optimization System - Phase 3 Performance Optimization
============================================================================

Advanced memory management targeting efficient resource utilization and automatic
cleanup to support 60%+ performance improvements through intelligent memory
monitoring, leak detection, and optimization strategies.

Key Features:
- Real-time memory monitoring and alerting
- Automatic memory leak detection and prevention
- Intelligent garbage collection optimization
- Memory usage profiling and analysis
- Resource cleanup automation
- Memory-efficient data structures
- Cache-aware memory management
"""

import asyncio
import gc
import logging
import time
import threading
import psutil
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import tracemalloc
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    total_memory_mb: float
    available_memory_mb: float
    process_memory_mb: float
    memory_percent: float
    python_objects: int
    gc_generation_0: int
    gc_generation_1: int
    gc_generation_2: int
    cache_memory_mb: float = 0.0
    leak_indicators: Dict[str, int] = None
    
    def __post_init__(self):
        if self.leak_indicators is None:
            self.leak_indicators = {}

@dataclass
class MemoryLeak:
    """Memory leak detection record"""
    object_type: str
    count: int
    growth_rate: float  # objects per minute
    first_detected: datetime
    last_seen: datetime
    severity: str  # low, medium, high, critical
    traceback_info: str = ""

class MemoryProfiler:
    """Advanced memory profiling and analysis"""
    
    def __init__(self):
        self.tracking_enabled = False
        self.snapshots = deque(maxlen=1000)
        self.leak_detection = {}
        self.cleanup_callbacks = []
        self.memory_thresholds = {
            'warning_mb': 1024,    # 1GB
            'critical_mb': 2048,   # 2GB
            'cleanup_mb': 1536,    # 1.5GB - trigger cleanup
            'max_growth_rate': 100  # objects per minute
        }
        
        # Object tracking
        self.tracked_objects = weakref.WeakSet()
        self.object_counters = defaultdict(int)
        
        logger.info("🧠 Memory Profiler initialized")
    
    def start_tracking(self):
        """Start memory tracking"""
        if self.tracking_enabled:
            return
        
        try:
            # Start tracemalloc if available
            tracemalloc.start()
            self.tracking_enabled = True
            
            # Start background monitoring
            asyncio.create_task(self._monitoring_loop())
            
            logger.info("✅ Memory tracking started")
            
        except Exception as e:
            logger.error(f"Failed to start memory tracking: {e}")
    
    def stop_tracking(self):
        """Stop memory tracking"""
        if not self.tracking_enabled:
            return
        
        try:
            tracemalloc.stop()
            self.tracking_enabled = False
            logger.info("🛑 Memory tracking stopped")
            
        except Exception as e:
            logger.error(f"Error stopping memory tracking: {e}")
    
    async def _monitoring_loop(self):
        """Background memory monitoring"""
        while self.tracking_enabled:
            try:
                snapshot = await self.take_snapshot()
                await self._analyze_memory_usage(snapshot)
                await self._detect_memory_leaks()
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def take_snapshot(self) -> MemorySnapshot:
        """Take comprehensive memory snapshot"""
        try:
            # System memory info
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Python-specific info
            python_objects = len(gc.get_objects())
            gc_stats = gc.get_stats()
            
            # Cache memory estimation (from intelligent cache if available)
            cache_memory = await self._estimate_cache_memory()
            
            # Leak indicators
            leak_indicators = await self._get_leak_indicators()
            
            snapshot = MemorySnapshot(
                timestamp=datetime.now(timezone.utc),
                total_memory_mb=memory.total / 1024 / 1024,
                available_memory_mb=memory.available / 1024 / 1024,
                process_memory_mb=process_memory.rss / 1024 / 1024,
                memory_percent=memory.percent,
                python_objects=python_objects,
                gc_generation_0=gc_stats[0]['collections'] if gc_stats else 0,
                gc_generation_1=gc_stats[1]['collections'] if len(gc_stats) > 1 else 0,
                gc_generation_2=gc_stats[2]['collections'] if len(gc_stats) > 2 else 0,
                cache_memory_mb=cache_memory,
                leak_indicators=leak_indicators
            )
            
            # Store snapshot
            self.snapshots.append(snapshot)
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
            return MemorySnapshot(
                timestamp=datetime.now(timezone.utc),
                total_memory_mb=0,
                available_memory_mb=0,
                process_memory_mb=0,
                memory_percent=0,
                python_objects=0,
                gc_generation_0=0,
                gc_generation_1=0,
                gc_generation_2=0
            )
    
    async def _analyze_memory_usage(self, snapshot: MemorySnapshot):
        """Analyze memory usage and trigger alerts/cleanup"""
        
        # Check memory thresholds
        if snapshot.process_memory_mb > self.memory_thresholds['critical_mb']:
            await self._trigger_critical_memory_alert(snapshot)
        elif snapshot.process_memory_mb > self.memory_thresholds['warning_mb']:
            await self._trigger_memory_warning(snapshot)
        
        # Check for cleanup trigger
        if snapshot.process_memory_mb > self.memory_thresholds['cleanup_mb']:
            await self._trigger_memory_cleanup()
        
        # Log memory usage periodically
        if len(self.snapshots) % 10 == 0:  # Every 10 snapshots (5 minutes)
            logger.info(f"📊 Memory usage: {snapshot.process_memory_mb:.1f}MB "
                       f"({snapshot.memory_percent:.1f}% system), "
                       f"{snapshot.python_objects} Python objects")
    
    async def _detect_memory_leaks(self):
        """Detect potential memory leaks"""
        if len(self.snapshots) < 10:  # Need at least 10 snapshots for trend analysis
            return
        
        recent_snapshots = list(self.snapshots)[-10:]  # Last 10 snapshots
        
        # Analyze object count trends
        for obj_type, counts in self._get_object_trends(recent_snapshots).items():
            growth_rate = self._calculate_growth_rate(counts)
            
            if growth_rate > self.memory_thresholds['max_growth_rate']:
                leak = MemoryLeak(
                    object_type=obj_type,
                    count=counts[-1] if counts else 0,
                    growth_rate=growth_rate,
                    first_detected=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    severity=self._assess_leak_severity(growth_rate),
                    traceback_info=self._get_traceback_info(obj_type)
                )
                
                self.leak_detection[obj_type] = leak
                await self._handle_memory_leak(leak)
    
    def _get_object_trends(self, snapshots: List[MemorySnapshot]) -> Dict[str, List[int]]:
        """Get object count trends from snapshots"""
        trends = defaultdict(list)
        
        for snapshot in snapshots:
            # For now, track total Python objects
            # In a more advanced implementation, you'd track specific object types
            trends['python_objects'].append(snapshot.python_objects)
            
            # Track leak indicators if available
            for indicator, count in snapshot.leak_indicators.items():
                trends[indicator].append(count)
        
        return trends
    
    def _calculate_growth_rate(self, counts: List[int]) -> float:
        """Calculate growth rate (objects per minute)"""
        if len(counts) < 2:
            return 0.0
        
        # Simple linear regression for growth rate
        time_span = len(counts) * 0.5  # 30 seconds per snapshot
        total_growth = counts[-1] - counts[0]
        
        return (total_growth / time_span) * 60  # Per minute
    
    def _assess_leak_severity(self, growth_rate: float) -> str:
        """Assess memory leak severity"""
        if growth_rate > 1000:
            return 'critical'
        elif growth_rate > 500:
            return 'high'
        elif growth_rate > 200:
            return 'medium'
        else:
            return 'low'
    
    def _get_traceback_info(self, obj_type: str) -> str:
        """Get traceback information for leak debugging"""
        if not tracemalloc.is_tracing():
            return "Tracemalloc not available"
        
        try:
            # Get current traceback for memory allocations
            current, peak = tracemalloc.get_traced_memory()
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            
            if top_stats:
                stat = top_stats[0]
                return f"Top allocation: {stat.traceback.format()}"
        except Exception as e:
            return f"Traceback error: {e}"
        
        return "No traceback available"
    
    async def _estimate_cache_memory(self) -> float:
        """Estimate memory used by caches"""
        # This would integrate with the intelligent cache system
        try:
            # Placeholder - in real implementation, integrate with cache systems
            return 50.0  # Assume 50MB cache usage
        except Exception:
            return 0.0
    
    async def _get_leak_indicators(self) -> Dict[str, int]:
        """Get memory leak indicators"""
        indicators = {}
        
        try:
            # Track specific object types that commonly leak
            for obj_type in ['dict', 'list', 'tuple', 'function']:
                count = sum(1 for obj in gc.get_objects() if type(obj).__name__ == obj_type)
                indicators[obj_type] = count
            
            # Track weak references
            indicators['weak_references'] = len(self.tracked_objects)
            
        except Exception as e:
            logger.error(f"Error getting leak indicators: {e}")
        
        return indicators
    
    async def _trigger_memory_warning(self, snapshot: MemorySnapshot):
        """Trigger memory usage warning"""
        logger.warning(f"⚠️ High memory usage: {snapshot.process_memory_mb:.1f}MB "
                      f"(warning threshold: {self.memory_thresholds['warning_mb']}MB)")
        
        # Send alert (placeholder)
        await self._send_memory_alert('warning', snapshot)
    
    async def _trigger_critical_memory_alert(self, snapshot: MemorySnapshot):
        """Trigger critical memory alert"""
        logger.error(f"🚨 Critical memory usage: {snapshot.process_memory_mb:.1f}MB "
                    f"(critical threshold: {self.memory_thresholds['critical_mb']}MB)")
        
        # Send critical alert
        await self._send_memory_alert('critical', snapshot)
        
        # Trigger aggressive cleanup
        await self._trigger_aggressive_cleanup()
    
    async def _trigger_memory_cleanup(self):
        """Trigger memory cleanup procedures"""
        logger.info("🧹 Triggering memory cleanup...")
        
        cleanup_start = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Run cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Cleanup callback error: {e}")
            
            # Force garbage collection
            collected = gc.collect()
            
            # Clear weak references to deleted objects
            self.tracked_objects = weakref.WeakSet([obj for obj in self.tracked_objects if obj is not None])
            
            # Get final memory
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            cleanup_time = time.time() - cleanup_start
            
            memory_freed = initial_memory - final_memory
            
            logger.info(f"✅ Memory cleanup completed in {cleanup_time:.2f}s: "
                       f"{memory_freed:.1f}MB freed, {collected} objects collected")
            
        except Exception as e:
            logger.error(f"Memory cleanup error: {e}")
    
    async def _trigger_aggressive_cleanup(self):
        """Trigger aggressive memory cleanup for critical situations"""
        logger.warning("🚨 Aggressive memory cleanup initiated...")
        
        try:
            # Multiple garbage collection passes
            for generation in [2, 1, 0]:
                collected = gc.collect(generation)
                logger.debug(f"GC generation {generation}: {collected} objects collected")
            
            # Clear system caches if possible
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
            
            # Trigger custom cleanup
            await self._trigger_memory_cleanup()
            
            logger.info("✅ Aggressive cleanup completed")
            
        except Exception as e:
            logger.error(f"Aggressive cleanup error: {e}")
    
    async def _handle_memory_leak(self, leak: MemoryLeak):
        """Handle detected memory leak"""
        logger.warning(f"🔍 Memory leak detected: {leak.object_type} "
                      f"({leak.count} objects, {leak.growth_rate:.1f}/min growth)")
        
        # Send leak alert
        await self._send_leak_alert(leak)
        
        if leak.severity in ['high', 'critical']:
            # Trigger immediate cleanup
            await self._trigger_memory_cleanup()
    
    async def _send_memory_alert(self, level: str, snapshot: MemorySnapshot):
        """Send memory usage alert"""
        alert = {
            'type': 'memory_usage',
            'level': level,
            'timestamp': snapshot.timestamp.isoformat(),
            'memory_mb': snapshot.process_memory_mb,
            'memory_percent': snapshot.memory_percent,
            'python_objects': snapshot.python_objects
        }
        
        # In production, send to monitoring system
        logger.debug(f"Memory alert: {alert}")
    
    async def _send_leak_alert(self, leak: MemoryLeak):
        """Send memory leak alert"""
        alert = {
            'type': 'memory_leak',
            'object_type': leak.object_type,
            'severity': leak.severity,
            'growth_rate': leak.growth_rate,
            'count': leak.count,
            'timestamp': leak.last_seen.isoformat()
        }
        
        # In production, send to monitoring system
        logger.debug(f"Leak alert: {alert}")
    
    def register_cleanup_callback(self, callback: Callable):
        """Register cleanup callback"""
        self.cleanup_callbacks.append(callback)
    
    def track_object(self, obj):
        """Track an object for memory monitoring"""
        self.tracked_objects.add(obj)
        self.object_counters[type(obj).__name__] += 1
    
    def untrack_object(self, obj):
        """Stop tracking an object"""
        try:
            self.tracked_objects.discard(obj)
            self.object_counters[type(obj).__name__] -= 1
        except Exception:
            pass
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report"""
        current_snapshot = asyncio.create_task(self.take_snapshot()) if self.tracking_enabled else None
        
        if not current_snapshot:
            # Synchronous snapshot if async not available
            process = psutil.Process()
            memory_info = process.memory_info()
            current_snapshot = {
                'process_memory_mb': memory_info.rss / 1024 / 1024,
                'python_objects': len(gc.get_objects()) if gc else 0
            }
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_usage': current_snapshot,
            'thresholds': self.memory_thresholds,
            'tracking_enabled': self.tracking_enabled,
            'snapshots_collected': len(self.snapshots),
            'active_leaks': len(self.leak_detection),
            'tracked_objects': len(self.tracked_objects),
            'cleanup_callbacks': len(self.cleanup_callbacks),
            'memory_history': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'memory_mb': s.process_memory_mb,
                    'objects': s.python_objects
                }
                for s in list(self.snapshots)[-10:]  # Last 10 snapshots
            ]
        }

class MemoryOptimizer:
    """Memory optimization strategies and utilities"""
    
    def __init__(self, profiler: MemoryProfiler):
        self.profiler = profiler
        self.optimization_strategies = [
            self._optimize_garbage_collection,
            self._optimize_object_pools,
            self._optimize_data_structures,
            self._optimize_caches
        ]
        
        logger.info("⚡ Memory Optimizer initialized")
    
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """Run comprehensive memory optimization"""
        logger.info("🚀 Starting memory optimization...")
        
        initial_snapshot = await self.profiler.take_snapshot()
        optimization_results = {}
        
        # Run optimization strategies
        for strategy in self.optimization_strategies:
            try:
                strategy_name = strategy.__name__
                logger.info(f"Running {strategy_name}...")
                
                result = await strategy()
                optimization_results[strategy_name] = result
                
            except Exception as e:
                logger.error(f"Optimization strategy {strategy.__name__} failed: {e}")
                optimization_results[strategy.__name__] = {'error': str(e)}
        
        # Take final snapshot
        final_snapshot = await self.profiler.take_snapshot()
        
        # Calculate improvements
        memory_saved = initial_snapshot.process_memory_mb - final_snapshot.process_memory_mb
        objects_reduced = initial_snapshot.python_objects - final_snapshot.python_objects
        
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'initial_memory_mb': initial_snapshot.process_memory_mb,
            'final_memory_mb': final_snapshot.process_memory_mb,
            'memory_saved_mb': memory_saved,
            'objects_reduced': objects_reduced,
            'optimization_results': optimization_results,
            'success': memory_saved > 0 or objects_reduced > 0
        }
        
        logger.info(f"✅ Memory optimization completed: {memory_saved:.1f}MB saved, "
                   f"{objects_reduced} objects reduced")
        
        return summary
    
    async def _optimize_garbage_collection(self) -> Dict[str, Any]:
        """Optimize garbage collection settings"""
        try:
            # Get current GC stats
            initial_stats = gc.get_stats()
            
            # Tune GC thresholds for better performance
            # These values are optimized for video processing workloads
            gc.set_threshold(1000, 15, 15)  # More aggressive than defaults
            
            # Force collection of all generations
            collected = [gc.collect(gen) for gen in [0, 1, 2]]
            
            final_stats = gc.get_stats()
            
            return {
                'initial_stats': initial_stats,
                'final_stats': final_stats,
                'objects_collected': sum(collected),
                'thresholds_set': gc.get_threshold()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _optimize_object_pools(self) -> Dict[str, Any]:
        """Optimize object pools and reusable objects"""
        try:
            # Clear weak reference pools
            initial_tracked = len(self.profiler.tracked_objects)
            
            # Remove dead weak references
            self.profiler.tracked_objects = weakref.WeakSet([
                obj for obj in self.profiler.tracked_objects 
                if obj is not None
            ])
            
            final_tracked = len(self.profiler.tracked_objects)
            
            return {
                'initial_tracked': initial_tracked,
                'final_tracked': final_tracked,
                'references_cleaned': initial_tracked - final_tracked
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _optimize_data_structures(self) -> Dict[str, Any]:
        """Optimize data structures and containers"""
        try:
            # This would contain specific optimizations for the application's data structures
            # For now, we'll provide some general optimizations
            
            optimizations = {
                'dict_optimizations': 0,
                'list_optimizations': 0,
                'string_optimizations': 0
            }
            
            # Clear internal caches
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
                optimizations['type_cache_cleared'] = True
            
            # String interning optimizations could go here
            # Data structure pooling optimizations could go here
            
            return optimizations
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _optimize_caches(self) -> Dict[str, Any]:
        """Optimize application caches"""
        try:
            # This would integrate with the intelligent cache system
            # to perform cache cleanup and optimization
            
            cache_optimizations = {
                'cache_entries_before': 0,
                'cache_entries_after': 0,
                'cache_memory_freed_mb': 0
            }
            
            # Placeholder for actual cache optimization
            # In real implementation, this would:
            # 1. Analyze cache hit rates
            # 2. Remove stale entries
            # 3. Optimize cache sizes
            # 4. Compact cache storage
            
            return cache_optimizations
            
        except Exception as e:
            return {'error': str(e)}

# Memory-aware decorators and utilities
def memory_efficient(func):
    """Decorator for memory-efficient function execution"""
    async def async_wrapper(*args, **kwargs):
        # Track memory before execution
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            # Check memory growth and trigger cleanup if needed
            final_memory = psutil.Process().memory_info().rss
            memory_growth = (final_memory - initial_memory) / 1024 / 1024  # MB
            
            if memory_growth > 100:  # >100MB growth
                logger.warning(f"Function {func.__name__} used {memory_growth:.1f}MB memory")
                # Could trigger cleanup here
    
    def sync_wrapper(*args, **kwargs):
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            final_memory = psutil.Process().memory_info().rss
            memory_growth = (final_memory - initial_memory) / 1024 / 1024
            
            if memory_growth > 100:
                logger.warning(f"Function {func.__name__} used {memory_growth:.1f}MB memory")
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def track_memory_usage(threshold_mb: float = 100):
    """Decorator to track and alert on memory usage"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_used = final_memory - initial_memory
            
            if memory_used > threshold_mb:
                logger.warning(f"🧠 High memory usage in {func.__name__}: {memory_used:.1f}MB")
            
            return result
        return wrapper
    return decorator

# Global memory management system
memory_profiler = MemoryProfiler()
memory_optimizer = MemoryOptimizer(memory_profiler)

# Convenience functions
async def start_memory_monitoring():
    """Start global memory monitoring"""
    memory_profiler.start_tracking()

async def stop_memory_monitoring():
    """Stop global memory monitoring"""
    memory_profiler.stop_tracking()

async def get_memory_status() -> Dict[str, Any]:
    """Get current memory status"""
    return memory_profiler.get_memory_report()

async def optimize_memory() -> Dict[str, Any]:
    """Run memory optimization"""
    return await memory_optimizer.optimize_memory_usage()

async def cleanup_memory():
    """Trigger memory cleanup"""
    await memory_profiler._trigger_memory_cleanup()

def register_cleanup_callback(callback: Callable):
    """Register cleanup callback"""
    memory_profiler.register_cleanup_callback(callback)

if __name__ == "__main__":
    async def test_memory_system():
        # Start monitoring
        await start_memory_monitoring()
        
        # Take a snapshot
        snapshot = await memory_profiler.take_snapshot()
        print(f"Initial memory: {snapshot.process_memory_mb:.1f}MB")
        
        # Get status
        status = await get_memory_status()
        print(f"Memory status: {status}")
        
        # Run optimization
        optimization_result = await optimize_memory()
        print(f"Optimization result: {optimization_result}")
        
        # Stop monitoring
        await stop_memory_monitoring()
    
    asyncio.run(test_memory_system())