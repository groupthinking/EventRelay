#!/usr/bin/env python3
"""
Automated Recovery System for Cursor Connection Issues
Implements comprehensive recovery strategies and escalation procedures.
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
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum

from cursor_monitor import CursorConnectionMonitor
from backup_api_manager import BackupAPIManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/garvey/Desktop/youtube_extension/logs/auto_recovery.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Enumeration of available recovery strategies."""
    RESTART_CURSOR = "restart_cursor"
    SWITCH_BACKUP_API = "switch_backup_api"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTIONS = "reset_connections"
    NETWORK_RESET = "network_reset"
    SYSTEM_RESTART = "system_restart"
    ADMIN_NOTIFICATION = "admin_notification"

@dataclass
class RecoveryAttempt:
    """Represents a recovery attempt."""
    timestamp: str
    strategy: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RecoveryPlan:
    """Represents a recovery plan with prioritized strategies."""
    name: str
    description: str
    strategies: List[RecoveryStrategy]
    max_attempts: int = 3
    timeout_seconds: int = 300
    escalation_triggers: Optional[List[str]] = None

class AutomatedRecoverySystem:
    """Automated recovery system for Cursor connection issues."""

    def __init__(self):
        self.monitor = CursorConnectionMonitor()
        self.backup_manager = BackupAPIManager()
        self.recovery_history: List[RecoveryAttempt] = []
        self.active_incident = None
        self.incident_start_time = None
        self.max_recovery_history = 100

        # Recovery strategies mapping
        self.strategy_handlers: Dict[RecoveryStrategy, Callable] = {
            RecoveryStrategy.RESTART_CURSOR: self._restart_cursor,
            RecoveryStrategy.SWITCH_BACKUP_API: self._switch_backup_api,
            RecoveryStrategy.CLEAR_CACHE: self._clear_cache,
            RecoveryStrategy.RESET_CONNECTIONS: self._reset_connections,
            RecoveryStrategy.NETWORK_RESET: self._network_reset,
            RecoveryStrategy.SYSTEM_RESTART: self._system_restart,
            RecoveryStrategy.ADMIN_NOTIFICATION: self._admin_notification
        }

        # Recovery plans for different scenarios
        self.recovery_plans = self._setup_recovery_plans()

        # Load recovery history
        self._load_recovery_history()

    def _setup_recovery_plans(self) -> Dict[str, RecoveryPlan]:
        """Setup predefined recovery plans."""
        return {
            "connection_timeout": RecoveryPlan(
                name="connection_timeout",
                description="Recovery plan for connection timeout issues",
                strategies=[
                    RecoveryStrategy.RESTART_CURSOR,
                    RecoveryStrategy.SWITCH_BACKUP_API,
                    RecoveryStrategy.CLEAR_CACHE,
                    RecoveryStrategy.ADMIN_NOTIFICATION
                ],
                max_attempts=3,
                timeout_seconds=180
            ),
            "api_failure": RecoveryPlan(
                name="api_failure",
                description="Recovery plan for API endpoint failures",
                strategies=[
                    RecoveryStrategy.SWITCH_BACKUP_API,
                    RecoveryStrategy.RESET_CONNECTIONS,
                    RecoveryStrategy.NETWORK_RESET,
                    RecoveryStrategy.ADMIN_NOTIFICATION
                ],
                max_attempts=2,
                timeout_seconds=120
            ),
            "process_crash": RecoveryPlan(
                name="process_crash",
                description="Recovery plan for Cursor process crashes",
                strategies=[
                    RecoveryStrategy.RESTART_CURSOR,
                    RecoveryStrategy.CLEAR_CACHE,
                    RecoveryStrategy.SYSTEM_RESTART,
                    RecoveryStrategy.ADMIN_NOTIFICATION
                ],
                max_attempts=3,
                timeout_seconds=240
            ),
            "network_issues": RecoveryPlan(
                name="network_issues",
                description="Recovery plan for network connectivity issues",
                strategies=[
                    RecoveryStrategy.NETWORK_RESET,
                    RecoveryStrategy.RESET_CONNECTIONS,
                    RecoveryStrategy.SWITCH_BACKUP_API,
                    RecoveryStrategy.ADMIN_NOTIFICATION
                ],
                max_attempts=2,
                timeout_seconds=150
            )
        }

    def _load_recovery_history(self):
        """Load recovery history from file."""
        history_file = "/Users/garvey/Desktop/youtube_extension/logs/recovery_history.json"

        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                    self.recovery_history = [
                        RecoveryAttempt(**attempt) for attempt in history_data
                    ]
                logger.info(f"Loaded {len(self.recovery_history)} recovery attempts")
            except Exception as e:
                logger.error(f"Failed to load recovery history: {e}")

    def _save_recovery_history(self):
        """Save recovery history to file."""
        try:
            history_file = "/Users/garvey/Desktop/youtube_extension/logs/recovery_history.json"

            # Keep only recent history
            recent_history = self.recovery_history[-self.max_recovery_history:]
            history_data = [asdict(attempt) for attempt in recent_history]

            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recovery history: {e}")

    async def detect_incident(self) -> Optional[str]:
        """Detect if there's an active incident requiring recovery."""
        # Get current status
        status = await self.monitor.check_cursor_status()

        if status.is_connected:
            # Reset incident state if connection is restored
            if self.active_incident:
                logger.info(f"Incident resolved: {self.active_incident}")
                self.active_incident = None
                self.incident_start_time = None
            return None

        # Determine incident type based on error
        incident_type = "unknown"

        if status.last_error:
            error_lower = status.last_error.lower()
            if "timeout" in error_lower or "connection" in error_lower:
                incident_type = "connection_timeout"
            elif "api" in error_lower or "endpoint" in error_lower:
                incident_type = "api_failure"
            elif "process" in error_lower or "crash" in error_lower:
                incident_type = "process_crash"
            elif "network" in error_lower:
                incident_type = "network_issues"

        # Start new incident if none active
        if not self.active_incident:
            self.active_incident = incident_type
            self.incident_start_time = datetime.now()
            logger.warning(f"New incident detected: {incident_type} - {status.last_error}")

        return incident_type

    async def execute_recovery_plan(self, incident_type: str) -> bool:
        """Execute the appropriate recovery plan for the incident type."""
        if incident_type not in self.recovery_plans:
            logger.error(f"No recovery plan found for incident type: {incident_type}")
            return False

        plan = self.recovery_plans[incident_type]
        logger.info(f"Executing recovery plan: {plan.name}")

        # Check if we're within timeout
        if self.incident_start_time:
            elapsed = datetime.now() - self.incident_start_time
            if elapsed.total_seconds() > plan.timeout_seconds:
                logger.error(f"Recovery timeout exceeded for {incident_type}")
                await self._escalate_incident(incident_type)
                return False

        # Execute strategies in order
        for strategy in plan.strategies:
            if not await self._execute_strategy(strategy):
                continue  # Try next strategy

            # Verify recovery success
            await asyncio.sleep(5)  # Wait for changes to take effect
            status = await self.monitor.check_cursor_status()

            if status.is_connected:
                logger.info(f"✅ Recovery successful using {strategy.value}")
                self.active_incident = None
                self.incident_start_time = None
                return True

        logger.error(f"All recovery strategies failed for {incident_type}")
        await self._escalate_incident(incident_type)
        return False

    async def _execute_strategy(self, strategy: RecoveryStrategy) -> bool:
        """Execute a specific recovery strategy."""
        handler = self.strategy_handlers.get(strategy)
        if not handler:
            logger.error(f"No handler found for strategy: {strategy}")
            return False

        start_time = time.time()
        logger.info(f"Executing recovery strategy: {strategy.value}")

        try:
            success = await handler()
            duration = (time.time() - start_time) * 1000

            attempt = RecoveryAttempt(
                timestamp=datetime.now().isoformat(),
                strategy=strategy.value,
                success=success,
                duration_ms=duration
            )

            self.recovery_history.append(attempt)
            self._save_recovery_history()

            if success:
                logger.info(f"Strategy {strategy.value} completed successfully")
            else:
                logger.warning(f"Strategy {strategy.value} failed")

            return success

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Strategy {strategy.value} error: {e}")

            attempt = RecoveryAttempt(
                timestamp=datetime.now().isoformat(),
                strategy=strategy.value,
                success=False,
                duration_ms=duration,
                error_message=str(e)
            )

            self.recovery_history.append(attempt)
            self._save_recovery_history()

            return False

    async def _restart_cursor(self) -> bool:
        """Restart the Cursor application."""
        try:
            logger.info("Restarting Cursor application...")

            # Kill existing processes
            subprocess.run(["pkill", "-f", "Cursor"], check=False)

            # Wait for processes to terminate
            await asyncio.sleep(3)

            # Start Cursor
            result = subprocess.run(
                ["open", "-a", "Cursor"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("Cursor restart command executed successfully")
                return True
            else:
                logger.error(f"Cursor restart failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Cursor restart error: {e}")
            return False

    async def _switch_backup_api(self) -> bool:
        """Switch to backup API configuration."""
        try:
            logger.info("Switching to backup API...")

            # Get current primary API (this would need to be implemented based on your config)
            current_primary = "anthropic"  # Placeholder

            result = await self.backup_manager.initiate_failover(current_primary)

            if result:
                new_provider, config = result
                logger.info(f"Successfully switched to backup API: {new_provider}")
                return True
            else:
                logger.error("No suitable backup API found")
                return False

        except Exception as e:
            logger.error(f"Backup API switch error: {e}")
            return False

    async def _clear_cache(self) -> bool:
        """Clear Cursor cache and temporary files."""
        try:
            logger.info("Clearing Cursor cache...")

            cache_paths = [
                "~/Library/Caches/com.cursor",
                "~/Library/Application Support/Cursor/Cache",
                "~/Library/Application Support/Cursor/Code Cache",
                "~/Library/Application Support/Cursor/GPUCache"
            ]

            cleared_count = 0
            for path in cache_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    import shutil
                    shutil.rmtree(expanded_path)
                    cleared_count += 1
                    logger.info(f"Cleared cache: {expanded_path}")

            logger.info(f"Cache clearing completed - {cleared_count} locations cleared")
            return True

        except Exception as e:
            logger.error(f"Cache clearing error: {e}")
            return False

    async def _reset_connections(self) -> bool:
        """Reset network connections and DNS cache."""
        try:
            logger.info("Resetting network connections...")

            # Reset DNS cache
            subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=False)
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], check=False)

            # Reset network interfaces (be careful with this)
            # subprocess.run(["sudo", "ifconfig", "en0", "down"], check=False)
            # await asyncio.sleep(2)
            # subprocess.run(["sudo", "ifconfig", "en0", "up"], check=False)

            logger.info("Network connections reset")
            return True

        except Exception as e:
            logger.error(f"Network reset error: {e}")
            return False

    async def _network_reset(self) -> bool:
        """Perform a comprehensive network reset."""
        try:
            logger.info("Performing comprehensive network reset...")

            # Renew DHCP lease
            subprocess.run(["sudo", "ipconfig", "set", "en0", "DHCP"], check=False)

            # Reset network settings
            await asyncio.sleep(5)

            # Test connectivity
            result = subprocess.run(
                ["ping", "-c", "3", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("Network connectivity restored")
                return True
            else:
                logger.error("Network connectivity test failed")
                return False

        except Exception as e:
            logger.error(f"Network reset error: {e}")
            return False

    async def _system_restart(self) -> bool:
        """Initiate system restart (use with caution)."""
        try:
            logger.warning("System restart requested - this is a last resort")

            # Only proceed if explicitly configured
            restart_config = "/Users/garvey/Desktop/youtube_extension/config/auto_restart_enabled"

            if os.path.exists(restart_config):
                logger.info("Initiating system restart...")
                subprocess.run(["sudo", "shutdown", "-r", "now"], check=False)
                return True
            else:
                logger.info("System restart not enabled - skipping")
                return False

        except Exception as e:
            logger.error(f"System restart error: {e}")
            return False

    async def _admin_notification(self) -> bool:
        """Send notification to administrator."""
        try:
            logger.info("Sending administrator notification...")

            # This would integrate with your notification system
            # Could be email, Slack, etc.

            notification = {
                "timestamp": datetime.now().isoformat(),
                "incident": self.active_incident,
                "message": "Automated recovery failed - manual intervention required",
                "system_status": await self.monitor.get_status_report()
            }

            # Save notification for later processing
            notification_file = f"/Users/garvey/Desktop/youtube_extension/logs/admin_notification_{int(time.time())}.json"
            with open(notification_file, 'w') as f:
                json.dump(notification, f, indent=2)

            logger.info(f"Administrator notification saved: {notification_file}")
            return True

        except Exception as e:
            logger.error(f"Admin notification error: {e}")
            return False

    async def _escalate_incident(self, incident_type: str):
        """Escalate incident to higher priority handling."""
        logger.critical(f"ESCALATION: Incident {incident_type} requires manual intervention")

        # Create escalation report
        escalation_report = {
            "timestamp": datetime.now().isoformat(),
            "incident_type": incident_type,
            "start_time": self.incident_start_time.isoformat() if self.incident_start_time else None,
            "duration_seconds": (datetime.now() - self.incident_start_time).total_seconds() if self.incident_start_time else 0,
            "recovery_attempts": len([r for r in self.recovery_history if not r.success]),
            "last_error": await self.monitor.check_cursor_status(),
            "system_info": {
                "cursor_version": self.monitor._get_cursor_version(),
                "os_version": "macOS",  # Could be detected
                "network_status": "unknown"  # Could be checked
            }
        }

        # Save escalation report
        escalation_file = f"/Users/garvey/Desktop/youtube_extension/logs/escalation_{int(time.time())}.json"
        with open(escalation_file, 'w') as f:
            json.dump(escalation_report, f, indent=2)

        logger.info(f"Escalation report saved: {escalation_file}")

    async def run_recovery_loop(self):
        """Main recovery monitoring loop."""
        logger.info("Starting automated recovery system...")

        while True:
            try:
                # Check for incidents
                incident = await self.detect_incident()

                if incident:
                    logger.info(f"Active incident detected: {incident}")

                    # Execute recovery plan
                    success = await self.execute_recovery_plan(incident)

                    if success:
                        logger.info("Recovery completed successfully")
                    else:
                        logger.error("Recovery failed - escalation initiated")

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(30)

    def get_recovery_report(self) -> Dict:
        """Generate a comprehensive recovery report."""
        total_attempts = len(self.recovery_history)
        successful_attempts = len([r for r in self.recovery_history if r.success])
        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

        # Group by strategy
        strategy_stats = {}
        for attempt in self.recovery_history:
            strategy = attempt.strategy
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"attempts": 0, "successes": 0, "avg_duration": 0}

            stats = strategy_stats[strategy]
            stats["attempts"] += 1
            if attempt.success:
                stats["successes"] += 1
            stats["avg_duration"] = ((stats["avg_duration"] * (stats["attempts"] - 1)) + attempt.duration_ms) / stats["attempts"]

        return {
            "timestamp": datetime.now().isoformat(),
            "active_incident": self.active_incident,
            "total_recovery_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "success_rate_percentage": success_rate,
            "strategy_statistics": strategy_stats,
            "recent_attempts": [asdict(attempt) for attempt in self.recovery_history[-10:]]
        }

async def main():
    """Main entry point for testing the recovery system."""
    recovery_system = AutomatedRecoverySystem()

    # Print current status
    incident = await recovery_system.detect_incident()
    if incident:
        print(f"Active incident: {incident}")
    else:
        print("No active incidents")

    # Print recovery report
    report = recovery_system.get_recovery_report()
    print("\nRecovery Report:")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
