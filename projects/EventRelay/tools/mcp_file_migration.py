#!/usr/bin/env python3
"""
MCP-Compliant File Migration Script
Handles safe file categorization and migration for architectural transformation
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict

@dataclass
class MigrationContext:
    """MCP-compliant context for file migration operations"""
    task: str = "file_migration"
    intent: str = "architectural_restructuring"
    source_root: str = ""
    target_structure: Dict[str, str] = None
    migrated_files: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.target_structure is None:
            self.target_structure = {}
        if self.migrated_files is None:
            self.migrated_files = []
        if self.errors is None:
            self.errors = []

class MCPFileMigrator:
    """MCP-compliant file migration system"""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.context = MigrationContext(source_root=str(root_path))

        # Define migration categories with MCP context
        self.categories = {
            'scripts': {
                'patterns': ['*.sh', '*.py'],
                'exclude_patterns': ['main.py', '__init__.py', 'setup.py', 'mcp_*.py'],
                'target': 'scripts/',
                'description': 'Utility scripts and automation tools'
            },
            'config': {
                'patterns': ['*.json', '*.yaml', '*.yml', '*.toml', '*.env*', '*.ini'],
                'exclude_patterns': ['package-lock.json', 'pyrightconfig.json'],
                'target': 'config/',
                'description': 'Configuration files and settings'
            },
            'docs': {
                'patterns': ['*.md', '*.txt', 'README*', 'LICENSE*'],
                'exclude_patterns': ['requirements*.txt'],
                'target': 'docs/',
                'description': 'Documentation and project files'
            },
            'data': {
                'patterns': ['*.db', '*.sqlite*', '*.json'],
                'include_dirs': ['data/', 'database/', 'results/', 'youtube_processed_videos/'],
                'target': 'data/',
                'description': 'Data files and databases'
            },
            'tools': {
                'include_dirs': ['tools/', 'scripts/utilities/', 'scripts/migration/'],
                'target': 'tools/',
                'description': 'Development tools and utilities'
            },
            'tests': {
                'include_dirs': ['tests/', 'testing/'],
                'target': 'tests/',
                'description': 'Test suites and testing infrastructure'
            }
        }

    def analyze_root_directory(self) -> Dict[str, List[str]]:
        """Analyze current root directory structure"""
        analysis = {}
        root_files = []

        for item in self.root_path.iterdir():
            if item.is_file():
                root_files.append(item.name)
            elif item.is_dir() and not item.name.startswith('.'):
                analysis[item.name + '/'] = [f.name for f in item.iterdir() if f.is_file()][:10]  # Sample first 10

        analysis['root_files'] = root_files
        return analysis

    def categorize_files(self) -> Dict[str, List[str]]:
        """Categorize files for migration"""
        categorized = {cat: [] for cat in self.categories.keys()}

        # Process root files
        for item in self.root_path.iterdir():
            if not item.is_file():
                continue

            file_name = item.name
            moved = False

            for category, rules in self.categories.items():
                if self._matches_category(file_name, rules):
                    categorized[category].append(file_name)
                    moved = True
                    break

            if not moved:
                categorized.setdefault('keep_root', []).append(file_name)

        return categorized

    def _matches_category(self, filename: str, rules: Dict) -> bool:
        """Check if file matches category rules"""
        # Check include patterns
        if 'patterns' in rules:
            for pattern in rules['patterns']:
                if pattern.startswith('*.'):
                    ext = pattern[1:]
                    if filename.endswith(ext):
                        # Check exclude patterns
                        if 'exclude_patterns' in rules:
                            for exclude in rules['exclude_patterns']:
                                if exclude.startswith('*.') and filename.endswith(exclude[1:]):
                                    return False
                                elif filename == exclude:
                                    return False
                        return True

        # Check include directories
        if 'include_dirs' in rules:
            for include_dir in rules['include_dirs']:
                if include_dir in filename or filename.startswith(include_dir.rstrip('/')):
                    return True

        return False

    def execute_migration(self, dry_run: bool = True) -> Dict[str, any]:
        """Execute file migration with MCP context tracking"""
        results = {
            'migrated': [],
            'skipped': [],
            'errors': [],
            'dry_run': dry_run
        }

        categorized = self.categorize_files()

        for category, files in categorized.items():
            if category == 'keep_root':
                continue

            target_dir = self.root_path / self.categories[category]['target']
            target_dir.mkdir(exist_ok=True)

            for file_name in files:
                source = self.root_path / file_name
                target = target_dir / file_name

                try:
                    if not dry_run:
                        if source.exists():
                            shutil.move(str(source), str(target))
                            self.context.migrated_files.append(f"{file_name} -> {self.categories[category]['target']}")
                            results['migrated'].append(f"{file_name} -> {self.categories[category]['target']}")
                    else:
                        results['migrated'].append(f"[DRY RUN] {file_name} -> {self.categories[category]['target']}")

                except Exception as e:
                    error_msg = f"Failed to migrate {file_name}: {str(e)}"
                    self.context.errors.append(error_msg)
                    results['errors'].append(error_msg)

        return results

    def generate_migration_report(self) -> str:
        """Generate MCP-compliant migration report"""
        report = f"""# MCP File Migration Report

## Migration Context
- **Task**: {self.context.task}
- **Intent**: {self.context.intent}
- **Source Root**: {self.context.source_root}

## Migration Summary
- **Files Migrated**: {len(self.context.migrated_files)}
- **Errors Encountered**: {len(self.context.errors)}

## Categorized Files
"""

        categorized = self.categorize_files()
        for category, files in categorized.items():
            if files:
                report += f"\n### {category.title()} ({len(files)} files)\n"
                for file in files[:10]:  # Show first 10
                    report += f"- {file}\n"
                if len(files) > 10:
                    report += f"- ... and {len(files) - 10} more\n"

        if self.context.errors:
            report += "\n## Errors\n"
            for error in self.context.errors:
                report += f"- {error}\n"

        return report

def main():
    """Main migration execution"""
    import argparse

    parser = argparse.ArgumentParser(description='MCP File Migration Tool')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without actually moving files')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze current structure')
    parser.add_argument('--path', default='.', help='Root path to migrate')

    args = parser.parse_args()

    # Initialize MCP migrator
    migrator = MCPFileMigrator(args.path)

    if args.analyze_only:
        print("=== Current Structure Analysis ===")
        analysis = migrator.analyze_root_directory()
        print(json.dumps(analysis, indent=2))

        print("\n=== File Categorization ===")
        categorized = migrator.categorize_files()
        print(json.dumps(categorized, indent=2))
        return

    # Execute migration
    print("=== Starting MCP File Migration ===")
    results = migrator.execute_migration(dry_run=args.dry_run)

    print(f"Migration completed ({'DRY RUN' if args.dry_run else 'LIVE'})")
    print(f"- Migrated: {len(results['migrated'])}")
    print(f"- Errors: {len(results['errors'])}")

    if results['migrated']:
        print("\nMigrated files:")
        for item in results['migrated'][:10]:
            print(f"  {item}")
        if len(results['migrated']) > 10:
            print(f"  ... and {len(results['migrated']) - 10} more")

    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  {error}")

    # Generate and save report
    report = migrator.generate_migration_report()
    report_file = Path(args.path) / 'MIGRATION_REPORT.md'
    report_file.write_text(report)
    print(f"\nMigration report saved to: {report_file}")

if __name__ == "__main__":
    main()
