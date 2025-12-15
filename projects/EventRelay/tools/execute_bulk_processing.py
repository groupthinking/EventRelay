#!/usr/bin/env python3
"""
BULK ISSUE EXECUTION TRIGGER

This script provides a simple interface to trigger the automated bulk issue processing.
It can be run manually or integrated with other automation systems.

Usage:
  python tools/execute_bulk_processing.py --dry-run     # Safe preview
  python tools/execute_bulk_processing.py --execute    # Live execution
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime


def run_command(command: list, description: str) -> tuple[bool, str]:
    """Run a command and return success status and output"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=300  # 5 minute timeout
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Command failed: {e.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 5 minutes"


def main():
    parser = argparse.ArgumentParser(
        description="Trigger automated bulk issue processing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true',
                      help='Run analysis only (safe preview)')
    group.add_argument('--execute', action='store_true', 
                      help='Execute bulk processing (requires confirmation)')
    
    args = parser.parse_args()
    
    print("🤖 BULK ISSUE PROCESSING TRIGGER")
    print("=" * 50)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTION'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.dry_run:
        # Run safe analysis
        success, output = run_command([
            'python', 'tools/bulk_issue_processor.py', '--analyze-only'
        ], "Running safe analysis")
        
        if success:
            print("✅ Analysis completed successfully!")
            print("\nOutput:")
            print(output)
        else:
            print("❌ Analysis failed!")
            print(f"Error: {output}")
            sys.exit(1)
            
    else:
        # Execute mode with confirmation
        print("⚠️  WARNING: This will make permanent changes to GitHub issues!")
        print("This action will:")
        print("- Close 500+ duplicate issues created by runaway automation")
        print("- Add explanatory comments to all closed issues")
        print("- Preserve legitimate security issues for manual review")
        print()
        
        confirm = input("Type 'EXECUTE_BULK_PROCESSING' to confirm: ")
        if confirm != 'EXECUTE_BULK_PROCESSING':
            print("❌ Confirmation failed. Cancelled for safety.")
            sys.exit(1)
        
        print("\n🚀 Executing automated bulk processing...")
        
        # Use the GitHub Actions script for actual execution
        success, output = run_command([
            'python', '.github/workflows/scripts/automated_bulk_processor.py'
        ], "Executing bulk issue processing")
        
        if success:
            print("✅ Bulk processing completed successfully!")
            print("\nOutput:")
            print(output)
        else:
            print("❌ Bulk processing failed!")
            print(f"Error: {output}")
            sys.exit(1)
    
    print(f"\n🎉 Process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()