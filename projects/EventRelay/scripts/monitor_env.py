#!/usr/bin/env python3
"""
Environment File Monitor
========================

Monitors .env file for changes and automatically validates configuration.
Useful during development when API keys are being added/updated.

This script uses the watchdog library if available, otherwise falls back
to polling-based monitoring.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Try to import watchdog for efficient file monitoring
WATCHDOG_AVAILABLE = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    # Define a dummy class for when watchdog is not available
    class FileSystemEventHandler:
        pass

# Import our validator
sys.path.insert(0, str(Path(__file__).parent))
from validate_env import EnvValidator

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


class EnvFileHandler(FileSystemEventHandler):
    """Handles .env file change events"""
    
    def __init__(self, env_path: Path, validator: EnvValidator):
        self.env_path = env_path
        self.validator = validator
        self.last_modified = 0
        
    def on_modified(self, event):
        """Called when any file in the directory is modified"""
        if not event.is_directory and event.src_path == str(self.env_path):
            # Debounce - ignore if modified within last second
            current_time = time.time()
            if current_time - self.last_modified < 1:
                return
            
            self.last_modified = current_time
            self.handle_change()
    
    def handle_change(self):
        """Handle .env file change"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{BLUE}[{timestamp}] .env file changed. Validating...{RESET}")
        
        # Run validation
        self.validator = EnvValidator(self.env_path)
        is_valid = self.validator.validate_all()
        
        # Print results
        if is_valid:
            print(f"{GREEN}✅ Configuration is valid{RESET}")
        else:
            print(f"{RED}❌ Configuration has issues{RESET}")
            
        # Print summary
        if self.validator.errors:
            print(f"{RED}Errors: {len(self.validator.errors)}{RESET}")
        if self.validator.warnings:
            print(f"{YELLOW}Warnings: {len(self.validator.warnings)}{RESET}")


class PollingMonitor:
    """Fallback polling-based monitor when watchdog is not available"""
    
    def __init__(self, env_path: Path, validator: EnvValidator, interval: int = 2):
        self.env_path = env_path
        self.validator = validator
        self.interval = interval
        self.last_mtime = 0
        
        if self.env_path.exists():
            self.last_mtime = self.env_path.stat().st_mtime
    
    def check_changes(self):
        """Check if file has been modified"""
        if not self.env_path.exists():
            return
        
        current_mtime = self.env_path.stat().st_mtime
        if current_mtime != self.last_mtime:
            self.last_mtime = current_mtime
            self.handle_change()
    
    def handle_change(self):
        """Handle .env file change"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{BLUE}[{timestamp}] .env file changed. Validating...{RESET}")
        
        # Run validation
        self.validator = EnvValidator(self.env_path)
        is_valid = self.validator.validate_all()
        
        # Print compact results
        if is_valid:
            print(f"{GREEN}✅ Configuration is valid{RESET}")
        else:
            print(f"{RED}❌ Configuration has issues{RESET}")
            
        # Print summary
        if self.validator.errors:
            print(f"{RED}Errors: {len(self.validator.errors)}{RESET}")
            for error in self.validator.errors:
                print(f"{RED}  • {error}{RESET}")
        if self.validator.warnings:
            print(f"{YELLOW}Warnings: {len(self.validator.warnings)}{RESET}")
    
    def run(self):
        """Start polling loop"""
        print(f"{BLUE}Monitoring {self.env_path} (polling every {self.interval}s){RESET}")
        print(f"{YELLOW}Press Ctrl+C to stop{RESET}\n")
        
        try:
            while True:
                self.check_changes()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Monitoring stopped{RESET}")


def monitor_with_watchdog(env_path: Path, validator: EnvValidator):
    """Use watchdog for efficient file monitoring"""
    event_handler = EnvFileHandler(env_path, validator)
    observer = Observer()
    observer.schedule(event_handler, str(env_path.parent), recursive=False)
    observer.start()
    
    print(f"{GREEN}✓ Started monitoring {env_path}{RESET}")
    print(f"{YELLOW}Press Ctrl+C to stop{RESET}\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print(f"\n{YELLOW}Monitoring stopped{RESET}")
    
    observer.join()


def main():
    """Main monitoring entry point"""
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}🔍 Environment Configuration Monitor{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
    
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    
    # Check if .env exists
    if not env_path.exists():
        print(f"{RED}❌ .env file not found at {env_path}{RESET}")
        print(f"\nCreate it first:")
        print(f"  cp .env.example .env")
        print(f"  # OR")
        print(f"  python3 scripts/setup_env.py")
        return 1
    
    # Initial validation
    print(f"Running initial validation...\n")
    validator = EnvValidator(env_path)
    validator.validate_all()
    validator.print_results()
    
    # Start monitoring
    print(f"{BOLD}Starting file monitor...{RESET}\n")
    
    if WATCHDOG_AVAILABLE:
        monitor_with_watchdog(env_path, validator)
    else:
        print("⚠️  watchdog not installed. Using polling mode.")
        print("   Install for better performance: pip install watchdog\n")
        monitor = PollingMonitor(env_path, validator)
        monitor.run()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"{RED}Monitor failed: {e}{RESET}")
        sys.exit(1)
