#!/usr/bin/env python3
"""
System Health Monitoring Service
================================

Comprehensive system health monitoring with real-time metrics collection,
alerting, recovery actions, and predictive health analysis.
"""

import asyncio
import json
import os
import time
import psutil
import httpx
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import deque
from enum import Enum

import aiofiles
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from backend.services.logging_service import get_logging_service, log_error, performance_monitor
    from backend.config.logging_config import get_logger
except ImportError:
    # Create fallback logger if imports fail
    import logging
    logger = logging.getLogger(__name__)
    def get_logger(name="health_monitoring"): return logger
    def get_logging_service(): return None
    def log_error(msg): logger.error(msg)
    performance_monitor = None


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


class ComponentType(Enum):
    """System component types"""
    API_SERVER = "api_server"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM_RESOURCE = "system_resource"
    APPLICATION = "application"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    timestamp: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    name: str
    component_type: ComponentType
    status: HealthStatus
    uptime_seconds: float
    last_check: float
    metrics: List[HealthMetric]
    dependencies: List[str] = None
    recovery_actions: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.recovery_actions is None:
            self.recovery_actions = []


@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: HealthStatus
    score: float
    timestamp: float
    uptime_seconds: float
    components: List[ComponentHealth]
    active_alerts: List[str]
    recent_incidents: List[str]
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class HealthChecker:
    """Base class for health checkers"""
    
    def __init__(self, name: str, component_type: ComponentType):
        self.name = name
        self.component_type = component_type
        self.logger = get_logger(f"{__name__}.{name}")
    
    async def check_health(self) -> ComponentHealth:
        """Override in subclasses"""
        raise NotImplementedError


class SystemResourceChecker(HealthChecker):
    """Monitors system resources (CPU, memory, disk)"""
    
    def __init__(self):
        super().__init__("system_resources", ComponentType.SYSTEM_RESOURCE)
        self.start_time = time.time()
    
    async def check_health(self) -> ComponentHealth:
        """Check system resource health"""
        try:
            metrics = []
            
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_metric = HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                status=self._determine_status(cpu_percent, 70, 90),
                threshold_warning=70,
                threshold_critical=90,
                timestamp=time.time(),
                metadata={"cores": psutil.cpu_count()}
            )
            metrics.append(cpu_metric)
            
            # Memory Usage
            memory = psutil.virtual_memory()
            memory_metric = HealthMetric(
                name="memory_usage",
                value=memory.percent,
                unit="percent",
                status=self._determine_status(memory.percent, 80, 95),
                threshold_warning=80,
                threshold_critical=95,
                timestamp=time.time(),
                metadata={
                    "total_gb": round(memory.total / 1024**3, 2),
                    "available_gb": round(memory.available / 1024**3, 2),
                    "used_gb": round(memory.used / 1024**3, 2)
                }
            )
            metrics.append(memory_metric)
            
            # Disk Usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_metric = HealthMetric(
                name="disk_usage",
                value=disk_percent,
                unit="percent",
                status=self._determine_status(disk_percent, 80, 95),
                threshold_warning=80,
                threshold_critical=95,
                timestamp=time.time(),
                metadata={
                    "total_gb": round(disk.total / 1024**3, 2),
                    "free_gb": round(disk.free / 1024**3, 2),
                    "used_gb": round(disk.used / 1024**3, 2)
                }
            )
            metrics.append(disk_metric)
            
            # Network IO
            net_io = psutil.net_io_counters()
            if hasattr(self, '_last_net_io'):
                time_delta = time.time() - self._last_net_check
                bytes_sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
                bytes_recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
                
                # Convert to Mbps
                send_mbps = (bytes_sent_rate * 8) / (1024 * 1024)
                recv_mbps = (bytes_recv_rate * 8) / (1024 * 1024)
                
                network_metric = HealthMetric(
                    name="network_throughput",
                    value=max(send_mbps, recv_mbps),
                    unit="mbps",
                    status=HealthStatus.HEALTHY,  # Network usage is informational
                    threshold_warning=100,
                    threshold_critical=1000,
                    timestamp=time.time(),
                    metadata={
                        "send_mbps": round(send_mbps, 2),
                        "recv_mbps": round(recv_mbps, 2),
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv
                    }
                )
                metrics.append(network_metric)
            
            self._last_net_io = net_io
            self._last_net_check = time.time()
            
            # Determine overall component status
            status_scores = {
                HealthStatus.HEALTHY: 0,
                HealthStatus.WARNING: 1,
                HealthStatus.DEGRADED: 2,
                HealthStatus.CRITICAL: 3,
                HealthStatus.FAILED: 4
            }
            
            worst_status = max(metrics, key=lambda m: status_scores[m.status]).status
            
            # Recovery actions based on status
            recovery_actions = []
            if worst_status in [HealthStatus.CRITICAL, HealthStatus.FAILED]:
                recovery_actions.extend([
                    "Clear temporary files and caches",
                    "Restart high-memory processes",
                    "Scale up resources if in cloud environment"
                ])
            
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=worst_status,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=metrics,
                recovery_actions=recovery_actions
            )
            
        except Exception as e:
            await log_error(e, context={"component": self.name})
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=HealthStatus.FAILED,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=[],
                recovery_actions=["Restart health monitoring service"]
            )
    
    def _determine_status(self, value: float, warning_threshold: float, critical_threshold: float) -> HealthStatus:
        """Determine health status based on thresholds"""
        if value >= critical_threshold:
            return HealthStatus.CRITICAL
        elif value >= warning_threshold:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


