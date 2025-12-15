#!/usr/bin/env python3
"""
Database Index Analysis and Optimization
========================================

Phase 3 Performance Optimization: Intelligent database index analysis and
optimization targeting 95% of queries under 100ms response time.

Key Features:
- Automatic index usage analysis
- Query performance monitoring
- Index recommendation system
- Connection pool optimization
- Real-time performance tracking
- Automated maintenance scheduling
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncpg
import psutil
from contextlib import asynccontextmanager

# Import performance monitoring
try:
    from ..backend.services.performance_monitor import performance_monitor, track_database_query_time
except ImportError:
    performance_monitor = None
    async def track_database_query_time(query_time_ms, query_type="general"):
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryPerformanceMetric:
    """Query performance metric"""
    query: str
    calls: int
    total_time: float
    mean_time: float
    min_time: float
    max_time: float
    stddev_time: float
    rows: int
    hit_percent: float

@dataclass
class IndexRecommendation:
    """Index recommendation"""
    table_name: str
    columns: List[str]
    index_type: str
    reason: str
    expected_improvement: str
    query_examples: List[str]
    priority: str  # "high", "medium", "low"

@dataclass
class DatabaseHealthMetrics:
    """Database health metrics"""
    total_queries: int
    avg_query_time: float
    slow_query_count: int
    slow_query_percent: float
    connection_count: int
    cache_hit_ratio: float
    table_bloat_percent: float
    index_usage_percent: float

class DatabaseOptimizer:
    """
    Database optimization and monitoring system
    
    Features:
    - Query performance analysis
    - Index optimization recommendations
    - Connection pool monitoring
    - Automatic maintenance scheduling
    - Real-time performance tracking
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection_pool = None
        self.monitoring_enabled = True
        self.slow_query_threshold = 100.0  # 100ms
        self.target_hit_ratio = 95.0  # 95% cache hit ratio
        
        # Performance tracking
        self.query_history = []
        self.optimization_history = []
        self.current_recommendations = []
        
        logger.info("🔧 Database Optimizer initialized")
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=10,
                max_size=50,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30
            )
            
            logger.info("✅ Database connection pool initialized")
            
            # Enable query statistics if not already enabled
            await self._enable_query_stats()
            
        except Exception as e:
            logger.error(f"Failed to initialize database optimizer: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with performance tracking"""
        start_time = time.time()
        
        async with self.connection_pool.acquire() as connection:
            try:
                yield connection
            finally:
                # Track connection acquisition time
                acquisition_time = (time.time() - start_time) * 1000
                if acquisition_time > 10:  # More than 10ms to get connection
                    logger.warning(f"Slow connection acquisition: {acquisition_time:.2f}ms")
    
    async def _enable_query_stats(self):
        """Enable query statistics collection"""
        try:
            async with self.get_connection() as conn:
                # Enable pg_stat_statements if available
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                logger.info("✅ Query statistics enabled")
        except Exception as e:
            logger.warning(f"Could not enable query statistics: {e}")
    
    async def analyze_query_performance(self) -> List[QueryPerformanceMetric]:
        """Analyze query performance from pg_stat_statements"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT 
                        query,
                        calls,
                        total_exec_time as total_time,
                        mean_exec_time as mean_time,
                        min_exec_time as min_time,
                        max_exec_time as max_time,
                        stddev_exec_time as stddev_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements 
                    WHERE calls > 10  -- Only analyze frequently called queries
                    ORDER BY mean_exec_time DESC
                    LIMIT 100
                """
                
                start_time = time.time()
                rows = await conn.fetch(query)
                query_time = (time.time() - start_time) * 1000
                
                await track_database_query_time(query_time, "performance_analysis")
                
                metrics = []
                for row in rows:
                    metrics.append(QueryPerformanceMetric(
                        query=row['query'][:200],  # Truncate for readability
                        calls=row['calls'],
                        total_time=row['total_time'],
                        mean_time=row['mean_time'],
                        min_time=row['min_time'],
                        max_time=row['max_time'],
                        stddev_time=row['stddev_time'],
                        rows=row['rows'],
                        hit_percent=row['hit_percent'] or 0
                    ))
                
                logger.info(f"Analyzed {len(metrics)} query performance metrics")
                return metrics
                
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return []
    
    async def get_slow_queries(self, threshold_ms: float = None) -> List[QueryPerformanceMetric]:
        """Get queries slower than threshold"""
        if threshold_ms is None:
            threshold_ms = self.slow_query_threshold
        
        all_metrics = await self.analyze_query_performance()
        slow_queries = [m for m in all_metrics if m.mean_time > threshold_ms]
        
        logger.info(f"Found {len(slow_queries)} slow queries (>{threshold_ms}ms)")
        return slow_queries
    
    async def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze index usage statistics"""
        try:
            async with self.get_connection() as conn:
                # Index usage statistics
                index_usage_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch,
                        CASE 
                            WHEN idx_tup_read > 0 THEN 
                                round(idx_tup_fetch * 100.0 / idx_tup_read, 2) 
                            ELSE 0 
                        END as usage_ratio
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY idx_tup_read DESC
                """
                
                # Unused indexes
                unused_indexes_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public' 
                      AND idx_scan = 0
                      AND indexname NOT LIKE '%_pkey'  -- Exclude primary keys
                    ORDER BY pg_relation_size(indexrelid) DESC
                """
                
                # Missing indexes (table scans)
                table_scans_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        n_tup_ins + n_tup_upd + n_tup_del as write_activity
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                      AND seq_scan > idx_scan  -- More sequential scans than index scans
                    ORDER BY seq_tup_read DESC
                """
                
                start_time = time.time()
                
                index_usage = await conn.fetch(index_usage_query)
                unused_indexes = await conn.fetch(unused_indexes_query)
                table_scans = await conn.fetch(table_scans_query)
                
                query_time = (time.time() - start_time) * 1000
                await track_database_query_time(query_time, "index_analysis")
                
                return {
                    'index_usage': [dict(row) for row in index_usage],
                    'unused_indexes': [dict(row) for row in unused_indexes],
                    'tables_with_scans': [dict(row) for row in table_scans],
                    'total_indexes': len(index_usage),
                    'unused_count': len(unused_indexes),
                    'scan_heavy_tables': len(table_scans)
                }
                
        except Exception as e:
            logger.error(f"Error analyzing index usage: {e}")
            return {}
    
    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Generate intelligent index recommendations"""
        recommendations = []
        
        try:
            # Get slow queries and analyze them
            slow_queries = await self.get_slow_queries()
            index_analysis = await self.analyze_index_usage()
            
            # Analyze query patterns for missing indexes
            for query_metric in slow_queries:
                query = query_metric.query.lower()
                
                # Simple pattern matching for common optimization opportunities
                if 'where' in query and 'order by' not in query:
                    # Potential filtering index needed
                    if query_metric.mean_time > 500:  # Very slow query
                        recommendations.append(IndexRecommendation(
                            table_name="identified_from_query",
                            columns=["extracted_from_where_clause"],
                            index_type="btree",
                            reason=f"Query filtering without index (avg: {query_metric.mean_time:.2f}ms)",
                            expected_improvement="50-80% faster",
                            query_examples=[query_metric.query[:100]],
                            priority="high"
                        ))
                
                elif 'order by' in query:
                    # Potential sorting index needed
                    if query_metric.mean_time > 200:
                        recommendations.append(IndexRecommendation(
                            table_name="identified_from_query",
                            columns=["order_by_columns"],
                            index_type="btree",
                            reason=f"Query sorting without index (avg: {query_metric.mean_time:.2f}ms)",
                            expected_improvement="30-60% faster",
                            query_examples=[query_metric.query[:100]],
                            priority="medium"
                        ))
            
            # Analyze tables with high sequential scan activity
            for table_info in index_analysis.get('tables_with_scans', []):
                if table_info['seq_tup_read'] > 10000:  # High scan activity
                    recommendations.append(IndexRecommendation(
                        table_name=table_info['tablename'],
                        columns=["frequently_filtered_columns"],
                        index_type="btree",
                        reason=f"High sequential scan activity ({table_info['seq_tup_read']} tuples)",
                        expected_improvement="40-70% faster",
                        query_examples=["SELECT queries on this table"],
                        priority="high"
                    ))
            
            # Specific recommendations for known patterns
            specific_recommendations = await self._get_specific_recommendations()
            recommendations.extend(specific_recommendations)
            
            self.current_recommendations = recommendations
            logger.info(f"Generated {len(recommendations)} index recommendations")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating index recommendations: {e}")
            return []
    
    async def _get_specific_recommendations(self) -> List[IndexRecommendation]:
        """Get specific recommendations for known table patterns"""
        recommendations = []
        
        try:
            async with self.get_connection() as conn:
                # Check if video_processing_results table needs optimization
                video_table_stats = await conn.fetchrow("""
                    SELECT 
                        seq_scan, 
                        seq_tup_read, 
                        idx_scan,
                        n_tup_ins + n_tup_upd + n_tup_del as write_activity
                    FROM pg_stat_user_tables 
                    WHERE tablename = 'video_processing_results'
                """)
                
                if video_table_stats and video_table_stats['seq_scan'] > video_table_stats['idx_scan']:
                    recommendations.append(IndexRecommendation(
                        table_name="video_processing_results",
                        columns=["video_id", "processing_type", "status"],
                        index_type="btree",
                        reason="High sequential scan activity on video results lookup",
                        expected_improvement="60-80% faster video result queries",
                        query_examples=[
                            "SELECT * FROM video_processing_results WHERE video_id = ? AND processing_type = ?",
                            "SELECT * FROM video_processing_results WHERE status = 'completed'"
                        ],
                        priority="high"
                    ))
                
                # Check performance_metrics table
                perf_metrics_stats = await conn.fetchrow("""
                    SELECT 
                        seq_scan, 
                        seq_tup_read, 
                        idx_scan
                    FROM pg_stat_user_tables 
                    WHERE tablename = 'performance_metrics_optimized'
                """)
                
                if perf_metrics_stats and perf_metrics_stats['seq_tup_read'] > 50000:
                    recommendations.append(IndexRecommendation(
                        table_name="performance_metrics_optimized",
                        columns=["component", "timestamp"],
                        index_type="btree",
                        reason="Time-series queries need timestamp-based indexing",
                        expected_improvement="70-90% faster metrics queries",
                        query_examples=[
                            "SELECT * FROM performance_metrics_optimized WHERE component = ? AND timestamp >= ?",
                            "SELECT AVG(value) FROM performance_metrics_optimized WHERE timestamp >= ?"
                        ],
                        priority="high"
                    ))
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Error getting specific recommendations: {e}")
            return []
    
    async def get_database_health_metrics(self) -> DatabaseHealthMetrics:
        """Get comprehensive database health metrics"""
        try:
            async with self.get_connection() as conn:
                # Overall query performance
                query_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_queries,
                        AVG(mean_exec_time) as avg_query_time,
                        COUNT(*) FILTER (WHERE mean_exec_time > 100) as slow_query_count
                    FROM pg_stat_statements
                    WHERE calls > 1
                """)
                
                # Connection stats
                connection_stats = await conn.fetchrow("""
                    SELECT COUNT(*) as connection_count
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                
                # Cache hit ratio
                cache_stats = await conn.fetchrow("""
                    SELECT 
                        sum(blks_hit) as cache_hits,
                        sum(blks_hit + blks_read) as total_reads
                    FROM pg_stat_database
                """)
                
                # Table bloat check
                bloat_stats = await conn.fetchrow("""
                    SELECT 
                        AVG(
                            CASE 
                                WHEN n_dead_tup > 0 THEN 
                                    (n_dead_tup * 100.0 / (n_live_tup + n_dead_tup))
                                ELSE 0 
                            END
                        ) as avg_bloat_percent
                    FROM pg_stat_user_tables
                    WHERE n_live_tup > 0
                """)
                
                # Index usage
                index_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_indexes,
                        COUNT(*) FILTER (WHERE idx_scan > 0) as used_indexes
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                """)
                
                # Calculate metrics
                total_queries = query_stats['total_queries'] or 0
                slow_queries = query_stats['slow_query_count'] or 0
                slow_query_percent = (slow_queries / total_queries * 100) if total_queries > 0 else 0
                
                cache_hits = cache_stats['cache_hits'] or 0
                total_reads = cache_stats['total_reads'] or 0
                cache_hit_ratio = (cache_hits / total_reads * 100) if total_reads > 0 else 0
                
                total_indexes = index_stats['total_indexes'] or 0
                used_indexes = index_stats['used_indexes'] or 0
                index_usage_percent = (used_indexes / total_indexes * 100) if total_indexes > 0 else 0
                
                return DatabaseHealthMetrics(
                    total_queries=total_queries,
                    avg_query_time=query_stats['avg_query_time'] or 0,
                    slow_query_count=slow_queries,
                    slow_query_percent=slow_query_percent,
                    connection_count=connection_stats['connection_count'] or 0,
                    cache_hit_ratio=cache_hit_ratio,
                    table_bloat_percent=bloat_stats['avg_bloat_percent'] or 0,
                    index_usage_percent=index_usage_percent
                )
                
        except Exception as e:
            logger.error(f"Error getting database health metrics: {e}")
            return DatabaseHealthMetrics(0, 0, 0, 0, 0, 0, 0, 0)
    
    async def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run database performance benchmark"""
        logger.info("🏃 Running database performance benchmark...")
        
        benchmark_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tests': [],
            'summary': {}
        }
        
        try:
            async with self.get_connection() as conn:
                # Test 1: Simple SELECT performance
                start_time = time.time()
                await conn.fetchrow("SELECT 1")
                simple_query_time = (time.time() - start_time) * 1000
                
                benchmark_results['tests'].append({
                    'name': 'Simple SELECT',
                    'time_ms': simple_query_time,
                    'meets_target': simple_query_time < 10,
                    'target_ms': 10
                })
                
                # Test 2: Video result lookup (if table exists)
                try:
                    start_time = time.time()
                    await conn.fetchrow("""
                        SELECT id, result, status 
                        FROM video_processing_results 
                        WHERE video_id = 'test123' 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    video_lookup_time = (time.time() - start_time) * 1000
                    
                    benchmark_results['tests'].append({
                        'name': 'Video Result Lookup',
                        'time_ms': video_lookup_time,
                        'meets_target': video_lookup_time < 100,
                        'target_ms': 100
                    })
                except Exception:
                    pass  # Table might not exist
                
                # Test 3: Aggregate query performance
                start_time = time.time()
                await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_tables,
                        SUM(pg_total_relation_size(oid)) as total_size
                    FROM pg_class 
                    WHERE relkind = 'r'
                """)
                aggregate_time = (time.time() - start_time) * 1000
                
                benchmark_results['tests'].append({
                    'name': 'Aggregate Query',
                    'time_ms': aggregate_time,
                    'meets_target': aggregate_time < 100,
                    'target_ms': 100
                })
                
                # Calculate summary
                total_tests = len(benchmark_results['tests'])
                tests_meeting_target = len([t for t in benchmark_results['tests'] if t['meets_target']])
                avg_query_time = sum(t['time_ms'] for t in benchmark_results['tests']) / total_tests
                
                benchmark_results['summary'] = {
                    'total_tests': total_tests,
                    'tests_meeting_target': tests_meeting_target,
                    'target_achievement_percent': (tests_meeting_target / total_tests * 100),
                    'avg_query_time_ms': avg_query_time,
                    'performance_grade': 'A' if tests_meeting_target == total_tests else 'B' if tests_meeting_target >= total_tests * 0.8 else 'C'
                }
                
                logger.info(f"✅ Benchmark completed: {tests_meeting_target}/{total_tests} tests meeting targets")
                
        except Exception as e:
            logger.error(f"Error running performance benchmark: {e}")
            benchmark_results['error'] = str(e)
        
        return benchmark_results
    
    async def optimize_connection_pool(self) -> Dict[str, Any]:
        """Optimize connection pool settings based on current usage"""
        try:
            pool_stats = {
                'current_size': self.connection_pool.get_size(),
                'max_size': self.connection_pool.get_max_size(),
                'min_size': self.connection_pool.get_min_size(),
                'idle_size': self.connection_pool.get_idle_size()
            }
            
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            
            optimization_suggestions = []
            
            # Pool size optimization
            utilization = (pool_stats['current_size'] - pool_stats['idle_size']) / pool_stats['current_size']
            
            if utilization > 0.8:
                optimization_suggestions.append({
                    'type': 'increase_pool_size',
                    'current_max': pool_stats['max_size'],
                    'suggested_max': min(pool_stats['max_size'] + 10, 100),
                    'reason': f'High pool utilization: {utilization:.1%}'
                })
            elif utilization < 0.3 and pool_stats['max_size'] > 20:
                optimization_suggestions.append({
                    'type': 'decrease_pool_size',
                    'current_max': pool_stats['max_size'],
                    'suggested_max': max(pool_stats['max_size'] - 5, 20),
                    'reason': f'Low pool utilization: {utilization:.1%}'
                })
            
            # Memory-based optimization
            if memory_info.percent > 85:
                optimization_suggestions.append({
                    'type': 'reduce_connections',
                    'reason': f'High memory usage: {memory_info.percent:.1f}%',
                    'suggested_action': 'Consider reducing max_size or optimizing queries'
                })
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_stats': pool_stats,
                'system_resources': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_info.percent,
                    'available_memory_gb': memory_info.available / (1024**3)
                },
                'utilization': utilization,
                'optimization_suggestions': optimization_suggestions
            }
            
        except Exception as e:
            logger.error(f"Error optimizing connection pool: {e}")
            return {}
    
    async def get_optimization_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive optimization dashboard"""
        try:
            health_metrics = await self.get_database_health_metrics()
            slow_queries = await self.get_slow_queries()
            index_analysis = await self.analyze_index_usage()
            recommendations = self.current_recommendations or await self.generate_index_recommendations()
            pool_optimization = await self.optimize_connection_pool()
            
            # Calculate performance targets achievement
            target_achievements = {
                'sub_100ms_queries': {
                    'target_percent': 95.0,
                    'current_percent': max(0, 100 - health_metrics.slow_query_percent),
                    'achieved': health_metrics.slow_query_percent < 5.0
                },
                'cache_hit_ratio': {
                    'target_percent': 95.0,
                    'current_percent': health_metrics.cache_hit_ratio,
                    'achieved': health_metrics.cache_hit_ratio >= 95.0
                },
                'index_utilization': {
                    'target_percent': 80.0,
                    'current_percent': health_metrics.index_usage_percent,
                    'achieved': health_metrics.index_usage_percent >= 80.0
                }
            }
            
            dashboard = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'health_metrics': asdict(health_metrics),
                'performance_targets': target_achievements,
                'slow_queries_summary': {
                    'count': len(slow_queries),
                    'avg_time': sum(q.mean_time for q in slow_queries) / len(slow_queries) if slow_queries else 0,
                    'slowest_query_time': max((q.mean_time for q in slow_queries), default=0)
                },
                'index_analysis': index_analysis,
                'recommendations': {
                    'count': len(recommendations),
                    'high_priority': len([r for r in recommendations if r.priority == 'high']),
                    'medium_priority': len([r for r in recommendations if r.priority == 'medium']),
                    'low_priority': len([r for r in recommendations if r.priority == 'low'])
                },
                'connection_pool': pool_optimization,
                'overall_grade': self._calculate_performance_grade(health_metrics, target_achievements)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating optimization dashboard: {e}")
            return {}
    
    def _calculate_performance_grade(self, health_metrics: DatabaseHealthMetrics, targets: Dict[str, Any]) -> str:
        """Calculate overall performance grade"""
        score = 0
        
        # Sub-100ms queries target (40 points)
        if targets['sub_100ms_queries']['achieved']:
            score += 40
        else:
            score += 40 * (targets['sub_100ms_queries']['current_percent'] / 100)
        
        # Cache hit ratio (30 points)
        if targets['cache_hit_ratio']['achieved']:
            score += 30
        else:
            score += 30 * (targets['cache_hit_ratio']['current_percent'] / 100)
        
        # Index utilization (20 points)
        if targets['index_utilization']['achieved']:
            score += 20
        else:
            score += 20 * (targets['index_utilization']['current_percent'] / 100)
        
        # Connection efficiency (10 points)
        if health_metrics.connection_count < 50:  # Reasonable connection count
            score += 10
        elif health_metrics.connection_count < 100:
            score += 5
        
        # Convert to letter grade
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

