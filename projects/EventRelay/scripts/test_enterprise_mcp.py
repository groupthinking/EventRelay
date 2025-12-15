#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Enterprise MCP Server
Validates all reliability patterns and enterprise features
"""

import asyncio
import json
import logging
import time
import random
import aiohttp
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from pathlib import Path

# Import enterprise components
from enterprise_mcp_server import (
    EnterpriseMCPServer, CircuitBreaker, RateLimiter, 
    MetricsCollector, HealthChecker, RetryManager,
    CircuitBreakerState, CircuitBreakerOpenException
)
from monitoring_dashboard import MCPMonitoringDashboard, AlertManager
from production_deployment import SecretsManager, ProductionHardening

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows requests"""
        cb = CircuitBreaker("test_cb")
        
        async with cb:
            # Should not raise exception
            pass
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.success_calls == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failure threshold"""
        cb = CircuitBreaker("test_cb")
        cb.config.failure_threshold = 2
        
        # Simulate failures
        for i in range(2):
            try:
                async with cb:
                    raise Exception("Simulated failure")
            except Exception:
                pass
        
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects requests when open"""
        cb = CircuitBreaker("test_cb")
        cb.state = CircuitBreakerState.OPEN
        cb.timeout_start = time.time()
        
        with pytest.raises(CircuitBreakerOpenException):
            async with cb:
                pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout"""
        cb = CircuitBreaker("test_cb")
        cb.state = CircuitBreakerState.OPEN
        cb.timeout_start = time.time() - 61  # Simulate timeout passed
        cb.config.timeout_seconds = 60
        
        # Should transition to half-open and allow request
        async with cb:
            pass
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.success_count >= 1

class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        """Test rate limiter allows requests within limit"""
        rl = RateLimiter(rate=10.0, burst=10, name="test_rl")
        
        # Should allow requests within burst limit
        for i in range(10):
            assert await rl.acquire() == True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_rejects_over_limit(self):
        """Test rate limiter rejects requests over limit"""
        rl = RateLimiter(rate=1.0, burst=2, name="test_rl")
        
        # Use up burst tokens
        assert await rl.acquire() == True
        assert await rl.acquire() == True
        
        # Should reject next request
        assert await rl.acquire() == False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_token_replenishment(self):
        """Test rate limiter replenishes tokens over time"""
        rl = RateLimiter(rate=5.0, burst=1, name="test_rl")  # 5 tokens per second
        
        # Use up token
        assert await rl.acquire() == True
        assert await rl.acquire() == False
        
        # Wait for token replenishment
        await asyncio.sleep(0.3)  # Should get 1.5 tokens
        assert await rl.acquire() == True

class TestMetricsCollector:
    """Test metrics collection"""
    
    def test_metrics_counter(self):
        """Test counter metrics"""
        metrics = MetricsCollector()
        
        metrics.record_counter("test.counter", 5)
        metrics.record_counter("test.counter", 3)
        
        assert metrics.counters["test.counter"] == 8
    
    def test_metrics_gauge(self):
        """Test gauge metrics"""
        metrics = MetricsCollector()
        
        metrics.record_gauge("test.gauge", 10.5)
        metrics.record_gauge("test.gauge", 20.5)
        
        assert metrics.gauges["test.gauge"] == 20.5
    
    def test_metrics_timing(self):
        """Test timing metrics"""
        metrics = MetricsCollector()
        
        metrics.record_timing("test.timing", 1.5)
        
        assert "test.timing.duration" in metrics.metrics
        assert len(metrics.metrics["test.timing.duration"]) == 1
    
    def test_metrics_summary(self):
        """Test metrics summary"""
        metrics = MetricsCollector()
        
        metrics.record_counter("test.requests", 100)
        metrics.record_gauge("test.memory", 75.5)
        
        summary = metrics.get_summary()
        assert summary["counters"]["test.requests"] == 100
        assert summary["gauges"]["test.memory"] == 75.5
        assert "uptime_seconds" in summary

class TestHealthChecker:
    """Test health checking functionality"""
    
    @pytest.mark.asyncio
    async def test_health_checker_registration(self):
        """Test health check registration"""
        hc = HealthChecker()
        
        async def test_check():
            return {"healthy": True, "status": "ok"}
        
        hc.register_check("test_check", test_check, interval=60)
        
        assert "test_check" in hc.checks
        assert hc.checks["test_check"]["interval"] == 60
    
    @pytest.mark.asyncio
    async def test_health_checker_execution(self):
        """Test health check execution"""
        hc = HealthChecker()
        
        async def healthy_check():
            return {"healthy": True}
        
        async def unhealthy_check():
            return {"healthy": False, "error": "test error"}
        
        hc.register_check("healthy", healthy_check, interval=0)
        hc.register_check("unhealthy", unhealthy_check, interval=0)
        
        results = await hc.run_checks()
        
        assert results["overall_status"] == "degraded"  # Mixed results
        assert results["checks"]["healthy"]["status"] == "healthy"
        assert results["checks"]["unhealthy"]["status"] == "unhealthy"

class TestRetryManager:
    """Test retry logic"""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful operation on first attempt"""
        rm = RetryManager(max_attempts=3)
        
        async def successful_operation():
            return "success"
        
        result = await rm.execute_with_retry(successful_operation, "test")
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful operation after initial failures"""
        rm = RetryManager(max_attempts=3, base_delay=0.1)
        attempts = 0
        
        async def eventually_successful():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise Exception(f"Failure {attempts}")
            return "success"
        
        result = await rm.execute_with_retry(eventually_successful, "test")
        assert result == "success"
        assert attempts == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts and raises last exception"""
        rm = RetryManager(max_attempts=2, base_delay=0.1)
        
        async def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            await rm.execute_with_retry(always_fails, "test")

