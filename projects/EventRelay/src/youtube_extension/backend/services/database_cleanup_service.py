#!/usr/bin/env python3
"""
Database Cleanup Service
========================

Automated cleanup service for SQLite monitoring databases to prevent
unnecessary growth and maintain optimal performance.

Features:
- Configurable retention policies for different data types
- Automated cleanup scheduling
- Comprehensive logging and monitoring
- Safe deletion with transaction rollback support
- Integration with existing monitoring services
"""

import asyncio
import sqlite3
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time

_API_COST_DB_OVERRIDE = os.getenv("API_COST_MONITOR_DB_PATH")
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_COST_DB_PATH = (
    Path(_API_COST_DB_OVERRIDE).expanduser().resolve()
    if _API_COST_DB_OVERRIDE and _API_COST_DB_OVERRIDE not in {":memory:", ":memory"}
    else (_PROJECT_ROOT / ".runtime" / "api_cost_monitoring.db").resolve()
)
API_COST_DB_NAME = API_COST_DB_PATH.name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RetentionPolicy:
    """Retention policy for a specific table/data type"""
    table_name: str
    retention_days: int
    batch_size: int = 1000
    enabled: bool = True
    description: str = ""

@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    database_path: str
    table_name: str
    records_deleted: int
    space_freed_mb: float
    execution_time_ms: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

