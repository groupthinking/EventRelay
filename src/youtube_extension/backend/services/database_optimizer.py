#!/usr/bin/env python3
"""
Database Query Optimization System - Phase 3 Performance Optimization
=====================================================================

High-performance database optimization targeting 95% of queries under 100ms
response time through intelligent query optimization, connection pooling,
and automated performance monitoring.

Key Features:
- Connection pooling with intelligent sizing
- Query optimization and caching
- Automatic index recommendations
- Real-time performance monitoring
- Database health checks and alerts
- Query plan analysis and optimization
- Batch operation optimization
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import sqlite3
import os
import hashlib
import psutil

# Database imports (gracefully handle missing dependencies)
try:
    import aiopg
    import asyncpg
    import psycopg2
    from psycopg2 import pool as sync_pool
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False
    aiopg = asyncpg = psycopg2 = sync_pool = None

try:
    from .performance_monitor import performance_monitor, track_database_query_time
    from .intelligent_cache import cache_get, cache_set, cached
except ImportError:
    performance_monitor = None
    async def track_database_query_time(time_ms, query_type="general"): pass
    async def cache_get(key): return None
    async def cache_set(key, value, ttl=None, tags=None): return False
    def cached(ttl=None, tags=None): 
        def decorator(func): return func
        return decorator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """Database query statistics"""
    query_hash: str
    query_pattern: str
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0
    last_executed: datetime = None
    error_count: int = 0
    
    def update_stats(self, execution_time_ms: float, success: bool = True):
        """Update query statistics"""
        self.execution_count += 1
        self.total_execution_time_ms += execution_time_ms
        self.avg_execution_time_ms = self.total_execution_time_ms / self.execution_count
        self.min_execution_time_ms = min(self.min_execution_time_ms, execution_time_ms)
        self.max_execution_time_ms = max(self.max_execution_time_ms, execution_time_ms)
        self.last_executed = datetime.now(timezone.utc)
        
        if not success:
            self.error_count += 1

@dataclass
class IndexRecommendation:
    """Database index recommendation"""
    table_name: str
    columns: List[str]
    index_type: str  # btree, hash, gin, etc.
    estimated_improvement: float  # percentage
    query_pattern: str
    priority: str  # high, medium, low
    created_at: datetime
    reason: str

class DatabaseConnectionPool:
    """Intelligent database connection pool"""
    
    def __init__(self, 
                 database_url: str,
                 min_connections: int = 5,
                 max_connections: int = 20,
                 pool_timeout: int = 30):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool_timeout = pool_timeout
        
        # Pool management
        self.pool = None
        self.pool_stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_in_use': 0,
            'connections_available': 0,
            'total_queries': 0,
            'failed_queries': 0,
            'avg_connection_time_ms': 0.0
        }
        
        # Connection monitoring
        self.connection_history = deque(maxlen=1000)
        self._lock = threading.Lock()
        # SQLite path parsing
        self._sqlite_path = None
        if self.database_url.startswith('sqlite://'):
            # Formats: sqlite:///:memory: or sqlite:////absolute/path.db
            path = self.database_url[len('sqlite://'):]  # may start with /:memory: or ////
            if path.startswith('/:memory:'):
                self._sqlite_path = ':memory:'
            else:
                # Normalize leading slashes
                if path.startswith('/') and not path.startswith('//'):
                    # Single leading slash -> relative; make absolute under workspace
                    self._sqlite_path = os.path.abspath(path)
                else:
                    # Likely '///absolute' or similar; reduce to absolute
                    self._sqlite_path = '/' + path.lstrip('/')
    
    async def initialize(self):
        """Initialize the connection pool"""
        try:
            if HAS_POSTGRESQL and 'postgresql' in self.database_url:
                # PostgreSQL connection pool
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=self.min_connections,
                    max_size=self.max_connections,
                    command_timeout=self.pool_timeout
                )
                logger.info(f"✅ PostgreSQL connection pool initialized ({self.min_connections}-{self.max_connections} connections)")
            else:
                # SQLite or other - prepare SQLite path
                if self._sqlite_path and self._sqlite_path != ':memory:':
                    os.makedirs(os.path.dirname(self._sqlite_path), exist_ok=True)
                    logger.info(f"✅ SQLite database configured at {self._sqlite_path}")
                else:
                    logger.info("✅ SQLite in-memory database configured")
                
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    async def get_connection(self):
        """Get connection from pool with monitoring"""
        start_time = time.time()
        
        try:
            if self.pool:
                connection = await self.pool.acquire()
            else:
                # SQLite fallback (file or memory)
                connection = sqlite3.connect(self._sqlite_path or ':memory:')
            
            connection_time = (time.time() - start_time) * 1000
            
            with self._lock:
                self.pool_stats['connections_in_use'] += 1
                self.pool_stats['avg_connection_time_ms'] = (
                    (self.pool_stats['avg_connection_time_ms'] * len(self.connection_history) + connection_time) /
                    (len(self.connection_history) + 1)
                )
                self.connection_history.append(connection_time)
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise
    
    async def release_connection(self, connection):
        """Release connection back to pool"""
        try:
            if self.pool and hasattr(self.pool, 'release'):
                await self.pool.release(connection)
            elif hasattr(connection, 'close'):
                connection.close()
            
            with self._lock:
                self.pool_stats['connections_in_use'] = max(0, self.pool_stats['connections_in_use'] - 1)
                
        except Exception as e:
            logger.error(f"Failed to release database connection: {e}")
    
    async def close(self):
        """Close the connection pool"""
        try:
            if self.pool and hasattr(self.pool, 'close'):
                await self.pool.close()
                logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            **self.pool_stats,
            'pool_configuration': {
                'min_connections': self.min_connections,
                'max_connections': self.max_connections,
                'pool_timeout': self.pool_timeout
            },
            'recent_connection_times': list(self.connection_history)[-50:]  # Last 50 connection times
        }

class QueryOptimizer:
    """Advanced database query optimizer"""
    
    def __init__(self, connection_pool: DatabaseConnectionPool):
        self.connection_pool = connection_pool
        
        # Query monitoring and statistics
        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_query_threshold_ms = 100  # Phase 3 target: sub-100ms
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Optimization recommendations
        self.index_recommendations: List[IndexRecommendation] = []
        self.optimization_history = []
        
        # Performance targets
        self.performance_targets = {
            'sub_100ms_percentage': 95.0,  # 95% of queries under 100ms
            'avg_query_time_ms': 50.0,     # Average query time under 50ms
            'max_acceptable_time_ms': 1000,  # No query over 1 second
            'cache_hit_rate': 80.0         # 80% cache hit rate
        }
        
        logger.info("🚀 Query Optimizer initialized with Phase 3 performance targets")
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query pattern"""
        # Normalize query for pattern matching
        normalized = query.lower().strip()
        # Remove parameter values for pattern matching
        import re
        normalized = re.sub(r'\b\d+\b', '?', normalized)  # Replace numbers with ?
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # Replace string literals
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_query_pattern(self, query: str) -> str:
        """Extract query pattern for analysis"""
        # Extract the main operation and table(s)
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select'):
            # Extract table names from FROM clause
            import re
            from_match = re.search(r'from\s+(\w+)', query_lower)
            table = from_match.group(1) if from_match else 'unknown'
            return f"SELECT from {table}"
        elif query_lower.startswith('insert'):
            into_match = re.search(r'into\s+(\w+)', query_lower)
            table = into_match.group(1) if into_match else 'unknown'
            return f"INSERT into {table}"
        elif query_lower.startswith('update'):
            update_match = re.search(r'update\s+(\w+)', query_lower)
            table = update_match.group(1) if update_match else 'unknown'
            return f"UPDATE {table}"
        elif query_lower.startswith('delete'):
            from_match = re.search(r'from\s+(\w+)', query_lower)
            table = from_match.group(1) if from_match else 'unknown'
            return f"DELETE from {table}"
        else:
            return "OTHER"
    
    async def execute_query(self, query: str, params: Tuple = None, use_cache: bool = True) -> Any:
        """
        Execute optimized database query with performance monitoring
        
        Target: 95% of queries under 100ms response time
        """
        query_hash = self._get_query_hash(query)
        query_pattern = self._get_query_pattern(query)
        start_time = time.time()
        
        # Check query cache first
        if use_cache:
            cache_key = f"query:{query_hash}:{hashlib.md5(str(params).encode()).hexdigest() if params else 'no_params'}"
            cached_result = await cache_get(cache_key)
            
            if cached_result is not None:
                execution_time = (time.time() - start_time) * 1000
                logger.debug(f"Query cache HIT ({execution_time:.2f}ms): {query_pattern}")
                
                # Update stats for cache hit (very fast execution)
                await self._update_query_stats(query_hash, query_pattern, execution_time, True)
                return cached_result
        
        # Execute query
        connection = None
        try:
            connection = await self.connection_pool.get_connection()
            
            if hasattr(connection, 'fetch'):
                # PostgreSQL (asyncpg)
                if params:
                    result = await connection.fetch(query, *params)
                else:
                    result = await connection.fetch(query)
            elif hasattr(connection, 'execute'):
                # SQLite or other
                cursor = connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                result = cursor.fetchall()
            else:
                raise Exception(f"Unsupported connection type: {type(connection)}")
            
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics
            await self._update_query_stats(query_hash, query_pattern, execution_time, True)
            
            # Cache result if appropriate
            if use_cache and execution_time > 50:  # Cache slower queries
                await cache_set(cache_key, result, ttl=self.cache_ttl, tags=["database_query"])
            
            # Track performance
            if performance_monitor:
                await track_database_query_time(execution_time, query_pattern)
            
            # Check for slow query
            if execution_time > self.slow_query_threshold_ms:
                await self._handle_slow_query(query, query_pattern, execution_time)
            
            logger.debug(f"Query executed ({execution_time:.2f}ms): {query_pattern}")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            await self._update_query_stats(query_hash, query_pattern, execution_time, False)
            
            logger.error(f"Query failed ({execution_time:.2f}ms): {query_pattern} - {e}")
            raise
            
        finally:
            if connection:
                await self.connection_pool.release_connection(connection)
    
    async def execute_batch_queries(self, queries_and_params: List[Tuple[str, Tuple]]) -> List[Any]:
        """
        Execute batch of queries with optimization
        
        Target: Significant improvement over sequential execution
        """
        start_time = time.time()
        
        logger.info(f"🚀 Executing batch: {len(queries_and_params)} queries")
        
        # Group similar queries for batch processing
        query_groups = defaultdict(list)
        for i, (query, params) in enumerate(queries_and_params):
            pattern = self._get_query_pattern(query)
            query_groups[pattern].append((i, query, params))
        
        # Execute groups in parallel
        connection = None
        try:
            connection = await self.connection_pool.get_connection()
            results = [None] * len(queries_and_params)
            
            # Execute each group
            for pattern, group_queries in query_groups.items():
                if len(group_queries) > 1 and hasattr(connection, 'executemany'):
                    # Use batch execution if available
                    batch_start = time.time()
                    
                    # Extract queries and params
                    queries = [q[1] for q in group_queries]
                    params_list = [q[2] for q in group_queries]
                    
                    # Execute batch (simplified - real implementation would be more complex)
                    for i, (original_index, query, params) in enumerate(group_queries):
                        query_result = await self.execute_query(query, params, use_cache=True)
                        results[original_index] = query_result
                    
                    batch_time = (time.time() - batch_start) * 1000
                    logger.debug(f"Batch executed ({batch_time:.2f}ms): {len(group_queries)} {pattern} queries")
                else:
                    # Execute individually
                    for original_index, query, params in group_queries:
                        query_result = await self.execute_query(query, params, use_cache=True)
                        results[original_index] = query_result
            
            total_time = (time.time() - start_time) * 1000
            avg_time_per_query = total_time / len(queries_and_params)
            
            logger.info(f"✅ Batch completed ({total_time:.2f}ms, {avg_time_per_query:.2f}ms/query avg)")
            return results
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Batch failed ({total_time:.2f}ms): {e}")
            raise
            
        finally:
            if connection:
                await self.connection_pool.release_connection(connection)
    
    async def _update_query_stats(self, query_hash: str, query_pattern: str, execution_time_ms: float, success: bool):
        """Update query execution statistics"""
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = QueryStats(
                query_hash=query_hash,
                query_pattern=query_pattern
            )
        
        self.query_stats[query_hash].update_stats(execution_time_ms, success)
    
    async def _handle_slow_query(self, query: str, pattern: str, execution_time_ms: float):
        """Handle slow query detection and optimization"""
        logger.warning(f"🐌 Slow query detected ({execution_time_ms:.2f}ms): {pattern}")
        
        # Generate optimization recommendations
        await self._analyze_slow_query(query, pattern, execution_time_ms)
        
        # Add to optimization history
        self.optimization_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query_pattern': pattern,
            'execution_time_ms': execution_time_ms,
            'recommendations_generated': True
        })
    
    async def _analyze_slow_query(self, query: str, pattern: str, execution_time_ms: float):
        """Analyze slow query and generate optimization recommendations"""
        
        # Extract table names and operations
        query_lower = query.lower()
        
        # Basic optimization recommendations
        recommendations = []
        
        if 'where' in query_lower and 'index' not in query_lower:
            # Recommend index on WHERE clause columns
            import re
            where_match = re.search(r'where\s+(\w+)', query_lower)
            if where_match:
                column = where_match.group(1)
                table_match = re.search(r'from\s+(\w+)', query_lower)
                table = table_match.group(1) if table_match else 'unknown'
                
                recommendation = IndexRecommendation(
                    table_name=table,
                    columns=[column],
                    index_type='btree',
                    estimated_improvement=30.0,
                    query_pattern=pattern,
                    priority='high' if execution_time_ms > 500 else 'medium',
                    created_at=datetime.now(timezone.utc),
                    reason=f'WHERE clause on {column} column causing slow query ({execution_time_ms:.1f}ms)'
                )
                self.index_recommendations.append(recommendation)
        
        if 'order by' in query_lower:
            # Recommend index on ORDER BY columns
            order_match = re.search(r'order by\s+(\w+)', query_lower)
            if order_match:
                column = order_match.group(1)
                table_match = re.search(r'from\s+(\w+)', query_lower)
                table = table_match.group(1) if table_match else 'unknown'
                
                recommendation = IndexRecommendation(
                    table_name=table,
                    columns=[column],
                    index_type='btree',
                    estimated_improvement=25.0,
                    query_pattern=pattern,
                    priority='medium',
                    created_at=datetime.now(timezone.utc),
                    reason=f'ORDER BY clause on {column} column could benefit from index'
                )
                self.index_recommendations.append(recommendation)
        
        if 'join' in query_lower:
            # Recommend indexes on JOIN columns
            recommendation = IndexRecommendation(
                table_name='multiple',
                columns=['join_columns'],
                index_type='btree',
                estimated_improvement=40.0,
                query_pattern=pattern,
                priority='high',
                created_at=datetime.now(timezone.utc),
                reason=f'JOIN operation causing slow query ({execution_time_ms:.1f}ms) - check foreign key indexes'
            )
            self.index_recommendations.append(recommendation)
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive database performance report"""
        
        # Calculate performance metrics
        if not self.query_stats:
            return {'message': 'No query statistics available yet'}
        
        total_queries = sum(stats.execution_count for stats in self.query_stats.values())
        avg_execution_times = [stats.avg_execution_time_ms for stats in self.query_stats.values()]
        
        # Performance analysis
        sub_100ms_queries = sum(
            stats.execution_count for stats in self.query_stats.values() 
            if stats.avg_execution_time_ms < 100
        )
        sub_100ms_percentage = (sub_100ms_queries / total_queries * 100) if total_queries > 0 else 0
        
        overall_avg_time = statistics.mean(avg_execution_times) if avg_execution_times else 0
        
        # Slow query analysis
        slow_queries = [
            {
                'pattern': stats.query_pattern,
                'avg_time_ms': stats.avg_execution_time_ms,
                'execution_count': stats.execution_count,
                'error_rate': (stats.error_count / stats.execution_count * 100) if stats.execution_count > 0 else 0
            }
            for stats in self.query_stats.values() 
            if stats.avg_execution_time_ms > 100
        ]
        
        # Performance grade calculation
        if sub_100ms_percentage >= 95 and overall_avg_time < 50:
            grade = "A+"
            assessment = "Excellent - Performance targets exceeded!"
        elif sub_100ms_percentage >= 90 and overall_avg_time < 75:
            grade = "A"
            assessment = "Very good - Close to performance targets"
        elif sub_100ms_percentage >= 80 and overall_avg_time < 100:
            grade = "B+"
            assessment = "Good - Meeting basic performance requirements"
        elif sub_100ms_percentage >= 70:
            grade = "B"
            assessment = "Moderate - Some optimization needed"
        else:
            grade = "C"
            assessment = "Needs significant optimization"
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance_summary': {
                'total_queries_executed': total_queries,
                'sub_100ms_percentage': sub_100ms_percentage,
                'overall_avg_execution_time_ms': overall_avg_time,
                'performance_grade': grade,
                'assessment': assessment,
                'targets_met': {
                    'sub_100ms_target': sub_100ms_percentage >= self.performance_targets['sub_100ms_percentage'],
                    'avg_time_target': overall_avg_time <= self.performance_targets['avg_query_time_ms']
                }
            },
            'detailed_metrics': {
                'query_patterns': len(self.query_stats),
                'slow_queries_count': len(slow_queries),
                'slow_queries': slow_queries[:10],  # Top 10 slow queries
                'optimization_recommendations': len(self.index_recommendations),
                'recent_optimizations': len(self.optimization_history)
            },
            'recommendations': {
                'index_recommendations': [asdict(rec) for rec in self.index_recommendations[-5:]],  # Latest 5 recommendations
                'optimization_priority': 'high' if sub_100ms_percentage < 90 else 'medium' if sub_100ms_percentage < 95 else 'low',
                'next_actions': self._generate_next_actions(sub_100ms_percentage, overall_avg_time)
            },
            'connection_pool_stats': self.connection_pool.get_pool_stats()
        }
    
    def _generate_next_actions(self, sub_100ms_percentage: float, avg_time_ms: float) -> List[str]:
        """Generate next action recommendations"""
        actions = []
        
        if sub_100ms_percentage < 95:
            actions.append(f"Optimize slow queries - currently {sub_100ms_percentage:.1f}% under 100ms (target: 95%)")
        
        if avg_time_ms > 50:
            actions.append(f"Reduce average query time from {avg_time_ms:.1f}ms to under 50ms")
        
        if len(self.index_recommendations) > 0:
            actions.append(f"Implement {len(self.index_recommendations)} pending index recommendations")
        
        if not actions:
            actions.append("Performance targets met - continue monitoring and maintain current optimization level")
        
        return actions

class DatabaseHealthMonitor:
    """Database health monitoring and alerting"""
    
    def __init__(self, query_optimizer: QueryOptimizer):
        self.query_optimizer = query_optimizer
        self.health_checks_enabled = True
        self.health_history = deque(maxlen=1000)
        self.alert_thresholds = {
            'avg_query_time_ms': 100,
            'slow_query_percentage': 5,
            'connection_pool_usage': 80,
            'error_rate_percentage': 1
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive database health check"""
        start_time = time.time()
        
        health_status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_health': 'healthy',
            'checks': {},
            'alerts': [],
            'recommendations': []
        }
        
        try:
            # Connection pool health
            pool_stats = self.query_optimizer.connection_pool.get_pool_stats()
            pool_usage = (pool_stats['connections_in_use'] / self.query_optimizer.connection_pool.max_connections) * 100
            
            health_status['checks']['connection_pool'] = {
                'status': 'healthy' if pool_usage < 80 else 'warning',
                'usage_percentage': pool_usage,
                'connections_available': pool_stats['connections_available'],
                'connections_in_use': pool_stats['connections_in_use']
            }
            
            if pool_usage >= self.alert_thresholds['connection_pool_usage']:
                health_status['alerts'].append({
                    'severity': 'warning',
                    'message': f'High connection pool usage: {pool_usage:.1f}%'
                })
            
            # Query performance health
            if self.query_optimizer.query_stats:
                total_queries = sum(stats.execution_count for stats in self.query_optimizer.query_stats.values())
                avg_times = [stats.avg_execution_time_ms for stats in self.query_optimizer.query_stats.values()]
                overall_avg_time = statistics.mean(avg_times) if avg_times else 0
                
                slow_query_count = sum(
                    1 for stats in self.query_optimizer.query_stats.values() 
                    if stats.avg_execution_time_ms > 100
                )
                slow_query_percentage = (slow_query_count / len(self.query_optimizer.query_stats) * 100) if self.query_optimizer.query_stats else 0
                
                health_status['checks']['query_performance'] = {
                    'status': 'healthy' if overall_avg_time < 100 and slow_query_percentage < 5 else 'warning',
                    'avg_query_time_ms': overall_avg_time,
                    'slow_query_percentage': slow_query_percentage,
                    'total_query_patterns': len(self.query_optimizer.query_stats)
                }
                
                if overall_avg_time >= self.alert_thresholds['avg_query_time_ms']:
                    health_status['alerts'].append({
                        'severity': 'warning',
                        'message': f'High average query time: {overall_avg_time:.1f}ms'
                    })
                
                if slow_query_percentage >= self.alert_thresholds['slow_query_percentage']:
                    health_status['alerts'].append({
                        'severity': 'critical',
                        'message': f'High slow query percentage: {slow_query_percentage:.1f}%'
                    })
            
            # Generate recommendations
            if health_status['alerts']:
                health_status['overall_health'] = 'degraded'
                health_status['recommendations'] = [
                    'Review and optimize slow queries',
                    'Consider increasing connection pool size',
                    'Implement recommended database indexes',
                    'Enable query result caching for frequent queries'
                ]
            
            # Record health check
            check_duration = (time.time() - start_time) * 1000
            self.health_history.append({
                'timestamp': time.time(),
                'duration_ms': check_duration,
                'status': health_status['overall_health'],
                'alert_count': len(health_status['alerts'])
            })
            
            return health_status
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_health': 'unhealthy',
                'error': str(e),
                'checks': {},
                'alerts': [{'severity': 'critical', 'message': f'Health check failed: {e}'}],
                'recommendations': ['Check database connectivity', 'Review database logs']
            }

