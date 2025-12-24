#!/usr/bin/env python3
"""
Load Balancer and Horizontal Scaling Preparation
===============================================

Phase 3 Performance Optimization: Load balancing and horizontal scaling
preparation for handling increased load and ensuring 99.9%+ uptime with
automatic failover capabilities.

Key Features:
- Intelligent load balancing with multiple algorithms
- Health checking and automatic failover
- Service discovery and registration
- Auto-scaling based on metrics
- Circuit breaker pattern for resilience
- Request routing and rate limiting
- Performance monitoring and analytics
"""

import asyncio
import json
import logging
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable
import aiohttp
import hashlib

# Import performance monitoring
try:
    from .performance_monitor import performance_monitor
    from .memory_manager import memory_manager
except ImportError:
    performance_monitor = None
    memory_manager = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    HEALTH_AWARE = "health_aware"

class ServiceStatus(Enum):
    """Service status states"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceInstance:
    """Service instance information"""
    id: str
    host: str
    port: int
    weight: int = 1
    status: ServiceStatus = ServiceStatus.HEALTHY
    current_connections: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0
    last_health_check: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_health_check is None:
            self.last_health_check = datetime.now(timezone.utc)
    
    @property
    def url(self) -> str:
        """Get service URL"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        total = self.total_requests + self.total_failures
        return (self.total_failures / total) * 100 if total > 0 else 0.0
    
    @property
    def load_score(self) -> float:
        """Calculate load score for load balancing"""
        # Combine connections, response time, and failure rate
        connection_score = self.current_connections * 10
        response_time_score = self.avg_response_time / 100
        failure_score = self.failure_rate * 2
        
        return connection_score + response_time_score + failure_score

@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    interval: int = 30  # seconds
    timeout: int = 5    # seconds
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    endpoint: str = "/health"
    expected_status: int = 200

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

class CircuitBreaker:
    """Circuit breaker for service resilience"""
    
    def __init__(self, service_id: str, config: CircuitBreakerConfig):
        self.service_id = service_id
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
        
    def can_execute(self) -> bool:
        """Check if request can be executed"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if we should move to half-open
            if (time.time() - self.last_failure_time) > self.config.recovery_timeout:
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logger.info(f"🔄 Circuit breaker HALF_OPEN for {self.service_id}")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful execution"""
        if self.state == "HALF_OPEN":
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info(f"✅ Circuit breaker CLOSED for {self.service_id}")
        elif self.state == "CLOSED":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"🚫 Circuit breaker OPEN for {self.service_id}")
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning(f"🚫 Circuit breaker OPEN (from half-open) for {self.service_id}")

