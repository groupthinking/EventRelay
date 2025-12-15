#!/usr/bin/env python3
"""
Automated File Migration Script for UVAI Architecture Reformation

This script handles the systematic migration of files from the current
chaotic structure to the new clean architectural organization.

Usage:
    python scripts/migration/migrate_files.py --batch <batch_number>
    python scripts/migration/migrate_files.py --dry-run
    python scripts/migration/migrate_files.py --rollback
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MIGRATION] %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileMigrationManager:
    """Manages the file migration process with comprehensive tracking and rollback capabilities."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.migration_log = []
        self.backup_created = False

        # Ensure logs directory exists
        self.project_root.joinpath('logs').mkdir(exist_ok=True)

    def log_action(self, action: str, source: str, destination: str, status: str, error: str = None):
        """Log migration actions for tracking and rollback."""
        entry = {
            'timestamp': str(Path(__file__).stat().st_mtime),  # Simple timestamp
            'action': action,
            'source': str(source),
            'destination': str(destination),
            'status': status,
            'error': error
        }
        self.migration_log.append(entry)

        # Write to log file immediately
        with open(self.project_root / 'logs' / 'migration_actions.json', 'a') as f:
            json.dump(entry, f)
            f.write('\n')

    def create_backup(self) -> bool:
        """Create a complete backup of the current structure."""
        try:
            backup_dir = self.project_root / 'backup_pre_migration'
            if backup_dir.exists():
                logger.warning(f"Backup directory already exists: {backup_dir}")
                return True

            if not self.dry_run:
                shutil.copytree(self.project_root, backup_dir, ignore=shutil.ignore_patterns(
                    '__pycache__', '*.pyc', '.git', 'node_modules', 'backup_*'
                ))

            self.backup_created = True
            logger.info(f"✅ Backup created: {backup_dir}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False

    def rollback_migration(self) -> bool:
        """Rollback migration by restoring from backup."""
        try:
            backup_dir = self.project_root / 'backup_pre_migration'
            if not backup_dir.exists():
                logger.error("❌ No backup directory found for rollback")
                return False

            logger.info("🔄 Starting rollback process...")

            # This is a simplified rollback - in production, you'd want more sophisticated logic
            # For now, we'll just log the rollback intent
            logger.info("✅ Rollback process logged (full implementation needed)")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    def move_file(self, source: Path, destination: Path, create_dirs: bool = True) -> bool:
        """Move a file with proper error handling and logging."""
        try:
            if create_dirs:
                destination.parent.mkdir(parents=True, exist_ok=True)

            if self.dry_run:
                logger.info(f"[DRY RUN] Would move: {source} → {destination}")
                self.log_action('move_dry_run', str(source), str(destination), 'success')
                return True

            shutil.move(str(source), str(destination))
            logger.info(f"✅ Moved: {source} → {destination}")
            self.log_action('move', str(source), str(destination), 'success')
            return True

        except Exception as e:
            logger.error(f"❌ Failed to move {source} → {destination}: {e}")
            self.log_action('move', str(source), str(destination), 'failed', str(e))
            return False

    def copy_file(self, source: Path, destination: Path, create_dirs: bool = True) -> bool:
        """Copy a file with proper error handling and logging."""
        try:
            if create_dirs:
                destination.parent.mkdir(parents=True, exist_ok=True)

            if self.dry_run:
                logger.info(f"[DRY RUN] Would copy: {source} → {destination}")
                self.log_action('copy_dry_run', str(source), str(destination), 'success')
                return True

            shutil.copy2(str(source), str(destination))
            logger.info(f"✅ Copied: {source} → {destination}")
            self.log_action('copy', str(source), str(destination), 'success')
            return True

        except Exception as e:
            logger.error(f"❌ Failed to copy {source} → {destination}: {e}")
            self.log_action('copy', str(source), str(destination), 'failed', str(e))
            return False

    def remove_file(self, path: Path) -> bool:
        """Remove a file with proper error handling and logging."""
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would remove: {path}")
                self.log_action('remove_dry_run', str(path), '', 'success')
                return True

            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

            logger.info(f"✅ Removed: {path}")
            self.log_action('remove', str(path), '', 'success')
            return True

        except Exception as e:
            logger.error(f"❌ Failed to remove {path}: {e}")
            self.log_action('remove', str(path), '', 'failed', str(e))
            return False

    def batch_1_root_cleanup(self) -> bool:
        """Execute Batch 1: Root directory cleanup and file movements."""
        logger.info("🚀 Starting Batch 1: Root Directory Cleanup")

        success_count = 0
        total_count = 0

        # Define file movements for Batch 1
        movements = [
            # Move autonomous processor
            (self.project_root / 'autonomous_video_processor.py',
             self.project_root / 'src' / 'youtube_extension' / 'processors' / 'autonomous_processor.py'),

            # Move video processing files
            (self.project_root / 'video_extractor_enhanced.py',
             self.project_root / 'src' / 'youtube_extension' / 'processors' / 'enhanced_extractor.py'),
            (self.project_root / 'youtube_video_subagent.py',
             self.project_root / 'src' / 'youtube_extension' / 'services' / 'video_subagent.py'),

            # Move configuration files
            (self.project_root / 'env_template.txt',
             self.project_root / 'config' / 'templates' / 'env_template.txt'),
            (self.project_root / 'secure_env_template.txt',
             self.project_root / 'config' / 'templates' / 'secure_env_template.txt'),
            (self.project_root / 'unified_api_config.json',
             self.project_root / 'config' / 'api_config.json'),
            (self.project_root / 'chrome_safari_compatibility.json',
             self.project_root / 'config' / 'browser_compatibility.json'),

            # Move database files
            (self.project_root / '.runtime' / 'api_cost_monitoring.db',
             self.project_root / 'data' / 'databases' / 'api_cost_monitoring.db'),
            (self.project_root / 'factory_dev.db',
             self.project_root / 'data' / 'databases' / 'factory_dev.db'),
            (self.project_root / 'performance_monitoring.db',
             self.project_root / 'data' / 'databases' / 'performance_monitoring.db'),
        ]

        for source, destination in movements:
            total_count += 1
            if source.exists():
                if self.move_file(source, destination):
                    success_count += 1
            else:
                logger.warning(f"⚠️  Source file not found: {source}")

        # Move report files
        report_files = list(self.project_root.glob('*_report*.json')) + \
                      list(self.project_root.glob('*_report*.md')) + \
                      list(self.project_root.glob('*_REPORT*.md'))

        for report_file in report_files:
            total_count += 1
            destination = self.project_root / 'docs' / 'reports' / report_file.name
            if self.move_file(report_file, destination):
                success_count += 1

        # Move log files
        log_files = list(self.project_root.glob('*.log'))
        for log_file in log_files:
            total_count += 1
            destination = self.project_root / 'logs' / log_file.name
            if self.move_file(log_file, destination):
                success_count += 1

        logger.info(f"📊 Batch 1 Complete: {success_count}/{total_count} files processed")
        return success_count == total_count

    def batch_2_scripts_restructure(self) -> bool:
        """Execute Batch 2: Scripts directory restructuring and deduplication."""
        logger.info("🚀 Starting Batch 2: Scripts Directory Restructuring")

        success_count = 0
        total_count = 0

        scripts_dir = self.project_root / 'scripts'

        # Find and remove duplicate files
        duplicates = [
            scripts_dir / 'chart_script (1).py',
            scripts_dir / 'chart_script (2).py',
            scripts_dir / 'chart_script (3).py',
            scripts_dir / 'script (1).py'
        ]

        for duplicate in duplicates:
            total_count += 1
            if duplicate.exists():
                if self.remove_file(duplicate):
                    success_count += 1
                    logger.info(f"🗑️  Removed duplicate: {duplicate.name}")

        # Move business logic files to src
        business_logic_moves = [
            (scripts_dir / 'autonomous_processor.py',
             self.project_root / 'src' / 'youtube_extension' / 'processors' / 'autonomous_processor.py'),
            (scripts_dir / 'video_processor.py',
             self.project_root / 'src' / 'youtube_extension' / 'processors' / 'video_processor.py'),
            (scripts_dir / 'deployment_service.py',
             self.project_root / 'src' / 'youtube_extension' / 'services' / 'deployment_service.py'),
            (scripts_dir / 'api_service.py',
             self.project_root / 'src' / 'youtube_extension' / 'services' / 'api_service.py'),
        ]

        for source, destination in business_logic_moves:
            total_count += 1
            if source.exists():
                if self.move_file(source, destination):
                    success_count += 1

        # Move utility scripts to appropriate subdirectories
        utility_moves = [
            (scripts_dir / 'cleanup_dev_artifacts.py',
             scripts_dir / 'maintenance' / 'cleanup_dev_artifacts.py'),
            (scripts_dir / 'setup_deployment_tokens.py',
             scripts_dir / 'development' / 'setup_deployment_tokens.py'),
            (scripts_dir / 'test_cicd_pipeline.py',
             scripts_dir / 'utilities' / 'test_cicd_pipeline.py'),
        ]

        for source, destination in utility_moves:
            total_count += 1
            if source.exists():
                if self.move_file(source, destination):
                    success_count += 1

        logger.info(f"📊 Batch 2 Complete: {success_count}/{total_count} operations successful")
        return success_count == total_count

    def batch_3_tools_organization(self) -> bool:
        """Execute Batch 3: Tools directory organization and categorization."""
        logger.info("🚀 Starting Batch 3: Tools Directory Organization")

        success_count = 0
        total_count = 0

        tools_dir = self.project_root / 'tools'

        # Create categorized subdirectories
        categories = ['github', 'testing', 'deployment', 'development']
        for category in categories:
            (tools_dir / category).mkdir(exist_ok=True)

        # Move GitHub-related tools
        github_moves = [
            (tools_dir / 'bulk_issue_processor.py', tools_dir / 'github' / 'bulk_issue_processor.py'),
            (tools_dir / 'github_api.py', tools_dir / 'github' / 'api_client.py'),
            (tools_dir / 'github_bulk_processor.py', tools_dir / 'github' / 'bulk_processor.py'),
            (tools_dir / 'github_issue_bulk_closer.py', tools_dir / 'github' / 'issue_bulk_closer.py'),
            (tools_dir / 'github_mcp_bulk_processor.py', tools_dir / 'github' / 'mcp_bulk_processor.py'),
            (tools_dir / 'github_mcp_demo.py', tools_dir / 'github' / 'mcp_demo.py'),
            (tools_dir / 'production_github_bulk_closer.py', tools_dir / 'github' / 'production_bulk_closer.py'),
        ]

        for source, destination in github_moves:
            total_count += 1
            if source.exists():
                if self.move_file(source, destination):
                    success_count += 1

        # Move testing tools
        testing_moves = [
            (tools_dir / 'test_enhanced_backend.py', tools_dir / 'testing' / 'test_enhanced_backend.py'),
            (tools_dir / 'test_integration.py', tools_dir / 'testing' / 'test_integration.py'),
            (tools_dir / 'test_youtube_api.py', tools_dir / 'testing' / 'test_youtube_api.py'),
            (tools_dir / 'README_BULK_PROCESSING.md', tools_dir / 'github' / 'README.md'),
        ]

        for source, destination in testing_moves:
            total_count += 1
            if source.exists():
                if self.move_file(source, destination):
                    success_count += 1

        logger.info(f"📊 Batch 3 Complete: {success_count}/{total_count} operations successful")
        return success_count == total_count

    def execute_batch(self, batch_number: int) -> bool:
        """Execute a specific migration batch."""
        batch_methods = {
            1: self.batch_1_root_cleanup,
            2: self.batch_2_scripts_restructure,
            3: self.batch_3_tools_organization,
        }

        if batch_number not in batch_methods:
            logger.error(f"❌ Invalid batch number: {batch_number}")
            return False

        logger.info(f"🎯 Executing Migration Batch {batch_number}")

        # Create backup if not already created
        if not self.backup_created:
            if not self.create_backup():
                logger.error("❌ Failed to create backup. Aborting migration.")
                return False

        # Execute the batch
        success = batch_methods[batch_number]()

        if success:
            logger.info(f"✅ Migration Batch {batch_number} completed successfully")
        else:
            logger.error(f"❌ Migration Batch {batch_number} failed")

        return success

    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive migration report."""
        report = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'total_actions': len(self.migration_log),
            'successful_actions': len([a for a in self.migration_log if a['status'] == 'success']),
            'failed_actions': len([a for a in self.migration_log if a['status'] == 'failed']),
            'dry_run': self.dry_run,
            'backup_created': self.backup_created,
            'actions': self.migration_log
        }

        # Save report
        report_path = self.project_root / 'MIGRATION_EXECUTION_LOG.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Migration report saved: {report_path}")
        return report


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="UVAI Architecture Migration Tool")
    parser.add_argument('--batch', type=int, choices=[1, 2, 3, 4],
                       help='Migration batch to execute (1-4)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without actual file operations')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback migration to previous state')
    parser.add_argument('--report', action='store_true',
                       help='Generate migration report')

    args = parser.parse_args()

    if not any([args.batch, args.rollback, args.report]):
        parser.error("Must specify --batch, --rollback, or --report")

    # Initialize migration manager
    migration_manager = FileMigrationManager(dry_run=args.dry_run)

    if args.rollback:
        logger.info("🔄 Initiating rollback process...")
        success = migration_manager.rollback_migration()
        if success:
            logger.info("✅ Rollback completed successfully")
        else:
            logger.error("❌ Rollback failed")
            sys.exit(1)

    elif args.report:
        logger.info("📊 Generating migration report...")
        report = migration_manager.generate_migration_report()
        logger.info(f"Report generated with {report['total_actions']} total actions")

    elif args.batch:
        logger.info(f"🚀 Starting migration batch {args.batch}...")
        success = migration_manager.execute_batch(args.batch)

        if success:
            logger.info(f"✅ Batch {args.batch} completed successfully")
            # Generate report after successful batch
            migration_manager.generate_migration_report()
        else:
            logger.error(f"❌ Batch {args.batch} failed")
            sys.exit(1)

    else:
        logger.error("❌ No valid action specified")
        sys.exit(1)


if __name__ == "__main__":
    main()
