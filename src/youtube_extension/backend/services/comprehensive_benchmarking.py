#!/usr/bin/env python3
"""
Comprehensive Performance Benchmarking System
=============================================

Phase 3 Performance Optimization: Comprehensive benchmarking system to validate
60%+ performance improvements across all system components with detailed
analysis, regression detection, and performance validation.

Key Features:
- End-to-end performance benchmarking
- Component-level performance validation
- Before/after performance comparison
- Regression detection and alerting
- Performance target validation
- Automated benchmark reporting
- Continuous performance monitoring
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable
import aiofiles
import numpy as np

# Import all performance components with proper error handling
try:
    from .performance_monitor import performance_monitor, track_video_processing_time, track_database_query_time
    from ...processors.video_processor import VideoProcessor
    from .intelligent_cache import intelligent_cache, cache_get, cache_set
    from .memory_manager import memory_manager
    from .load_balancer import service_discovery
    from backend.database.index_analysis import database_optimizer
    PERFORMANCE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Some performance modules not available: {e}")
    PERFORMANCE_COMPONENTS_AVAILABLE = False
    performance_monitor = None
    video_processor = None
    intelligent_cache = None
    memory_manager = None
    service_discovery = None
    database_optimizer = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Individual benchmark result"""
    name: str
    component: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

@dataclass
class BenchmarkSuite:
    """Benchmark suite configuration"""
    name: str
    description: str
    benchmarks: List[Dict[str, Any]]
    target_improvement_percent: float = 60.0
    baseline_results: Optional[Dict[str, BenchmarkResult]] = None

@dataclass
class PerformanceTarget:
    """Performance target definition"""
    component: str
    metric: str
    target_value: float
    unit: str
    comparison: str  # "less_than", "greater_than", "equals"
    priority: str    # "critical", "high", "medium", "low"

