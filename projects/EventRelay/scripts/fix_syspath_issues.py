#!/usr/bin/env python3
"""
Phase 1.2: Fix Active sys.path Manipulations
Removes remaining active sys.path manipulations from core files
"""

import re
from pathlib import Path

def fix_syspath_in_file(file_path: Path) -> bool:
    """Remove active sys.path manipulations from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Remove active sys.path.insert and sys.path.append lines
        patterns = [
            r'^\s*sys\.path\.insert\(.*?\)\s*$',
            r'^\s*sys\.path\.append\(.*?\)\s*$',
            r'^\s*sys\.path\.extend\(.*?\)\s*$',
            r'^\s*sys\.path\.remove\(.*?\)\s*$'
        ]

        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)

        # Clean up empty lines that might be left behind
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False

def main():
    project_root = Path(__file__).resolve().parent.parent

    # Files identified in Phase 1.1 analysis with active sys.path issues
    files_to_fix = [
        project_root / "test_100_videos.py",
        project_root / "gap_fixing_workflow.py",
        project_root / "start_enhanced_backend.py",
        project_root / "scripts/batch_process.py",
        project_root / "scripts/enhanced_continuous_runner.py",
        project_root / "scripts/test_live_deployment.py",
        project_root / "scripts/continuous_runner.py",
        project_root / "src/youtube_extension/backend/main.py",
        project_root / "src/youtube_extension/backend/main_v2.py",
        project_root / "src/youtube_extension/backend/real_video_processor.py",
        project_root / "src/youtube_extension/backend/test_real_pipeline.py",
        project_root / "src/youtube_extension/backend/deployment_manager.py",
        project_root / "src/youtube_extension/backend/http_server.py",
        project_root / "src/youtube_extension/backend/main_refactored.py",
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if file_path.exists():
            if fix_syspath_in_file(file_path):
                print(f"Fixed sys.path issues in {file_path.name}")
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")

    print(f"\nCompleted Phase 1.2: Fixed {fixed_count} files")

    return fixed_count > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