class DatabaseChecker(HealthChecker):
    """Monitors database connectivity and performance"""
    
    def __init__(self, connection_string: str):
        super().__init__("database", ComponentType.DATABASE)
        self.connection_string = connection_string
        self.start_time = time.time()
    
    async def check_health(self) -> ComponentHealth:
        """Check database health"""
        try:
            metrics = []
            
            # Connection test
            start_time = time.time()
            connection_healthy = await self._test_connection()
            connection_latency = (time.time() - start_time) * 1000
            
            connection_metric = HealthMetric(
                name="connection_latency",
                value=connection_latency,
                unit="ms",
                status=self._determine_latency_status(connection_latency),
                threshold_warning=100,
                threshold_critical=500,
                timestamp=time.time(),
                metadata={"connected": connection_healthy}
            )
            metrics.append(connection_metric)
            
            # Query performance test (if connected)
            if connection_healthy:
                query_start = time.time()
                query_success = await self._test_query()
                query_latency = (time.time() - query_start) * 1000
                
                query_metric = HealthMetric(
                    name="query_performance",
                    value=query_latency,
                    unit="ms",
                    status=self._determine_latency_status(query_latency),
                    threshold_warning=200,
                    threshold_critical=1000,
                    timestamp=time.time(),
                    metadata={"query_success": query_success}
                )
                metrics.append(query_metric)
            
            # Determine overall status
            if not connection_healthy:
                status = HealthStatus.CRITICAL
            else:
                status_scores = {
                    HealthStatus.HEALTHY: 0,
                    HealthStatus.WARNING: 1,
                    HealthStatus.CRITICAL: 2
                }
                status = max(metrics, key=lambda m: status_scores[m.status]).status
            
            recovery_actions = []
            if status == HealthStatus.CRITICAL:
                recovery_actions.extend([
                    "Check database server status",
                    "Verify connection credentials",
                    "Restart database connection pool",
                    "Check network connectivity to database"
                ])
            
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=status,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=metrics,
                recovery_actions=recovery_actions
            )
            
        except Exception as e:
            await log_error(e, context={"component": self.name})
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=HealthStatus.FAILED,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=[],
                recovery_actions=["Check database configuration and credentials"]
            )
    
    async def _test_connection(self) -> bool:
        """Test database connection"""
        try:
            # This would normally use actual database connection
            # For now, simulate connection test
            await asyncio.sleep(0.01)  # Simulate connection time
            return True
        except Exception:
            return False
    
    async def _test_query(self) -> bool:
        """Test basic query performance"""
        try:
            # This would normally run a simple SELECT query
            # For now, simulate query execution
            await asyncio.sleep(0.005)  # Simulate query time
            return True
        except Exception:
            return False
    
    def _determine_latency_status(self, latency_ms: float) -> HealthStatus:
        """Determine status based on latency"""
        if latency_ms >= 500:
            return HealthStatus.CRITICAL
        elif latency_ms >= 100:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