class TestSecretsManager:
    """Test secrets management"""
    
    def test_secrets_encryption_decryption(self):
        """Test encryption and decryption of secrets"""
        sm = SecretsManager(key_file=Path("test_secrets.key"))
        
        # Clean up from previous tests
        if Path("test_secrets.key").exists():
            Path("test_secrets.key").unlink()
        if Path("secrets.encrypted").exists():
            Path("secrets.encrypted").unlink()
        
        original_secret = "very-secret-api-key-12345"
        encrypted = sm.encrypt_secret(original_secret)
        decrypted = sm.decrypt_secret(encrypted)
        
        assert decrypted == original_secret
        assert encrypted != original_secret
        
        # Cleanup
        if Path("test_secrets.key").exists():
            Path("test_secrets.key").unlink()
        if Path("secrets.encrypted").exists():
            Path("secrets.encrypted").unlink()
    
    def test_secrets_storage_loading(self):
        """Test storing and loading encrypted secrets"""
        sm = SecretsManager(key_file=Path("test_secrets.key"))
        
        # Clean up from previous tests
        for file in ["test_secrets.key", "secrets.encrypted"]:
            if Path(file).exists():
                Path(file).unlink()
        
        secrets = {
            "api_key": "secret-api-key",
            "db_password": "super-secret-password",
            "jwt_secret": "jwt-signing-secret"
        }
        
        sm.store_secrets(secrets)
        loaded_secrets = sm.load_secrets()
        
        assert loaded_secrets == secrets
        
        # Cleanup
        for file in ["test_secrets.key", "secrets.encrypted"]:
            if Path(file).exists():
                Path(file).unlink()

class TestAlertManager:
    """Test alert management"""
    
    def test_alert_rule_creation(self):
        """Test alert rule creation and storage"""
        am = AlertManager()
        
        # Should have default rules
        assert len(am.rules) > 0
        assert "high_cpu" in am.rules
        assert "high_memory" in am.rules
    
    def test_alert_evaluation_triggering(self):
        """Test alert evaluation and triggering"""
        am = AlertManager()
        
        # Clear existing rules for clean test
        am.rules.clear()
        am.active_alerts.clear()
        
        from production_deployment import AlertRule
        am.add_rule(AlertRule("test_alert", "test.metric", 50.0, "greater", "warning"))
        
        # Should trigger alert
        metrics = {"test.metric": 75.0}
        new_alerts = am.evaluate_alerts(metrics)
        
        assert len(new_alerts) == 1
        assert new_alerts[0]["rule_name"] == "test_alert"
        assert "test_alert" in am.active_alerts
    
    def test_alert_resolution(self):
        """Test alert resolution when condition clears"""
        am = AlertManager()
        
        # Clear existing rules
        am.rules.clear()
        am.active_alerts.clear()
        
        from production_deployment import AlertRule
        am.add_rule(AlertRule("test_alert", "test.metric", 50.0, "greater", "warning"))
        
        # Trigger alert
        metrics = {"test.metric": 75.0}
        am.evaluate_alerts(metrics)
        assert "test_alert" in am.active_alerts
        
        # Resolve alert
        metrics = {"test.metric": 25.0}
        am.evaluate_alerts(metrics)
        assert "test_alert" not in am.active_alerts

class TestEnterpriseMCPServer:
    """Integration tests for Enterprise MCP Server"""
    
    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        """Test MCP server initializes with all enterprise components"""
        config = {
            "test_mode": True,
            "log_level": "INFO"
        }
        
        server = EnterpriseMCPServer(config)
        
        # Verify enterprise components are initialized
        assert server.metrics is not None
        assert server.health_checker is not None
        assert server.retry_manager is not None
        assert len(server.circuit_breakers) > 0
        assert len(server.rate_limiters) > 0
        
        # Verify circuit breakers
        expected_breakers = ["youtube_api", "ai_processing", "video_analysis"]
        for breaker_name in expected_breakers:
            assert breaker_name in server.circuit_breakers
            assert server.circuit_breakers[breaker_name].state == CircuitBreakerState.CLOSED
        
        # Verify rate limiters
        expected_limiters = ["api_calls", "video_processing", "ai_requests"]
        for limiter_name in expected_limiters:
            assert limiter_name in server.rate_limiters