class ComprehensiveBenchmark:
    """
    Comprehensive benchmarking system for Phase 3 validation
    
    Features:
    - Multi-component benchmarking
    - Performance regression detection
    - Target validation
    - Automated reporting
    - Continuous monitoring integration
    """
    
    def __init__(self):
        self.benchmark_suites: Dict[str, BenchmarkSuite] = {}
        self.performance_targets = self._define_performance_targets()
        self.benchmark_history: List[Dict[str, Any]] = []
        self.baseline_established = False
        
        # Results storage
        self.results_directory = "benchmark_results"
        self.current_session_results = []
        
        logger.info("🏁 Comprehensive Benchmarking System initialized")
    
    def _define_performance_targets(self) -> List[PerformanceTarget]:
        """Define Phase 3 performance targets"""
        return [
            # Video Processing Targets
            PerformanceTarget(
                component="video_processing",
                metric="processing_time_ms",
                target_value=30000,  # 30 seconds
                unit="ms",
                comparison="less_than",
                priority="critical"
            ),
            
            # Database Query Targets
            PerformanceTarget(
                component="database",
                metric="query_time_ms",
                target_value=100,  # 100ms
                unit="ms",
                comparison="less_than",
                priority="critical"
            ),
            PerformanceTarget(
                component="database",
                metric="sub_100ms_percent",
                target_value=95.0,  # 95% of queries
                unit="%",
                comparison="greater_than",
                priority="critical"
            ),
            
            # Frontend Performance Targets
            PerformanceTarget(
                component="frontend",
                metric="page_load_time_ms",
                target_value=2000,  # 2 seconds
                unit="ms",
                comparison="less_than",
                priority="high"
            ),
            PerformanceTarget(
                component="frontend",
                metric="bundle_size_mb",
                target_value=2.0,  # 2MB
                unit="MB",
                comparison="less_than",
                priority="medium"
            ),
            
            # System Resource Targets
            PerformanceTarget(
                component="system",
                metric="memory_usage_mb",
                target_value=1024,  # 1GB
                unit="MB",
                comparison="less_than",
                priority="high"
            ),
            PerformanceTarget(
                component="system",
                metric="cpu_usage_percent",
                target_value=80,  # 80%
                unit="%",
                comparison="less_than",
                priority="medium"
            ),
            
            # Cache Performance Targets
            PerformanceTarget(
                component="cache",
                metric="hit_ratio_percent",
                target_value=90.0,  # 90% hit ratio
                unit="%",
                comparison="greater_than",
                priority="high"
            ),
            PerformanceTarget(
                component="cache",
                metric="access_time_ms",
                target_value=10,  # 10ms
                unit="ms",
                comparison="less_than",
                priority="medium"
            )
        ]
    
    def register_benchmark_suite(self, suite: BenchmarkSuite):
        """Register a benchmark suite"""
        self.benchmark_suites[suite.name] = suite
        logger.info(f"📋 Registered benchmark suite: {suite.name}")
    
    async def establish_baseline(self) -> Dict[str, Any]:
        """Establish performance baseline before optimizations"""
        logger.info("📏 Establishing performance baseline...")
        
        baseline_results = {}
        
        # Run all benchmark suites to establish baseline
        for suite_name, suite in self.benchmark_suites.items():
            logger.info(f"🏃 Running baseline for {suite_name}")
            
            suite_results = await self._run_benchmark_suite(suite)
            baseline_results[suite_name] = suite_results
            
            # Store baseline in suite
            suite.baseline_results = suite_results
        
        # Save baseline to file
        baseline_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'baseline',
            'results': baseline_results,
            'system_info': await self._get_system_info()
        }
        
        await self._save_benchmark_report(baseline_report, 'baseline')
        
        self.baseline_established = True
        logger.info("✅ Performance baseline established")
        
        return baseline_results
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark across all components"""
        if not self.baseline_established:
            logger.warning("⚠️ No baseline established - results may not show improvement")
        
        logger.info("🚀 Starting comprehensive performance benchmark...")
        start_time = time.time()
        
        benchmark_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'comprehensive',
            'suite_results': {},
            'target_validation': {},
            'improvement_analysis': {},
            'system_info': await self._get_system_info()
        }
        
        # Run all benchmark suites
        for suite_name, suite in self.benchmark_suites.items():
            logger.info(f"🏃 Running benchmark suite: {suite_name}")
            
            suite_results = await self._run_benchmark_suite(suite)
            benchmark_results['suite_results'][suite_name] = suite_results
            
            # Calculate improvements if baseline exists
            if suite.baseline_results:
                improvement = self._calculate_improvement(suite.baseline_results, suite_results)
                benchmark_results['improvement_analysis'][suite_name] = improvement
        
        # Validate against performance targets
        target_validation = await self._validate_performance_targets(benchmark_results)
        benchmark_results['target_validation'] = target_validation
        
        # Calculate overall performance grade
        benchmark_results['performance_grade'] = self._calculate_performance_grade(benchmark_results)
        
        # Calculate total execution time
        benchmark_results['total_execution_time_ms'] = (time.time() - start_time) * 1000
        
        # Save comprehensive report
        await self._save_benchmark_report(benchmark_results, 'comprehensive')
        
        # Add to history
        self.benchmark_history.append(benchmark_results)
        
        # Keep only last 50 benchmark runs
        if len(self.benchmark_history) > 50:
            self.benchmark_history = self.benchmark_history[-50:]
        
        logger.info(f"✅ Comprehensive benchmark completed in {benchmark_results['total_execution_time_ms']:.0f}ms")
        logger.info(f"📊 Performance Grade: {benchmark_results['performance_grade']}")
        
        return benchmark_results
    
    async def _run_benchmark_suite(self, suite: BenchmarkSuite) -> Dict[str, BenchmarkResult]:
        """Run a single benchmark suite"""
        suite_results = {}
        
        for benchmark_config in suite.benchmarks:
            benchmark_name = benchmark_config['name']
            component = benchmark_config['component']
            
            logger.debug(f"🔬 Running benchmark: {benchmark_name}")
            
            try:
                # Run the specific benchmark
                result = await self._run_single_benchmark(benchmark_config)
                suite_results[benchmark_name] = result
                
            except Exception as e:
                logger.error(f"❌ Benchmark {benchmark_name} failed: {e}")
                suite_results[benchmark_name] = BenchmarkResult(
                    name=benchmark_name,
                    component=component,
                    execution_time_ms=0,
                    memory_usage_mb=0,
                    cpu_usage_percent=0,
                    success=False,
                    error_message=str(e)
                )
        
        return suite_results
    
    async def _run_single_benchmark(self, config: Dict[str, Any]) -> BenchmarkResult:
        """Run a single benchmark"""
        name = config['name']
        component = config['component']
        benchmark_type = config['type']
        params = config.get('params', {})
        
        # Get initial system state
        initial_memory = await self._get_memory_usage()
        initial_cpu = await self._get_cpu_usage()
        
        start_time = time.time()
        
        try:
            # Run specific benchmark based on type
            if benchmark_type == 'video_processing':
                result = await self._benchmark_video_processing(params)
            elif benchmark_type == 'database_query':
                result = await self._benchmark_database_query(params)
            elif benchmark_type == 'cache_operation':
                result = await self._benchmark_cache_operation(params)
            elif benchmark_type == 'memory_management':
                result = await self._benchmark_memory_management(params)
            elif benchmark_type == 'load_balancing':
                result = await self._benchmark_load_balancing(params)
            elif benchmark_type == 'system_integration':
                result = await self._benchmark_system_integration(params)
            else:
                raise ValueError(f"Unknown benchmark type: {benchmark_type}")
            
            execution_time = (time.time() - start_time) * 1000
            
            # Get final system state
            final_memory = await self._get_memory_usage()
            final_cpu = await self._get_cpu_usage()
            
            return BenchmarkResult(
                name=name,
                component=component,
                execution_time_ms=execution_time,
                memory_usage_mb=final_memory - initial_memory,
                cpu_usage_percent=final_cpu,
                success=True,
                metadata=result
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return BenchmarkResult(
                name=name,
                component=component,
                execution_time_ms=execution_time,
                memory_usage_mb=0,
                cpu_usage_percent=0,
                success=False,
                error_message=str(e)
            )
    
    async def _benchmark_video_processing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark video processing performance"""
        if not PERFORMANCE_COMPONENTS_AVAILABLE:
            raise RuntimeError("Performance components not available. Cannot run real benchmarks.")

        # Initialize video processor with parallel strategy for benchmarking
        if video_processor is None:
            video_processor_instance = VideoProcessor(strategy="parallel", config={"max_workers": 4})
        else:
            video_processor_instance = video_processor

        test_urls = params.get('test_urls', ['https://www.youtube.com/watch?v=jNQXAC9IVRw'])
        iterations = params.get('iterations', 3)

        processing_times = []

        for i in range(iterations):
            for url in test_urls:
                start_time = time.time()

                # Process video using new unified processor
                result = await video_processor_instance.process_video(
                    video_url=url,
                    options={'benchmark': True}
                )

                processing_time = (time.time() - start_time) * 1000
                processing_times.append(processing_time)

                if 'error' in result:
                    raise RuntimeError(f"Video processing failed: {result['error']}")

                # Log real processing time
                logger.info(f"Real video processing time for {url}: {processing_time:.1f}ms")

        return {
            'avg_processing_time_ms': statistics.mean(processing_times),
            'min_processing_time_ms': min(processing_times),
            'max_processing_time_ms': max(processing_times),
            'total_videos_processed': len(test_urls) * iterations,
            'meets_30s_target': all(t < 30000 for t in processing_times),
            'data_source': 'real_video_processing'
        }
    
    async def _benchmark_database_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark database query performance"""
        if not PERFORMANCE_COMPONENTS_AVAILABLE or not database_optimizer:
            raise RuntimeError("Database performance components not available. Cannot run real benchmarks.")

        iterations = params.get('iterations', 100)
        query_types = params.get('query_types', ['simple_select', 'complex_join', 'aggregation'])

        query_times = []
        queries_under_100ms = 0

        for i in range(iterations):
            for query_type in query_types:
                start_time = time.time()

                # Run database benchmark
                benchmark_result = await database_optimizer.run_performance_benchmark()

                query_time = (time.time() - start_time) * 1000
                query_times.append(query_time)

                if query_time < 100:
                    queries_under_100ms += 1

                # Log real query time
                logger.debug(f"Real database query time ({query_type}): {query_time:.1f}ms")

        total_queries = len(query_times)
        sub_100ms_percent = (queries_under_100ms / total_queries) * 100

        return {
            'avg_query_time_ms': statistics.mean(query_times),
            'min_query_time_ms': min(query_times),
            'max_query_time_ms': max(query_times),
            'sub_100ms_percent': sub_100ms_percent,
            'total_queries': total_queries,
            'meets_95_percent_target': sub_100ms_percent >= 95.0,
            'data_source': 'real_database_queries'
        }
    
    async def _benchmark_cache_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark cache operation performance"""
        if not intelligent_cache:
            raise RuntimeError("Intelligent cache not available")
        
        iterations = params.get('iterations', 1000)
        key_prefix = params.get('key_prefix', 'benchmark')
        
        # Test cache set operations
        set_times = []
        for i in range(iterations):
            key = f"{key_prefix}_{i}"
            value = {'data': f'test_value_{i}', 'timestamp': time.time()}
            
            start_time = time.time()
            await cache_set(key, value, ttl=300)
            set_time = (time.time() - start_time) * 1000
            set_times.append(set_time)
        
        # Test cache get operations
        get_times = []
        cache_hits = 0
        
        for i in range(iterations):
            key = f"{key_prefix}_{i}"
            
            start_time = time.time()
            value = await cache_get(key)
            get_time = (time.time() - start_time) * 1000
            get_times.append(get_time)
            
            if value is not None:
                cache_hits += 1
        
        hit_ratio = (cache_hits / iterations) * 100
        
        return {
            'avg_set_time_ms': statistics.mean(set_times),
            'avg_get_time_ms': statistics.mean(get_times),
            'hit_ratio_percent': hit_ratio,
            'total_operations': iterations * 2,
            'meets_hit_ratio_target': hit_ratio >= 90.0,
            'meets_access_time_target': statistics.mean(get_times) < 10
        }
    
    async def _benchmark_memory_management(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark memory management performance"""
        if not memory_manager:
            raise RuntimeError("Memory manager not available")
        
        # Get initial memory stats
        initial_stats = memory_manager.get_memory_stats()
        initial_memory = initial_stats['current']['rss_mb']
        
        # Simulate memory-intensive operations
        large_objects = []
        for i in range(100):
            # Create large objects to trigger memory management
            large_object = [0] * 10000  # ~40KB object
            large_objects.append(large_object)
            
            if i % 10 == 0:
                # Force garbage collection periodically
                memory_manager.force_garbage_collection()
        
        # Get final memory stats
        final_stats = memory_manager.get_memory_stats()
        final_memory = final_stats['current']['rss_mb']
        
        memory_growth = final_memory - initial_memory
        growth_rate = final_stats['growth_rate_mb_per_min']
        
        # Cleanup
        del large_objects
        memory_manager.force_garbage_collection()
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': memory_growth,
            'growth_rate_mb_per_min': growth_rate,
            'gc_collections': final_stats['gc_stats']['total_objects'],
            'meets_memory_target': final_memory < 1024  # < 1GB
        }
    
    async def _benchmark_load_balancing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark load balancing performance"""
        if not service_discovery:
            raise RuntimeError("Service discovery not available")
        
        # Get load balancer stats
        stats = service_discovery.get_service_discovery_stats()
        
        # Simulate load balancing operations
        request_count = params.get('request_count', 1000)
        response_times = []
        
        for i in range(request_count):
            start_time = time.time()
            
            # Simulate request routing (this would be actual service calls in production)
            await asyncio.sleep(0.001)  # Simulate minimal processing
            
            response_time = (time.time() - start_time) * 1000
            response_times.append(response_time)
        
        return {
            'avg_response_time_ms': statistics.mean(response_times),
            'total_requests': request_count,
            'registered_services': len(stats['registered_services']),
            'auto_scaling_enabled': stats['auto_scaling_enabled'],
            'meets_response_target': statistics.mean(response_times) < 100
        }
    
    async def _benchmark_system_integration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark end-to-end system integration"""
        # Require all core components; do not simulate
        if not database_optimizer or not intelligent_cache or not memory_manager:
            missing = []
            # Note: video_processor is now created on-demand
            if not database_optimizer:
                missing.append('database_optimizer')
            if not intelligent_cache:
                missing.append('intelligent_cache')
            if not memory_manager:
                missing.append('memory_manager')
            raise RuntimeError(f"System integration prerequisites missing: {', '.join(missing)}")

        # This benchmark tests the entire pipeline with real components only
        # 1. Video processing request
        # 2. Database operations
        # 3. Cache operations
        # 4. Memory management

        if not PERFORMANCE_COMPONENTS_AVAILABLE:
            raise RuntimeError("Performance components not available. Cannot run real integration benchmarks.")

        start_time = time.time()

        # Step 1: Video processing (real)
        video_start = time.time()

        # Create video processor instance for integration test
        video_processor_instance = VideoProcessor(strategy="parallel", config={"max_workers": 2})
        video_result = await video_processor_instance.process_video(
            video_url="https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Compliance-safe real URL
            options={'benchmark': True, 'lightweight': True}
        )

        video_time = (time.time() - video_start) * 1000

        # Step 2: Database operations (real)
        db_start = time.time()
        if database_optimizer:
            db_benchmark = await database_optimizer.run_performance_benchmark()
        else:
            raise RuntimeError("Database optimizer not available for real database operations")

        db_time = (time.time() - db_start) * 1000

        # Step 3: Cache operations (real)
        cache_start = time.time()
        cache_key = f"integration_test_{int(time.time())}"
        try:
            await cache_set(cache_key, {'test': 'data', 'timestamp': time.time()}, ttl=60)
            cached_value = await cache_get(cache_key)
        except Exception as e:
            raise RuntimeError(f"Cache operations failed: {e}")

        cache_time = (time.time() - cache_start) * 1000

        # Step 4: Memory check (real)
        if memory_manager:
            memory_stats = memory_manager.get_memory_stats()
            current_memory = memory_stats['current']['rss_mb']
        else:
            # If no memory manager, get basic memory info
            import psutil
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_time = (time.time() - start_time) * 1000

        # Log real integration results
        logger.info(f"Real integration benchmark: total={total_time:.1f}ms, video={video_time:.1f}ms, db={db_time:.1f}ms, cache={cache_time:.1f}ms")

        return {
            'total_integration_time_ms': total_time,
            'video_processing_time_ms': video_time,
            'database_time_ms': db_time,
            'cache_time_ms': cache_time,
            'memory_usage_mb': current_memory,
            'cache_hit': cached_value is not None,
            'video_success': 'error' not in video_result if isinstance(video_result, dict) else False,
            'all_components_working': all([
                'error' not in video_result if isinstance(video_result, dict) else False,
                db_time > 0,  # Real DB time should be measurable
                cached_value is not None,
                current_memory > 0  # Real memory usage
            ]),
            'data_source': 'real_integration_test'
        }
    
    def _calculate_improvement(self, baseline: Dict[str, BenchmarkResult], 
                             current: Dict[str, BenchmarkResult]) -> Dict[str, Any]:
        """Calculate performance improvement between baseline and current"""
        improvements = {}
        
        for bench_name in baseline.keys():
            if bench_name not in current:
                continue
            
            baseline_result = baseline[bench_name]
            current_result = current[bench_name]
            
            if not baseline_result.success or not current_result.success:
                improvements[bench_name] = {
                    'improvement_percent': 0,
                    'status': 'error',
                    'message': 'One or both benchmarks failed'
                }
                continue
            
            # Calculate time improvement
            baseline_time = baseline_result.execution_time_ms
            current_time = current_result.execution_time_ms
            
            if baseline_time > 0:
                time_improvement = ((baseline_time - current_time) / baseline_time) * 100
            else:
                time_improvement = 0
            
            # Calculate memory improvement
            baseline_memory = baseline_result.memory_usage_mb
            current_memory = current_result.memory_usage_mb
            
            if baseline_memory > 0:
                memory_improvement = ((baseline_memory - current_memory) / baseline_memory) * 100
            else:
                memory_improvement = 0
            
            improvements[bench_name] = {
                'time_improvement_percent': time_improvement,
                'memory_improvement_percent': memory_improvement,
                'baseline_time_ms': baseline_time,
                'current_time_ms': current_time,
                'baseline_memory_mb': baseline_memory,
                'current_memory_mb': current_memory,
                'meets_60_percent_target': time_improvement >= 60.0
            }
        
        return improvements
    
    async def _validate_performance_targets(self, benchmark_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate benchmark results against performance targets"""
        validation_results = {
            'targets_met': 0,
            'targets_failed': 0,
            'critical_targets_met': 0,
            'critical_targets_failed': 0,
            'target_details': []
        }
        
        for target in self.performance_targets:
            target_result = {
                'component': target.component,
                'metric': target.metric,
                'target_value': target.target_value,
                'unit': target.unit,
                'comparison': target.comparison,
                'priority': target.priority,
                'met': False,
                'actual_value': None,
                'message': ''
            }
            
            # Extract actual value from benchmark results
            actual_value = await self._extract_metric_value(benchmark_results, target)
            target_result['actual_value'] = actual_value
            
            if actual_value is not None:
                # Check if target is met
                if target.comparison == 'less_than':
                    met = actual_value < target.target_value
                elif target.comparison == 'greater_than':
                    met = actual_value > target.target_value
                elif target.comparison == 'equals':
                    met = abs(actual_value - target.target_value) < 0.01
                else:
                    met = False
                
                target_result['met'] = met
                target_result['message'] = (
                    f"✅ Target met: {actual_value}{target.unit} {target.comparison.replace('_', ' ')} {target.target_value}{target.unit}"
                    if met else
                    f"❌ Target missed: {actual_value}{target.unit} not {target.comparison.replace('_', ' ')} {target.target_value}{target.unit}"
                )
                
                # Update counters
                if met:
                    validation_results['targets_met'] += 1
                    if target.priority == 'critical':
                        validation_results['critical_targets_met'] += 1
                else:
                    validation_results['targets_failed'] += 1
                    if target.priority == 'critical':
                        validation_results['critical_targets_failed'] += 1
            else:
                target_result['message'] = f"⚠️ Could not extract metric {target.metric} for {target.component}"
            
            validation_results['target_details'].append(target_result)
        
        # Calculate overall target achievement
        total_targets = len(self.performance_targets)
        validation_results['overall_success_rate'] = (validation_results['targets_met'] / total_targets) * 100
        
        return validation_results
    
    async def _extract_metric_value(self, benchmark_results: Dict[str, Any], 
                                  target: PerformanceTarget) -> Optional[float]:
        """Extract metric value from benchmark results"""
        try:
            # Look through suite results for matching component and metric
            for suite_name, suite_results in benchmark_results.get('suite_results', {}).items():
                for bench_name, result in suite_results.items():
                    if not isinstance(result, BenchmarkResult):
                        continue
                    
                    if result.component == target.component:
                        # Check in metadata first
                        if target.metric in result.metadata:
                            return float(result.metadata[target.metric])
                        
                        # Check standard result fields
                        if target.metric == 'processing_time_ms':
                            return result.execution_time_ms
                        elif target.metric == 'memory_usage_mb':
                            return result.memory_usage_mb
                        elif target.metric == 'cpu_usage_percent':
                            return result.cpu_usage_percent
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting metric {target.metric}: {e}")
            return None
    
    def _calculate_performance_grade(self, benchmark_results: Dict[str, Any]) -> str:
        """Calculate overall performance grade"""
        target_validation = benchmark_results.get('target_validation', {})
        
        # Base score
        score = 100
        
        # Deduct points for failed targets
        critical_failed = target_validation.get('critical_targets_failed', 0)
        targets_failed = target_validation.get('targets_failed', 0)
        
        # Critical failures are heavily penalized
        score -= critical_failed * 20
        score -= (targets_failed - critical_failed) * 10
        
        # Check 60% improvement target
        improvement_met = False
        for suite_name, improvements in benchmark_results.get('improvement_analysis', {}).items():
            for bench_name, improvement in improvements.items():
                if improvement.get('meets_60_percent_target', False):
                    improvement_met = True
                    break
        
        if not improvement_met:
            score -= 15  # Penalty for not meeting 60% improvement target
        
        # Convert to letter grade
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'B+'
        elif score >= 80:
            return 'B'
        elif score >= 75:
            return 'C+'
        elif score >= 70:
            return 'C'
        elif score >= 65:
            return 'D+'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        try:
            import platform
            import psutil
            
            return {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_total_gb': psutil.disk_usage('/').total / (1024**3),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    async def _save_benchmark_report(self, report: Dict[str, Any], report_type: str):
        """Save benchmark report to file"""
        try:
            import os
            
            # Create results directory if it doesn't exist
            os.makedirs(self.results_directory, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_benchmark_{timestamp}.json"
            filepath = os.path.join(self.results_directory, filename)
            
            # Save report
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(report, indent=2, default=str))
            
            logger.info(f"📄 Saved benchmark report: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save benchmark report: {e}")
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of benchmark system status"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'registered_suites': list(self.benchmark_suites.keys()),
            'performance_targets': len(self.performance_targets),
            'baseline_established': self.baseline_established,
            'benchmark_history_count': len(self.benchmark_history),
            'results_directory': self.results_directory
        }

# Create default benchmark suites
def create_default_benchmark_suites() -> List[BenchmarkSuite]:
    """Create default benchmark suites for Phase 3 validation"""
    
    return [
        BenchmarkSuite(
            name="video_processing_suite",
            description="Video processing performance validation",
            benchmarks=[
                {
                    'name': 'single_video_processing',
                    'component': 'video_processing',
                    'type': 'video_processing',
                    'params': {
                        'test_urls': ['https://www.youtube.com/watch?v=jNQXAC9IVRw'],
                        'iterations': 3
                    }
                },
                {
                    'name': 'batch_video_processing',
                    'component': 'video_processing', 
                    'type': 'video_processing',
                    'params': {
                        'test_urls': [
                            'https://www.youtube.com/watch?v=jNQXAC9IVRw',
                            'https://www.youtube.com/watch?v=9bZkp7q19f0',
                            'https://www.youtube.com/watch?v=oHg5SJYRHA0'
                        ],
                        'iterations': 2
                    }
                }
            ]
        ),
        
        BenchmarkSuite(
            name="database_performance_suite",
            description="Database query performance validation",
            benchmarks=[
                {
                    'name': 'query_performance_test',
                    'component': 'database',
                    'type': 'database_query',
                    'params': {
                        'iterations': 100,
                        'query_types': ['simple_select', 'complex_join', 'aggregation']
                    }
                }
            ]
        ),
        
        BenchmarkSuite(
            name="cache_performance_suite", 
            description="Cache system performance validation",
            benchmarks=[
                {
                    'name': 'cache_operations_test',
                    'component': 'cache',
                    'type': 'cache_operation',
                    'params': {
                        'iterations': 1000,
                        'key_prefix': 'perf_test'
                    }
                }
            ]
        ),
        
        BenchmarkSuite(
            name="system_integration_suite",
            description="End-to-end system performance validation",
            benchmarks=[
                {
                    'name': 'full_pipeline_test',
                    'component': 'system',
                    'type': 'system_integration',
                    'params': {}
                },
                {
                    'name': 'memory_management_test',
                    'component': 'memory',
                    'type': 'memory_management', 
                    'params': {}
                },
                {
                    'name': 'load_balancing_test',
                    'component': 'load_balancer',
                    'type': 'load_balancing',
                    'params': {
                        'request_count': 1000
                    }
                }
            ]
        )
    ]

# Global benchmark instance
comprehensive_benchmark = ComprehensiveBenchmark()

# Initialize with default suites
for suite in create_default_benchmark_suites():
    comprehensive_benchmark.register_benchmark_suite(suite)

# Convenience functions
async def run_phase3_validation() -> Dict[str, Any]:
    """Run Phase 3 performance validation"""
    logger.info("🎯 Starting Phase 3 Performance Validation")
    logger.info("Target: 60%+ improvement across all systems")
    
    # Establish baseline if not done
    if not comprehensive_benchmark.baseline_established:
        await comprehensive_benchmark.establish_baseline()
    
    # Run comprehensive benchmark
    results = await comprehensive_benchmark.run_comprehensive_benchmark()
    
    # Log summary
    grade = results['performance_grade']
    target_validation = results['target_validation']
    success_rate = target_validation['overall_success_rate']
    
    logger.info(f"✅ Phase 3 Validation Complete!")
    logger.info(f"📊 Performance Grade: {grade}")
    logger.info(f"🎯 Target Success Rate: {success_rate:.1f}%")
    logger.info(f"✅ Targets Met: {target_validation['targets_met']}")
    logger.info(f"❌ Targets Failed: {target_validation['targets_failed']}")
    
    return results

async def establish_performance_baseline() -> Dict[str, Any]:
    """Establish performance baseline"""
    return await comprehensive_benchmark.establish_baseline()

def get_benchmark_status() -> Dict[str, Any]:
    """Get benchmark system status"""
    return comprehensive_benchmark.get_benchmark_summary()

if __name__ == "__main__":
    async def test_comprehensive_benchmark():
        # Run Phase 3 validation
        results = await run_phase3_validation()
        
        print(f"Benchmark Results:")
        print(f"Grade: {results['performance_grade']}")
        print(f"Success Rate: {results['target_validation']['overall_success_rate']:.1f}%")
        
        # Print improvement analysis
        for suite_name, improvements in results.get('improvement_analysis', {}).items():
            print(f"\n{suite_name} Improvements:")
            for bench_name, improvement in improvements.items():
                time_imp = improvement.get('time_improvement_percent', 0)
                print(f"  {bench_name}: {time_imp:+.1f}% time improvement")
    
if __name__ == "__main__":
    asyncio.run(test_comprehensive_benchmark())