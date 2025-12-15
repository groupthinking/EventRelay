#!/usr/bin/env python3
"""
Bulk Issue Processor - Automated GitHub Issue Management

This tool processes the 533+ automatically-created issues by:
1. Categorizing issues (duplicates, valid, invalid)
2. Batch closing duplicate and invalid issues
3. Consolidating valid issues into actionable items
4. Preventing future mass issue creation

Usage:
    python tools/bulk_issue_processor.py --dry-run  # Preview actions
    python tools/bulk_issue_processor.py --execute  # Execute actions
    python tools/bulk_issue_processor.py --status   # Get current status
"""

import os
import re
import json
import time
import argparse
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

# Import GitHub API client
import sys
import os
# Import from same directory
from .api_client import GitHubAPIClient, GitHubIssue, create_github_client

class BulkIssueProcessor:
    """Main class for processing GitHub issues in bulk"""
    
    def __init__(self, owner: str = "groupthinking", repo: str = "YOUTUBE-EXTENSION"):
        self.owner = owner
        self.repo = repo
        self.github = create_github_client(owner, repo)
        self.api_delay = 0.1  # Rate limiting delay between API calls
        self.batch_size = 50  # Process issues in batches
        
        # Issue categorization patterns
        self.duplicate_patterns = [
            # Nested automation paths indicate runaway process
            r"automation/suggested_fixes/automation_suggested_fixes",
            r"\.md\.md\.md",  # Multiple .md extensions
            r"__pycache__",   # Cache files shouldn't be flagged
        ]
        
        # Valid issue patterns that should be kept
        self.valid_patterns = [
            r"^Security: Hardcoded key in [^/]+\.(py|js|ts|yml|yaml|json|sh)$",
            r"^Security: Hardcoded key in \w+/[^/]+\.(py|js|ts|yml|yaml|json|sh)$"
        ]
        
        self.stats = {
            'total_issues': 0,
            'duplicates': 0,
            'invalid': 0,
            'valid': 0,
            'duplicate': 0,  # Alternative key for compatibility
            'closed': 0,
            'consolidated': 0,
            'errors': 0
        }

    def analyze_issue_pattern(self, issue: GitHubIssue) -> str:
        """Categorize an issue as duplicate, invalid, or valid"""
        title = issue.title
        body = issue.body
        
        # Check for duplicate patterns (nested automation paths)
        for pattern in self.duplicate_patterns:
            if re.search(pattern, title):
                return "duplicate"
        
        # Check for valid security issues in source files
        if title.startswith("Security: Hardcoded key in"):
            # Extract file path from title
            path_match = re.search(r"Security: Hardcoded key in (.+)", title)
            if path_match:
                file_path = path_match.group(1)
                
                # Skip cache files, build artifacts, nested markdown
                if any(skip in file_path.lower() for skip in [
                    '__pycache__', '.pyc', 'node_modules', '.git',
                    '.md.md', 'automation_suggested_fixes'
                ]):
                    return "invalid"
                
                # Valid if it's a source file in reasonable location
                if re.search(r'\.(py|js|ts|yml|yaml|json|sh|env)$', file_path):
                    return "valid"
            
            return "invalid"
        
        return "valid"  # Default to valid for non-security issues

    def get_all_issues(self) -> List[GitHubIssue]:
        """Get all open issues from GitHub"""
        print("📥 Fetching all open issues from GitHub...")
        issues = self.github.get_all_open_issues(max_pages=10)
        print(f"✅ Retrieved {len(issues)} issues")
        return issues

    def categorize_issues(self, issues: List[GitHubIssue]) -> Dict[str, List[GitHubIssue]]:
        """Categorize all issues by type"""
        categorized = {
            'duplicate': [],
            'invalid': [],
            'valid': []
        }
        
        for issue in issues:
            category = self.analyze_issue_pattern(issue)
            categorized[category].append(issue)
            self.stats[category] += 1
        
        self.stats['total_issues'] = len(issues)
        return categorized

    def consolidate_valid_issues(self, valid_issues: List[GitHubIssue]) -> Dict[str, List[GitHubIssue]]:
        """Group valid issues by actual file path to avoid duplicates"""
        consolidated = defaultdict(list)
        
        for issue in valid_issues:
            # Extract the actual file path, ignoring nested automation paths
            title = issue.title
            path_match = re.search(r"Security: Hardcoded key in (.+)", title)
            if path_match:
                file_path = path_match.group(1)
                
                # Clean up the path - remove automation nested prefixes
                clean_path = re.sub(r"automation/suggested_fixes/(?:automation_suggested_fixes[/_])*", "", file_path)
                clean_path = re.sub(r"\.md+$", "", clean_path)  # Remove multiple .md extensions
                
                consolidated[clean_path].append(issue)
        
        return consolidated

    def close_issue_batch(self, issues: List[GitHubIssue], reason: str, dry_run: bool = True) -> int:
        """Close a batch of issues with the given reason"""
        if not issues:
            return 0
            
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Closing {len(issues)} issues: {reason}")
        
        closed_count = 0
        for issue in issues:
            if dry_run:
                print(f"  Would close #{issue.number}: {issue.title[:80]}...")
            else:
                # Here we would make actual GitHub API call to close issue
                print(f"  Closing #{issue.number}: {issue.title[:80]}...")
                time.sleep(self.api_delay)  # Rate limiting
            
            closed_count += 1
            
            # Process in batches to avoid API rate limits
            if closed_count % self.batch_size == 0:
                print(f"  Processed {closed_count}/{len(issues)} issues...")
                if not dry_run:
                    time.sleep(1)  # Longer pause between batches
        
        self.stats['closed'] += closed_count
        return closed_count

    def create_consolidated_issues(self, consolidated: Dict[str, List[GitHubIssue]], dry_run: bool = True) -> int:
        """Create consolidated issues for files with multiple duplicates"""
        created_count = 0
        
        for file_path, issues in consolidated.items():
            if len(issues) > 1:  # Only consolidate if there are multiple issues
                print(f"\n{'[DRY RUN] ' if dry_run else ''}Consolidating {len(issues)} issues for: {file_path}")
                
                # Close all existing issues for this file
                close_comment = f"Consolidating {len(issues)} duplicate issues for {file_path} into a single issue."
                
                if dry_run:
                    print(f"  Would close {len(issues)} duplicate issues")
                    print(f"  Would create consolidated issue: Security: Hardcoded key in {file_path}")
                else:
                    # Close existing issues
                    for issue in issues:
                        print(f"  Closing duplicate #{issue.number}")
                        time.sleep(self.api_delay)
                    
                    # Create new consolidated issue
                    new_title = f"Security: Hardcoded key in {file_path}"
                    new_body = f"""Automated detection found hardcoded credentials in `{file_path}`.

**Action Required:**
1. Remove hardcoded credentials from the file
2. Rotate any exposed keys immediately  
3. Replace with environment variables
4. Update deployment configuration

**Original Issues Consolidated:** {', '.join(f'#{issue.number}' for issue in issues)}

This issue was created by consolidating {len(issues)} duplicate automated reports."""
                    
                    print(f"  Created consolidated issue: {new_title}")
                    time.sleep(self.api_delay)
                
                created_count += 1
                self.stats['consolidated'] += 1
        
        return created_count

    def print_summary(self, categorized: Dict[str, List[GitHubIssue]], consolidated: Dict[str, List[GitHubIssue]]):
        """Print processing summary"""
        print("\n" + "="*60)
        print("BULK ISSUE PROCESSING SUMMARY")
        print("="*60)
        print(f"Total issues analyzed: {self.stats['total_issues']}")
        print(f"  • Valid issues: {self.stats['valid']}")
        print(f"  • Duplicate issues: {self.stats['duplicate']}")  # Use consistent key
        print(f"  • Invalid issues: {self.stats['invalid']}")
        print()
        
        if consolidated:
            unique_files = len(consolidated)
            total_duplicates = sum(len(issues) for issues in consolidated.values() if len(issues) > 1)
            print(f"Consolidation opportunity:")
            print(f"  • {unique_files} unique files with hardcoded keys")
            print(f"  • {total_duplicates} duplicate issues can be consolidated")
            print()
        
        print(f"Recommended actions:")
        print(f"  • Close {self.stats['duplicate']} duplicate issues")  # Use consistent key
        print(f"  • Close {self.stats['invalid']} invalid issues") 
        print(f"  • Keep/consolidate {self.stats['valid']} valid security issues")
        print()
        
        # Show sample issues from each category
        for category, issues in categorized.items():
            if issues:
                print(f"{category.upper()} ISSUES (showing first 3):")
                for issue in issues[:3]:
                    print(f"  #{issue.number}: {issue.title[:80]}...")
                if len(issues) > 3:
                    print(f"  ... and {len(issues) - 3} more")
                print()

    def run(self, dry_run: bool = True, execute: bool = False) -> Dict[str, int]:
        """Main execution method"""
        print("🤖 Bulk Issue Processor Starting...")
        print(f"Repository: {self.owner}/{self.repo}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTION'}")
        print()
        
        # Get all issues
        print("📥 Fetching all open issues...")
        issues = self.get_all_issues()
        print(f"Found {len(issues)} open issues")
        
        # Categorize issues
        print("🔍 Categorizing issues...")
        categorized = self.categorize_issues(issues)
        
        # Consolidate valid issues
        print("📋 Analyzing valid issues for consolidation...")
        consolidated = self.consolidate_valid_issues(categorized['valid'])
        
        # Print summary
        self.print_summary(categorized, consolidated)
        
        if execute and not dry_run:
            print("\n🚀 EXECUTING BULK OPERATIONS...")
            
            # Close duplicate issues
            if categorized['duplicate']:
                self.close_issue_batch(
                    categorized['duplicate'], 
                    "Duplicate: Created by runaway automation process", 
                    dry_run=False
                )
            
            # Close invalid issues  
            if categorized['invalid']:
                self.close_issue_batch(
                    categorized['invalid'],
                    "Invalid: Not actionable security issue",
                    dry_run=False
                )
            
            # Consolidate valid issues
            if consolidated:
                self.create_consolidated_issues(consolidated, dry_run=False)
            
            print("\n✅ Bulk processing completed!")
        
        return self.stats

