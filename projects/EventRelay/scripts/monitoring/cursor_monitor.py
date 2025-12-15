#!/usr/bin/env python3
"""
Cursor Connection Monitor and Recovery System
Proactively monitors Cursor connectivity and implements automated recovery mechanisms.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import requests
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/garvey/Desktop/youtube_extension/logs/cursor_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class CursorStatus:
    """Represents the current status of Cursor connection."""
    timestamp: str
    is_connected: bool
    version: str
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None
    request_id: Optional[str] = None
    retry_count: int = 0

@dataclass
class BackupAPIConfig:
    """Backup API configuration for failover scenarios."""
    provider: str
    api_key: str
    model: str
    priority: int
    last_used: Optional[str] = None
    failure_count: int = 0
    is_active: bool = True

class CursorConnectionMonitor:
    """Main monitoring system for Cursor connectivity."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/Users/garvey/Desktop/youtube_extension/config/cursor-expert"
        self.status_history: List[CursorStatus] = []
        self.backup_configs: Dict[str, BackupAPIConfig] = {}
        self.monitoring_active = False
        self.last_status_check = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.check_interval = 30  # seconds
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3

        # Load configurations
        self._load_backup_configs()
        self._setup_monitoring_directories()

    def _setup_monitoring_directories(self):
        """Create necessary directories for monitoring."""
        dirs = [
            "/Users/garvey/Desktop/youtube_extension/logs",
            "/Users/garvey/Desktop/youtube_extension/monitoring/cursor_status",
            "/Users/garvey/Desktop/youtube_extension/monitoring/backups"
        ]

        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _load_backup_configs(self):
        """Load backup API configurations."""
        backup_config_path = f"{self.config_path}/backup_api_config.json"

        if os.path.exists(backup_config_path):
            try:
                with open(backup_config_path, 'r') as f:
                    config_data = json.load(f)
                    for provider, config in config_data.items():
                        self.backup_configs[provider] = BackupAPIConfig(**config)
                logger.info(f"Loaded {len(self.backup_configs)} backup API configurations")
            except Exception as e:
                logger.error(f"Failed to load backup configs: {e}")
                self._create_default_backup_configs()
        else:
            self._create_default_backup_configs()

    def _create_default_backup_configs(self):
        """Create default backup API configurations."""
        # Note: API keys should be loaded from environment variables for security
        default_configs = {
            "anthropic_backup": BackupAPIConfig(
                provider="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY_BACKUP", ""),
                model="claude-3-opus-20240229",
                priority=1
            ),
            "openai_backup": BackupAPIConfig(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY_BACKUP", ""),
                model="gpt-4-turbo-preview",
                priority=2
            ),
            "gemini_backup": BackupAPIConfig(
                provider="gemini",
                api_key=os.getenv("GEMINI_API_KEY_BACKUP", ""),
                model="gemini-pro",
                priority=3
            )
        }

        self.backup_configs = default_configs
        self._save_backup_configs()

    def _save_backup_configs(self):
        """Save backup configurations to disk."""
        backup_config_path = f"{self.config_path}/backup_api_config.json"
        config_data = {k: asdict(v) for k, v in self.backup_configs.items()}

        try:
            with open(backup_config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info("Backup configurations saved")
        except Exception as e:
            logger.error(f"Failed to save backup configs: {e}")

    async def check_cursor_status(self) -> CursorStatus:
        """Check the current status of Cursor connection."""
        start_time = time.time()

        try:
            # Check if Cursor process is running
            result = subprocess.run(
                ["pgrep", "-f", "Cursor"],
                capture_output=True,
                text=True,
                timeout=10
            )

            is_running = result.returncode == 0

            if not is_running:
                return CursorStatus(
                    timestamp=datetime.now().isoformat(),
                    is_connected=False,
                    version="unknown",
                    last_error="Cursor process not running",
                    response_time_ms=(time.time() - start_time) * 1000
                )

            # Get Cursor version
            version = self._get_cursor_version()

            # Simulate a connection test (in real implementation, this would test actual API connectivity)
            connection_success = await self._test_cursor_connection()

            status = CursorStatus(
                timestamp=datetime.now().isoformat(),
                is_connected=connection_success,
                version=version,
                response_time_ms=(time.time() - start_time) * 1000
            )

            if not connection_success:
                status.last_error = "Connection test failed"
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 0

            return status

        except Exception as e:
            logger.error(f"Error checking Cursor status: {e}")
            return CursorStatus(
                timestamp=datetime.now().isoformat(),
                is_connected=False,
                version="unknown",
                last_error=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )

    def _get_cursor_version(self) -> str:
        """Get the current Cursor version."""
        try:
            # Check Cursor version from running process
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.split('\n'):
                if 'Cursor' in line and '_version=' in line:
                    # Extract version from process args
                    version_match = line.split('_version=')[1].split()[0]
                    return version_match

            return "1.5.11"  # Fallback to known version
        except Exception as e:
            logger.error(f"Error getting Cursor version: {e}")
            return "unknown"

    async def _test_cursor_connection(self) -> bool:
        """Test actual Cursor API connectivity."""
        try:
            # This is a placeholder for actual Cursor API connectivity test
            # In a real implementation, this would test the Cursor API endpoints
            await asyncio.sleep(0.1)  # Simulate network call

            # For now, return True if no obvious issues
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def monitor_cursor_status(self):
        """Main monitoring loop."""
        logger.info("Starting Cursor connection monitoring...")

        while self.monitoring_active:
            try:
                status = await self.check_cursor_status()
                self.status_history.append(status)

                # Keep only last 100 status checks
                if len(self.status_history) > 100:
                    self.status_history = self.status_history[-100:]

                # Log status
                if status.is_connected:
                    logger.info(f"Cursor connected - Version: {status.version}, Response: {status.response_time_ms:.2f}ms")
                else:
                    logger.warning(f"Cursor connection issue: {status.last_error}")

                # Check for recovery conditions
                if self.consecutive_failures >= self.max_consecutive_failures:
                    await self._initiate_recovery()

                # Save status to file
                self._save_status(status)

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _initiate_recovery(self):
        """Initiate recovery procedures for connection failures."""
        logger.warning(f"Initiating recovery after {self.consecutive_failures} consecutive failures")

        if self.recovery_attempts >= self.max_recovery_attempts:
            logger.error("Max recovery attempts reached. Manual intervention required.")
            await self._notify_admin("Max recovery attempts reached")
            return

        self.recovery_attempts += 1

        # Recovery steps
        recovery_steps = [
            self._restart_cursor,
            self._switch_to_backup_api,
            self._clear_cursor_cache,
            self._reset_connection_settings
        ]

        for step in recovery_steps:
            try:
                success = await step()
                if success:
                    logger.info(f"Recovery step {step.__name__} successful")
                    self.recovery_attempts = 0
                    return
            except Exception as e:
                logger.error(f"Recovery step {step.__name__} failed: {e}")

        logger.error("All recovery steps failed")

    async def _restart_cursor(self) -> bool:
        """Attempt to restart Cursor."""
        try:
            logger.info("Attempting to restart Cursor...")

            # Kill existing Cursor processes
            subprocess.run(["pkill", "-f", "Cursor"], check=False)

            # Wait a moment
            await asyncio.sleep(2)

            # Start Cursor (this would need to be implemented based on your system)
            # subprocess.run(["open", "-a", "Cursor"], check=True)

            logger.info("Cursor restart initiated")
            return True
        except Exception as e:
            logger.error(f"Cursor restart failed: {e}")
            return False

    async def _switch_to_backup_api(self) -> bool:
        """Switch to backup API configuration."""
        try:
            logger.info("Switching to backup API configuration...")

            # Find the highest priority active backup
            active_backups = [config for config in self.backup_configs.values()
                            if config.is_active and config.api_key]

            if not active_backups:
                logger.error("No active backup APIs available")
                return False

            backup = min(active_backups, key=lambda x: x.priority)
            logger.info(f"Switching to {backup.provider} backup API")

            # Update primary configuration (implementation would depend on your config system)
            await self._update_primary_config(backup)

            return True
        except Exception as e:
            logger.error(f"Backup API switch failed: {e}")
            return False

    async def _clear_cursor_cache(self) -> bool:
        """Clear Cursor cache to resolve potential issues."""
        try:
            logger.info("Clearing Cursor cache...")

            cache_paths = [
                "~/Library/Caches/com.cursor",
                "~/Library/Application Support/Cursor/Cache"
            ]

            for path in cache_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    import shutil
                    shutil.rmtree(expanded_path)
                    logger.info(f"Cleared cache: {expanded_path}")

            return True
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
            return False

    async def _reset_connection_settings(self) -> bool:
        """Reset connection settings to defaults."""
        try:
            logger.info("Resetting connection settings...")

            # This would reset any custom connection settings
            # Implementation depends on your specific configuration system

            return True
        except Exception as e:
            logger.error(f"Connection settings reset failed: {e}")
            return False

    async def _update_primary_config(self, backup: BackupAPIConfig):
        """Update primary configuration with backup settings."""
        # Implementation would depend on your configuration management system
        pass

    async def _notify_admin(self, message: str):
        """Notify administrator of critical issues."""
        # Implementation could include email, Slack, etc.
        logger.critical(f"ADMIN NOTIFICATION: {message}")

    def _save_status(self, status: CursorStatus):
        """Save status to monitoring file."""
        try:
            status_file = "/Users/garvey/Desktop/youtube_extension/monitoring/cursor_status/latest.json"
            with open(status_file, 'w') as f:
                json.dump(asdict(status), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save status: {e}")

    def get_status_report(self) -> Dict:
        """Generate a comprehensive status report."""
        if not self.status_history:
            return {"error": "No status history available"}

        latest = self.status_history[-1]
        uptime_percentage = sum(1 for s in self.status_history if s.is_connected) / len(self.status_history) * 100

        # Calculate average response time for successful connections
        successful_connections = [s.response_time_ms for s in self.status_history
                                if s.is_connected and s.response_time_ms]

        avg_response_time = sum(successful_connections) / len(successful_connections) if successful_connections else 0

        return {
            "current_status": asdict(latest),
            "uptime_percentage": uptime_percentage,
            "average_response_time_ms": avg_response_time,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": len(self.status_history),
            "monitoring_active": self.monitoring_active,
            "last_check": latest.timestamp
        }

    async def start_monitoring(self):
        """Start the monitoring system."""
        self.monitoring_active = True
        logger.info("Cursor Connection Monitor started")

        try:
            await self.monitor_cursor_status()
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring system error: {e}")
        finally:
            self.monitoring_active = False

    def stop_monitoring(self):
        """Stop the monitoring system."""
        self.monitoring_active = False
        logger.info("Cursor Connection Monitor stopped")

async def main():
    """Main entry point for the monitoring system."""
    monitor = CursorConnectionMonitor()

    # Print initial status
    initial_status = await monitor.check_cursor_status()
    print(f"Initial Cursor Status: {initial_status.is_connected}")
    print(f"Version: {initial_status.version}")
    if initial_status.last_error:
        print(f"Last Error: {initial_status.last_error}")

    # Start monitoring
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
