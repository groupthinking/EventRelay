#!/usr/bin/env python3
"""
GitHub Actions Issue Reporter
============================

Lightweight CLI tool for logging failures in GitHub Actions workflows.
Integrates with the persistent issue tracker for recurrence detection and MCP correlation.
"""

import argparse
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from uvai.api.v1.services.issue_tracker import (
        get_issue_tracker, IssueSeverity, IssueCategory
    )
except ImportError:
    print("❌ Failed to import issue tracker service")
    sys.exit(1)


def detect_github_env() -> Dict[str, Any]:
    """Detect GitHub Actions environment variables"""
    return {k: v for k, v in {
        'run_id': os.getenv('GITHUB_RUN_ID'),
        'job': os.getenv('GITHUB_JOB'),
        'workflow': os.getenv('GITHUB_WORKFLOW'),
    }.items() if v}


def detect_mcp_env() -> Dict[str, Any]:
    """Detect MCP environment variables"""
    return {k: v for k, v in {
        'session_id': os.getenv('MCP_SESSION_ID'),
        'provider': os.getenv('MCP_PROVIDER'),
        'operation': os.getenv('MCP_OPERATION'),
    }.items() if v}


async def report_issue(args: argparse.Namespace) -> int:
    """Report an issue using the issue tracker"""
    try:
        print("🚀 GitHub Actions Issue Reporter")

        github_env = detect_github_env()
        mcp_env = detect_mcp_env()

        if github_env:
            print(f"✅ Detected GitHub: {github_env}")

        if mcp_env:
            print(f"✅ Detected MCP: {mcp_env}")

        # Determine severity and category
        try:
            severity = IssueSeverity(args.severity or 'medium')
        except ValueError:
            severity = IssueSeverity.MEDIUM

        try:
            category = IssueCategory(args.category or 'unknown')
        except ValueError:
            category = IssueCategory.UNKNOWN

        # Get issue tracker
        tracker = await get_issue_tracker()

        # Create issue
        title = args.title or f"GitHub Actions Failure: {github_env.get('job', 'unknown')}"
        description = args.description or "Workflow failure occurred"

        issue_id = await tracker.track_issue(
            title=title,
            description=description,
            error_message=args.error_output or description,
            component=args.component,
            severity=severity,
            category=category,
            mcp_session_id=mcp_env.get('session_id'),
            mcp_provider=mcp_env.get('provider'),
            mcp_operation=mcp_env.get('operation'),
            environment="ci-cd" if github_env else "production"
        )

        print(f"✅ Issue tracked: {issue_id}")

        # Check for recurrence
        issue = await tracker.get_issue(issue_id)
        if issue and issue.recurrence_pattern.occurrence_count > 1:
            print(f"⚠️  Recurring issue ({issue.recurrence_pattern.occurrence_count} occurrences)")

        # GitHub Actions output
        if github_env and 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"issue_id={issue_id}\n")

        return 0

    except Exception as e:
        print(f"❌ Failed to report issue: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="GitHub Actions Issue Reporter")
    parser.add_argument('--title', help='Issue title')
    parser.add_argument('--description', help='Issue description')
    parser.add_argument('--component', required=True, help='Component name')
    parser.add_argument('--severity', choices=['low', 'medium', 'high', 'critical'], help='Issue severity')
    parser.add_argument('--category', choices=['infrastructure', 'api_error', 'processing_error', 'mcp_error', 'configuration_error', 'dependency_error', 'network_error', 'performance_error', 'security_error', 'unknown'], help='Issue category')
    parser.add_argument('--error-output', help='Error output to include')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if not args.title and not args.error_output:
        parser.error("Must provide --title or --error-output")

    exit_code = asyncio.run(report_issue(args))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()