class DatabaseCleanupService:
    """
    Automated cleanup service for SQLite monitoring databases
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "database_cleanup_config.json"
        )
        self.cleanup_stats = {
            'total_cleanups': 0,
            'total_records_deleted': 0,
            'total_space_freed_mb': 0.0,
            'last_cleanup': None,
            'errors': 0
        }

        # Default retention policies
        self.retention_policies = self._load_default_policies()

        # Load custom configuration if exists
        self._load_config()

    def _load_default_policies(self) -> Dict[str, List[RetentionPolicy]]:
        """Load default retention policies for each database type"""
        return {
            'performance_monitoring.db': [
                RetentionPolicy(
                    table_name='performance_metrics',
                    retention_days=30,
                    batch_size=5000,
                    description='Keep performance metrics for 30 days'
                ),
                RetentionPolicy(
                    table_name='performance_alerts',
                    retention_days=90,
                    batch_size=1000,
                    description='Keep performance alerts for 90 days'
                ),
                RetentionPolicy(
                    table_name='benchmark_results',
                    retention_days=180,
                    batch_size=500,
                    description='Keep benchmark results for 180 days'
                )
            ],
            API_COST_DB_NAME: [
                RetentionPolicy(
                    table_name='api_usage',
                    retention_days=90,
                    batch_size=10000,
                    description='Keep API usage data for 90 days'
                ),
                RetentionPolicy(
                    table_name='daily_budgets',
                    retention_days=365,
                    batch_size=100,
                    description='Keep daily budget data for 1 year'
                )
            ]
        }

    def _load_config(self) -> None:
        """Load custom configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Update retention policies from config
                if 'retention_policies' in config:
                    for db_name, policies in config['retention_policies'].items():
                        if db_name not in self.retention_policies:
                            self.retention_policies[db_name] = []

                        for policy_config in policies:
                            policy = RetentionPolicy(**policy_config)
                            # Update existing or add new
                            existing_idx = next(
                                (i for i, p in enumerate(self.retention_policies[db_name])
                                 if p.table_name == policy.table_name), None
                            )
                            if existing_idx is not None:
                                self.retention_policies[db_name][existing_idx] = policy
                            else:
                                self.retention_policies[db_name].append(policy)

                logger.info(f"Loaded custom configuration from {self.config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {self.config_path}: {e}")

    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            config = {
                'retention_policies': {
                    db_name: [asdict(policy) for policy in policies]
                    for db_name, policies in self.retention_policies.items()
                },
                'cleanup_stats': self.cleanup_stats,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)

            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def add_retention_policy(self, db_name: str, policy: RetentionPolicy) -> None:
        """Add or update a retention policy"""
        if db_name not in self.retention_policies:
            self.retention_policies[db_name] = []

        # Remove existing policy for same table if exists
        self.retention_policies[db_name] = [
            p for p in self.retention_policies[db_name]
            if p.table_name != policy.table_name
        ]

        self.retention_policies[db_name].append(policy)
        self.save_config()
        logger.info(f"Added retention policy for {db_name}.{policy.table_name}")

    def get_database_size_mb(self, db_path: str) -> float:
        """Get database file size in MB"""
        try:
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                return size_bytes / (1024 * 1024)
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to get size for {db_path}: {e}")
            return 0.0

    def cleanup_table(self, db_path: str, policy: RetentionPolicy) -> CleanupResult:
        """Clean up old records from a specific table"""
        start_time = time.time()
        records_deleted = 0
        initial_size = self.get_database_size_mb(db_path)

        try:
            if not os.path.exists(db_path):
                return CleanupResult(
                    database_path=db_path,
                    table_name=policy.table_name,
                    records_deleted=0,
                    space_freed_mb=0.0,
                    execution_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc),
                    success=False,
                    error_message=f"Database file not found: {db_path}"
                )

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Verify table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                             (policy.table_name,))
                if not cursor.fetchone():
                    return CleanupResult(
                        database_path=db_path,
                        table_name=policy.table_name,
                        records_deleted=0,
                        space_freed_mb=0.0,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        timestamp=datetime.now(timezone.utc),
                        success=False,
                        error_message=f"Table {policy.table_name} not found"
                    )

                # Calculate cutoff date
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)

                # Determine a valid timestamp column for retention checks
                cursor.execute(f"PRAGMA table_info({policy.table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                time_col = None
                for candidate in ("timestamp", "created_at", "createdAt", "ts"):
                    if candidate in columns:
                        time_col = candidate
                        break

                if not time_col:
                    # No recognizable time column; skip with a warning
                    logger.warning(
                        f"Skipping cleanup for {db_path}.{policy.table_name}: no timestamp-like column found"
                    )
                    return CleanupResult(
                        database_path=db_path,
                        table_name=policy.table_name,
                        records_deleted=0,
                        space_freed_mb=0.0,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        timestamp=datetime.now(timezone.utc),
                        success=False,
                        error_message="time column not found"
                    )

                # Delete old records in batches (SQLite-compatible; DELETE ... LIMIT is not portable)
                while True:
                    cursor.execute(
                        f"""
                        DELETE FROM {policy.table_name}
                        WHERE rowid IN (
                            SELECT rowid FROM {policy.table_name}
                            WHERE {time_col} < ?
                            LIMIT ?
                        )
                        """,
                        (cutoff_date.isoformat(), policy.batch_size),
                    )

                    batch_deleted = cursor.rowcount
                    records_deleted += batch_deleted
                    conn.commit()

                    if batch_deleted < policy.batch_size:
                        break

                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                conn.commit()

        except Exception as e:
            logger.error(f"Error cleaning up {db_path}.{policy.table_name}: {e}")
            return CleanupResult(
                database_path=db_path,
                table_name=policy.table_name,
                records_deleted=records_deleted,
                space_freed_mb=0.0,
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_message=str(e)
            )

        final_size = self.get_database_size_mb(db_path)
        space_freed = max(0, initial_size - final_size)
        execution_time = (time.time() - start_time) * 1000

        result = CleanupResult(
            database_path=db_path,
            table_name=policy.table_name,
            records_deleted=records_deleted,
            space_freed_mb=space_freed,
            execution_time_ms=execution_time,
            timestamp=datetime.now(timezone.utc),
            success=True
        )

        logger.info(
            f"Cleaned up {db_path}.{policy.table_name}: "
            f"{records_deleted} records deleted, "
            f"{space_freed:.2f}MB space freed in {execution_time:.1f}ms"
        )

        return result

    def cleanup_database(self, db_path: str) -> List[CleanupResult]:
        """Clean up all tables in a specific database"""
        results = []

        db_key = Path(db_path).name
        if db_key not in self.retention_policies:
            logger.warning(f"No retention policies found for {db_key}")
            return results

        logger.info(f"Starting cleanup for database: {db_path}")

        for policy in self.retention_policies[db_key]:
            if policy.enabled:
                result = self.cleanup_table(db_path, policy)
                results.append(result)

                if result.success:
                    self.cleanup_stats['total_records_deleted'] += result.records_deleted
                    self.cleanup_stats['total_space_freed_mb'] += result.space_freed_mb
                else:
                    self.cleanup_stats['errors'] += 1

        self.cleanup_stats['total_cleanups'] += 1
        self.cleanup_stats['last_cleanup'] = datetime.now(timezone.utc).isoformat()

        successful_cleanups = sum(1 for r in results if r.success)
        total_records = sum(r.records_deleted for r in results)
        total_space = sum(r.space_freed_mb for r in results)

        logger.info(
            f"Completed cleanup for {db_path}: "
            f"{successful_cleanups}/{len(results)} tables cleaned, "
            f"{total_records} total records deleted, "
            f"{total_space:.2f}MB space freed"
        )

        return results

    def cleanup_all_databases(self) -> Dict[str, List[CleanupResult]]:
        """Clean up all configured databases"""
        all_results = {}

        # Find database files in the project
        project_root = _PROJECT_ROOT
        db_files = list(project_root.glob("*.db"))

        runtime_dir = project_root / ".runtime"
        if runtime_dir.exists():
            db_files.extend(runtime_dir.glob("*.db"))

        logger.info(f"Found {len(db_files)} database files to check")

        for db_path_obj in db_files:
            db_path = str(db_path_obj)
            db_name = db_path_obj.name

            if db_name in self.retention_policies:
                results = self.cleanup_database(db_path)
                if results:
                    all_results[db_name] = results

        return all_results

    def get_cleanup_report(self) -> Dict[str, Any]:
        """Generate a comprehensive cleanup report"""
        return {
            'cleanup_stats': self.cleanup_stats,
            'retention_policies': {
                db_name: [asdict(policy) for policy in policies]
                for db_name, policies in self.retention_policies.items()
            },
            'database_sizes': {
                db_name: self.get_database_size_mb(db_name)
                for db_name in self.retention_policies.keys()
                if os.path.exists(db_name)
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    async def schedule_cleanup(self, interval_hours: int = 24) -> None:
        """Run cleanup on a schedule"""
        logger.info(f"Starting scheduled cleanup every {interval_hours} hours")

        while True:
            try:
                logger.info("Running scheduled database cleanup")
                results = self.cleanup_all_databases()

                # Log summary
                total_databases = len(results)
                total_records = sum(
                    sum(r.records_deleted for r in db_results)
                    for db_results in results.values()
                )
                total_space = sum(
                    sum(r.space_freed_mb for r in db_results)
                    for db_results in results.values()
                )

                logger.info(
                    f"Scheduled cleanup completed: "
                    f"{total_databases} databases cleaned, "
                    f"{total_records} records deleted, "
                    f"{total_space:.2f}MB space freed"
                )

            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {e}")

            # Wait for next interval
            await asyncio.sleep(interval_hours * 3600)

# Global cleanup service instance
cleanup_service = DatabaseCleanupService()

async def run_database_cleanup() -> Dict[str, List[CleanupResult]]:
    """Convenience function to run database cleanup"""
    return cleanup_service.cleanup_all_databases()

def get_cleanup_report() -> Dict[str, Any]:
    """Get cleanup service report"""
    return cleanup_service.get_cleanup_report()

if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "schedule":
        # Run scheduled cleanup
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        asyncio.run(cleanup_service.schedule_cleanup(interval))
    else:
        # Run one-time cleanup
        results = asyncio.run(run_database_cleanup())
        print("Cleanup completed:")
        for db_name, db_results in results.items():
            print(f"  {db_name}:")
            for result in db_results:
                status = "✓" if result.success else "✗"
                print(f"    {status} {result.table_name}: {result.records_deleted} records, "
                      f"{result.space_freed_mb:.2f}MB freed")
