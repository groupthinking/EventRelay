#!/usr/bin/env python3
"""
File System Watcher for Claude Code Changes
==========================================
Monitors project files and automatically validates changes made by Claude Code.
"""

import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ClaudeCodeValidator(FileSystemEventHandler):
    """Validates files modified by Claude Code"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.last_validation = 0
        self.validation_cooldown = 2  # seconds
        
    def on_modified(self, event):
        """Called when files are modified"""
        if event.is_directory:
            return
            
        # Avoid spam validation
        current_time = time.time()
        if current_time - self.last_validation < self.validation_cooldown:
            return
            
        self.last_validation = current_time
        
        # Check if it's a Python file or test file
        file_path = Path(event.src_path)
        if file_path.suffix in ['.py', '.md'] or 'test' in file_path.name:
            print(f"🔍 Validating changes to: {file_path.relative_to(self.project_root)}")
            self.validate_changes()
    
    def validate_changes(self):
        """Run validation checks"""
        try:
            # Run our test consistency checker
            result = subprocess.run(
                ["python3", "scripts/verify_tests.py"], 
                cwd=self.project_root,
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Claude Code validation passed")
            else:
                print("❌ Claude Code validation failed:")
                print(result.stdout)
                print(result.stderr)
                
                # Optionally auto-fix common issues
                self.attempt_auto_fix()
                
        except Exception as e:
            print(f"Error during validation: {e}")
    
    def attempt_auto_fix(self):
        """Attempt to automatically fix common Claude Code issues"""
        print("🔧 Attempting auto-fix...")
        
        # Check for banned video IDs and suggest fix
        for py_file in self.project_root.glob("**/*.py"):
            if "test" in py_file.name:
                try:
                    content = py_file.read_text()
                    if "dQw4w9WgXcQ" in content:
                        print(f"🔧 Found banned video ID in {py_file}")
                        print("💡 Run: sed -i 's/dQw4w9WgXcQ/auJzb1D-fag/g' " + str(py_file))
                        
                    if "pyfakefs" in content:
                        print(f"🔧 Found banned mock system in {py_file}")
                        print("💡 Convert to real file operations with tempfile")
                        
                except Exception as e:
                    print(f"Error checking {py_file}: {e}")

def main():
    """Start the file system watcher"""
    project_root = Path.cwd()
    
    print("🔍 Claude Code File Watcher")
    print(f"📁 Monitoring: {project_root}")
    print("🎯 Watching for changes...")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    event_handler = ClaudeCodeValidator(project_root)
    observer = Observer()
    
    # Watch specific directories
    watch_dirs = ["tests", "src", "scripts"]
    for watch_dir in watch_dirs:
        if (project_root / watch_dir).exists():
            observer.schedule(event_handler, str(project_root / watch_dir), recursive=True)
            print(f"👁️  Watching: {watch_dir}/")
    
    # Also watch root for new files
    observer.schedule(event_handler, str(project_root), recursive=False)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping file watcher...")
        observer.stop()
    
    observer.join()
    print("✅ File watcher stopped")

if __name__ == "__main__":
    main()