class LoadBalancer:
    """
    Intelligent load balancer with multiple algorithms and health checking
    
    Features:
    - Multiple load balancing algorithms
    - Health checking and automatic failover
    - Circuit breaker pattern
    - Request routing and metrics collection
    - Auto-scaling integration
    """
    
    def __init__(self, 
                 service_name: str,
                 algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.HEALTH_AWARE,
                 health_check_config: HealthCheckConfig = None):
        
        self.service_name = service_name
        self.algorithm = algorithm
        self.health_check_config = health_check_config or HealthCheckConfig()
        
        # Service registry
        self.services: Dict[str, ServiceInstance] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Load balancing state
        self.round_robin_index = 0
        self.request_history = deque(maxlen=10000)
        
        # Health checking
        self.health_check_task = None
        self.health_check_enabled = True
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'requests_per_minute': deque(maxlen=60)
        }
        
        logger.info(f"⚖️ Load balancer initialized for '{service_name}' with {algorithm.value}")
    
    async def start(self):
        """Start load balancer services"""
        if self.health_check_enabled:
            self.health_check_task = asyncio.create_task(self._health_check_worker())
        
        logger.info(f"✅ Load balancer started for {self.service_name}")
    
    async def stop(self):
        """Stop load balancer services"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"⏹️ Load balancer stopped for {self.service_name}")
    
    def register_service(self, instance: ServiceInstance):
        """Register a service instance"""
        self.services[instance.id] = instance
        
        # Create circuit breaker
        circuit_config = CircuitBreakerConfig()
        self.circuit_breakers[instance.id] = CircuitBreaker(instance.id, circuit_config)
        
        logger.info(f"📝 Registered service instance: {instance.id} at {instance.url}")
    
    def unregister_service(self, instance_id: str):
        """Unregister a service instance"""
        if instance_id in self.services:
            instance = self.services[instance_id]
            del self.services[instance_id]
            
            if instance_id in self.circuit_breakers:
                del self.circuit_breakers[instance_id]
            
            logger.info(f"🗑️ Unregistered service instance: {instance_id}")
    
    def get_healthy_services(self) -> List[ServiceInstance]:
        """Get list of healthy service instances"""
        healthy_services = []
        
        for instance in self.services.values():
            # Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(instance.id)
            if circuit_breaker and not circuit_breaker.can_execute():
                continue
            
            # Check health status
            if instance.status == ServiceStatus.HEALTHY:
                healthy_services.append(instance)
        
        return healthy_services
    
    async def route_request(self, request_data: Dict[str, Any] = None) -> Optional[ServiceInstance]:
        """Route request to appropriate service instance"""
        healthy_services = self.get_healthy_services()
        
        if not healthy_services:
            logger.error(f"❌ No healthy services available for {self.service_name}")
            return None
        
        # Select service based on algorithm
        selected_service = self._select_service(healthy_services, request_data)
        
        if selected_service:
            # Update connection count
            selected_service.current_connections += 1
            
            # Record request
            self.metrics['total_requests'] += 1
            self.request_history.append({
                'timestamp': time.time(),
                'service_id': selected_service.id,
                'request_data': request_data
            })
            
            logger.debug(f"🎯 Routed request to {selected_service.id}")
        
        return selected_service
    
    def _select_service(self, services: List[ServiceInstance], request_data: Dict[str, Any]) -> ServiceInstance:
        """Select service instance based on load balancing algorithm"""
        if not services:
            return None
        
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            selected = services[self.round_robin_index % len(services)]
            self.round_robin_index += 1
            return selected
        
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            # Create weighted list
            weighted_services = []
            for service in services:
                weighted_services.extend([service] * service.weight)
            
            if weighted_services:
                selected = weighted_services[self.round_robin_index % len(weighted_services)]
                self.round_robin_index += 1
                return selected
        
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return min(services, key=lambda s: s.current_connections)
        
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            return min(services, key=lambda s: s.avg_response_time)
        
        elif self.algorithm == LoadBalancingAlgorithm.IP_HASH:
            if request_data and 'client_ip' in request_data:
                hash_value = int(hashlib.md5(request_data['client_ip'].encode()).hexdigest(), 16)
                return services[hash_value % len(services)]
            else:
                return random.choice(services)
        
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return random.choice(services)
        
        elif self.algorithm == LoadBalancingAlgorithm.HEALTH_AWARE:
            # Combine multiple factors for intelligent selection
            return min(services, key=lambda s: s.load_score)
        
        # Default to round robin
        return services[0]
    
    async def record_response(self, service_id: str, response_time: float, success: bool):
        """Record response from service instance"""
        if service_id not in self.services:
            return
        
        instance = self.services[service_id]
        circuit_breaker = self.circuit_breakers.get(service_id)
        
        # Update connection count
        instance.current_connections = max(0, instance.current_connections - 1)
        
        # Update response time (exponential moving average)
        alpha = 0.1
        if instance.avg_response_time == 0:
            instance.avg_response_time = response_time
        else:
            instance.avg_response_time = (alpha * response_time + 
                                        (1 - alpha) * instance.avg_response_time)
        
        # Update request/failure counts
        if success:
            instance.total_requests += 1
            self.metrics['successful_requests'] += 1
            
            if circuit_breaker:
                circuit_breaker.record_success()
        else:
            instance.total_failures += 1
            self.metrics['failed_requests'] += 1
            
            if circuit_breaker:
                circuit_breaker.record_failure()
        
        # Update global metrics
        self._update_global_metrics(response_time)
        
        # Record performance metrics
        if performance_monitor:
            await performance_monitor.record_metric(
                f"load_balancer_{self.service_name}",
                "response_time",
                response_time,
                "ms"
            )
    
    def _update_global_metrics(self, response_time: float):
        """Update global load balancer metrics"""
        # Update average response time
        total_requests = self.metrics['successful_requests'] + self.metrics['failed_requests']
        if total_requests > 0:
            current_avg = self.metrics['avg_response_time']
            self.metrics['avg_response_time'] = ((current_avg * (total_requests - 1) + response_time) / 
                                               total_requests)
        
        # Update requests per minute
        current_minute = int(time.time() / 60)
        
        # Initialize requests per minute tracking
        if not hasattr(self, '_last_minute'):
            self._last_minute = current_minute
            self._current_minute_requests = 0
        
        if current_minute == self._last_minute:
            self._current_minute_requests += 1
        else:
            # New minute - record previous and reset
            self.metrics['requests_per_minute'].append(self._current_minute_requests)
            self._last_minute = current_minute
            self._current_minute_requests = 1
    
    async def _health_check_worker(self):
        """Background worker for health checking"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check worker: {e}")
                await asyncio.sleep(self.health_check_config.interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all service instances"""
        tasks = []
        
        for instance in self.services.values():
            task = asyncio.create_task(self._check_instance_health(instance))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_instance_health(self, instance: ServiceInstance):
        """Check health of a single service instance"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                health_url = f"{instance.url}{self.health_check_config.endpoint}"
                
                async with session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=self.health_check_config.timeout)
                ) as response:
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == self.health_check_config.expected_status:
                        # Health check passed
                        if instance.status != ServiceStatus.HEALTHY:
                            instance.status = ServiceStatus.HEALTHY
                            logger.info(f"✅ Service {instance.id} is now healthy")
                        
                        # Update response time
                        instance.avg_response_time = (instance.avg_response_time + response_time) / 2
                        
                    else:
                        logger.warning(f"⚠️ Health check failed for {instance.id}: HTTP {response.status}")
                        await self._handle_health_check_failure(instance)
        
        except Exception as e:
            logger.warning(f"⚠️ Health check failed for {instance.id}: {e}")
            await self._handle_health_check_failure(instance)
        
        finally:
            instance.last_health_check = datetime.now(timezone.utc)
    
    async def _handle_health_check_failure(self, instance: ServiceInstance):
        """Handle health check failure"""
        # Mark as unhealthy if not already
        if instance.status == ServiceStatus.HEALTHY:
            instance.status = ServiceStatus.UNHEALTHY
            logger.warning(f"❌ Service {instance.id} marked as unhealthy")
        
        # Update circuit breaker
        circuit_breaker = self.circuit_breakers.get(instance.id)
        if circuit_breaker:
            circuit_breaker.record_failure()
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""
        healthy_count = len(self.get_healthy_services())
        total_count = len(self.services)
        
        # Calculate requests per minute
        rpm = 0
        if self.metrics['requests_per_minute']:
            rpm = sum(list(self.metrics['requests_per_minute'])[-5:]) / 5  # Average of last 5 minutes
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service_name': self.service_name,
            'algorithm': self.algorithm.value,
            'service_instances': {
                'total': total_count,
                'healthy': healthy_count,
                'unhealthy': total_count - healthy_count,
                'availability_percent': (healthy_count / total_count * 100) if total_count > 0 else 0
            },
            'request_metrics': {
                'total_requests': self.metrics['total_requests'],
                'successful_requests': self.metrics['successful_requests'],
                'failed_requests': self.metrics['failed_requests'],
                'success_rate_percent': ((self.metrics['successful_requests'] / 
                                        max(1, self.metrics['total_requests'])) * 100),
                'avg_response_time_ms': self.metrics['avg_response_time'],
                'requests_per_minute': rpm
            },
            'instances': [
                {
                    'id': instance.id,
                    'url': instance.url,
                    'status': instance.status.value,
                    'current_connections': instance.current_connections,
                    'total_requests': instance.total_requests,
                    'total_failures': instance.total_failures,
                    'failure_rate_percent': instance.failure_rate,
                    'avg_response_time_ms': instance.avg_response_time,
                    'load_score': instance.load_score,
                    'last_health_check': instance.last_health_check.isoformat(),
                    'circuit_breaker_state': self.circuit_breakers[instance.id].state if instance.id in self.circuit_breakers else 'N/A'
                }
                for instance in self.services.values()
            ]
        }
    
    def should_scale_up(self) -> bool:
        """Determine if service should scale up"""
        # Check if all instances are under high load
        healthy_services = self.get_healthy_services()
        
        if not healthy_services:
            return True  # No healthy services available
        
        high_load_count = 0
        for instance in healthy_services:
            # High load conditions:
            # - Many connections
            # - Slow response time
            # - High CPU usage (if available in metadata)
            if (instance.current_connections > 10 or 
                instance.avg_response_time > 1000 or  # > 1 second
                instance.metadata.get('cpu_percent', 0) > 80):
                high_load_count += 1
        
        # Scale up if more than 70% of instances are under high load
        scale_up_threshold = len(healthy_services) * 0.7
        return high_load_count >= scale_up_threshold
    
    def should_scale_down(self) -> bool:
        """Determine if service should scale down"""
        healthy_services = self.get_healthy_services()
        
        if len(healthy_services) <= 1:
            return False  # Keep at least one instance
        
        low_load_count = 0
        for instance in healthy_services:
            # Low load conditions:
            # - Few connections
            # - Fast response time
            # - Low CPU usage
            if (instance.current_connections < 2 and 
                instance.avg_response_time < 100 and  # < 100ms
                instance.metadata.get('cpu_percent', 100) < 20):
                low_load_count += 1
        
        # Scale down if more than 80% of instances are under low load
        scale_down_threshold = len(healthy_services) * 0.8
        return low_load_count >= scale_down_threshold