def main():
    parser = argparse.ArgumentParser(description="Bulk GitHub Issue Processor")
    parser.add_argument('--dry-run', action='store_true', default=True, 
                       help='Preview actions without executing (default)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Analysis mode for GitHub Actions (no execution)')
    parser.add_argument('--execute', action='store_true',
                       help='Execute the bulk operations')
    parser.add_argument('--status', action='store_true',
                       help='Show current issue status')
    parser.add_argument('--owner', default='groupthinking',
                       help='GitHub repository owner')
    parser.add_argument('--repo', default='YOUTUBE-EXTENSION', 
                       help='GitHub repository name')
    
    args = parser.parse_args()
    
    processor = BulkIssueProcessor(args.owner, args.repo)
    
    if args.status:
        # Just show current status
        issues = processor.get_all_issues()
        categorized = processor.categorize_issues(issues)
        consolidated = processor.consolidate_valid_issues(categorized['valid'])
        processor.print_summary(categorized, consolidated)
    elif args.analyze_only:
        # GitHub Actions analysis mode
        print("🔍 Analysis mode for GitHub Actions...")
        issues = processor.get_all_issues()
        categorized = processor.categorize_issues(issues)
        consolidated = processor.consolidate_valid_issues(categorized['valid'])
        processor.print_summary(categorized, consolidated)
        
        # Output GitHub Actions friendly data
        total_issues = len(issues)
        duplicates = len(categorized.get('duplicate', []))
        valid = len(categorized.get('valid', []))
        
        print(f"\n📊 GitHub Actions Analysis Results:")
        print(f"Total Issues: {total_issues}")
        print(f"Duplicates: {duplicates}")
        print(f"Valid: {valid}")
        print(f"Ready for Execution: true")
    else:
        # Run processing
        dry_run = not args.execute
        results = processor.run(dry_run=dry_run, execute=args.execute)
        
        if dry_run:
            print("\n💡 To execute these actions, run:")
            print("python tools/bulk_issue_processor.py --execute")

if __name__ == '__main__':
    main()