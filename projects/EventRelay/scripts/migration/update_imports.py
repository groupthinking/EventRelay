#!/usr/bin/env python3
"""
Import Statement Update Script for UVAI Architecture Reformation

This script systematically replaces problematic sys.path manipulations
with proper Python package imports and updates all import statements
to use the new package structure.

Usage:
    python scripts/migration/update_imports.py --scan
    python scripts/migration/update_imports.py --update
    python scripts/migration/update_imports.py --validate
"""

import ast
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [IMPORTS] %(message)s',
    handlers=[
        logging.FileHandler('logs/import_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImportUpdateManager:
    """Manages the systematic update of import statements across the codebase."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.import_log = []
        self.files_processed = 0
        self.files_updated = 0
        self.errors_encountered = 0

        # Ensure logs directory exists
        self.project_root.joinpath('logs').mkdir(exist_ok=True)

    def log_import_action(self, file_path: str, action: str, old_import: str,
                         new_import: str, status: str, error: str = None):
        """Log import update actions for tracking."""
        entry = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'file': file_path,
            'action': action,
            'old_import': old_import,
            'new_import': new_import,
            'status': status,
            'error': error
        }
        self.import_log.append(entry)

        # Write to log file immediately
        with open(self.project_root / 'logs' / 'import_updates.json', 'a') as f:
            json.dump(entry, f)
            f.write('\n')

    def scan_for_problematic_imports(self) -> Dict[str, List[str]]:
        """Scan the entire codebase for problematic import patterns."""
        logger.info("🔍 Scanning for problematic import patterns...")

        problematic_files = {}
        python_files = list(self.project_root.rglob('*.py'))

        # Exclude certain directories
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'backup_*', 'logs', 'temp'}
        python_files = [f for f in python_files if not any(excl in f.parts for excl in exclude_dirs)]

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                issues = []

                # Check for sys.path manipulations
                if 'sys.path.insert' in content or 'sys.path.append' in content:
                    issues.append('sys.path manipulation')

                # Check for problematic relative imports
                if re.search(r'from \.\.\s+import', content) or re.search(r'from \.\s+import', content):
                    issues.append('problematic relative imports')

                # Check for hardcoded paths
                if '/Users/' in content or 'C:\\' in content or '../' in content:
                    issues.append('hardcoded paths')

                if issues:
                    problematic_files[str(file_path.relative_to(self.project_root))] = issues

            except Exception as e:
                logger.warning(f"⚠️  Could not scan {file_path}: {e}")

        logger.info(f"📊 Found {len(problematic_files)} files with import issues")
        return problematic_files

    def update_sys_path_manipulations(self, file_path: Path) -> bool:
        """Update sys.path manipulations in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = []

            # Pattern 1: # REMOVED: sys.path.insert for uvai_root
            uvai_root_pattern = r'sys\.path\.insert\(0,\s*str\(uvai_root\)\)'
            if re.search(uvai_root_pattern, content):
                # This will be replaced with proper package imports
                content = re.sub(uvai_root_pattern, '# REMOVED: sys.path.insert for uvai_root', content)
                changes_made.append('uvai_root sys.path.insert')

            # Pattern 2: # REMOVED: sys.path.insert for project_root
            project_root_pattern = r'sys\.path\.insert\(0,\s*str\(project_root\)\)'
            if re.search(project_root_pattern, content):
                content = re.sub(project_root_pattern, '# REMOVED: sys.path.insert for project_root', content)
                changes_made.append('project_root sys.path.insert')

            # Pattern 3: # REMOVED: sys.path.insert with Path manipulation
            path_pattern = r'sys\.path\.insert\(0,\s*str\(Path\(__file__\)\..*\)\)'
            if re.search(path_pattern, content):
                content = re.sub(path_pattern, '# REMOVED: sys.path.insert with Path manipulation', content)
                changes_made.append('Path-based sys.path.insert')

            # Pattern 4: sys.path.append variations
            append_patterns = [
                (r'sys\.path\.append\(.*\)', 'sys.path.append removed'),
            ]
            for pattern, description in append_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, f'# REMOVED: {description}', content)
                    changes_made.append(description)

            # If changes were made, update the file
            if content != original_content and changes_made:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                self.log_import_action(
                    str(file_path.relative_to(self.project_root)),
                    'update_sys_path',
                    '; '.join(changes_made),
                    'Removed sys.path manipulations',
                    'success'
                )

                logger.info(f"✅ Updated sys.path in: {file_path.name}")
                return True

        except Exception as e:
            self.log_import_action(
                str(file_path.relative_to(self.project_root)),
                'update_sys_path',
                'sys.path patterns',
                'Failed to update',
                'failed',
                str(e)
            )
            logger.error(f"❌ Failed to update {file_path}: {e}")
            return False

        return False

    def update_import_statements(self, file_path: Path) -> bool:
        """Update import statements to use new package structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = []

            # Import transformation mappings
            import_mappings = {
                # Backend imports
                'from youtube_extension.services.deployment_manager import': 'from youtube_extension.services.deployment_manager import',
                'from youtube_extension.services.deploy.core import': 'from youtube_extension.services.deploy.core import',
                'from youtube_extension.main import': 'from youtube_extension.main import',

                # Service imports
                'from youtube_extension.services.real_video_processor import': 'from youtube_extension.services.real_video_processor import',
                'from youtube_extension.services.real_youtube_api import': 'from youtube_extension.services.real_youtube_api import',
                'from youtube_extension.services.api_cost_monitor import': 'from youtube_extension.services.api_cost_monitor import',

                # Processor imports
                'from youtube_extension.processors.simple_real_processor import': 'from youtube_extension.processors.simple_real_processor import',

                # Relative import fixes
                'from youtube_extension.services.logging_service import': 'from youtube_extension.services.logging_service import',
                'from youtube_extension.config.logging_config import': 'from youtube_extension.config.logging_config import',
                'from youtube_extension.core.': 'from youtube_extension.core.',
                'from youtube_extension.services.': 'from youtube_extension.services.',
            }

            for old_pattern, new_pattern in import_mappings.items():
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    changes_made.append(f'{old_pattern} → {new_pattern}')

            # If changes were made, update the file
            if content != original_content and changes_made:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                self.log_import_action(
                    str(file_path.relative_to(self.project_root)),
                    'update_imports',
                    '; '.join(changes_made),
                    'Updated to new package structure',
                    'success'
                )

                logger.info(f"✅ Updated imports in: {file_path.name}")
                return True

        except Exception as e:
            self.log_import_action(
                str(file_path.relative_to(self.project_root)),
                'update_imports',
                'import statements',
                'Failed to update',
                'failed',
                str(e)
            )
            logger.error(f"❌ Failed to update imports in {file_path}: {e}")
            return False

        return False

    def validate_imports(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate that imports in a file can be resolved."""
        try:
            # Parse the file to extract import statements
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            issues = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        # Check for problematic patterns
                        if module_name.startswith('.'):
                            issues.append(f'Relative import: {module_name}')
                        elif 'sys.path' in content:
                            issues.append('sys.path manipulation found')

                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ''
                    if module_name.startswith('.'):
                        issues.append(f'Relative import: from {module_name}')
                    elif module_name and not module_name.startswith('youtube_extension'):
                        # Check if it's a local module that should be updated
                        if any(local in module_name for local in ['backend', 'services', 'processors']):
                            issues.append(f'Local import not updated: {module_name}')

            return len(issues) == 0, issues

        except SyntaxError as e:
            return False, [f'Syntax error: {e}']
        except Exception as e:
            return False, [f'Validation error: {e}']

    def process_file(self, file_path: Path) -> bool:
        """Process a single file for import updates."""
        self.files_processed += 1

        try:
            # Update sys.path manipulations
            sys_path_updated = self.update_sys_path_manipulations(file_path)

            # Update import statements
            imports_updated = self.update_import_statements(file_path)

            # Validate the results
            is_valid, issues = self.validate_imports(file_path)

            if issues:
                logger.warning(f"⚠️  Validation issues in {file_path.name}: {issues}")

            if sys_path_updated or imports_updated:
                self.files_updated += 1
                return True

            return True  # File processed successfully even if no changes needed

        except Exception as e:
            self.errors_encountered += 1
            logger.error(f"❌ Error processing {file_path}: {e}")
            return False

    def scan_and_update(self) -> bool:
        """Scan entire codebase and update problematic imports."""
        logger.info("🚀 Starting comprehensive import update process...")

        # First, scan for problematic files
        problematic_files = self.scan_for_problematic_imports()

        if not problematic_files:
            logger.info("✅ No problematic imports found!")
            return True

        logger.info(f"📋 Found {len(problematic_files)} files to process")

        # Process each problematic file
        success_count = 0
        for file_path_str in problematic_files.keys():
            file_path = self.project_root / file_path_str
            if self.process_file(file_path):
                success_count += 1

        # Process additional Python files for import updates
        logger.info("🔄 Processing remaining Python files for import updates...")
        python_files = list(self.project_root.rglob('*.py'))
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'backup_*', 'logs', 'temp'}
        python_files = [f for f in python_files if not any(excl in f.parts for excl in exclude_dirs)]

        for file_path in python_files:
            if str(file_path.relative_to(self.project_root)) not in problematic_files:
                self.process_file(file_path)
                success_count += 1

        logger.info(f"📊 Import update complete:")
        logger.info(f"   Files processed: {self.files_processed}")
        logger.info(f"   Files updated: {self.files_updated}")
        logger.info(f"   Errors encountered: {self.errors_encountered}")

        return self.errors_encountered == 0

    def generate_import_report(self) -> Dict[str, Any]:
        """Generate a comprehensive import update report."""
        report = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'files_processed': self.files_processed,
            'files_updated': self.files_updated,
            'errors_encountered': self.errors_encountered,
            'dry_run': self.dry_run,
            'import_actions': self.import_log
        }

        # Save report
        report_path = self.project_root / 'IMPORT_OPTIMIZATION_REPORT.md'
        with open(report_path, 'w') as f:
            f.write("# Import Optimization Report\n\n")
            f.write(f"Generated: {report['timestamp']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Files processed: {report['files_processed']}\n")
            f.write(f"- Files updated: {report['files_updated']}\n")
            f.write(f"- Errors encountered: {report['errors_encountered']}\n")
            f.write(f"- Dry run: {report['dry_run']}\n\n")
            f.write("## Actions Taken\n\n")
            for action in report['import_actions']:
                f.write(f"- **{action['file']}**: {action['action']} - {action['status']}\n")
                if action.get('old_import'):
                    f.write(f"  - Old: `{action['old_import']}`\n")
                if action.get('new_import'):
                    f.write(f"  - New: `{action['new_import']}`\n")
                if action.get('error'):
                    f.write(f"  - Error: {action['error']}\n")
                f.write("\n")

        # Also save JSON version
        json_report_path = self.project_root / 'logs' / 'import_update_report.json'
        with open(json_report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Import report saved: {report_path}")
        return report


def main():
    """Main entry point for the import update script."""
    import argparse

    parser = argparse.ArgumentParser(description="UVAI Import Update Tool")
    parser.add_argument('--scan', action='store_true',
                       help='Scan for problematic import patterns')
    parser.add_argument('--update', action='store_true',
                       help='Update problematic imports')
    parser.add_argument('--validate', action='store_true',
                       help='Validate import statements')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without actual changes')

    args = parser.parse_args()

    if not any([args.scan, args.update, args.validate]):
        parser.error("Must specify --scan, --update, or --validate")

    # Initialize import manager
    import_manager = ImportUpdateManager(dry_run=args.dry_run)

    if args.scan:
        logger.info("🔍 Scanning for import issues...")
        problematic_files = import_manager.scan_for_problematic_imports()

        print("\n📋 Files with import issues:")
        for file_path, issues in problematic_files.items():
            print(f"  {file_path}: {', '.join(issues)}")

        print(f"\n📊 Total files with issues: {len(problematic_files)}")

    elif args.update:
        logger.info("🔄 Updating import statements...")
        success = import_manager.scan_and_update()

        if success:
            logger.info("✅ Import update process completed successfully")
            # Generate report
            import_manager.generate_import_report()
        else:
            logger.error("❌ Import update process encountered errors")
            sys.exit(1)

    elif args.validate:
        logger.info("✅ Validating import statements...")
        # This would require additional implementation for full validation
        logger.info("Validation feature - implementation needed")

    else:
        logger.error("❌ No valid action specified")
        sys.exit(1)


if __name__ == "__main__":
    main()
