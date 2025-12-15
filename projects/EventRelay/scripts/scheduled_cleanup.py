#!/usr/bin/env python3
"""
Scheduled Database Cleanup Script
=================================

Automated script to run database cleanup operations for UVAI YouTube extension.
This script can be run manually or scheduled via cron/systemd timers.

Usage:
    python scheduled_cleanup.py                    # Run all cleanups
    python scheduled_cleanup.py --performance     # Performance monitoring only
    python scheduled_cleanup.py --api-costs       # API costs only
    python scheduled_cleanup.py --dry-run         # Preview what would be cleaned
    python scheduled_cleanup.py --schedule 24     # Run every 24 hours

Environment Variables:
    CLEANUP_DRY_RUN=true/false        # Enable dry run mode
    CLEANUP_LOG_LEVEL=INFO/DEBUG      # Set logging level
    CLEANUP_REPORT_EMAIL=address      # Email address for reports
"""

import asyncio
import logging
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Dict, Any

try:
    from youtube_extension.backend.services.database_cleanup_service import (
        cleanup_service,
        run_database_cleanup,
        API_COST_DB_PATH,
    )
    from youtube_extension.backend.services.performance_monitor import performance_monitor
    from youtube_extension.backend.services.api_cost_monitor import cost_monitor
    CLEANUP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import cleanup services: {e}")
    CLEANUP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('CLEANUP_LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScheduledCleanupRunner:
    """Runner for scheduled database cleanup operations"""

    def __init__(self):
        self.dry_run = os.getenv('CLEANUP_DRY_RUN', 'false').lower() == 'true'
        self.report_email = os.getenv('CLEANUP_REPORT_EMAIL')
        self.results = {}

    async def run_performance_cleanup(self) -> Dict[str, Any]:
        """Run cleanup for performance monitoring database"""
        logger.info("Starting performance monitoring cleanup...")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would clean performance monitoring database")
                return {"dry_run": True, "database": "performance_monitoring.db"}

            result = await performance_monitor.trigger_manual_cleanup()
            logger.info(f"Performance cleanup completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in performance cleanup: {e}")
            return {"error": str(e), "database": "performance_monitoring.db"}

    async def run_api_cost_cleanup(self) -> Dict[str, Any]:
        """Run cleanup for API cost monitoring database"""
        logger.info("Starting API cost monitoring cleanup...")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would clean API cost monitoring database")
                return {"dry_run": True, "database": str(API_COST_DB_PATH)}

            result = await cost_monitor.trigger_manual_cleanup()
            logger.info(f"API cost cleanup completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in API cost cleanup: {e}")
            return {"error": str(e), "database": str(API_COST_DB_PATH)}

    async def run_all_cleanups(self) -> Dict[str, Any]:
        """Run cleanup for all databases"""
        logger.info("Starting comprehensive database cleanup...")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would clean all databases")
                return {
                    "dry_run": True,
                    "databases": ["performance_monitoring.db", str(API_COST_DB_PATH)]
                }

            # Run comprehensive cleanup using the service
            if CLEANUP_AVAILABLE:
                results = await run_database_cleanup()
                logger.info(f"Comprehensive cleanup completed: {len(results)} databases cleaned")
                return {
                    "success": True,
                    "databases_cleaned": len(results),
                    "results": results
                }
            else:
                # Fallback to individual cleanups
                perf_result = await self.run_performance_cleanup()
                api_result = await self.run_api_cost_cleanup()

                return {
                    "success": True,
                    "method": "individual",
                    "performance": perf_result,
                    "api_costs": api_result
                }

        except Exception as e:
            logger.error(f"Error in comprehensive cleanup: {e}")
            return {"error": str(e)}

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable cleanup report"""
        timestamp = datetime.now(timezone.utc).isoformat()
        report_lines = [
            "=" * 60,
            f"DATABASE CLEANUP REPORT - {timestamp}",
            "=" * 60,
            ""
        ]

        if self.dry_run:
            report_lines.append("DRY RUN MODE - No actual cleanup performed")
            report_lines.append("")
            return "\n".join(report_lines)

        if "error" in results:
            report_lines.extend([
                "❌ CLEANUP FAILED",
                f"Error: {results['error']}",
                ""
            ])
            return "\n".join(report_lines)

        # Success report
        if "databases_cleaned" in results:
            # Comprehensive cleanup report
            total_records = 0
            total_space = 0.0

            for db_name, db_results in results.get("results", {}).items():
                report_lines.extend([
                    f"Database: {db_name}",
                    f"Tables cleaned: {len(db_results)}"
                ])

                for result in db_results:
                    if result.get("success"):
                        records = result.get("records_deleted", 0)
                        space = result.get("space_freed_mb", 0.0)
                        total_records += records
                        total_space += space

                        report_lines.append(
                            f"  ✅ {result.get('table_name')}: "
                            f"{records} records deleted, {space:.2f}MB freed"
                        )
                    else:
                        report_lines.append(
                            f"  ❌ {result.get('table_name')}: "
                            f"Failed - {result.get('error', 'Unknown error')}"
                        )

                report_lines.append("")

            report_lines.extend([
                "SUMMARY:",
                f"Total databases cleaned: {results.get('databases_cleaned', 0)}",
                f"Total records deleted: {total_records}",
                f"Total space freed: {total_space:.2f}MB",
                ""
            ])

        else:
            # Individual cleanup report
            for cleanup_type, result in results.items():
                if cleanup_type not in ["success", "method"]:
                    report_lines.append(f"{cleanup_type.upper()}:")
                    if "error" in result:
                        report_lines.append(f"  ❌ Failed: {result['error']}")
                    elif result.get("dry_run"):
                        report_lines.append("  📋 Dry run - no changes made")
                    else:
                        records = result.get("total_records_deleted", 0)
                        space = result.get("total_space_freed_mb", 0.0)
                        report_lines.append(
                            f"  ✅ Success: {records} records deleted, {space:.2f}MB freed"
                        )
                    report_lines.append("")

        report_lines.extend([
            "=" * 60,
            "Cleanup completed successfully!",
            "=" * 60
        ])

        return "\n".join(report_lines)

    def save_report(self, report: str, results: Dict[str, Any]):
        """Save cleanup report to file"""
        try:
            reports_dir = Path(__file__).parent.parent / "logs"
            reports_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"cleanup_report_{timestamp}.txt"
            json_file = reports_dir / f"cleanup_results_{timestamp}.json"

            # Save human-readable report
            with open(report_file, 'w') as f:
                f.write(report)

            # Save JSON results
            with open(json_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"Reports saved to: {report_file} and {json_file}")

        except Exception as e:
            logger.error(f"Failed to save reports: {e}")

    async def run_scheduled_cleanup(self, interval_hours: int = 24):
        """Run cleanup on a schedule"""
        logger.info(f"Starting scheduled cleanup every {interval_hours} hours")

        while True:
            try:
                logger.info("Running scheduled database cleanup")
                results = await self.run_all_cleanups()
                report = self.generate_report(results)
                self.save_report(report, results)

                # Print report to console for cron logging
                print(report)

            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {e}")

            # Wait for next interval
            logger.info(f"Waiting {interval_hours} hours until next cleanup...")
            await asyncio.sleep(interval_hours * 3600)

async def main():
    """Main entry point for the cleanup script"""
    parser = argparse.ArgumentParser(description="UVAI Database Cleanup Script")
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Clean only performance monitoring database"
    )
    parser.add_argument(
        "--api-costs",
        action="store_true",
        help="Clean only API cost monitoring database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned without making changes"
    )
    parser.add_argument(
        "--schedule",
        type=int,
        metavar="HOURS",
        help="Run cleanup every N hours (continuous mode)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if services are available
    if not CLEANUP_AVAILABLE:
        logger.error("Cleanup services not available. Please check imports.")
        sys.exit(1)

    runner = ScheduledCleanupRunner()

    # Override dry run if specified
    if args.dry_run:
        runner.dry_run = True
        logger.info("DRY RUN MODE ENABLED")

    try:
        if args.schedule:
            # Scheduled mode
            logger.info(f"Starting scheduled cleanup every {args.schedule} hours")
            await runner.run_scheduled_cleanup(args.schedule)

        elif args.performance:
            # Performance cleanup only
            results = await runner.run_performance_cleanup()
            report = runner.generate_report({"performance": results})

        elif args.api_costs:
            # API costs cleanup only
            results = await runner.run_api_cost_cleanup()
            report = runner.generate_report({"api_costs": results})

        else:
            # Full cleanup (default)
            results = await runner.run_all_cleanups()
            report = runner.generate_report(results)

        # Print and save report
        print(report)
        runner.save_report(report, results)

        # Exit with appropriate code
        if "error" in str(results).lower():
            sys.exit(1)
        else:
            logger.info("Cleanup completed successfully")

    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
