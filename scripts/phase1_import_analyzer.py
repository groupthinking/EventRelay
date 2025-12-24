#!/usr/bin/env python3
"""
Phase 1.1: Core Package Import Analyzer
Scans core Python files for import issues and sys.path manipulations
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class ImportIssue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    code_line: str

class ImportAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.issues: List[ImportIssue] = []
        self.files_processed = 0

    def scan_core_files(self) -> Dict[str, List[ImportIssue]]:
        """Scan core package files for import issues"""
        core_patterns = [
            "*.py",  # Root level Python files
            "backend/*.py",  # Backend files
            "agents/*.py",  # Agent files
            "intelligence_layer/*.py",  # Intelligence layer
            "factory/*.py",  # Factory files
        ]

        results = {}

        for pattern in core_patterns:
            files = list(self.root_path.glob(pattern))
            print(f"Scanning {len(files)} files matching {pattern}")

            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    issues = self.analyze_file(file_path)
                    if issues:
                        results[str(file_path.relative_to(self.root_path))] = issues
                        self.issues.extend(issues)

        return results

    def analyze_file(self, file_path: Path) -> List[ImportIssue]:
        """Analyze a single file for import issues"""
        issues = []
        self.files_processed += 1

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                line_clean = line.strip()

                # Check for sys.path manipulations
                if self._has_syspath_manipulation(line_clean):
                    issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="sys.path",
                        description="sys.path manipulation found",
                        code_line=line_clean
                    ))

                # Check for problematic imports
                if self._has_problematic_import(line_clean):
                    issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="import",
                        description="Potentially problematic import",
                        code_line=line_clean
                    ))

                # Check for relative imports that might need updating
                if self._has_relative_import(line_clean):
                    issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="relative_import",
                        description="Relative import that may need updating",
                        code_line=line_clean
                    ))

        except Exception as e:
            issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=0,
                issue_type="error",
                description=f"Failed to analyze file: {str(e)}",
                code_line=""
            ))

        return issues

    def _has_syspath_manipulation(self, line: str) -> bool:
        """Check if line contains sys.path manipulation"""
        syspath_patterns = [
            r"sys\.path\.append",
            r"sys\.path\.insert",
            r"sys\.path\.remove",
            r"sys\.path\.extend"
        ]
        return any(re.search(pattern, line) for pattern in syspath_patterns)

    def _has_problematic_import(self, line: str) -> bool:
        """Check for potentially problematic imports"""
        if not line.startswith("import ") and not line.startswith("from "):
            return False

        # Check for imports that might be broken
        problematic_patterns = [
            r"from \.\.",  # Parent directory imports
            r"from \.",   # Current directory imports (sometimes problematic)
        ]

        return any(re.search(pattern, line) for pattern in problematic_patterns)

    def _has_relative_import(self, line: str) -> bool:
        """Check for relative imports"""
        if not line.startswith("from "):
            return False

        return "from ." in line or "from .." in line

    def generate_report(self) -> str:
        """Generate analysis report"""
        report = f"""# Import Analysis Report - Phase 1.1

## Summary
- Files processed: {self.files_processed}
- Total issues found: {len(self.issues)}

## Issues by Type
"""

        issue_types = {}
        for issue in self.issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1

        for issue_type, count in issue_types.items():
            report += f"- {issue_type}: {count}\n"

        report += "\n## Detailed Issues\n\n"

        for issue in self.issues[:50]:  # Limit to first 50 for readability
            report += f"### {issue.file_path}:{issue.line_number}\n"
            report += f"- **Type:** {issue.issue_type}\n"
            report += f"- **Description:** {issue.description}\n"
            report += f"- **Code:** `{issue.code_line}`\n\n"

        if len(self.issues) > 50:
            report += f"\n... and {len(self.issues) - 50} more issues\n"

        return report

def main():
    analyzer = ImportAnalyzer("/Users/garvey/UVAI/src/core/youtube_extension")
    print("Starting Phase 1.1: Core Package Import Analysis...")

    results = analyzer.scan_core_files()

    report = analyzer.generate_report()

    with open("PHASE1_ANALYSIS_REPORT.md", "w") as f:
        f.write(report)

    print(f"Analysis complete! Found {len(analyzer.issues)} issues in {analyzer.files_processed} files")
    print("Report saved to PHASE1_ANALYSIS_REPORT.md")

    return len(analyzer.issues) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
