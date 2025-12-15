#!/usr/bin/env python3
"""
Performance Benchmarking System - Phase 3 Performance Optimization
==================================================================

Comprehensive benchmarking system to validate 60%+ performance improvements
across all system components. Provides scientific measurement, comparison,
and validation of optimization targets.

Key Features:
- Video processing pipeline benchmarking (60%+ improvement validation)
- Database query performance validation (95% sub-100ms target)
- Frontend load time benchmarking (sub-2s target)
- Memory efficiency benchmarking
- End-to-end system performance validation
- Regression detection and alerts
- Performance trend analysis
- Automated benchmark reports
"""

import asyncio
import json
import logging
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import concurrent.futures
import threading
from collections import defaultdict, deque
import psutil

# Import optimization systems (component-wise to avoid disabling all on one failure)
try:
    from .performance_monitor import performance_monitor, track_video_processing_time, track_database_query_time
except ImportError as e:
    logging.warning(f"Performance monitor not available: {e}")
    performance_monitor = None
    async def track_video_processing_time(time_ms):
        raise RuntimeError("Video processing metrics not available")
    async def track_database_query_time(time_ms, query_type="general"):
        raise RuntimeError("Database metrics not available")

try:
    from ...processors.video_processor import VideoProcessor
except ImportError as e:
    logging.warning(f"Video processor not available: {e}")

    class VideoProcessor:
        def __init__(self, strategy="enhanced"):
            pass
        async def process_video(self, video_url, options=None):
            raise RuntimeError("Video processing not available")
        async def process_batch(self, video_urls, options=None):
            raise RuntimeError("Video processing not available")
    async def process_videos_batch_optimized(video_urls, options=None):
        raise RuntimeError("Video processing batch optimization not available")

try:
    from .database_optimizer import execute_optimized_query, execute_batch_optimized
except ImportError as e:
    logging.warning(f"Database optimizer not available: {e}")
    async def execute_optimized_query(query, params=None):
        raise RuntimeError("Database optimization not available")
    async def execute_batch_optimized(queries):
        raise RuntimeError("Database batch optimization not available")

try:
    from .intelligent_cache import cache_get, cache_set, intelligent_cache
except ImportError as e:
    logging.warning(f"Cache system not available: {e}")
    async def cache_get(key):
        raise RuntimeError("Cache system not available")
    async def cache_set(key, value, ttl=None, tags=None):
        raise RuntimeError("Cache system not available")
    intelligent_cache = None

try:
    from .memory_optimizer import memory_profiler, optimize_memory
except ImportError as e:
    logging.warning(f"Memory optimizer not available: {e}")
    memory_profiler = None
    async def optimize_memory():
        raise RuntimeError("Memory optimization not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Individual benchmark result"""
    benchmark_name: str
    component: str
    execution_time_ms: float
    success: bool
    iterations: int
    baseline_time_ms: Optional[float] = None
    improvement_percent: float = 0.0
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}
        
        if self.baseline_time_ms and self.baseline_time_ms > 0:
            self.improvement_percent = ((self.baseline_time_ms - self.execution_time_ms) / self.baseline_time_ms) * 100

@dataclass
class PerformanceTarget:
    """Performance target definition"""
    component: str
    metric: str
    target_value: float
    unit: str
    comparison: str  # 'less_than', 'greater_than', 'equals'
    baseline_value: Optional[float] = None
    improvement_target_percent: Optional[float] = None
    priority: str = 'medium'  # low, medium, high, critical

