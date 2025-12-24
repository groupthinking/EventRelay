#!/usr/bin/env python3
"""
Update timeout configurations to prevent Chrome from closing after 5 minutes.
This script updates all 300-second (5-minute) timeouts to 7200 seconds (2 hours).
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Define files and their timeout patterns
TIMEOUT_CONFIGS = [
    {
        'file': 'config/llama_agent_config.json',
        'type': 'json',
        'paths': [
            ['llama_agent', 'processing', 'timeout'],
            ['llama_agent', 'performance', 'resource_limits', 'max_processing_time']
        ]
    },
    {
        'file': 'src/youtube_extension/backend/middleware/error_handling_middleware.py',
        'type': 'python',
        'pattern': r'timeout_seconds:\s*float\s*=\s*300\.0',
        'replacement': 'timeout_seconds: float = 7200.0'
    },
    {
        'file': 'scripts/enterprise_mcp_server.py',
        'type': 'python',
        'pattern': r'max_timeout_seconds:\s*int\s*=\s*300',
        'replacement': 'max_timeout_seconds: int = 7200'
    }
]

def backup_file(filepath: Path) -> Path:
    """Create a backup of the file before modification."""
    backup_path = filepath.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}{filepath.suffix}')
    backup_path.write_text(filepath.read_text())
    return backup_path

def update_json_file(filepath: Path, paths: List[List[str]], new_value: int = 7200) -> bool:
    """Update JSON file with new timeout values."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        updated = False
        for path in paths:
            current = data
            for key in path[:-1]:
                if key in current:
                    current = current[key]
                else:
                    break
            else:
                if path[-1] in current and current[path[-1]] == 300:
                    current[path[-1]] = new_value
                    updated = True
                    print(f"  ✅ Updated {'.'.join(path)}: 300 → {new_value}")
        
        if updated:
            with open(filepath, 'w') as f:
                json.dump(data, json.dumps(data, indent=2))
        
        return updated
    except Exception as e:
        print(f"  ❌ Error updating JSON: {e}")
        return False

def update_python_file(filepath: Path, pattern: str, replacement: str) -> bool:
    """Update Python file with new timeout values."""
    try:
        content = filepath.read_text()
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            filepath.write_text(new_content)
            print(f"  ✅ Updated timeout: 300 → 7200")
            return True
        else:
            print(f"  ℹ️  Pattern not found or already updated")
            return False
    except Exception as e:
        print(f"  ❌ Error updating Python file: {e}")
        return False

def main():
    print("🔧 Updating Timeout Configurations")
    print("=" * 50)
    print("This script will update all 5-minute (300 second) timeouts")
    print("to 2 hours (7200 seconds) to prevent Chrome from closing.")
    print("")
    
    base_path = Path.cwd()
    updated_files = []
    
    for config in TIMEOUT_CONFIGS:
        filepath = base_path / config['file']
        
        print(f"📁 Processing: {config['file']}")
        
        if not filepath.exists():
            print(f"  ⚠️  File not found, skipping")
            continue
        
        # Create backup
        backup_path = backup_file(filepath)
        print(f"  📋 Backup created: {backup_path.name}")
        
        # Update file
        if config['type'] == 'json':
            success = update_json_file(filepath, config['paths'])
        elif config['type'] == 'python':
            success = update_python_file(filepath, config['pattern'], config['replacement'])
        else:
            print(f"  ❌ Unknown file type: {config['type']}")
            success = False
        
        if success:
            updated_files.append(str(filepath))
        
        print("")
    
    # Summary
    print("=" * 50)
    print("📊 Summary")
    print(f"  Files updated: {len(updated_files)}")
    
    if updated_files:
        print("\n  Modified files:")
        for f in updated_files:
            print(f"    - {f}")
    
    print("\n✅ Configuration update complete!")
    print("\n📝 Next steps:")
    print("  1. Restart any running services to apply changes")
    print("  2. Test Chrome browser stays open past 5 minutes")
    print("  3. If issues persist, check BROWSER_TIMEOUT_FIX.md")
    
    # Create a summary file
    summary = {
        'timestamp': datetime.now().isoformat(),
        'updated_files': updated_files,
        'backup_created': True,
        'new_timeout_seconds': 7200,
        'old_timeout_seconds': 300
    }
    
    summary_file = base_path / 'timeout_update_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
