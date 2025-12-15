#!/usr/bin/env python3
"""
API Cost Monitoring and Management Service
==========================================

Real-time API cost tracking, quota management, and optimization for UVAI platform.
Monitors OpenAI, Anthropic, Gemini, YouTube Data API, and other service usage.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import threading
import sqlite3

# Default database location. Allow override via environment variable.
_DEFAULT_DB_PATH_ENV = os.getenv("API_COST_MONITOR_DB_PATH")
DEFAULT_DB_PATH = (
    _DEFAULT_DB_PATH_ENV
    if _DEFAULT_DB_PATH_ENV
    else str((Path(".runtime") / "api_cost_monitoring.db").resolve())
)

# Import cleanup service for database maintenance
try:
    from .database_cleanup_service import cleanup_service
    CLEANUP_AVAILABLE = True
except ImportError:
    CLEANUP_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class APIUsageRecord:
    """Individual API usage record with cost tracking"""
    service: str
    endpoint: str
    tokens_used: int
    cost: float
    timestamp: datetime
    request_type: str
    user_id: Optional[str] = None
    video_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

@dataclass
class RateLimitTracker:
    """Rate limiting tracker for API calls"""
    max_requests: int
    window_seconds: int
    requests: deque = None
    
    def __post_init__(self):
        if self.requests is None:
            self.requests = deque()

class APICostMonitor:
    """
    Comprehensive API cost monitoring and management service
    
    Features:
    - Real-time cost tracking for all API services
    - Rate limiting with intelligent backoff
    - Quota management and budget alerts  
    - Cost optimization through caching
    - Circuit breaker pattern for failed APIs
    - Detailed usage analytics and reporting
    """
    
    # API Cost Models (per 1K tokens/requests)
    COST_MODELS = {
        'openai': {
            'gpt-4o': {'input': 0.0025, 'output': 0.01},
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
            'text-embedding-3-small': {'input': 0.00002, 'output': 0},
            'text-embedding-3-large': {'input': 0.00013, 'output': 0}
        },
        'anthropic': {
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
            'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075},
            'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125}
        },
        'google': {
            'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005},
            'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003}
        },
        'youtube': {
            'search': 100,  # quota units per request
            'videos': 1,    # quota units per request  
            'channels': 1,  # quota units per request
            'captions': 200 # quota units per request
        }
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the API cost monitor"""
        resolved_path = db_path or DEFAULT_DB_PATH
        if resolved_path not in {":memory:", ":memory:"}:
            resolved_path = str(Path(resolved_path).expanduser().resolve())
        self.db_path = resolved_path
        self.daily_budget = float(os.getenv('API_DAILY_BUDGET', '10.00'))
        self.alert_threshold = float(os.getenv('API_ALERT_THRESHOLD', '8.00'))
        self.cost_tracking_enabled = os.getenv('API_COST_TRACKING', 'true').lower() == 'true'
        
        # Rate limiters for different services
        self.rate_limiters = {
            'openai': RateLimitTracker(int(os.getenv('OPENAI_RATE_LIMIT', '50')), 60),
            'anthropic': RateLimitTracker(int(os.getenv('ANTHROPIC_RATE_LIMIT', '30')), 60),
            'google': RateLimitTracker(int(os.getenv('GEMINI_RATE_LIMIT', '60')), 60),
            'youtube': RateLimitTracker(int(os.getenv('YOUTUBE_QUOTA_LIMIT', '10000')), 86400)  # Daily quota
        }
        
        # Circuit breakers
        self.circuit_breakers = defaultdict(lambda: {'failures': 0, 'last_failure': None, 'open': False})
        self.max_failures = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5'))
        
        # Current session tracking
        self.session_costs = defaultdict(float)
        self.session_requests = defaultdict(int)
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"📊 API Cost Monitor initialized - Budget: ${self.daily_budget}, Alert: ${self.alert_threshold}")
    
    def _init_database(self):
        """Initialize the SQLite database for cost tracking"""
        try:
            if self.db_path not in {":memory:", ":memory"}:
                db_parent = Path(self.db_path).expanduser().resolve().parent
                db_parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    request_type TEXT,
                    user_id TEXT,
                    video_id TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_budgets (
                    date TEXT PRIMARY KEY,
                    total_cost REAL DEFAULT 0,
                    alert_sent BOOLEAN DEFAULT 0,
                    budget_exceeded BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON api_usage(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_service ON api_usage(service)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize cost monitoring database: {e}")
    
    def check_rate_limit(self, service: str) -> Tuple[bool, int]:
        """
        Check if service is within rate limits
        
        Returns:
            (allowed: bool, wait_seconds: int)
        """
        if service not in self.rate_limiters:
            return True, 0
            
        with self._lock:
            limiter = self.rate_limiters[service]
            now = time.time()
            
            # Remove old requests outside the window
            while limiter.requests and now - limiter.requests[0] > limiter.window_seconds:
                limiter.requests.popleft()
            
            # Check if under limit
            if len(limiter.requests) < limiter.max_requests:
                limiter.requests.append(now)
                return True, 0
            
            # Calculate wait time
            oldest_request = limiter.requests[0]
            wait_seconds = int(limiter.window_seconds - (now - oldest_request)) + 1
            
            return False, wait_seconds
    
    def check_circuit_breaker(self, service: str) -> bool:
        """Check if circuit breaker is open for service"""
        breaker = self.circuit_breakers[service]
        
        if not breaker['open']:
            return False
            
        # Check if we should try again (5 minute cooldown)
        if breaker['last_failure'] and time.time() - breaker['last_failure'] > 300:
            breaker['open'] = False
            breaker['failures'] = 0
            logger.info(f"🔄 Circuit breaker reset for {service}")
            return False
            
        return True
    
    def record_api_failure(self, service: str, error: str):
        """Record API failure for circuit breaker"""
        with self._lock:
            breaker = self.circuit_breakers[service]
            breaker['failures'] += 1
            breaker['last_failure'] = time.time()
            
            if breaker['failures'] >= self.max_failures:
                breaker['open'] = True
                logger.warning(f"🚫 Circuit breaker opened for {service} after {breaker['failures']} failures")
    
    def calculate_cost(self, service: str, model: str, input_tokens: int, output_tokens: int = 0) -> float:
        """Calculate cost based on service, model, and token usage"""
        if service not in self.COST_MODELS:
            return 0.0
        
        service_costs = self.COST_MODELS[service]
        if model not in service_costs:
            # Use average cost for unknown models
            model = list(service_costs.keys())[0]
        
        if service == 'youtube':
            # YouTube uses quota units, not token pricing
            return input_tokens * 0.0001  # Rough estimate per quota unit
        
        model_cost = service_costs[model]
        if isinstance(model_cost, dict):
            input_cost = (input_tokens / 1000) * model_cost['input']
            output_cost = (output_tokens / 1000) * model_cost['output']
            return input_cost + output_cost
        else:
            return (input_tokens / 1000) * model_cost
    
    async def record_usage(self, 
                          service: str, 
                          endpoint: str, 
                          tokens_used: int, 
                          model: str = None,
                          output_tokens: int = 0,
                          request_type: str = None,
                          user_id: str = None,
                          video_id: str = None,
                          success: bool = True,
                          error_message: str = None) -> APIUsageRecord:
        """Record API usage and calculate costs"""
        
        if not self.cost_tracking_enabled:
            return None
        
        # Calculate cost
        cost = self.calculate_cost(service, model or 'default', tokens_used, output_tokens)
        
        # Create usage record
        record = APIUsageRecord(
            service=service,
            endpoint=endpoint,
            tokens_used=tokens_used,
            cost=cost,
            timestamp=datetime.now(timezone.utc),
            request_type=request_type,
            user_id=user_id,
            video_id=video_id,
            success=success,
            error_message=error_message
        )
        
        # Update session tracking
        with self._lock:
            self.session_costs[service] += cost
            self.session_requests[service] += 1
        
        # Store in database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_usage 
                (service, endpoint, tokens_used, cost, timestamp, request_type, user_id, video_id, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.service, record.endpoint, record.tokens_used, record.cost,
                record.timestamp.isoformat(), record.request_type, record.user_id, 
                record.video_id, record.success, record.error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record API usage: {e}")
        
        # Check budget alerts
        await self._check_budget_alerts()
        
        logger.debug(f"💰 API Usage: {service} - ${cost:.4f} ({tokens_used} tokens)")
        
        return record
    
    async def _check_budget_alerts(self):
        """Check and send budget alerts if thresholds are exceeded"""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            daily_cost = await self.get_daily_cost(today)
            
            if daily_cost >= self.alert_threshold:
                await self._send_budget_alert(daily_cost, 'threshold')
            
            if daily_cost >= self.daily_budget:
                await self._send_budget_alert(daily_cost, 'exceeded')
                
        except Exception as e:
            logger.error(f"Error checking budget alerts: {e}")
    
    async def _send_budget_alert(self, current_cost: float, alert_type: str):
        """Send budget alert (implement notification system)"""
        alert_msg = f"🚨 API Budget Alert: ${current_cost:.2f} "
        
        if alert_type == 'threshold':
            alert_msg += f"(Alert threshold: ${self.alert_threshold})"
        else:
            alert_msg += f"EXCEEDED daily budget of ${self.daily_budget}"
        
        logger.warning(alert_msg)
        
        # TODO: Implement actual notification system (email, Slack, etc.)
        # For now, just log the alert
    
    async def get_daily_cost(self, date: str = None) -> float:
        """Get total cost for a specific date"""
        if not date:
            date = datetime.now(timezone.utc).date().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(cost) FROM api_usage 
                WHERE DATE(timestamp) = ?
            ''', (date,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] is not None else 0.0
            
        except Exception as e:
            logger.error(f"Error getting daily cost: {e}")
            return 0.0
    
    async def get_usage_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get detailed usage analytics for the past N days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Date range
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)
            
            # Total costs by service
            cursor.execute('''
                SELECT service, SUM(cost), COUNT(*), AVG(cost)
                FROM api_usage 
                WHERE DATE(timestamp) BETWEEN ? AND ?
                GROUP BY service
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            service_stats = {}
            for row in cursor.fetchall():
                service, total_cost, request_count, avg_cost = row
                service_stats[service] = {
                    'total_cost': total_cost,
                    'request_count': request_count,
                    'average_cost': avg_cost
                }
            
            # Daily breakdown
            cursor.execute('''
                SELECT DATE(timestamp), SUM(cost), COUNT(*)
                FROM api_usage 
                WHERE DATE(timestamp) BETWEEN ? AND ?
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            daily_stats = []
            for row in cursor.fetchall():
                date, total_cost, request_count = row
                daily_stats.append({
                    'date': date,
                    'total_cost': total_cost,
                    'request_count': request_count
                })
            
            # Error rates
            cursor.execute('''
                SELECT service, 
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors,
                       COUNT(*) as total
                FROM api_usage 
                WHERE DATE(timestamp) BETWEEN ? AND ?
                GROUP BY service
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            error_rates = {}
            for row in cursor.fetchall():
                service, errors, total = row
                error_rates[service] = {
                    'error_count': errors,
                    'total_requests': total,
                    'error_rate': (errors / total) * 100 if total > 0 else 0
                }
            
            conn.close()
            
            # Current session stats
            session_stats = {
                'costs': dict(self.session_costs),
                'requests': dict(self.session_requests)
            }
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'service_breakdown': service_stats,
                'daily_breakdown': daily_stats,
                'error_rates': error_rates,
                'current_session': session_stats,
                'budget_status': {
                    'daily_budget': self.daily_budget,
                    'alert_threshold': self.alert_threshold,
                    'today_cost': await self.get_daily_cost(),
                    'budget_remaining': max(0, self.daily_budget - await self.get_daily_cost())
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating usage analytics: {e}")
            return {}
    
    async def optimize_api_usage(self) -> Dict[str, Any]:
        """Provide API usage optimization recommendations"""
        analytics = await self.get_usage_analytics(30)  # 30-day analysis
        recommendations = []
        
        # Check for high-cost services
        for service, stats in analytics.get('service_breakdown', {}).items():
            avg_cost = stats.get('average_cost', 0)
            if avg_cost > 0.01:  # High average cost per request
                recommendations.append(f"Consider caching for {service} (avg cost: ${avg_cost:.4f}/request)")
        
        # Check error rates
        for service, rates in analytics.get('error_rates', {}).items():
            error_rate = rates.get('error_rate', 0)
            if error_rate > 5:  # More than 5% error rate
                recommendations.append(f"High error rate for {service}: {error_rate:.1f}% - implement better error handling")
        
        # Budget analysis
        budget_status = analytics.get('budget_status', {})
        utilization = (budget_status.get('today_cost', 0) / budget_status.get('daily_budget', 1)) * 100
        
        if utilization > 80:
            recommendations.append("Approaching daily budget limit - consider implementing request throttling")
        
        return {
            'recommendations': recommendations,
            'budget_utilization': f"{utilization:.1f}%",
            'top_cost_services': sorted(
                analytics.get('service_breakdown', {}).items(),
                key=lambda x: x[1].get('total_cost', 0),
                reverse=True
            )[:3]
        }
    
    def get_current_quota_usage(self) -> Dict[str, int]:
        """Get current quota usage for all services"""
        usage = {}
        for service, limiter in self.rate_limiters.items():
            usage[service] = len(limiter.requests)
        return usage

    async def get_cost_dashboard(self) -> Dict[str, Any]:
        """Get real-time cost dashboard data"""
        analytics = await self.get_usage_analytics(1)  # Today's data
        optimization = await self.optimize_api_usage()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'today_summary': {
                'total_cost': await self.get_daily_cost(),
                'budget_remaining': max(0, self.daily_budget - await self.get_daily_cost()),
                'requests_made': sum(stats.get('request_count', 0) for stats in analytics.get('service_breakdown', {}).values()),
                'services_used': len(analytics.get('service_breakdown', {}))
            },
            'rate_limit_status': {
                service: {
                    'requests_used': len(limiter.requests),
                    'limit': limiter.max_requests,
                    'window_seconds': limiter.window_seconds
                } for service, limiter in self.rate_limiters.items()
            },
            'circuit_breaker_status': {
                service: breaker for service, breaker in self.circuit_breakers.items()
            },
            'optimization': optimization
        }

    async def cleanup_old_data(self):
        """Clean up old API usage data to prevent database bloat"""
        try:
            # Use the comprehensive cleanup service if available
            if CLEANUP_AVAILABLE:
                logger.info("Using comprehensive database cleanup service for API costs")
                results = cleanup_service.cleanup_database(self.db_path)

                # Log cleanup results
                for result in results:
                    if result.success:
                        logger.info(
                            f"API cost cleanup: {result.table_name} - "
                            f"{result.records_deleted} records deleted, "
                            f"{result.space_freed_mb:.2f}MB freed"
                        )
                    else:
                        logger.warning(
                            f"API cost cleanup failed for {result.table_name}: "
                            f"{result.error_message}"
                        )
            else:
                # Fallback to basic cleanup if service not available
                logger.info("Using basic cleanup for API costs (cleanup service not available)")
                await self._basic_cost_cleanup()

        except Exception as e:
            logger.error(f"Error in API cost cleanup process: {e}")

    async def _basic_cost_cleanup(self):
        """Basic cleanup fallback for API cost data"""
        try:
            # Keep 90 days of detailed API usage
            usage_cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Clean up old API usage records
            cursor.execute('DELETE FROM api_usage WHERE timestamp < ?', (usage_cutoff,))

            # Keep daily budgets for 1 year
            budget_cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
            cursor.execute('DELETE FROM daily_budgets WHERE date < ?', (budget_cutoff,))

            conn.commit()
            conn.close()

            logger.info("Basic API cost cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error in basic API cost cleanup: {e}")

    async def trigger_manual_cleanup(self) -> Dict[str, Any]:
        """Manually trigger API cost database cleanup and return results"""
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

            logger.info(f"Manual API cost cleanup completed: {cleanup_summary}")
            return cleanup_summary

        except Exception as e:
            logger.error(f"Error in manual API cost cleanup: {e}")
            return {"error": str(e)}

# Global instance
cost_monitor = APICostMonitor()

async def track_api_call(service: str, endpoint: str, tokens: int, **kwargs) -> APIUsageRecord:
    """Convenience function for tracking API calls"""
    return await cost_monitor.record_usage(service, endpoint, tokens, **kwargs)

def check_rate_limit_decorator(service: str):
    """Decorator to check rate limits before API calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            allowed, wait_time = cost_monitor.check_rate_limit(service)
            if not allowed:
                logger.warning(f"⏰ Rate limit reached for {service}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            
            if cost_monitor.check_circuit_breaker(service):
                raise Exception(f"Circuit breaker open for {service}")
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                cost_monitor.record_api_failure(service, str(e))
                raise
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the cost monitor
    import asyncio
    
    async def test_cost_monitor():
        monitor = APICostMonitor()
        
        # Test usage recording
        await monitor.record_usage(
            service="openai",
            endpoint="chat/completions",
            tokens_used=1500,
            model="gpt-4o-mini",
            output_tokens=500,
            request_type="video_analysis"
        )
        
        # Get analytics
        analytics = await monitor.get_usage_analytics()
        print("📊 Usage Analytics:")
        print(json.dumps(analytics, indent=2, default=str))
        
        # Get dashboard
        dashboard = await monitor.get_cost_dashboard()
        print("\n📈 Cost Dashboard:")
        print(json.dumps(dashboard, indent=2, default=str))
    
if __name__ == "__main__":
    asyncio.run(test_cost_monitor())