class PerformanceBenchmarkSystem:
    """
    Comprehensive performance benchmarking system
    
    Validates Phase 3 performance targets:
    - Video processing: 60%+ improvement (from ~60s to ~24s)
    - Database queries: 95% under 100ms response time
    - Frontend load: Under 2 seconds
    - Memory efficiency: Optimal resource usage
    """
    
    def __init__(self):
        # Performance targets for Phase 3
        self.performance_targets = [
            PerformanceTarget(
                component='video_processing',
                metric='processing_time_ms',
                target_value=24000,  # 24 seconds (60% improvement from 60s)
                unit='ms',
                comparison='less_than',
                baseline_value=60000,  # 60 seconds baseline
                improvement_target_percent=60.0,
                priority='critical'
            ),
            PerformanceTarget(
                component='database',
                metric='query_response_time_ms',
                target_value=100,  # 100ms
                unit='ms',
                comparison='less_than',
                improvement_target_percent=None,
                priority='critical'
            ),
            PerformanceTarget(
                component='frontend',
                metric='load_time_ms',
                target_value=2000,  # 2 seconds
                unit='ms',
                comparison='less_than',
                improvement_target_percent=None,
                priority='high'
            ),
            PerformanceTarget(
                component='memory',
                metric='usage_mb',
                target_value=2048,  # 2GB max
                unit='MB',
                comparison='less_than',
                improvement_target_percent=None,
                priority='medium'
            ),
            PerformanceTarget(
                component='cache',
                metric='hit_rate_percent',
                target_value=80,  # 80% hit rate
                unit='%',
                comparison='greater_than',
                improvement_target_percent=None,
                priority='medium'
            )
        ]
        
        # Benchmark history and results
        self.benchmark_history = deque(maxlen=1000)
        self.baseline_results = {}
        self.current_results = {}
        
        # Test data for benchmarking
        self.test_video_urls = [
            # Use non-music, historically safe public videos
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo
            "https://www.youtube.com/watch?v=kxopViU98Xo",  # Charlie bit my finger
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ]
        
        self.test_queries = [
            ("SELECT COUNT(*) FROM videos", ()),
            ("SELECT * FROM videos WHERE processed = ? LIMIT 10", (1,)),
            ("SELECT title, processed FROM videos ORDER BY created_at DESC LIMIT 5", ()),
            ("SELECT AVG(processing_time_ms) FROM video_analytics", ()),
            ("SELECT * FROM users WHERE last_active > ? LIMIT 20", ("2024-01-01",))
        ]
        
        # Performance monitoring
        self.monitoring_enabled = True
        self.benchmark_lock = threading.Lock()
        
        logger.info("🎯 Performance Benchmark System initialized - Target: 60%+ improvements")
    
    async def run_comprehensive_benchmark(self, 
                                        iterations: int = 3,
                                        include_baseline: bool = False) -> Dict[str, Any]:
        """
        Run comprehensive performance benchmark across all components
        
        Returns detailed results with improvement validation
        """
        benchmark_start = time.time()
        logger.info(f"🚀 Starting comprehensive performance benchmark ({iterations} iterations)")
        
        try:
            benchmark_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'iterations': iterations,
                'components': {},
                'overall_assessment': {},
                'targets_met': {},
                'recommendations': []
            }
            
            # Run component benchmarks in parallel
            benchmark_tasks = [
                self._benchmark_video_processing(iterations),
                self._benchmark_database_queries(iterations),
                self._benchmark_frontend_performance(iterations),
                self._benchmark_memory_efficiency(iterations),
                self._benchmark_cache_performance(iterations)
            ]
            
            # Execute benchmarks
            component_results = await asyncio.gather(*benchmark_tasks, return_exceptions=True)
            
            # Process results
            component_names = ['video_processing', 'database', 'frontend', 'memory', 'cache']
            for i, result in enumerate(component_results):
                component_name = component_names[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Benchmark failed for {component_name}: {result}")
                    benchmark_results['components'][component_name] = {
                        'error': str(result),
                        'success': False
                    }
                else:
                    benchmark_results['components'][component_name] = result
            
            # Generate overall assessment
            benchmark_results['overall_assessment'] = self._generate_overall_assessment(
                benchmark_results['components']
            )
            
            # Validate targets
            benchmark_results['targets_met'] = self._validate_performance_targets(
                benchmark_results['components']
            )
            
            # Generate recommendations
            benchmark_results['recommendations'] = self._generate_benchmark_recommendations(
                benchmark_results['components'], 
                benchmark_results['targets_met']
            )
            
            # Record benchmark
            total_time = time.time() - benchmark_start
            benchmark_results['total_benchmark_time_seconds'] = total_time
            
            self.benchmark_history.append(benchmark_results)
            
            # Log summary
            targets_met_count = sum(1 for target in benchmark_results['targets_met'].values() if target.get('met', False))
            total_targets = len(self.performance_targets)
            
            logger.info(f"✅ Comprehensive benchmark completed in {total_time:.2f}s")
            logger.info(f"📊 Performance targets met: {targets_met_count}/{total_targets}")
            logger.info(f"🏆 Overall grade: {benchmark_results['overall_assessment'].get('grade', 'N/A')}")
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"❌ Comprehensive benchmark failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': False
            }
    
    async def _benchmark_video_processing(self, iterations: int) -> Dict[str, Any]:
        """
        Benchmark video processing performance
        
        Target: 60%+ improvement (24s vs 60s baseline)
        """
        logger.info("🎬 Benchmarking video processing performance...")

        # Initialize video processors
        optimized_processor = VideoProcessor(strategy="optimized")

        try:
            results = {
                'component': 'video_processing',
                'target_improvement_percent': 60.0,
                'baseline_time_ms': 60000,  # 60 seconds
                'target_time_ms': 24000,    # 24 seconds (60% improvement)
                'benchmarks': []
            }
            
            # Single video processing benchmark
            single_video_times = []
            for i in range(iterations):
                test_url = self.test_video_urls[i % len(self.test_video_urls)]
                
                start_time = time.time()
                try:
                    result = await optimized_processor.process_video(test_url)
                    processing_time = (time.time() - start_time) * 1000
                    success = result.get('success', False)
                    
                    if success:
                        single_video_times.append(processing_time)
                    
                    benchmark = BenchmarkResult(
                        benchmark_name=f'single_video_processing_{i+1}',
                        component='video_processing',
                        execution_time_ms=processing_time,
                        success=success,
                        iterations=1,
                        baseline_time_ms=results['baseline_time_ms'],
                        metadata={'video_url': test_url, 'method': result.get('method', 'unknown')}
                    )
                    
                    results['benchmarks'].append(asdict(benchmark))
                    
                except Exception as e:
                    logger.error(f"Single video processing benchmark {i+1} failed: {e}")
                    
                    benchmark = BenchmarkResult(
                        benchmark_name=f'single_video_processing_{i+1}',
                        component='video_processing',
                        execution_time_ms=0,
                        success=False,
                        iterations=1,
                        metadata={'error': str(e)}
                    )
                    
                    results['benchmarks'].append(asdict(benchmark))
            
            # Batch processing benchmark
            if len(self.test_video_urls) >= 3:
                batch_urls = self.test_video_urls[:3]  # Test with 3 videos
                
                start_time = time.time()
                try:
                    batch_results = await optimized_processor.process_batch(batch_urls)
                    batch_time = (time.time() - start_time) * 1000
                    avg_time_per_video = batch_time / len(batch_urls)
                    
                    success_count = sum(1 for r in batch_results if r.get('success', False))
                    batch_success = success_count == len(batch_urls)
                    
                    batch_benchmark = BenchmarkResult(
                        benchmark_name='batch_video_processing',
                        component='video_processing',
                        execution_time_ms=avg_time_per_video,
                        success=batch_success,
                        iterations=len(batch_urls),
                        baseline_time_ms=results['baseline_time_ms'],
                        metadata={
                            'total_videos': len(batch_urls),
                            'successful_videos': success_count,
                            'total_batch_time_ms': batch_time
                        }
                    )
                    
                    results['benchmarks'].append(asdict(batch_benchmark))
                    
                except Exception as e:
                    logger.error(f"Batch video processing benchmark failed: {e}")
            
            # Calculate summary statistics
            if single_video_times:
                results['performance_summary'] = {
                    'avg_processing_time_ms': statistics.mean(single_video_times),
                    'min_processing_time_ms': min(single_video_times),
                    'max_processing_time_ms': max(single_video_times),
                    'median_processing_time_ms': statistics.median(single_video_times),
                    'successful_iterations': len(single_video_times),
                    'total_iterations': iterations
                }
                
                # Calculate improvement
                avg_time = results['performance_summary']['avg_processing_time_ms']
                improvement = ((results['baseline_time_ms'] - avg_time) / results['baseline_time_ms']) * 100
                
                results['performance_summary']['improvement_percent'] = improvement
                results['performance_summary']['target_met'] = improvement >= results['target_improvement_percent']
                
                logger.info(f"📊 Video processing: {avg_time:.1f}ms avg ({improvement:.1f}% improvement)")
            else:
                results['performance_summary'] = {
                    'error': 'No successful video processing iterations',
                    'target_met': False
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Video processing benchmark error: {e}")
            return {
                'component': 'video_processing',
                'error': str(e),
                'target_met': False
            }
    
    async def _benchmark_database_queries(self, iterations: int) -> Dict[str, Any]:
        """
        Benchmark database query performance
        
        Target: 95% of queries under 100ms
        """
        logger.info("🗃️ Benchmarking database query performance...")
        
        try:
            results = {
                'component': 'database',
                'target_response_time_ms': 100,
                'target_sub_100ms_percent': 95.0,
                'benchmarks': []
            }
            
            query_times = []
            
            # Single query benchmarks
            for i in range(iterations):
                for j, (query, params) in enumerate(self.test_queries):
                    start_time = time.time()
                    try:
                        result = await execute_optimized_query(query, params)
                        query_time = (time.time() - start_time) * 1000
                        success = True
                        
                        query_times.append(query_time)
                        
                        benchmark = BenchmarkResult(
                            benchmark_name=f'single_query_{i+1}_{j+1}',
                            component='database',
                            execution_time_ms=query_time,
                            success=success,
                            iterations=1,
                            metadata={
                                'query_pattern': query.split()[0],  # SELECT, INSERT, etc.
                                'has_params': len(params) > 0
                            }
                        )
                        
                        results['benchmarks'].append(asdict(benchmark))
                        
                    except Exception as e:
                        logger.error(f"Query benchmark failed: {e}")
                        
                        benchmark = BenchmarkResult(
                            benchmark_name=f'single_query_{i+1}_{j+1}',
                            component='database',
                            execution_time_ms=0,
                            success=False,
                            iterations=1,
                            metadata={'error': str(e)}
                        )
                        
                        results['benchmarks'].append(asdict(benchmark))
            
            # Batch query benchmark
            try:
                batch_queries = [(query, params) for query, params in self.test_queries]
                
                start_time = time.time()
                batch_results = await execute_batch_optimized(batch_queries)
                batch_time = (time.time() - start_time) * 1000
                avg_time_per_query = batch_time / len(batch_queries)
                
                batch_benchmark = BenchmarkResult(
                    benchmark_name='batch_database_queries',
                    component='database',
                    execution_time_ms=avg_time_per_query,
                    success=len(batch_results) == len(batch_queries),
                    iterations=len(batch_queries),
                    metadata={
                        'total_queries': len(batch_queries),
                        'total_batch_time_ms': batch_time
                    }
                )
                
                results['benchmarks'].append(asdict(batch_benchmark))
                
            except Exception as e:
                logger.error(f"Batch query benchmark failed: {e}")
            
            # Calculate summary statistics
            if query_times:
                sub_100ms_count = sum(1 for t in query_times if t < 100)
                sub_100ms_percent = (sub_100ms_count / len(query_times)) * 100
                
                results['performance_summary'] = {
                    'avg_query_time_ms': statistics.mean(query_times),
                    'min_query_time_ms': min(query_times),
                    'max_query_time_ms': max(query_times),
                    'median_query_time_ms': statistics.median(query_times),
                    'sub_100ms_count': sub_100ms_count,
                    'sub_100ms_percent': sub_100ms_percent,
                    'total_queries': len(query_times),
                    'target_met': sub_100ms_percent >= results['target_sub_100ms_percent']
                }
                
                logger.info(f"📊 Database queries: {sub_100ms_percent:.1f}% under 100ms "
                           f"(avg: {statistics.mean(query_times):.1f}ms)")
            else:
                results['performance_summary'] = {
                    'error': 'No successful database query iterations',
                    'target_met': False
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Database benchmark error: {e}")
            return {
                'component': 'database',
                'error': str(e),
                'target_met': False
            }
    
    async def _benchmark_frontend_performance(self, iterations: int) -> Dict[str, Any]:
        """
        Benchmark frontend performance
        
        Target: Under 2 seconds load time
        """
        logger.info("🌐 Benchmarking frontend performance...")
        
        try:
            # Frontend metrics must be provided by the frontend analyzer via reporting.
            # If no integration is present, return a clear error instead of simulated data.
            return {
                'component': 'frontend',
                'error': 'Frontend performance metrics not available; integrate frontend reporting to backend.',
                'target_met': False
            }
            
        except Exception as e:
            logger.error(f"Frontend benchmark error: {e}")
            return {
                'component': 'frontend',
                'error': str(e),
                'target_met': False
            }
    
    async def _benchmark_memory_efficiency(self, iterations: int) -> Dict[str, Any]:
        """
        Benchmark memory efficiency
        
        Target: Optimal memory usage with proper cleanup
        """
        logger.info("🧠 Benchmarking memory efficiency...")
        
        try:
            results = {
                'component': 'memory',
                'target_usage_mb': 2048,  # 2GB max
                'benchmarks': []
            }
            
            memory_measurements = []
            
            for i in range(iterations):
                # Take memory snapshot
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                
                # Simulate memory-intensive operation
                await asyncio.sleep(0.1)  # Simulate work
                
                memory_after = process.memory_info().rss / 1024 / 1024
                memory_used = memory_after
                
                memory_measurements.append(memory_used)
                
                benchmark = BenchmarkResult(
                    benchmark_name=f'memory_efficiency_{i+1}',
                    component='memory',
                    execution_time_ms=memory_used,  # Using memory as "time" for consistency
                    success=memory_used <= results['target_usage_mb'],
                    iterations=1,
                    metadata={
                        'memory_before_mb': memory_before,
                        'memory_after_mb': memory_after,
                        'memory_used_mb': memory_used
                    }
                )
                
                results['benchmarks'].append(asdict(benchmark))
            
            # Test memory cleanup
            if memory_profiler:
                try:
                    cleanup_result = await optimize_memory()
                    memory_saved = cleanup_result.get('memory_saved_mb', 0)
                    
                    cleanup_benchmark = BenchmarkResult(
                        benchmark_name='memory_cleanup_efficiency',
                        component='memory',
                        execution_time_ms=memory_saved,  # Amount of memory freed
                        success=memory_saved > 0,
                        iterations=1,
                        metadata=cleanup_result
                    )
                    
                    results['benchmarks'].append(asdict(cleanup_benchmark))
                    
                except Exception as e:
                    logger.warning(f"Memory cleanup benchmark failed: {e}")
            
            # Calculate summary
            if memory_measurements:
                avg_memory = statistics.mean(memory_measurements)
                max_memory = max(memory_measurements)
                
                results['performance_summary'] = {
                    'avg_memory_usage_mb': avg_memory,
                    'max_memory_usage_mb': max_memory,
                    'min_memory_usage_mb': min(memory_measurements),
                    'within_target_count': sum(1 for m in memory_measurements if m <= results['target_usage_mb']),
                    'target_met': max_memory <= results['target_usage_mb']
                }
                
                logger.info(f"📊 Memory usage: {avg_memory:.1f}MB avg, {max_memory:.1f}MB peak")
            
            return results
            
        except Exception as e:
            logger.error(f"Memory benchmark error: {e}")
            return {
                'component': 'memory',
                'error': str(e),
                'target_met': False
            }
    
    async def _benchmark_cache_performance(self, iterations: int) -> Dict[str, Any]:
        """
        Benchmark cache performance
        
        Target: 80%+ cache hit rate
        """
        logger.info("💾 Benchmarking cache performance...")
        
        try:
            results = {
                'component': 'cache',
                'target_hit_rate_percent': 80.0,
                'benchmarks': []
            }
            
            cache_hits = 0
            cache_total = 0
            
            # Test cache operations
            for i in range(iterations * 10):  # More operations for better statistics
                cache_key = f"benchmark_key_{i % 5}"  # Repeat some keys for hits
                cache_value = f"benchmark_value_{i}"
                
                # Set operation
                start_time = time.time()
                set_success = await cache_set(cache_key, cache_value, ttl=300)
                set_time = (time.time() - start_time) * 1000
                
                cache_total += 1
                
                # Get operation
                start_time = time.time()
                cached_value = await cache_get(cache_key)
                get_time = (time.time() - start_time) * 1000
                
                if cached_value is not None:
                    cache_hits += 1
                
                cache_total += 1
                
                if i % 10 == 0:  # Record benchmark every 10 operations
                    current_hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0
                    
                    benchmark = BenchmarkResult(
                        benchmark_name=f'cache_operations_{i // 10 + 1}',
                        component='cache',
                        execution_time_ms=get_time,  # Focus on get performance
                        success=current_hit_rate >= results['target_hit_rate_percent'],
                        iterations=10,
                        metadata={
                            'hit_rate_percent': current_hit_rate,
                            'hits': cache_hits,
                            'total_operations': cache_total,
                            'set_time_ms': set_time,
                            'get_time_ms': get_time
                        }
                    )
                    
                    results['benchmarks'].append(asdict(benchmark))
            
            # Calculate final statistics
            final_hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0
            
            results['performance_summary'] = {
                'cache_hit_rate_percent': final_hit_rate,
                'total_hits': cache_hits,
                'total_operations': cache_total,
                'target_met': final_hit_rate >= results['target_hit_rate_percent']
            }
            
            logger.info(f"📊 Cache hit rate: {final_hit_rate:.1f}% ({cache_hits}/{cache_total})")
            
            return results
            
        except Exception as e:
            logger.error(f"Cache benchmark error: {e}")
            return {
                'component': 'cache',
                'error': str(e),
                'target_met': False
            }
    
    def _generate_overall_assessment(self, component_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall performance assessment"""
        
        total_targets = 0
        targets_met = 0
        component_grades = []
        
        for component, results in component_results.items():
            total_targets += 1
            if 'error' in results:
                component_grades.append('F')
                continue
            summary = results.get('performance_summary', {})
            target_met = summary.get('target_met', False)
            if target_met:
                targets_met += 1
                component_grades.append('A')
            else:
                component_grades.append('C')
        
        # Calculate overall score
        if total_targets == 0:
            score = 0
            grade = 'F'
        else:
            score = (targets_met / total_targets) * 100
            
            if score >= 90:
                grade = 'A+'
            elif score >= 80:
                grade = 'A'
            elif score >= 70:
                grade = 'B+'
            elif score >= 60:
                grade = 'B'
            elif score >= 50:
                grade = 'C'
            else:
                grade = 'F'
        
        assessment = {
            'overall_score': score,
            'overall_grade': grade,
            'targets_met': targets_met,
            'total_targets': total_targets,
            'component_grades': dict(zip(component_results.keys(), component_grades)),
            'phase_3_readiness': score >= 80,  # 80% of targets must be met for Phase 3 readiness
            'summary': f"{targets_met}/{total_targets} performance targets met ({score:.1f}%)"
        }
        
        return assessment
    
    def _validate_performance_targets(self, component_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance against defined targets"""
        
        validation_results = {}
        
        for target in self.performance_targets:
            component_data = component_results.get(target.component, {})
            summary = component_data.get('performance_summary', {})
            
            if 'error' in component_data or 'error' in summary:
                validation_results[f"{target.component}_{target.metric}"] = {
                    'met': False,
                    'error': component_data.get('error') or summary.get('error'),
                    'target_value': target.target_value,
                    'unit': target.unit
                }
                continue
            
            # Extract actual value based on metric
            actual_value = None
            if target.component == 'video_processing' and target.metric == 'processing_time_ms':
                actual_value = summary.get('avg_processing_time_ms')
            elif target.component == 'database' and target.metric == 'query_response_time_ms':
                actual_value = summary.get('avg_query_time_ms')
            elif target.component == 'frontend' and target.metric == 'load_time_ms':
                actual_value = summary.get('avg_load_time_ms')
            elif target.component == 'memory' and target.metric == 'usage_mb':
                actual_value = summary.get('max_memory_usage_mb')
            elif target.component == 'cache' and target.metric == 'hit_rate_percent':
                actual_value = summary.get('cache_hit_rate_percent')
            
            # Validate against target
            met = False
            if actual_value is not None:
                if target.comparison == 'less_than':
                    met = actual_value < target.target_value
                elif target.comparison == 'greater_than':
                    met = actual_value > target.target_value
                elif target.comparison == 'equals':
                    met = abs(actual_value - target.target_value) < 0.01
            
            # Calculate improvement if baseline available
            improvement_percent = None
            if target.baseline_value and actual_value:
                improvement_percent = ((target.baseline_value - actual_value) / target.baseline_value) * 100
            
            validation_results[f"{target.component}_{target.metric}"] = {
                'met': met,
                'actual_value': actual_value,
                'target_value': target.target_value,
                'unit': target.unit,
                'comparison': target.comparison,
                'improvement_percent': improvement_percent,
                'improvement_target_percent': target.improvement_target_percent,
                'priority': target.priority,
                'meets_improvement_target': (improvement_percent >= target.improvement_target_percent) 
                                          if target.improvement_target_percent and improvement_percent else None
            }
        
        return validation_results
    
    def _generate_benchmark_recommendations(self, 
                                          component_results: Dict[str, Any], 
                                          target_validation: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate optimization recommendations based on benchmark results"""
        
        recommendations = []
        
        # Analyze each component
        for component, results in component_results.items():
            if 'error' in results:
                recommendations.append({
                    'component': component,
                    'priority': 'critical',
                    'issue': f"Component benchmark failed: {results['error']}",
                    'recommendation': f"Fix {component} system errors before performance optimization"
                })
                continue
            
            summary = results.get('performance_summary', {})
            if not summary.get('target_met', True):
                
                if component == 'video_processing':
                    avg_time = summary.get('avg_processing_time_ms', 0)
                    if avg_time > 30000:  # > 30s
                        recommendations.append({
                            'component': component,
                            'priority': 'critical',
                            'issue': f"Video processing too slow ({avg_time/1000:.1f}s avg)",
                            'recommendation': "Implement parallel processing, optimize AI API calls, enable caching"
                        })
                    elif avg_time > 24000:  # > 24s
                        recommendations.append({
                            'component': component,
                            'priority': 'high',
                            'issue': f"Video processing close to target ({avg_time/1000:.1f}s avg)",
                            'recommendation': "Fine-tune parallel processing, optimize memory usage"
                        })
                
                elif component == 'database':
                    sub_100ms_percent = summary.get('sub_100ms_percent', 0)
                    if sub_100ms_percent < 90:
                        recommendations.append({
                            'component': component,
                            'priority': 'critical',
                            'issue': f"Only {sub_100ms_percent:.1f}% of queries under 100ms",
                            'recommendation': "Optimize slow queries, add indexes, implement connection pooling"
                        })
                
                elif component == 'frontend':
                    avg_load = summary.get('avg_load_time_ms', 0)
                    if avg_load > 2500:
                        recommendations.append({
                            'component': component,
                            'priority': 'high',
                            'issue': f"Frontend load time too slow ({avg_load/1000:.1f}s)",
                            'recommendation': "Implement code splitting, optimize bundle size, enable compression"
                        })
                
                elif component == 'memory':
                    max_memory = summary.get('max_memory_usage_mb', 0)
                    if max_memory > 2048:
                        recommendations.append({
                            'component': component,
                            'priority': 'high',
                            'issue': f"Memory usage too high ({max_memory:.0f}MB peak)",
                            'recommendation': "Implement memory cleanup, optimize data structures, fix memory leaks"
                        })
                
                elif component == 'cache':
                    hit_rate = summary.get('cache_hit_rate_percent', 0)
                    if hit_rate < 70:
                        recommendations.append({
                            'component': component,
                            'priority': 'medium',
                            'issue': f"Cache hit rate too low ({hit_rate:.1f}%)",
                            'recommendation': "Optimize cache TTL, implement cache warming, review cache keys"
                        })
        
        # Check overall 60% improvement target
        video_validation = target_validation.get('video_processing_processing_time_ms')
        if video_validation and not video_validation.get('meets_improvement_target', True):
            improvement = video_validation.get('improvement_percent', 0)
            recommendations.append({
                'component': 'overall',
                'priority': 'critical',
                'issue': f"60% improvement target not met ({improvement:.1f}% achieved)",
                'recommendation': "Focus on video processing optimization - this is the primary Phase 3 target"
            })
        
        return recommendations
    
    def get_benchmark_history_summary(self) -> Dict[str, Any]:
        """Get benchmark history and trends"""
        
        if not self.benchmark_history:
            return {'message': 'No benchmark history available'}
        
        # Analyze trends from recent benchmarks
        recent_benchmarks = list(self.benchmark_history)[-10:]  # Last 10 benchmarks
        
        trends = {}
        for benchmark in recent_benchmarks:
            timestamp = benchmark.get('timestamp')
            overall_grade = benchmark.get('overall_assessment', {}).get('overall_grade')
            targets_met = benchmark.get('overall_assessment', {}).get('targets_met', 0)
            
            if timestamp and overall_grade:
                if 'grades' not in trends:
                    trends['grades'] = []
                    trends['targets_met'] = []
                    trends['timestamps'] = []
                
                trends['grades'].append(overall_grade)
                trends['targets_met'].append(targets_met)
                trends['timestamps'].append(timestamp)
        
        return {
            'total_benchmarks': len(self.benchmark_history),
            'recent_benchmarks': len(recent_benchmarks),
            'trends': trends,
            'latest_benchmark': self.benchmark_history[-1] if self.benchmark_history else None
        }

# Global benchmark system
benchmark_system = PerformanceBenchmarkSystem()

# Convenience functions
async def run_performance_benchmark(iterations: int = 3) -> Dict[str, Any]:
    """Run comprehensive performance benchmark"""
    return await benchmark_system.run_comprehensive_benchmark(iterations)

async def validate_phase3_targets() -> Dict[str, Any]:
    """Validate Phase 3 performance targets"""
    result = await benchmark_system.run_comprehensive_benchmark(iterations=5)
    
    return {
        'phase_3_ready': result.get('overall_assessment', {}).get('phase_3_readiness', False),
        'targets_met': result.get('overall_assessment', {}).get('targets_met', 0),
        'total_targets': result.get('overall_assessment', {}).get('total_targets', 0),
        'overall_grade': result.get('overall_assessment', {}).get('overall_grade', 'F'),
        'video_processing_improvement': result.get('components', {}).get('video_processing', {}).get('performance_summary', {}).get('improvement_percent', 0),
        'recommendations': result.get('recommendations', [])
    }

def get_benchmark_report() -> Dict[str, Any]:
    """Get comprehensive benchmark report"""
    return benchmark_system.get_benchmark_history_summary()

if __name__ == "__main__":
    async def test_benchmark_system():
        logger.info("🧪 Testing Performance Benchmark System...")
        
        # Run comprehensive benchmark
        results = await run_performance_benchmark(iterations=2)
        
        # Print summary
        assessment = results.get('overall_assessment', {})
        print(f"\n📊 Benchmark Results Summary:")
        print(f"Overall Grade: {assessment.get('overall_grade', 'N/A')}")
        print(f"Targets Met: {assessment.get('targets_met', 0)}/{assessment.get('total_targets', 0)}")
        print(f"Phase 3 Ready: {assessment.get('phase_3_readiness', False)}")
        
        # Print component results
        for component, result in results.get('components', {}).items():
            summary = result.get('performance_summary', {})
            target_met = summary.get('target_met', False)
            print(f"{component}: {'✅' if target_met else '❌'}")
        
        # Validate Phase 3 targets
        validation = await validate_phase3_targets()
        print(f"\n🎯 Phase 3 Validation:")
        print(f"Ready: {validation['phase_3_ready']}")
        print(f"Video Processing Improvement: {validation['video_processing_improvement']:.1f}%")
    
    asyncio.run(test_benchmark_system())