# Global database optimizer instance
database_optimizer = None

async def initialize_database_optimizer(database_url: str):
    """Initialize global database optimizer"""
    global database_optimizer
    database_optimizer = DatabaseOptimizer(database_url)
    await database_optimizer.initialize()

async def get_database_performance_dashboard() -> Dict[str, Any]:
    """Get database performance dashboard"""
    if database_optimizer:
        return await database_optimizer.get_optimization_dashboard()
    return {}

async def run_database_benchmark() -> Dict[str, Any]:
    """Run database performance benchmark"""
    if database_optimizer:
        return await database_optimizer.run_performance_benchmark()
    return {}

if __name__ == "__main__":
    async def test_database_optimizer():
        # Example database URL (adjust for your setup)
        db_url = "postgresql://user:password@localhost:5432/uvai_db"
        
        optimizer = DatabaseOptimizer(db_url)
        
        try:
            await optimizer.initialize()
            
            # Run performance analysis
            slow_queries = await optimizer.get_slow_queries()
            print(f"Found {len(slow_queries)} slow queries")
            
            # Generate recommendations
            recommendations = await optimizer.generate_index_recommendations()
            print(f"Generated {len(recommendations)} optimization recommendations")
            
            # Get dashboard
            dashboard = await optimizer.get_optimization_dashboard()
            print(f"Performance grade: {dashboard.get('overall_grade', 'N/A')}")
            
            # Run benchmark
            benchmark = await optimizer.run_performance_benchmark()
            print(f"Benchmark results: {json.dumps(benchmark, indent=2, default=str)}")
            
        finally:
            await optimizer.close()
    
if __name__ == "__main__":
    asyncio.run(test_database_optimizer())