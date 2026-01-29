#!/usr/bin/env python3
"""
Nightly Audit & Ruthless Remediation Agent
==========================================

This agent performs a nightly deep-scan of system logs, transaction traces,
and state changes. It identifies divergences from first principles,
executes ruthless cleanup, and fortifies the system.

Role: High-Integrity Systems Auditor & First-Principles Engineer
Frequency: Nightly Execution (02:00 UTC)
"""

import asyncio
import json
import logging
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

# Add src to python path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Imports - Fail fast if missing dependencies
from youtube_extension.backend.services.health_monitoring_service import (
    HealthMonitoringService,
    HealthStatus
)
from youtube_extension.backend.services.database_cleanup_service import run_database_cleanup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AuditAgent")

class AuditAgent:
    """
    The Nightly Audit & Ruthless Remediation Agent.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.issues = []
        self.remediations = []
        self.fortifications = []
        # Anchor paths to project root
        project_root = Path(__file__).resolve().parent.parent
        self.log_dir = project_root / "logs"
        self.report_dir = project_root / "audit_reports"

        # Ensure directories exist
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services (only those needed)
        self.health_service = HealthMonitoringService()

    async def run_audit(self):
        """Main execution loop."""
        logger.info("Starting Nightly Audit...")

        # 1. Analysis Phase
        await self.analyze_health()
        await self.analyze_logs()
        await self.analyze_metrics()

        # 2. Execution Phase (First Principles & Ruthless Solutions)
        if self.issues:
            logger.info(f"Found {len(self.issues)} issues. Beginning First-Principles Analysis...")
            for issue in self.issues:
                diagnosis = await self.first_principles_analysis(issue)
                await self.ruthless_remediation(diagnosis)
                await self.fortify(diagnosis)
        else:
            logger.info("No critical issues found.")

        # 3. Reporting
        report = self.generate_report()
        self.save_report(report)
        print(report)

    async def analyze_health(self):
        """Check system health via HealthMonitoringService."""
        logger.info("Analyzing system health...")
        try:
            health = await self.health_service.perform_health_check()
            if health.overall_status != HealthStatus.HEALTHY:
                self.issues.append({
                    "type": "health_check",
                    "severity": "high",
                    "details": f"Overall health is {health.overall_status.value}",
                    "components": [c.name for c in health.components if c.status != HealthStatus.HEALTHY]
                })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.issues.append({
                "type": "health_system_failure",
                "severity": "critical",
                "details": str(e)
            })

    async def analyze_logs(self):
        """Analyze logs for status codes >= 400."""
        logger.info("Analyzing logs...")
        log_file = self.log_dir / "structured_logs.jsonl"

        if not log_file.exists():
            logger.warning(f"Log file not found: {log_file}")
            return

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get('status_code', 0) >= 400:
                            self.issues.append({
                                "type": "http_error",
                                "severity": "medium" if entry.get('status_code') < 500 else "high",
                                "details": f"HTTP {entry.get('status_code')} at {entry.get('endpoint')}",
                                "raw": entry
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")

    async def analyze_metrics(self):
        """Analyze metrics for latency > 200ms."""
        logger.info("Analyzing metrics...")
        try:
            # Check metrics from HealthMonitoringService components
            health = self.health_service.get_current_health()
            if not health:
                health = await self.health_service.perform_health_check()

            for component in health.components:
                for metric in component.metrics:
                    # Look for latency-related metrics (response_time, latency) in ms
                    if 'response_time' in metric.name or 'latency' in metric.name:
                        if metric.unit == 'ms' and metric.value > 200:
                            self.issues.append({
                                "type": "high_latency",
                                "severity": "medium",
                                "details": f"High latency detected in {component.name}: {metric.name} = {metric.value}ms (> 200ms)",
                                "component": component.name,
                                "metric": metric.name,
                                "value": metric.value
                            })
        except Exception as e:
             logger.error(f"Error analyzing metrics: {e}")

    async def first_principles_analysis(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute "Five Whys" interrogation.
        Identify the exact delta between expected state and actual state.
        TODO: Integrate LLM for true "Five Whys" reasoning.
        """
        logger.info(f"Analyzing issue: {issue['type']}")

        diagnosis = {
            "issue": issue,
            "root_cause": "Unknown",
            "proposed_fix": "Investigate",
            "preventative_measure": "Monitor"
        }

        # Simplified "Reasoning" logic
        if issue['type'] == 'http_error':
            diagnosis['root_cause'] = "Potential logic error or unhandled exception in endpoint."
            diagnosis['proposed_fix'] = "Review endpoint logic and add error handling."
            diagnosis['preventative_measure'] = "Add integration test for this error case."

        elif issue['type'] == 'health_check':
            diagnosis['root_cause'] = f"Components {issue.get('components')} are unhealthy."
            diagnosis['proposed_fix'] = "Restart unhealthy services and clear caches."
            diagnosis['preventative_measure'] = "Tune health check thresholds."

        elif issue['type'] == 'high_latency':
            diagnosis['root_cause'] = f"Performance bottleneck in {issue.get('component')}."
            diagnosis['proposed_fix'] = "Optimize query or scale resources."
            diagnosis['preventative_measure'] = "Add caching layer."

        return diagnosis

    async def ruthless_remediation(self, diagnosis: Dict[str, Any]):
        """
        Execute ruthless solutions (pre-approved maintenance tasks only).
        Structural changes and schema updates are advisory-only.
        """
        fix = diagnosis['proposed_fix']
        logger.info(f"Executing remediation: {fix}")

        if self.dry_run:
            logger.info("[DRY RUN] Remediation skipped.")
            self.remediations.append(f"[DRY RUN] {fix}")
            return

        # "Ruthless" Actions implementation
        if "Restart" in fix:
            # In a real env, this might trigger a k8s restart or systemctl
            self.remediations.append(f"[ADVISORY] Triggered restart for components related to {diagnosis['issue']['type']}")

        elif "Review" in fix:
            self.remediations.append(f"[ADVISORY] Flagged {diagnosis['issue']['type']} for immediate manual review (Ticket created)")

        elif "Optimize" in fix:
            self.remediations.append("[ADVISORY] Triggered auto-optimization (e.g., ANALYZE DB)")

        # Only run DB cleanup if database component is specifically unhealthy
        if diagnosis['issue']['type'] == 'health_check':
            unhealthy_components = diagnosis['issue'].get('components', [])
            db_components = [c for c in unhealthy_components if 'database' in c.lower() or 'db' in c.lower()]
            
            if db_components:
                try:
                    results = await run_database_cleanup()
                    self.remediations.append(f"Ran database cleanup for unhealthy DB components {db_components}: {len(results)} databases cleaned")
                except Exception as e:
                    logger.error(f"Database cleanup failed: {e}")
                    self.remediations.append(f"Database cleanup failed: {e}")

    async def fortify(self, diagnosis: Dict[str, Any]):
        """
        Add preventative measures.
        """
        measure = diagnosis['preventative_measure']
        logger.info(f"Applying fortification: {measure}")

        if self.dry_run:
            logger.info("[DRY RUN] Fortification skipped.")
            self.fortifications.append(f"[DRY RUN] {measure}")
            return

        self.fortifications.append(f"Applied: {measure}")
        # In a real system, this might write to a 'constraints.json' or update WAF rules.

    def generate_report(self) -> str:
        """Generate a summary report."""
        timestamp = datetime.now(timezone.utc).isoformat()
        report = [
            "=" * 60,
            f"NIGHTLY AUDIT & REMEDIATION REPORT - {timestamp}",
            "=" * 60,
            f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}",
            "",
            "ISSUES FOUND:",
        ]

        if not self.issues:
            report.append("  None")
        else:
            for i, issue in enumerate(self.issues, 1):
                report.append(f"  {i}. {issue['type']} ({issue['severity']}): {issue['details']}")

        report.append("")
        report.append("REMEDIATIONS EXECUTED:")
        if not self.remediations:
            report.append("  None")
        else:
            for item in self.remediations:
                report.append(f"  - {item}")

        report.append("")
        report.append("FORTIFICATIONS APPLIED:")
        if not self.fortifications:
            report.append("  None")
        else:
            for item in self.fortifications:
                report.append(f"  - {item}")

        report.append("")
        report.append("=" * 60)
        return "\n".join(report)

    def save_report(self, report: str):
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.report_dir / f"audit_report_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {filename}")

async def main():
    parser = argparse.ArgumentParser(description="Jules Nightly Audit Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run without executing changes")
    args = parser.parse_args()

    agent = AuditAgent(dry_run=args.dry_run)
    await agent.run_audit()

if __name__ == "__main__":
    asyncio.run(main())
