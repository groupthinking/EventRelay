#!/usr/bin/env python3
"""
Backup API Manager for Cursor Connection Failover
Manages backup API keys and handles automatic failover scenarios.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """Represents an API endpoint configuration."""
    name: str
    url: str
    headers: Dict[str, str]
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.5

@dataclass
class APIHealthCheck:
    """Represents the health status of an API endpoint."""
    endpoint: str
    timestamp: str
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    consecutive_failures: int = 0

class BackupAPIManager:
    """Manages backup API configurations and failover logic."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/Users/garvey/Desktop/youtube_extension/config/cursor-expert"
        self.backup_config_file = f"{self.config_path}/backup_api_config.json"
        self.health_check_file = f"{self.config_path}/api_health_status.json"
        self.api_endpoints = self._setup_api_endpoints()
        self.health_history: Dict[str, List[APIHealthCheck]] = {}
        self.max_health_history = 50
        self.health_check_interval = 300  # 5 minutes
        self.failover_threshold = 3  # consecutive failures before failover
        self.recovery_threshold = 2  # consecutive successes for recovery

        # Load existing data
        self._load_health_history()

    def _setup_api_endpoints(self) -> Dict[str, APIEndpoint]:
        """Setup API endpoints for different providers."""
        return {
            "anthropic": APIEndpoint(
                name="anthropic",
                url="https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                timeout=30
            ),
            "openai": APIEndpoint(
                name="openai",
                url="https://api.openai.com/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                timeout=30
            ),
            "gemini": APIEndpoint(
                name="gemini",
                url="https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        }

    def _load_health_history(self):
        """Load existing health history from file."""
        if os.path.exists(self.health_check_file):
            try:
                with open(self.health_check_file, 'r') as f:
                    data = json.load(f)
                    for endpoint, history in data.items():
                        self.health_history[endpoint] = [
                            APIHealthCheck(**check) for check in history
                        ]
                logger.info("Loaded health history for API endpoints")
            except Exception as e:
                logger.error(f"Failed to load health history: {e}")

    def _save_health_history(self):
        """Save health history to file."""
        try:
            data = {}
            for endpoint, history in self.health_history.items():
                data[endpoint] = [asdict(check) for check in history[-self.max_health_history:]]

            with open(self.health_check_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health history: {e}")

    async def test_api_endpoint(self, provider: str, api_key: str) -> APIHealthCheck:
        """Test an API endpoint's connectivity and responsiveness."""
        start_time = time.time()
        endpoint = self.api_endpoints.get(provider)

        if not endpoint:
            return APIHealthCheck(
                endpoint=provider,
                timestamp=datetime.now().isoformat(),
                is_healthy=False,
                response_time_ms=0,
                error_message="Unknown provider"
            )

        try:
            # Prepare test request based on provider
            test_payload = self._prepare_test_payload(provider)
            headers = endpoint.headers.copy()
            headers["Authorization"] = f"Bearer {api_key}"

            # Special handling for different providers
            if provider == "gemini":
                headers["x-goog-api-key"] = api_key
                del headers["Authorization"]

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=endpoint.timeout)) as session:
                async with session.post(endpoint.url, json=test_payload, headers=headers) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return APIHealthCheck(
                            endpoint=provider,
                            timestamp=datetime.now().isoformat(),
                            is_healthy=True,
                            response_time_ms=response_time
                        )
                    else:
                        error_text = await response.text()
                        return APIHealthCheck(
                            endpoint=provider,
                            timestamp=datetime.now().isoformat(),
                            is_healthy=False,
                            response_time_ms=response_time,
                            error_message=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return APIHealthCheck(
                endpoint=provider,
                timestamp=datetime.now().isoformat(),
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )

    def _prepare_test_payload(self, provider: str) -> Dict:
        """Prepare test payload for different API providers."""
        if provider == "anthropic":
            return {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Say 'test'"}]
            }
        elif provider == "openai":
            return {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 10
            }
        elif provider == "gemini":
            return {
                "contents": [{
                    "parts": [{"text": "Say 'test'"}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 10
                }
            }
        else:
            return {}

    async def perform_health_checks(self):
        """Perform health checks on all configured API endpoints."""
        logger.info("Starting API health checks...")

        if not os.path.exists(self.backup_config_file):
            logger.error("Backup config file not found")
            return

        try:
            with open(self.backup_config_file, 'r') as f:
                configs = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup configs: {e}")
            return

        for provider, config in configs.items():
            if not config.get("is_active", True) or not config.get("api_key"):
                continue

            health_check = await self.test_api_endpoint(provider, config["api_key"])

            # Update health history
            if provider not in self.health_history:
                self.health_history[provider] = []

            self.health_history[provider].append(health_check)

            # Keep only recent history
            if len(self.health_history[provider]) > self.max_health_history:
                self.health_history[provider] = self.health_history[provider][-self.max_health_history:]

            # Update consecutive failures
            recent_checks = self.health_history[provider][-self.failover_threshold:]
            consecutive_failures = sum(1 for check in recent_checks if not check.is_healthy)
            health_check.consecutive_failures = consecutive_failures

            # Log results
            if health_check.is_healthy:
                logger.info(f"✅ {provider} healthy - {health_check.response_time_ms:.2f}ms")
            else:
                logger.warning(f"❌ {provider} unhealthy - {health_check.error_message}")

            # Update config with health status
            configs[provider]["last_health_check"] = health_check.timestamp
            configs[provider]["is_healthy"] = health_check.is_healthy
            configs[provider]["consecutive_failures"] = consecutive_failures

        # Save updated configs
        try:
            with open(self.backup_config_file, 'w') as f:
                json.dump(configs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save updated configs: {e}")

        # Save health history
        self._save_health_history()

    def get_failover_candidates(self) -> List[Tuple[str, Dict]]:
        """Get list of healthy API endpoints ordered by priority for failover."""
        if not os.path.exists(self.backup_config_file):
            return []

        try:
            with open(self.backup_config_file, 'r') as f:
                configs = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configs for failover: {e}")
            return []

        candidates = []
        for provider, config in configs.items():
            if (config.get("is_active", True) and
                config.get("is_healthy", False) and
                config.get("api_key") and
                config.get("consecutive_failures", 0) < self.failover_threshold):
                candidates.append((provider, config))

        # Sort by priority (lower number = higher priority)
        candidates.sort(key=lambda x: x[1].get("priority", 999))

        return candidates

    async def initiate_failover(self, from_provider: str) -> Optional[Tuple[str, Dict]]:
        """Initiate failover to the next available healthy API."""
        logger.info(f"Initiating failover from {from_provider}")

        candidates = self.get_failover_candidates()

        # Find candidates excluding the current provider
        available_candidates = [(p, c) for p, c in candidates if p != from_provider]

        if not available_candidates:
            logger.error("No healthy backup APIs available for failover")
            return None

        # Select the highest priority candidate
        selected_provider, selected_config = available_candidates[0]

        logger.info(f"Failover initiated: {from_provider} → {selected_provider}")

        # Update usage tracking
        selected_config["last_used"] = datetime.now().isoformat()
        selected_config["failover_count"] = selected_config.get("failover_count", 0) + 1

        # Save updated config
        try:
            with open(self.backup_config_file, 'r') as f:
                all_configs = json.load(f)

            all_configs[selected_provider] = selected_config

            with open(self.backup_config_file, 'w') as f:
                json.dump(all_configs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update failover config: {e}")

        return selected_provider, selected_config

    def get_health_report(self) -> Dict:
        """Generate a comprehensive health report for all APIs."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "details": {}
        }

        for provider, history in self.health_history.items():
            if not history:
                continue

            latest = history[-1]
            recent_checks = history[-10:]  # Last 10 checks

            healthy_checks = sum(1 for check in recent_checks if check.is_healthy)
            uptime_percentage = (healthy_checks / len(recent_checks)) * 100 if recent_checks else 0

            avg_response_time = sum(check.response_time_ms for check in recent_checks if check.is_healthy) / healthy_checks if healthy_checks > 0 else 0

            report["summary"][provider] = {
                "is_healthy": latest.is_healthy,
                "uptime_percentage": uptime_percentage,
                "average_response_time_ms": avg_response_time,
                "consecutive_failures": latest.consecutive_failures,
                "last_check": latest.timestamp
            }

            report["details"][provider] = [asdict(check) for check in recent_checks]

        return report

    async def monitor_api_health(self):
        """Continuous monitoring of API health."""
        logger.info("Starting API health monitoring...")

        while True:
            try:
                await self.perform_health_checks()

                # Check for degraded services and log warnings
                for provider, history in self.health_history.items():
                    if not history:
                        continue

                    latest = history[-1]
                    if latest.consecutive_failures >= self.failover_threshold:
                        logger.warning(f"🚨 {provider} has {latest.consecutive_failures} consecutive failures")

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.health_check_interval)

async def main():
    """Main entry point for testing the backup API manager."""
    manager = BackupAPIManager()

    # Perform initial health checks
    await manager.perform_health_checks()

    # Print health report
    report = manager.get_health_report()
    print(json.dumps(report, indent=2))

    # Test failover candidates
    candidates = manager.get_failover_candidates()
    print(f"\nFailover candidates: {len(candidates)}")
    for provider, config in candidates:
        print(f"  - {provider} (priority: {config.get('priority', 'N/A')})")

if __name__ == "__main__":
    asyncio.run(main())