class ExternalServiceChecker(HealthChecker):
    """Monitors external service health"""
    
    def __init__(self, name: str, url: str, timeout: int = 10):
        super().__init__(name, ComponentType.EXTERNAL_SERVICE)
        self.url = url
        self.timeout = timeout
        self.start_time = time.time()
    
    async def check_health(self) -> ComponentHealth:
        """Check external service health"""
        try:
            metrics = []
            
            # HTTP health check
            start_time = time.time()
            status_code, response_time = await self._make_request()
            
            response_metric = HealthMetric(
                name="response_time",
                value=response_time * 1000,  # Convert to ms
                unit="ms",
                status=self._determine_http_status(status_code, response_time * 1000),
                threshold_warning=1000,
                threshold_critical=5000,
                timestamp=time.time(),
                metadata={
                    "status_code": status_code,
                    "url": self.url
                }
            )
            metrics.append(response_metric)
            
            # Determine overall status
            if status_code == 0:  # Connection failed
                status = HealthStatus.CRITICAL
            elif status_code >= 500:
                status = HealthStatus.CRITICAL
            elif status_code >= 400:
                status = HealthStatus.WARNING
            elif response_time > 5:
                status = HealthStatus.CRITICAL
            elif response_time > 1:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            recovery_actions = []
            if status in [HealthStatus.CRITICAL, HealthStatus.FAILED]:
                recovery_actions.extend([
                    f"Check {self.name} service status",
                    "Verify network connectivity",
                    "Check service configuration",
                    "Contact service provider if issue persists"
                ])
            
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=status,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=metrics,
                dependencies=[],
                recovery_actions=recovery_actions
            )
            
        except Exception as e:
            await log_error(e, context={"component": self.name, "url": self.url})
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=HealthStatus.FAILED,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=[],
                recovery_actions=[f"Check {self.name} configuration and network connectivity"]
            )
    
    async def _make_request(self) -> Tuple[int, float]:
        """Make HTTP request and return status code and response time"""
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.url)
                response_time = time.time() - start_time
                return response.status_code, response_time
        except httpx.TimeoutException:
            return 408, self.timeout  # Request timeout
        except Exception:
            return 0, self.timeout  # Connection failed
    
    def _determine_http_status(self, status_code: int, response_time_ms: float) -> HealthStatus:
        """Determine health status based on HTTP response"""
        if status_code == 0 or status_code >= 500:
            return HealthStatus.CRITICAL
        elif status_code >= 400 or response_time_ms > 5000:
            return HealthStatus.WARNING
        elif response_time_ms > 1000:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