class LoadTester:
    """Load testing utilities"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def setup(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
    
    async def simulate_load(self, num_requests: int = 100, concurrency: int = 10):
        """Simulate load on the MCP server"""
        
        async def make_request(session, request_id):
            try:
                async with session.get(f"{self.base_url}/api/health") as response:
                    return {
                        "request_id": request_id,
                        "status_code": response.status,
                        "success": response.status == 200,
                        "timestamp": time.time()
                    }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "error": str(e),
                    "success": False,
                    "timestamp": time.time()
                }
        
        # Execute requests with limited concurrency
        semaphore = asyncio.Semaphore(concurrency)
        results = []
        
        async def limited_request(request_id):
            async with semaphore:
                return await make_request(self.session, request_id)
        
        tasks = [limited_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        success_rate = (successful / len(results)) * 100
        
        return {
            "total_requests": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "results": results
        }

async def run_load_test():
    """Run comprehensive load test"""
    logger.info("🚀 Starting Enterprise MCP Server Load Test")
    
    load_tester = LoadTester()
    await load_tester.setup()
    
    try:
        # Test 1: Baseline load
        logger.info("📊 Running baseline load test (100 requests, 10 concurrent)")
        baseline_results = await load_tester.simulate_load(100, 10)
        
        print(f"✅ Baseline Results:")
        print(f"   Success Rate: {baseline_results['success_rate']:.2f}%")
        print(f"   Successful: {baseline_results['successful']}")
        print(f"   Failed: {baseline_results['failed']}")
        
        # Test 2: High concurrency
        logger.info("📊 Running high concurrency test (200 requests, 50 concurrent)")
        high_concurrency_results = await load_tester.simulate_load(200, 50)
        
        print(f"✅ High Concurrency Results:")
        print(f"   Success Rate: {high_concurrency_results['success_rate']:.2f}%")
        print(f"   Successful: {high_concurrency_results['successful']}")
        print(f"   Failed: {high_concurrency_results['failed']}")
        
        # Test 3: Sustained load
        logger.info("📊 Running sustained load test (500 requests, 20 concurrent)")
        sustained_results = await load_tester.simulate_load(500, 20)
        
        print(f"✅ Sustained Load Results:")
        print(f"   Success Rate: {sustained_results['success_rate']:.2f}%")
        print(f"   Successful: {sustained_results['successful']}")
        print(f"   Failed: {sustained_results['failed']}")
        
    finally:
        await load_tester.cleanup()
    
    logger.info("✅ Load testing completed")

def run_unit_tests():
    """Run all unit tests"""
    logger.info("🧪 Running Enterprise MCP Server Unit Tests")
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header"
    ])
    
    if exit_code == 0:
        logger.info("✅ All unit tests passed")
    else:
        logger.error("❌ Some unit tests failed")
    
    return exit_code == 0

async def run_integration_tests():
    """Run integration tests"""
    logger.info("🔗 Running Integration Tests")
    
    try:
        # Test MCP server initialization
        logger.info("Testing MCP server initialization...")
        server = EnterpriseMCPServer({"test_mode": True})
        
        # Test health checks
        logger.info("Testing health checks...")
        health_status = await server.health_checker.run_checks()
        assert health_status["overall_status"] in ["healthy", "degraded"]
        
        # Test metrics collection
        logger.info("Testing metrics collection...")
        server.metrics.record_counter("test.integration", 1)
        server.metrics.record_gauge("test.gauge", 50.0)
        metrics_summary = server.metrics.get_summary()
        assert "test.integration" in metrics_summary["counters"]
        
        # Test circuit breakers
        logger.info("Testing circuit breakers...")
        cb = server.circuit_breakers["youtube_api"]
        metrics = cb.get_metrics()
        assert metrics["state"] == "closed"
        
        # Test rate limiters
        logger.info("Testing rate limiters...")
        rl = server.rate_limiters["api_calls"]
        acquired = await rl.acquire()
        assert acquired == True
        
        logger.info("✅ All integration tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

def main():
    """Main test execution"""
    logger.info("🚀 Enterprise MCP Server Test Suite")
    
    # Run unit tests
    unit_tests_passed = run_unit_tests()
    
    # Run integration tests
    async def run_async_tests():
        integration_passed = await run_integration_tests()
        
        # Run load tests if integration tests pass
        if integration_passed:
            try:
                await run_load_test()
            except Exception as e:
                logger.warning(f"⚠️ Load testing failed (server may not be running): {e}")
        
        return integration_passed
    
    integration_passed = asyncio.run(run_async_tests())
    
    # Summary
    print("\n" + "="*50)
    print("🏆 TEST SUITE SUMMARY")
    print("="*50)
    print(f"Unit Tests: {'✅ PASSED' if unit_tests_passed else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    print(f"Overall Status: {'✅ ALL TESTS PASSED' if unit_tests_passed and integration_passed else '❌ SOME TESTS FAILED'}")
    
    return unit_tests_passed and integration_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)