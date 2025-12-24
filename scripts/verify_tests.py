#!/usr/bin/env python3
"""Verify test consistency for REAL FILE OPERATIONS"""

import re
from pathlib import Path

def check_test_consistency():
    """Check for test data consistency issues"""
    test_files = list(Path("tests").glob("*.py"))
    issues = []
    
    for test_file in test_files:
        try:
            content = test_file.read_text()
            
            # Skip the old mock test file
            if "old_mock" in str(test_file):
                continue
            
            # Check for banned video IDs (but allow auJzb1D-fag)
            banned_ids = ["dQw4w9WgXcQ", "rickroll", "TEST123456A"]
            for banned_id in banned_ids:
                if banned_id in content:
                    issues.append(f"{test_file}: Contains banned video ID '{banned_id}'")
            
            # Ensure auJzb1D-fag is used as the standard test ID
            if "video_id=" in content and "auJzb1D-fag" not in content:
                issues.append(f"{test_file}: Should use 'auJzb1D-fag' as the standard test video ID")
            
            # Check for banned mock/fake systems
            banned_mocks = ["pyfakefs", "Patcher", "fake_filesystem", "mock"]
            for banned_mock in banned_mocks:
                if banned_mock in content and "old_mock" not in str(test_file):
                    issues.append(f"{test_file}: Contains banned mock/fake system '{banned_mock}'")
            
            # Ensure real file operations are used
            if "tempfile" not in content and "test_" in str(test_file) and "old_mock" not in str(test_file):
                issues.append(f"{test_file}: Should use tempfile for real file operations")
            
            # Check for video ID consistency
            video_ids = re.findall(r'video_id="([^"]+)"', content)
            # Fix regex to properly match assertion patterns
            assertions = re.findall(r'assert.*video_id.*==.*"([^"]+)"', content, re.MULTILINE)
            
            if video_ids and assertions:
                unique_video_ids = set(video_ids)
                unique_assertions = set(assertions)
                
                if unique_video_ids != unique_assertions:
                    issues.append(f"{test_file}: Video ID mismatch - Data uses {unique_video_ids}, assertions expect {unique_assertions}")
                    
        except Exception as e:
            issues.append(f"{test_file}: Error reading file - {e}")
    
    return issues

def check_project_structure():
    """Check for proper project structure"""
    issues = []
    
    # Check for loose Python files in root
    root_py_files = [f for f in Path(".").glob("*.py") if f.name not in ["setup.py", "manage.py"]]
    if root_py_files:
        issues.append(f"Loose Python files in root: {[f.name for f in root_py_files]}")
    
    # Check for essential directories
    required_dirs = ["src/youtube_extension", "tests", "scripts"]
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Missing required directory: {dir_path}")
    
    return issues

def main():
    """Run all consistency checks"""
    print("🔍 Running REAL FILE test consistency checks...")
    print("✅ No mock/fake filesystems allowed")
    print("✅ Using real temporary directories")
    print("")
    
    test_issues = check_test_consistency()
    structure_issues = check_project_structure()
    
    all_issues = test_issues + structure_issues
    
    if all_issues:
        print("❌ Issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✅ All REAL FILE consistency checks passed!")
        print("🎯 Tests use tempfile and shutil for isolation")
        print("🧹 No mock/fake systems detected")
        return 0

if __name__ == "__main__":
    exit(main())
