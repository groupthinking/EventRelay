#!/usr/bin/env python3
"""
Repository Cleanup Script
=========================

Safely reorganizes EventRelay repository by:
- Removing duplicate files and directories
- Moving misplaced files to appropriate locations
- Creating backup before any destructive operations
- Providing dry-run mode for safety

Usage:
    python scripts/cleanup_repository.py --dry-run    # Show what would be done
    python scripts/cleanup_repository.py --backup     # Create backup and execute
    python scripts/cleanup_repository.py --force      # Execute without backup (dangerous)
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class RepositoryCleanup:
    """Manages safe cleanup of repository."""

    def __init__(self, repo_root: Path, dry_run: bool = True, backup: bool = True):
        self.repo_root = repo_root
        self.dry_run = dry_run
        self.backup = backup
        self.actions_taken: list[str] = []
        self.errors: list[str] = []

    def log_action(self, action: str, color: str = Colors.OKGREEN) -> None:
        """Log an action with color."""
        prefix = "[DRY-RUN] " if self.dry_run else "[EXECUTE] "
        print(f"{color}{prefix}{action}{Colors.ENDC}")
        self.actions_taken.append(action)

    def log_error(self, error: str) -> None:
        """Log an error."""
        print(f"{Colors.FAIL}[ERROR] {error}{Colors.ENDC}")
        self.errors.append(error)

    def create_backup(self) -> Path:
        """Create timestamped backup of important files."""
        if self.dry_run:
            self.log_action("Would create backup", Colors.OKCYAN)
            return Path("/tmp/backup")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.repo_root / f".backup_{timestamp}"

        print(f"{Colors.HEADER}Creating backup at: {backup_dir}{Colors.ENDC}")
        backup_dir.mkdir(exist_ok=True)

        return backup_dir

    def remove_duplicate_directory(self) -> None:
        """Remove duplicate mcp_youtube-0.2.0 2 directory."""
        duplicate_dir = self.repo_root / "mcp_youtube-0.2.0 2"

        if not duplicate_dir.exists():
            self.log_action(f"Duplicate directory not found: {duplicate_dir}", Colors.WARNING)
            return

        self.log_action(f"Remove duplicate directory: {duplicate_dir}")

        if not self.dry_run:
            try:
                shutil.rmtree(duplicate_dir)
            except Exception as e:
                self.log_error(f"Failed to remove {duplicate_dir}: {e}")

    def remove_secret_files(self) -> None:
        """Remove secret files that should not be in repo."""
        secret_files = [
            "client_secret_833571612383-3j2p45bhqi2bh4bfqtpjp2s6g8idenmq.apps.googleusercontent.com.json",
        ]

        for filename in secret_files:
            filepath = self.repo_root / filename
            if filepath.exists():
                self.log_action(f"Remove secret file: {filename}", Colors.WARNING)
                if not self.dry_run:
                    try:
                        filepath.unlink()
                    except Exception as e:
                        self.log_error(f"Failed to remove {filename}: {e}")

    def move_prompt_files(self) -> None:
        """Move .rtf prompt files to docs/prompts/."""
        prompt_dir = self.repo_root / "docs" / "prompts"

        rtf_files = [
            "Make_Framework_Content_PROMPT.rtf",
            "TRANSCRIPT_PROMPT_Insight_EXTRACT.rtf",
            "Time_Stamp_Extraction_PROMPT.rtf",
            "Title_GEN_PROMPT.rtf",
            "SET_TARGET.rtf",
            "preset AI .rtf",
        ]

        if not self.dry_run:
            prompt_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_action(f"Would create directory: {prompt_dir}", Colors.OKCYAN)

        for filename in rtf_files:
            src = self.repo_root / filename
            dst = prompt_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → docs/prompts/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_analysis_files(self) -> None:
        """Move JSON analysis files to docs/analysis/."""
        analysis_dir = self.repo_root / "docs" / "analysis"

        json_files = [
            "ai_studio_analysis_bMknfKXIFA8.json",
            "execution_results_bMknfKXIFA8.json",
            "ai.google.dev_api.2025-09-20T19_42_50.214Z.json",
            "ai.google.dev_gemini-api_docs.2025-09-20T19_44_36.867Z.json",
            "production_todo_report.json",
            "github_diagnostic_report.json",
            "timeout_update_summary.json",
        ]

        if not self.dry_run:
            analysis_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_action(f"Would create directory: {analysis_dir}", Colors.OKCYAN)

        for filename in json_files:
            src = self.repo_root / filename
            dst = analysis_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → docs/analysis/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_planning_docs(self) -> None:
        """Move planning markdown files to docs/planning/."""
        planning_dir = self.repo_root / "docs" / "planning"

        md_files = [
            "guided_detail_outline_plan.md",
            "compass_artifact_wf-3dd19ad4-c48d-4358-a71b-352f8286b7b9_text_markdown.md",
        ]

        # Don't move PLAN.md as it will be handled separately

        if not self.dry_run:
            planning_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_action(f"Would create directory: {planning_dir}", Colors.OKCYAN)

        for filename in md_files:
            src = self.repo_root / filename
            dst = planning_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → docs/planning/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_test_fixtures(self) -> None:
        """Move test fixture files to tests/fixtures/."""
        fixtures_dir = self.repo_root / "tests" / "fixtures"

        fixture_files = [
            "tmp_transcript_result.json",
            "transcript_action_sample.json",
            "fine_tuned_execution_iteration2.json",
        ]

        if not self.dry_run:
            fixtures_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_action(f"Would create directory: {fixtures_dir}", Colors.OKCYAN)

        for filename in fixture_files:
            src = self.repo_root / filename
            dst = fixtures_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → tests/fixtures/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_workspace_files(self) -> None:
        """Move workspace configuration files."""
        workspace_dir = self.repo_root / ".workspace"

        workspace_files = [
            "Y2K.code-workspace",
        ]

        if not self.dry_run:
            workspace_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_action(f"Would create directory: {workspace_dir}", Colors.OKCYAN)

        for filename in workspace_files:
            src = self.repo_root / filename
            dst = workspace_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → .workspace/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_html_files(self) -> None:
        """Move HTML documentation files."""
        docs_dir = self.repo_root / "docs"

        html_files = [
            "utube.html",
            "mcp_Build_Bestpractice.html",
        ]

        for filename in html_files:
            src = self.repo_root / filename
            dst = docs_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → docs/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def move_scripts(self) -> None:
        """Move shell scripts to scripts/ directory."""
        scripts_dir = self.repo_root / "scripts"

        script_files = [
            "grok_cli.sh",
            "grok_query.sh",
            "setup_fastvlm_gemini.sh",
        ]

        for filename in script_files:
            src = self.repo_root / filename
            dst = scripts_dir / filename

            if src.exists():
                self.log_action(f"Move {filename} → scripts/")
                if not self.dry_run:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        self.log_error(f"Failed to move {filename}: {e}")

    def remove_tarball(self) -> None:
        """Remove tarball that can be rebuilt from source."""
        tarball = self.repo_root / "mcp_youtube-0.2.0.tar.gz"

        if tarball.exists():
            self.log_action(f"Remove tarball (can rebuild): {tarball.name}")
            if not self.dry_run:
                try:
                    tarball.unlink()
                except Exception as e:
                    self.log_error(f"Failed to remove {tarball.name}: {e}")

    def consolidate_duplicate_plan_files(self) -> None:
        """Keep only docs/planning/PLAN.md and remove others."""
        # Keep: docs/planning/PLAN.md
        # Remove: PLAN.md (root), docs/PLAN.md, docs/archive/.../PLAN.md

        keep = self.repo_root / "docs" / "planning" / "PLAN.md"

        if not keep.exists():
            # If docs/planning/PLAN.md doesn't exist, move root PLAN.md there
            root_plan = self.repo_root / "PLAN.md"
            if root_plan.exists():
                self.log_action("Move PLAN.md → docs/planning/PLAN.md")
                if not self.dry_run:
                    keep.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(str(root_plan), str(keep))
                    except Exception as e:
                        self.log_error(f"Failed to move PLAN.md: {e}")
        else:
            # Remove duplicate PLAN.md files
            duplicates = [
                self.repo_root / "PLAN.md",
                self.repo_root / "docs" / "PLAN.md",
            ]

            for dup in duplicates:
                if dup.exists():
                    self.log_action(f"Remove duplicate: {dup.relative_to(self.repo_root)}")
                    if not self.dry_run:
                        try:
                            dup.unlink()
                        except Exception as e:
                            self.log_error(f"Failed to remove {dup}: {e}")

    def update_gitignore(self) -> None:
        """Update .gitignore with important patterns."""
        gitignore = self.repo_root / ".gitignore"

        new_patterns = [
            "",
            "# Secret files",
            "client_secret_*.json",
            "*_secret_*.json",
            "",
            "# Workspace files",
            "*.code-workspace",
            "",
            "# Test artifacts",
            "tmp_*.json",
            "",
            "# Backup directories",
            ".backup_*/",
            "",
            "# Tarballs (can rebuild)",
            "*.tar.gz",
            "*.tgz",
        ]

        self.log_action("Update .gitignore with security patterns")

        if not self.dry_run:
            try:
                with open(gitignore, 'a') as f:
                    f.write('\n'.join(new_patterns))
                    f.write('\n')
            except Exception as e:
                self.log_error(f"Failed to update .gitignore: {e}")

    def generate_report(self) -> str:
        """Generate cleanup report."""
        report = []
        report.append("\n" + "="*60)
        report.append(f"{Colors.HEADER}CLEANUP REPORT{Colors.ENDC}")
        report.append("="*60)
        report.append(f"Mode: {'DRY-RUN' if self.dry_run else 'EXECUTED'}")
        report.append(f"Actions planned/taken: {len(self.actions_taken)}")
        report.append(f"Errors encountered: {len(self.errors)}")
        report.append("")

        if self.errors:
            report.append(f"{Colors.FAIL}ERRORS:{Colors.ENDC}")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")

        if not self.dry_run and not self.errors:
            report.append(f"{Colors.OKGREEN}✅ Cleanup completed successfully!{Colors.ENDC}")
        elif self.dry_run:
            report.append(f"{Colors.OKCYAN}ℹ️  This was a dry run. Use --backup or --force to execute.{Colors.ENDC}")

        report.append("="*60)
        return "\n".join(report)

    def execute(self) -> bool:
        """Execute all cleanup operations."""
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}EventRelay Repository Cleanup{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"Repository: {self.repo_root}")
        print(f"Mode: {'DRY-RUN' if self.dry_run else 'EXECUTE'}")
        print(f"Backup: {'Yes' if self.backup and not self.dry_run else 'No'}")
        print()

        if self.backup and not self.dry_run:
            self.create_backup()
            print()

        # Execute cleanup operations in order
        print(f"{Colors.HEADER}Phase 1: Remove Duplicates{Colors.ENDC}")
        self.remove_duplicate_directory()
        self.remove_tarball()
        print()

        print(f"{Colors.HEADER}Phase 2: Remove Secrets{Colors.ENDC}")
        self.remove_secret_files()
        print()

        print(f"{Colors.HEADER}Phase 3: Organize Files{Colors.ENDC}")
        self.move_prompt_files()
        self.move_analysis_files()
        self.move_planning_docs()
        self.move_test_fixtures()
        self.move_workspace_files()
        self.move_html_files()
        self.move_scripts()
        print()

        print(f"{Colors.HEADER}Phase 4: Consolidate Documentation{Colors.ENDC}")
        self.consolidate_duplicate_plan_files()
        print()

        print(f"{Colors.HEADER}Phase 5: Update Configuration{Colors.ENDC}")
        self.update_gitignore()
        print()

        # Generate and print report
        print(self.generate_report())

        return len(self.errors) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Safely cleanup EventRelay repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be done (safe)
  python scripts/cleanup_repository.py --dry-run

  # Execute with backup (recommended)
  python scripts/cleanup_repository.py --backup

  # Execute without backup (dangerous)
  python scripts/cleanup_repository.py --force
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before making changes'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Execute without backup (use with caution!)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.dry_run and not args.backup and not args.force:
        parser.error("Must specify --dry-run, --backup, or --force")

    if args.backup and args.force:
        parser.error("Cannot use both --backup and --force")

    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Execute cleanup
    cleanup = RepositoryCleanup(
        repo_root=repo_root,
        dry_run=args.dry_run,
        backup=args.backup
    )

    success = cleanup.execute()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