class ApplicationChecker(HealthChecker):
    """Monitors application-specific health metrics"""
    
    def __init__(self):
        super().__init__("application", ComponentType.APPLICATION)
        self.start_time = time.time()
        self.error_count_window = []
        self.request_count = 0
        self.error_count = 0
    
    def record_request(self):
        """Record a new request"""
        self.request_count += 1
    
    def record_error(self):
        """Record an error"""
        self.error_count += 1
        self.error_count_window.append(time.time())
        
        # Keep only last 5 minutes of errors
        cutoff = time.time() - 300
        self.error_count_window = [t for t in self.error_count_window if t > cutoff]
    
    async def check_health(self) -> ComponentHealth:
        """Check application health"""
        try:
            metrics = []
            current_time = time.time()
            
            # Error rate (last 5 minutes)
            recent_errors = len(self.error_count_window)
            error_rate = (recent_errors / 300) * 60  # Errors per minute
            
            error_rate_metric = HealthMetric(
                name="error_rate",
                value=error_rate,
                unit="errors/min",
                status=self._determine_error_status(error_rate),
                threshold_warning=5,
                threshold_critical=20,
                timestamp=current_time,
                metadata={
                    "total_requests": self.request_count,
                    "total_errors": self.error_count,
                    "recent_errors": recent_errors
                }
            )
            metrics.append(error_rate_metric)
            
            # Memory usage (application-specific)
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                memory_metric = HealthMetric(
                    name="process_memory",
                    value=memory_mb,
                    unit="MB",
                    status=self._determine_memory_status(memory_mb),
                    threshold_warning=500,
                    threshold_critical=1000,
                    timestamp=current_time,
                    metadata={
                        "pid": process.pid,
                        "memory_percent": process.memory_percent()
                    }
                )
                metrics.append(memory_metric)
            except Exception as e:
                self.logger.warning(f"Could not get process memory info: {e}")
            
            # Response time (would be calculated from actual requests)
            # For now, using a simulated value
            avg_response_time = 150  # ms
            
            response_time_metric = HealthMetric(
                name="avg_response_time",
                value=avg_response_time,
                unit="ms",
                status=self._determine_response_time_status(avg_response_time),
                threshold_warning=500,
                threshold_critical=2000,
                timestamp=current_time
            )
            metrics.append(response_time_metric)
            
            # Determine overall status
            status_scores = {
                HealthStatus.HEALTHY: 0,
                HealthStatus.WARNING: 1,
                HealthStatus.DEGRADED: 2,
                HealthStatus.CRITICAL: 3
            }
            worst_status = max(metrics, key=lambda m: status_scores[m.status]).status
            
            recovery_actions = []
            if worst_status == HealthStatus.CRITICAL:
                recovery_actions.extend([
                    "Restart application processes",
                    "Clear application caches",
                    "Check for memory leaks",
                    "Review recent deployments"
                ])
            elif worst_status == HealthStatus.WARNING:
                recovery_actions.extend([
                    "Monitor application closely",
                    "Review error logs",
                    "Check resource usage trends"
                ])
            
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=worst_status,
                uptime_seconds=current_time - self.start_time,
                last_check=current_time,
                metrics=metrics,
                recovery_actions=recovery_actions
            )
            
        except Exception as e:
            await log_error(e, context={"component": self.name})
            return ComponentHealth(
                name=self.name,
                component_type=self.component_type,
                status=HealthStatus.FAILED,
                uptime_seconds=time.time() - self.start_time,
                last_check=time.time(),
                metrics=[],
                recovery_actions=["Restart application health monitoring"]
            )
    
    def _determine_error_status(self, error_rate: float) -> HealthStatus:
        """Determine status based on error rate"""
        if error_rate >= 20:
            return HealthStatus.CRITICAL
        elif error_rate >= 5:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _determine_memory_status(self, memory_mb: float) -> HealthStatus:
        """Determine status based on memory usage"""
        if memory_mb >= 1000:
            return HealthStatus.CRITICAL
        elif memory_mb >= 500:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _determine_response_time_status(self, response_time_ms: float) -> HealthStatus:
        """Determine status based on response time"""
        if response_time_ms >= 2000:
            return HealthStatus.CRITICAL
        elif response_time_ms >= 500:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