class ServiceDiscovery:
    """Service discovery and registration system"""
    
    def __init__(self):
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.auto_scaling_enabled = True
        self.scaling_cooldown = 300  # 5 minutes
        self.last_scaling_action = {}
        
        logger.info("🔍 Service Discovery initialized")
    
    def register_load_balancer(self, service_name: str, load_balancer: LoadBalancer):
        """Register a load balancer for a service"""
        self.load_balancers[service_name] = load_balancer
        logger.info(f"📋 Registered load balancer for {service_name}")
    
    async def auto_scale_services(self):
        """Perform auto-scaling based on load metrics"""
        if not self.auto_scaling_enabled:
            return
        
        current_time = time.time()
        
        for service_name, lb in self.load_balancers.items():
            # Check cooldown period
            last_action = self.last_scaling_action.get(service_name, 0)
            if current_time - last_action < self.scaling_cooldown:
                continue
            
            # Check if scaling is needed
            if lb.should_scale_up():
                await self._scale_up_service(service_name, lb)
                self.last_scaling_action[service_name] = current_time
                
            elif lb.should_scale_down():
                await self._scale_down_service(service_name, lb)
                self.last_scaling_action[service_name] = current_time
    
    async def _scale_up_service(self, service_name: str, lb: LoadBalancer):
        """Scale up a service (add instance)"""
        logger.info(f"📈 Scaling UP {service_name}")
        
        # In a real implementation, this would:
        # 1. Start new container/VM instance
        # 2. Wait for it to be ready
        # 3. Register it with the load balancer
        
        # For demo purposes, we'll simulate adding an instance
        instance_count = len(lb.services) + 1
        new_instance = ServiceInstance(
            id=f"{service_name}-instance-{instance_count}",
            host="127.0.0.1",
            port=8000 + instance_count,
            weight=1
        )
        
        lb.register_service(new_instance)
        
        # Record scaling action
        if performance_monitor:
            await performance_monitor.record_metric(
                f"autoscaling_{service_name}",
                "scale_up_action",
                1,
                "count"
            )
    
    async def _scale_down_service(self, service_name: str, lb: LoadBalancer):
        """Scale down a service (remove instance)"""
        healthy_services = lb.get_healthy_services()
        
        if len(healthy_services) <= 1:
            return  # Don't scale below minimum
        
        # Find instance with least load
        least_loaded = min(healthy_services, key=lambda s: s.load_score)
        
        # Mark for draining
        least_loaded.status = ServiceStatus.DRAINING
        
        logger.info(f"📉 Scaling DOWN {service_name} - draining {least_loaded.id}")
        
        # In a real implementation, you would:
        # 1. Stop routing new requests to this instance
        # 2. Wait for existing requests to complete
        # 3. Shut down the instance
        # 4. Remove from load balancer
        
        # For demo purposes, we'll remove it after a short delay
        asyncio.create_task(self._remove_instance_after_drain(lb, least_loaded.id))
        
        # Record scaling action
        if performance_monitor:
            await performance_monitor.record_metric(
                f"autoscaling_{service_name}",
                "scale_down_action",
                1,
                "count"
            )
    
    async def _remove_instance_after_drain(self, lb: LoadBalancer, instance_id: str):
        """Remove instance after draining period"""
        await asyncio.sleep(30)  # Wait 30 seconds for draining
        lb.unregister_service(instance_id)
        logger.info(f"🗑️ Removed drained instance {instance_id}")
    
    def get_service_discovery_stats(self) -> Dict[str, Any]:
        """Get service discovery statistics"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'registered_services': list(self.load_balancers.keys()),
            'auto_scaling_enabled': self.auto_scaling_enabled,
            'scaling_cooldown_seconds': self.scaling_cooldown,
            'load_balancers': {
                name: lb.get_load_balancer_stats()
                for name, lb in self.load_balancers.items()
            }
        }

# Global service discovery instance
service_discovery = ServiceDiscovery()

# Convenience functions
def create_load_balancer(service_name: str, 
                        algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.HEALTH_AWARE) -> LoadBalancer:
    """Create and register a load balancer"""
    lb = LoadBalancer(service_name, algorithm)
    service_discovery.register_load_balancer(service_name, lb)
    return lb

async def start_auto_scaling():
    """Start auto-scaling worker"""
    while True:
        try:
            await service_discovery.auto_scale_services()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in auto-scaling: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    async def test_load_balancer():
        # Create load balancer
        lb = create_load_balancer("video_processor", LoadBalancingAlgorithm.HEALTH_AWARE)
        
        # Register service instances
        instances = [
            ServiceInstance("instance-1", "127.0.0.1", 8001),
            ServiceInstance("instance-2", "127.0.0.1", 8002),
            ServiceInstance("instance-3", "127.0.0.1", 8003)
        ]
        
        for instance in instances:
            lb.register_service(instance)
        
        # Start load balancer
        await lb.start()
        
        try:
            # Simulate requests
            for i in range(10):
                service = await lb.route_request({"request_id": i})
                if service:
                    print(f"Request {i} routed to {service.id}")
                    # Simulate response
                    await lb.record_response(service.id, random.uniform(50, 200), True)
                
                await asyncio.sleep(0.1)
            
            # Get stats
            stats = lb.get_load_balancer_stats()
            print(f"Load balancer stats: {json.dumps(stats, indent=2, default=str)}")
            
        finally:
            await lb.stop()
    
    asyncio.run(test_load_balancer())