# Global database optimization system
database_url = os.getenv("DATABASE_URL", "sqlite:////workspace/data/app.db")
connection_pool = DatabaseConnectionPool(database_url, min_connections=1, max_connections=10)
query_optimizer = QueryOptimizer(connection_pool)
health_monitor = DatabaseHealthMonitor(query_optimizer)

# Convenience functions
async def execute_optimized_query(query: str, params: Tuple = None) -> Any:
    """Execute database query with optimization"""
    return await query_optimizer.execute_query(query, params)

async def execute_batch_optimized(queries_and_params: List[Tuple[str, Tuple]]) -> List[Any]:
    """Execute batch queries with optimization"""
    return await query_optimizer.execute_batch_queries(queries_and_params)

async def get_database_performance_report() -> Dict[str, Any]:
    """Get comprehensive database performance report"""
    return await query_optimizer.get_performance_report()

async def get_database_health_status() -> Dict[str, Any]:
    """Get current database health status"""
    return await health_monitor.run_health_check()

async def initialize_database_optimization():
    """Initialize database optimization system"""
    await connection_pool.initialize()
    # Create minimal schema if using sqlite
    try:
        conn = await connection_pool.get_connection()
        try:
            cur = conn.cursor() if hasattr(conn, 'cursor') else None
            if cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        processed BOOLEAN DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS video_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        processing_time_ms REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # Seed minimal data if tables are empty
                try:
                    # Seed videos
                    cur.execute("SELECT COUNT(*) FROM videos")
                    videos_count = cur.fetchone()[0]
                    if videos_count == 0:
                        cur.executemany(
                            "INSERT INTO videos (title, processed) VALUES (?, ?)",
                            [
                                ("Sample Video A", 1),
                                ("Sample Video B", 0),
                                ("Sample Video C", 1),
                            ],
                        )

                    # Seed video analytics
                    cur.execute("SELECT COUNT(*) FROM video_analytics")
                    va_count = cur.fetchone()[0]
                    if va_count == 0:
                        cur.executemany(
                            "INSERT INTO video_analytics (processing_time_ms) VALUES (?)",
                            [
                                (1250.5,),
                                (980.2,),
                                (1575.0,),
                            ],
                        )

                    # Seed users
                    cur.execute("SELECT COUNT(*) FROM users")
                    users_count = cur.fetchone()[0]
                    if users_count == 0:
                        cur.executemany(
                            "INSERT INTO users (email) VALUES (?)",
                            [
                                ("user1@example.com",),
                                ("user2@example.com",),
                            ],
                        )
                except Exception as seed_err:
                    logger.warning(f"DB seeding skipped or failed: {seed_err}")
                if hasattr(conn, 'commit'):
                    conn.commit()
        finally:
            await connection_pool.release_connection(conn)
    except Exception as e:
        logger.warning(f"DB schema initialization skipped or failed: {e}")
    logger.info("🚀 Database optimization system initialized")

async def shutdown_database_optimization():
    """Shutdown database optimization system"""
    await connection_pool.close()
    logger.info("🛑 Database optimization system shutdown")

if __name__ == "__main__":
    async def test_database_optimization():
        # Initialize system
        await initialize_database_optimization()
        
        # Test queries
        try:
            # Simple query test
            result = await execute_optimized_query("SELECT 1 as test_value")
            print(f"Test query result: {result}")
            
            # Batch query test
            batch_queries = [
                ("SELECT 1 as batch_test", ()),
                ("SELECT 2 as batch_test", ()),
                ("SELECT 3 as batch_test", ())
            ]
            batch_results = await execute_batch_optimized(batch_queries)
            print(f"Batch query results: {len(batch_results)} results")
            
        except Exception as e:
            print(f"Query tests failed: {e}")
        
        # Get performance report
        report = await get_database_performance_report()
        print(f"Performance report: {json.dumps(report, indent=2, default=str)}")
        
        # Get health status
        health = await get_database_health_status()
        print(f"Health status: {health['overall_health']}")
        
        # Shutdown
        await shutdown_database_optimization()
    
if __name__ == "__main__":
    asyncio.run(test_database_optimization())