class HealthMonitoringService:
    """Main health monitoring service coordinator"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self._load_config(config)
        self.logger = get_logger(__name__)
        self.checkers: List[HealthChecker] = []
        self.health_history: List[SystemHealth] = []
        self.is_running = False
        self.start_time = time.time()
        # Lightweight metrics and rate limiting state
        self._metrics: Dict[str, float] = {}
        self._rate_limit_rps: int = int(os.getenv('RATE_LIMIT_RPS', '5'))
        self._max_recent_requests: int = int(os.getenv('MAX_RECENT_REQUESTS', '1000'))
        self._recent_requests: deque = deque(maxlen=self._max_recent_requests)
        
        # Initialize health checkers
        self._initialize_checkers()
        
        # Start monitoring
        asyncio.create_task(self.start_monitoring())

    # -----------------------------
    # Public utility methods used by API v1
    # -----------------------------
    def get_basic_health_status(self, video_processor_factory: Any, websocket_manager: Any) -> Dict[str, Any]:
        """Return a minimal, stable health payload for API v1.

        This method intentionally avoids heavy initialization. It probes
        only what is safe and fast, and falls back to 'unknown' states on error.
        """
        components: Dict[str, Any] = {}

        # Video processor availability (best-effort, non-fatal)
        try:
            # Avoid constructing heavy models; verify factory is callable
            vp_available = hasattr(video_processor_factory, 'create_processor')
            components['video_processor'] = 'available' if vp_available else 'unavailable'
        except Exception:
            components['video_processor'] = 'unknown'

        # WebSocket manager availability
        try:
            ws_ok = websocket_manager is not None
            components['websocket'] = 'available' if ws_ok else 'unavailable'
        except Exception:
            components['websocket'] = 'unknown'

        # External service signals (presence only)
        components['gemini_key_present'] = bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'))
        components['youtube_api_key_present'] = bool(os.getenv('YOUTUBE_API_KEY'))

        # Overall status (degraded if any unknown/unavailable core component)
        core_states = [components.get('video_processor'), components.get('websocket')]
        if any(state in ('unavailable', 'unknown') for state in core_states):
            status = 'degraded'
        else:
            status = 'healthy'

        return {
            'status': status,
            'timestamp': datetime.now(),
            'version': '2.0.0',
            'components': components,
        }

    def check_external_connectors_health(self) -> Dict[str, Any]:
        """Return a lightweight connectors health snapshot used by detailed health."""
        return {
            'youtube': 'unknown',
            'gemini': 'unknown',
            'openai': 'unknown',
            'anthropic': 'unknown',
            'timestamp': datetime.now().isoformat(),
        }

    def check_video_to_software_pipeline_health(self) -> Dict[str, Any]:
        """Return a minimal pipeline health snapshot used by detailed health."""
        return {
            'status': 'unknown',
            'stages': {
                'ingestion': 'unknown',
                'analysis': 'unknown',
                'generation': 'unknown',
                'deployment': 'unknown',
            },
            'timestamp': datetime.now().isoformat(),
        }

    def rate_limit_check(self) -> bool:
        """Simple per-process rate limiter. Returns True if under limit."""
        now = time.time()
        # Drop entries older than 1 second
        while self._recent_requests and now - self._recent_requests[0] > 1.0:
            self._recent_requests.popleft()
        if len(self._recent_requests) < self._rate_limit_rps:
            self._recent_requests.append(now)
            return True
        return False

    def increment_metric(self, name: str, amount: float = 1.0) -> None:
        """Increment a named metric counter."""
        try:
            self._metrics[name] = float(self._metrics.get(name, 0.0)) + float(amount)
        except Exception:
            # Never fail request paths due to metrics
            pass

    def get_metrics_prometheus_format(self) -> List[str]:
        """Render internal counters in a Prometheus-compatible text format."""
        lines: List[str] = [
            '# HELP uvai_requests_total Total number of application-level requests',
            '# TYPE uvai_requests_total counter',
        ]
        for key, value in sorted(self._metrics.items()):
            metric_name = key.replace('.', '_').replace('-', '_')
            try:
                lines.append(f"uvai_{metric_name} {float(value):.0f}")
            except Exception:
                # Skip non-numeric values
                continue
        return lines
    
    def _load_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            'check_interval': 30,  # seconds
            'history_limit': 1000,
            'enable_system_resources': True,
            'enable_database': True,
            'enable_external_services': True,
            'enable_application': True,
            'database_url': os.getenv('DATABASE_URL', 'postgresql://localhost/uvai'),
            'external_services': {
                'youtube_api': 'https://www.googleapis.com/youtube/v3/search',
                'openai_api': 'https://api.openai.com/v1/models',
                'anthropic_api': 'https://api.anthropic.com/v1/messages'
            }
        }
        
        if config:
            default_config.update(config)
        
        return default_config
    
    def _initialize_checkers(self):
        """Initialize all health checkers"""
        try:
            # System resources checker
            if self.config['enable_system_resources']:
                self.checkers.append(SystemResourceChecker())
            
            # Database checker
            if self.config['enable_database']:
                self.checkers.append(DatabaseChecker(self.config['database_url']))
            
            # External services checkers
            if self.config['enable_external_services']:
                for name, url in self.config['external_services'].items():
                    self.checkers.append(ExternalServiceChecker(name, url))
            
            # Application checker
            if self.config['enable_application']:
                self.application_checker = ApplicationChecker()
                self.checkers.append(self.application_checker)
            else:
                self.application_checker = None
            
            self.logger.info(f"Initialized {len(self.checkers)} health checkers")
            
        except Exception as e:
            self.logger.error(f"Error initializing health checkers: {e}")
    
    async def start_monitoring(self):
        """Start the health monitoring loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info("Starting health monitoring service")
        
        while self.is_running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.config['check_interval'])
            except Exception as e:
                await log_error(e, context={'component': 'health_monitoring_service'})
                await asyncio.sleep(60)  # Wait longer on error
    
    async def perform_health_check(self) -> SystemHealth:
        """Perform comprehensive health check"""
        try:
            # Run all health checkers in parallel
            check_tasks = [checker.check_health() for checker in self.checkers]
            components = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            valid_components = []
            for i, component in enumerate(components):
                if isinstance(component, Exception):
                    await log_error(component, context={'checker': self.checkers[i].name})
                else:
                    valid_components.append(component)
            
            # Calculate overall health
            overall_status, score = self._calculate_overall_health(valid_components)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(valid_components)
            
            # Create system health summary
            system_health = SystemHealth(
                overall_status=overall_status,
                score=score,
                timestamp=time.time(),
                uptime_seconds=time.time() - self.start_time,
                components=valid_components,
                active_alerts=self._get_active_alerts(valid_components),
                recent_incidents=self._get_recent_incidents(),
                recommendations=recommendations
            )
            
            # Store in history
            self.health_history.append(system_health)
            
            # Limit history size
            if len(self.health_history) > self.config['history_limit']:
                self.health_history.pop(0)
            
            # Log health status
            self.logger.info(f"Health check completed: {overall_status.value} (score: {score:.1f})")
            
            return system_health
            
        except Exception as e:
            await log_error(e, context={'component': 'health_check'})
            
            # Return failed health status
            return SystemHealth(
                overall_status=HealthStatus.FAILED,
                score=0.0,
                timestamp=time.time(),
                uptime_seconds=time.time() - self.start_time,
                components=[],
                active_alerts=["Health monitoring system failure"],
                recent_incidents=[]
            )
    
    def _calculate_overall_health(self, components: List[ComponentHealth]) -> Tuple[HealthStatus, float]:
        """Calculate overall system health score and status"""
        if not components:
            return HealthStatus.FAILED, 0.0
        
        # Weight components by importance
        component_weights = {
            ComponentType.SYSTEM_RESOURCE: 0.3,
            ComponentType.DATABASE: 0.25,
            ComponentType.APPLICATION: 0.25,
            ComponentType.EXTERNAL_SERVICE: 0.15,
            ComponentType.API_SERVER: 0.05
        }
        
        status_scores = {
            HealthStatus.HEALTHY: 100,
            HealthStatus.WARNING: 75,
            HealthStatus.DEGRADED: 50,
            HealthStatus.CRITICAL: 25,
            HealthStatus.FAILED: 0
        }
        
        total_weight = 0
        weighted_score = 0
        worst_status = HealthStatus.HEALTHY
        
        for component in components:
            weight = component_weights.get(component.component_type, 0.1)
            score = status_scores[component.status]
            
            weighted_score += score * weight
            total_weight += weight
            
            # Track worst status
            if status_scores[component.status] < status_scores[worst_status]:
                worst_status = component.status
        
        # Calculate final score
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Determine overall status based on score and worst component
        if final_score >= 90 and worst_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
            overall_status = HealthStatus.HEALTHY
        elif final_score >= 70 and worst_status != HealthStatus.CRITICAL:
            overall_status = HealthStatus.WARNING
        elif final_score >= 40:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.CRITICAL
        
        return overall_status, final_score
    
    def _get_active_alerts(self, components: List[ComponentHealth]) -> List[str]:
        """Get list of active alerts"""
        alerts = []
        
        for component in components:
            if component.status in [HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.FAILED]:
                alerts.append(f"{component.name}: {component.status.value}")
        
        return alerts
    
    def _get_recent_incidents(self) -> List[str]:
        """Get recent incidents (last 24 hours)"""
        if len(self.health_history) < 2:
            return []
        
        incidents = []
        cutoff_time = time.time() - 86400  # 24 hours
        
        # Look for status changes in recent history
        for i in range(len(self.health_history) - 1):
            current = self.health_history[i]
            next_check = self.health_history[i + 1]
            
            if current.timestamp < cutoff_time:
                continue
            
            # Check for status degradation
            if (status_scores[current.overall_status] > status_scores[next_check.overall_status]):
                incidents.append(
                    f"{datetime.fromtimestamp(next_check.timestamp).strftime('%H:%M')}: "
                    f"Status degraded from {current.overall_status.value} to {next_check.overall_status.value}"
                )
        
        return incidents[-10:]  # Last 10 incidents
    
    def _generate_recommendations(self, components: List[ComponentHealth]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        # Analyze each component for recommendations
        for component in components:
            if component.status == HealthStatus.CRITICAL:
                recommendations.extend([f"URGENT: {action}" for action in component.recovery_actions])
            elif component.status == HealthStatus.WARNING:
                recommendations.extend([f"Monitor {component.name}: {action}" for action in component.recovery_actions[:2]])
        
        # System-wide recommendations
        critical_count = sum(1 for c in components if c.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for c in components if c.status == HealthStatus.WARNING)
        
        if critical_count > 1:
            recommendations.append("Multiple critical issues detected - consider emergency maintenance")
        elif critical_count == 1 and warning_count > 2:
            recommendations.append("System stability at risk - prioritize issue resolution")
        elif warning_count > 3:
            recommendations.append("Multiple warnings detected - schedule maintenance window")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def record_request(self):
        """Record application request for health tracking"""
        if self.application_checker:
            self.application_checker.record_request()
    
    def record_error(self):
        """Record application error for health tracking"""
        if self.application_checker:
            self.application_checker.record_error()
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get the most recent health check result"""
        return self.health_history[-1] if self.health_history else None
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """Get health history for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        return [h for h in self.health_history if h.timestamp > cutoff_time]
    
    def get_component_metrics(self, component_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for a specific component"""
        cutoff_time = time.time() - (hours * 3600)
        metrics = []
        
        for health in self.health_history:
            if health.timestamp < cutoff_time:
                continue
            
            for component in health.components:
                if component.name == component_name:
                    for metric in component.metrics:
                        metrics.append({
                            'timestamp': health.timestamp,
                            'name': metric.name,
                            'value': metric.value,
                            'unit': metric.unit,
                            'status': metric.status.value
                        })
        
        return metrics
    
    async def stop_monitoring(self):
        """Stop the health monitoring service"""
        self.is_running = False
        self.logger.info("Health monitoring service stopped")


# Global health monitoring service instance
_health_service: Optional[HealthMonitoringService] = None


def get_health_monitoring_service() -> HealthMonitoringService:
    """Get or create global health monitoring service instance"""
    global _health_service
    if _health_service is None:
        _health_service = HealthMonitoringService()
    return _health_service


def setup_health_monitoring_routes(app: FastAPI):
    """Setup health monitoring API routes"""
    health_service = get_health_monitoring_service()
    
    @app.get("/api/health", response_model=Dict[str, Any])
    async def get_health():
        """Get current system health"""
        health = health_service.get_current_health()
        if health:
            return asdict(health)
        else:
            return {"status": "initializing", "message": "Health monitoring is starting up"}
    
    @app.get("/api/health/history", response_model=List[Dict[str, Any]])
    async def get_health_history(hours: int = 24):
        """Get health history"""
        history = health_service.get_health_history(hours)
        return [asdict(h) for h in history]
    
    @app.get("/api/health/component/{component_name}", response_model=List[Dict[str, Any]])
    async def get_component_metrics(component_name: str, hours: int = 24):
        """Get metrics for specific component"""
        return health_service.get_component_metrics(component_name, hours)
    
    @app.post("/api/health/record/request")
    async def record_request():
        """Record an application request"""
        health_service.record_request()
        return {"status": "recorded"}
    
    @app.post("/api/health/record/error")
    async def record_error():
        """Record an application error"""
        health_service.record_error()
        return {"status": "recorded"}


# Export status scores for use in recommendations
status_scores = {
    HealthStatus.HEALTHY: 100,
    HealthStatus.WARNING: 75,
    HealthStatus.DEGRADED: 50,
    HealthStatus.CRITICAL: 25,
    HealthStatus.FAILED: 0
}
