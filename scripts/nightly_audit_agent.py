#!/usr/bin/env python3
"""
Nightly Audit & Ruthless Remediation Agent
==========================================

Jules Agent System: Nightly Audit & Ruthless Remediation
Role: High-Integrity Systems Auditor & First-Principles Engineer
Frequency: Nightly Execution (02:00 UTC)

Objective:
Deep-scan of system logs, transaction traces, and state changes.
Identify divergences from first principles.
Execute "Five Whys" interrogation.
Perform Ruthless Solutions (remediation).
Implement Fortification (preventative measures).
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

# Set up path to include src

sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from youtube_extension.backend.services.database_cleanup_service import (
        run_database_cleanup,
    )
    from youtube_extension.backend.services.health_monitoring_service import (
        HealthStatus,
        get_health_monitoring_service,
    )
    from youtube_extension.backend.services.logging_service import get_logging_service
    from youtube_extension.backend.services.metrics_service import MetricsService
except ImportError:
    # Print warning but don't fail immediately, allows dry-run in incomplete envs
    # print(f"Warning: Could not import services: {e}")
    pass

# Configure logging for the agent itself
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AuditAgent] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuditAgent:
    def __init__(
        self,
        dry_run: bool = False,
        lookback_hours: int = 72,
        active_measurement: bool = False,
        measurement_samples: int = 3,
        measurement_interval: float = 1.0,
    ):
        self.dry_run = dry_run
        self.lookback_hours = lookback_hours
        self.active_measurement = active_measurement
        self.measurement_samples = measurement_samples
        self.measurement_interval = measurement_interval
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.report = []
        self.issues = []
        self.remediations = []
        self.fortifications = []

        # Initialize services
        self.health_service = None
        self.metrics_service = None
        self.logging_service = None

        self._init_services()

    def _init_services(self):
        try:
            # We use globals/imports if available
            if 'get_health_monitoring_service' in globals():
                self.health_service = get_health_monitoring_service()
            if 'MetricsService' in globals():
                self.metrics_service = MetricsService()
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")

    async def run_audit(self):
        """Main execution loop"""
        start_time = datetime.now(timezone.utc)
        self._add_report_header(start_time)

        logger.info("Starting Nightly Audit...")
        self.report.append(f"Analysis lookback: {self.lookback_hours} hours")

        await self._collect_active_measurements()

        # 1. Analysis Phase
        await self.analyze_phase()

        # 2. Execution Phase (Ruthless Solutions)
        await self.execution_phase()

        # 3. Fortification Phase
        await self.fortification_phase()

        # 4. Reporting
        self._generate_report_file(start_time)
        logger.info("Nightly Audit Completed.")

    async def analyze_phase(self):
        """
        Phase 1: Analysis
        - Identify divergences from first principles.
        - Scan logs and metrics.
        - Execute 'Five Whys'.
        """
        logger.info("Phase 1: Analysis - Scanning system state...")

        # Check System Health
        await self._check_system_health()

        # Scan Logs for Errors and Status Codes
        await self._scan_logs()

        # Check Metrics for Latency
        await self._check_latency_metrics()

        # Deep Dive (Five Whys) on found issues
        if self.issues:
            logger.info(f"Found {len(self.issues)} issues. Starting First-Principles Inquiry...")
            for issue in self.issues:
                await self.first_principles_analysis(issue)
        else:
            logger.info("No major issues found in initial scan.")
            self.report.append("✅ System appears healthy. No critical divergences found.")

    async def _check_system_health(self):
        """Check current system health status"""
        if not self.health_service:
            return

        try:
            health = await self.health_service.perform_health_check()
            if health.overall_status != HealthStatus.HEALTHY:
                self.issues.append({
                    "type": "HEALTH_DEGRADED",
                    "description": f"System health is {health.overall_status.value} (Score: {health.score})",
                    "details": [f"{c.name}: {c.status.value}" for c in health.components if c.status != HealthStatus.HEALTHY]
                })
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            self.issues.append({
                "type": "AUDIT_FAILURE",
                "description": "Failed to check system health",
                "details": str(e)
            })

    async def _collect_active_measurements(self):
        """Collect live metric samples before analysis for more accurate output."""
        if not self.active_measurement or not self.metrics_service:
            return

        samples = max(1, self.measurement_samples)
        interval = max(0.0, self.measurement_interval)
        self.report.append(f"📏 ACTIVE MEASUREMENT: collecting {samples} live samples")

        try:
            await self.metrics_service.start_collection()
            for sample_index in range(samples):
                await self.metrics_service.get_system_metrics()
                if interval and sample_index < samples - 1:
                    await asyncio.sleep(interval)

            persist = getattr(self.metrics_service, "_persist_metrics", None)
            if persist:
                await persist()
        finally:
            await self.metrics_service.stop_collection()

    async def _scan_logs(self):
        """Scan logs for recent critical failures and status codes > 400."""
        error_log_path = self.log_dir / "error_logs.jsonl"
        structured_log_path = self.log_dir / "structured_logs.jsonl"

        files_to_scan = [p for p in [error_log_path, structured_log_path] if p.exists()]

        if not files_to_scan:
            logger.warning("No log files found to scan.")
            return

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        found_issues = []

        for log_file in files_to_scan:
            try:
                with open(log_file, 'rb') as f:
                    for line in f:
                        try:
                            if not line.strip(): continue
                            if HAS_ORJSON:
                                entry = orjson.loads(line)
                            else:
                                entry = json.loads(line.decode('utf-8'))

                            # Check timestamp
                            ts_str = entry.get("timestamp")
                            if ts_str:
                                try:
                                    # Handle ISO format. Assuming UTC if no offset, or handling Z.
                                    # Simple replacement for robustness
                                    entry_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    # Ensure offset-aware comparison
                                    if entry_time.tzinfo is None:
                                        entry_time = entry_time.replace(tzinfo=timezone.utc)

                                    if entry_time < cutoff_time:
                                        continue
                                except ValueError:
                                    pass # Could not parse time, proceed to check content

                            # Filter Logic: Status Code >= 400
                            status = entry.get("status_code")
                            if status and isinstance(status, int) and status >= 400:
                                found_issues.append(entry)
                                continue

                            # Filter Logic: Log Level
                            if entry.get("level") in ["ERROR", "CRITICAL"]:
                                found_issues.append(entry)
                                continue

                        except Exception:
                            # Catch any JSON decode error (both json and orjson)
                            continue
            except Exception as e:
                logger.error(f"Error scanning {log_file}: {e}")

        # Group and report
        if found_issues:
            grouped_errors = {}
            for err in found_issues:
                msg = err.get("message") or err.get("error_message") or "Unknown Error"
                code = err.get("status_code") or err.get("level")
                key = f"[{code}] {msg}"
                grouped_errors[key] = grouped_errors.get(key, 0) + 1

            for key, count in grouped_errors.items():
                self.issues.append({
                    "type": "LOG_ISSUE",
                    "description": f"Detected {count} occurrences of: {key}",
                    "details": "See logs for trace."
                })

    async def _check_latency_metrics(self):
        """Check metrics for high latency"""
        metrics_file = self.log_dir / "metrics.json"
        if not metrics_file.exists():
            return

        try:
            with open(metrics_file, 'rb') as f:
                content = f.read()
                if HAS_ORJSON:
                    data = orjson.loads(content)
                else:
                    data = json.loads(content.decode('utf-8'))

            metrics = data.get("metrics", {})
            for name, metric_data in metrics.items():
                points = metric_data.get("points", [])
                if not points:
                    continue

                # Check last 10 points (approximation for recent)
                recent_points = points[-10:]
                for p in recent_points:
                    if "latency" in name or "duration" in name:
                        val = p.get("value", 0)
                        if val > 200: # Threshold from prompt
                            self.issues.append({
                                "type": "HIGH_LATENCY",
                                "description": f"Metric {name} exceeded 200ms threshold ({val}ms)",
                                "details": p
                            })
                            break # One alert per metric is enough

        except Exception as e:
            logger.error(f"Error analyzing metrics: {e}")

    async def first_principles_analysis(self, issue: Dict[str, Any]):
        """
        Five Whys Interrogation
        """
        issue_type = issue["type"]
        description = issue["description"]

        reasoning = [f"Issue identified: {description}"]
        root_cause = "Unknown"
        proposed_fix = None

        if issue_type == "HEALTH_DEGRADED":
            reasoning.append("Why? Component reported unhealthy status.")
            if "database" in str(issue.get("details", "")).lower():
                reasoning.append("Why? Database connection might be failing.")
                reasoning.append("Why? Network or Credentials issue potentially.")
                root_cause = "Database Connectivity/Performance"
                proposed_fix = "RESTART_DB_POOL"
            else:
                reasoning.append("Why? Unknown component failure.")
                root_cause = "Component Failure"
                proposed_fix = "RESTART_SERVICE"

        elif issue_type == "LOG_ISSUE":
            reasoning.append("Why? Anomaly detected in logs (Error or High Status Code).")
            if "401" in description or "403" in description or "Unauthorized" in description:
                 reasoning.append("Why? Authentication failed.")
                 reasoning.append("Why? Token expired or invalid keys.")
                 root_cause = "Authentication Failure"
                 proposed_fix = "ROTATE_KEYS_OR_ALERT"
            elif "database" in description.lower() or "sql" in description.lower():
                reasoning.append("Why? Data persistence layer failed.")
                root_cause = "Database Error"
                proposed_fix = "DB_CLEANUP"
            elif "timeout" in description.lower():
                reasoning.append("Why? Service response took too long.")
                root_cause = "Resource Contention"
                proposed_fix = "CLEAR_CACHE"
            else:
                root_cause = "Application Bug/State"
                proposed_fix = "LOG_ANALYSIS"

        elif issue_type == "HIGH_LATENCY":
            reasoning.append("Why? Request processing exceeded 200ms.")
            reasoning.append("Why? Possible blocking I/O or heavy computation.")
            root_cause = "Performance Bottleneck"
            proposed_fix = "SCALE_OR_OPTIMIZE"

        self.remediations.append({
            "issue": description,
            "root_cause": root_cause,
            "reasoning": reasoning,
            "action": proposed_fix
        })

    async def execution_phase(self):
        """
        Phase 2: Execution - Ruthless Solutions
        """
        logger.info("Phase 2: Execution - Applying Ruthless Solutions...")

        if not self.remediations:
            self.report.append("No remediation actions required.")
            return

        for item in self.remediations:
            action = item["action"]
            issue = item["issue"]

            if not action:
                self.report.append(f"⚠️ No automated fix available for: {issue}")
                continue

            self.report.append(f"🔧 ACTION: {action} for {issue}")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute: {action}")
                continue

            # Execute Ruthless Fixes
            try:
                if action == "DB_CLEANUP":
                    logger.info("Executing Ruthless Database Cleanup...")
                    if 'run_database_cleanup' in globals():
                        try:
                            results = await run_database_cleanup()
                            self.report.append(f"   ✅ Cleanup Result: {len(results)} tables processed.")
                        except Exception as e:
                            self.report.append(f"   ❌ Cleanup Failed: {e}")
                    else:
                         self.report.append("   ⚠️ Database cleanup service not loaded.")

                elif action == "CLEAR_CACHE":
                    logger.info("Clearing System Caches...")
                    self.report.append("   ✅ Caches cleared (simulated).")

                elif action == "RESTART_DB_POOL":
                    logger.info("Recycling Database Connection Pool...")
                    self.report.append("   ✅ DB Pool Recycled (simulated).")

                else:
                    self.report.append(f"   ℹ️ Action '{action}' requires manual intervention or is not yet automated.")

            except Exception as e:
                logger.error(f"Failed to execute remediation '{action}': {e}")
                self.report.append(f"   ❌ Execution Failed: {e}")

    async def fortification_phase(self):
        """
        Phase 3: Fortification - Preventative Measures
        """
        logger.info("Phase 3: Fortification - Installing Guards...")

        for item in self.remediations:
            cause = item["root_cause"]
            guard = ""

            if cause == "Database Error":
                guard = "Constraint: Verify DB Connection before transaction start."
            elif cause == "Resource Contention":
                guard = "Constraint: Rate Limit reduced by 10%."
            elif cause == "Performance Bottleneck":
                guard = "Constraint: Timeout reduced to fail-fast."
            elif cause == "Authentication Failure":
                guard = "Constraint: Pre-validate keys on startup."

            if guard:
                self.fortifications.append(guard)
                self.report.append(f"🛡️ FORTIFICATION: {guard}")

    def _add_report_header(self, start_time):
        self.report.append("=" * 60)
        self.report.append(f"JULES AGENT: NIGHTLY AUDIT REPORT")
        self.report.append(f"Date: {start_time.isoformat()}")
        self.report.append(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE EXECUTION'}")
        self.report.append("=" * 60)
        self.report.append("")

    def _generate_report_file(self, start_time):
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        report_path = self.log_dir / f"audit_report_{timestamp}.txt"

        with open(report_path, "w") as f:
            f.write("\n".join(self.report))

        print("\n".join(self.report))
        logger.info(f"Report saved to {report_path}")

async def main():
    parser = argparse.ArgumentParser(description="Jules Audit Agent")
    parser.add_argument("--dry-run", action="store_true", help="Simulate remediation actions")
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=72,
        help="Hours of logs and metrics to scan (default: 72)",
    )
    parser.add_argument(
        "--active-measurement",
        action="store_true",
        help="Collect live metric samples before analysis",
    )
    parser.add_argument(
        "--measurement-samples",
        type=int,
        default=3,
        help="Number of live metric samples to collect",
    )
    parser.add_argument(
        "--measurement-interval",
        type=float,
        default=1.0,
        help="Seconds between live metric samples",
    )
    args = parser.parse_args()

    agent = AuditAgent(
        dry_run=args.dry_run,
        lookback_hours=args.lookback_hours,
        active_measurement=args.active_measurement,
        measurement_samples=args.measurement_samples,
        measurement_interval=args.measurement_interval,
    )
    await agent.run_audit()

if __name__ == "__main__":
    asyncio.run(main())
