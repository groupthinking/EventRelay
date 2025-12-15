#!/usr/bin/env python3
"""
Revenue Pipeline Prerequisites Checker
=======================================

Validates all prerequisites before running the revenue pipeline test.
Provides clear guidance on missing requirements.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def check_api_keys() -> Tuple[bool, List[str]]:
    """Check if required API keys are set"""
    required_keys = ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']
    optional_keys = ['YOUTUBE_API_KEY', 'ANTHROPIC_API_KEY', 'ASSEMBLYAI_API_KEY']
    
    issues = []
    has_primary_key = False
    
    # Check for at least one primary AI key
    for key in required_keys:
        if os.getenv(key):
            has_primary_key = True
            break
    
    if not has_primary_key:
        issues.append(
            "At least one AI API key required. Set one of:\n"
            "  - GEMINI_API_KEY (recommended)\n"
            "  - GOOGLE_API_KEY\n"
            "  - OPENAI_API_KEY"
        )
    else:
        # Only report optional keys as informational when primary key is set
        optional_status = []
        for key in optional_keys:
            if not os.getenv(key):
                optional_status.append(f"  - {key} (optional, provides enhanced features)")
        
        if optional_status:
            issues.append(
                "Optional API keys not set:\n" + "\n".join(optional_status)
            )
    
    return has_primary_key, issues


def check_python_version() -> Tuple[bool, List[str]]:
    """Check Python version"""
    issues = []
    version_info = sys.version_info
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 9):
        issues.append(f"Python 3.9+ required, found {version_info.major}.{version_info.minor}")
        return False, issues
    
    return True, issues


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if key Python dependencies are installed"""
    issues = []
    required_modules = [
        ('youtube_extension', 'Core package not installed. Run: pip install -e .[dev,youtube,ml]'),
        ('fastapi', 'FastAPI not installed. Run: pip install fastapi'),
        ('aiohttp', 'aiohttp not installed. Run: pip install aiohttp'),
    ]
    
    for module, error_msg in required_modules:
        try:
            __import__(module)
        except ImportError:
            issues.append(error_msg)
    
    return len(issues) == 0, issues


def check_vercel_cli() -> Tuple[bool, List[str]]:
    """Check if Vercel CLI is installed (optional for deployment)"""
    issues = []
    try:
        result = subprocess.run(
            ['vercel', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            issues.append("Vercel CLI not found. Install with: npm i -g vercel (optional for deployment)")
            return False, issues
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("Vercel CLI not found. Install with: npm i -g vercel (optional for deployment)")
        return False, issues
    
    return True, issues


def check_disk_space() -> Tuple[bool, List[str]]:
    """Check available disk space"""
    issues = []
    try:
        # Use current directory for cross-platform compatibility
        check_path = os.getcwd()
        stat = os.statvfs(check_path) if hasattr(os, 'statvfs') else None
        if stat is None:
            # Windows doesn't have statvfs, skip this check
            return True, []
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        
        if available_gb < 2:
            issues.append(f"Low disk space: {available_gb:.2f}GB available. Recommend at least 2GB free.")
            return False, issues
        elif available_gb < 5:
            issues.append(f"Only {available_gb:.2f}GB available. Recommend at least 5GB for full testing.")
    except Exception as e:
        issues.append(f"Could not check disk space: {e}")
    
    return True, issues


def check_env_file() -> Tuple[bool, List[str]]:
    """Check if .env file exists"""
    issues = []
    env_path = Path('.env')
    env_example = Path('.env.example')
    
    if not env_path.exists():
        if env_example.exists():
            issues.append(
                ".env file not found. Create one from example:\n"
                "  cp .env.example .env\n"
                "  # Then edit .env and add your API keys"
            )
        else:
            issues.append(
                ".env file not found. Create one with your API keys:\n"
                "  GEMINI_API_KEY=your_key_here"
            )
        return False, issues
    
    return True, issues


def get_check_title(check_name: str) -> str:
    """Get properly formatted title for check name"""
    titles = {
        'python': 'Python',
        'dependencies': 'Dependencies',
        'api_keys': 'API Keys',
        'env_file': '.env File',
        'vercel_cli': 'Vercel CLI',
        'disk_space': 'Disk Space'
    }
    return titles.get(check_name, check_name.replace('_', ' ').title())


def print_section(title: str, passed: bool, issues: List[str]):
    """Print a check section"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"\n{BOLD}[{status}] {title}{RESET}")
    
    if issues:
        for issue in issues:
            # Handle multi-line issues
            lines = issue.split('\n')
            for i, line in enumerate(lines):
                prefix = "  ⚠️  " if i == 0 else "     "
                print(f"{YELLOW}{prefix}{line}{RESET}")


def print_summary(checks: Dict[str, Tuple[bool, List[str]]]):
    """Print overall summary"""
    critical_checks = ['python', 'dependencies', 'api_keys']
    critical_passed = all(checks[key][0] for key in critical_checks if key in checks)
    
    print(f"\n{'=' * 60}")
    print(f"{BOLD}PREREQUISITE CHECK SUMMARY{RESET}")
    print(f"{'=' * 60}")
    
    for check_name, (passed, _) in checks.items():
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {status} {get_check_title(check_name)}")
    
    print(f"{'=' * 60}\n")
    
    if critical_passed:
        print(f"{GREEN}{BOLD}✓ All critical prerequisites met!{RESET}")
        print(f"\n{BLUE}You can now run the revenue pipeline test:{RESET}")
        print(f"{BOLD}  python3 scripts/test_revenue_pipeline.py{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ Critical prerequisites missing{RESET}")
        print(f"\n{YELLOW}Fix the issues above before running the test.{RESET}\n")
        return False


def print_quick_setup_guide():
    """Print a quick setup guide"""
    print(f"\n{BLUE}{BOLD}QUICK SETUP GUIDE{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")
    print("""
1. Create and activate virtual environment:
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

2. Install dependencies:
   pip install -e .[dev,youtube,ml]

3. Set up environment variables:
   cp .env.example .env
   # Edit .env and add your API keys

4. Run prerequisite check:
   python3 scripts/check_revenue_pipeline_prerequisites.py

5. Run the revenue pipeline test:
   python3 scripts/test_revenue_pipeline.py
""")


def main():
    """Main prerequisite checker"""
    print(f"\n{BOLD}{BLUE}Revenue Pipeline Prerequisites Checker{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    print("Checking system requirements for revenue pipeline testing...\n")
    
    checks = {
        'python': check_python_version(),
        'dependencies': check_dependencies(),
        'api_keys': check_api_keys(),
        'env_file': check_env_file(),
        'vercel_cli': check_vercel_cli(),
        'disk_space': check_disk_space(),
    }
    
    for check_name, (passed, issues) in checks.items():
        print_section(get_check_title(check_name), passed, issues)
    
    success = print_summary(checks)
    
    if not success:
        print_quick_setup_guide()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
