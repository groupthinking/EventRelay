#!/usr/bin/env python3
"""
Interactive .env Setup Helper
=============================

Helps users create and populate their .env file with proper API keys.
Provides guidance on where to obtain each key.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# Import shared constants
sys.path.insert(0, str(Path(__file__).parent))
from env_constants import PLACEHOLDER_VALUES, REQUIRED_AI_KEYS

# ANSI color codes for better UX
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a colored header"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")


# API key configurations with help URLs
API_KEYS = {
    'GEMINI_API_KEY': {
        'name': 'Google Gemini API',
        'url': 'https://aistudio.google.com/app/apikey',
        'required': True,
        'priority': 1,
        'description': 'PRIMARY key for AI analysis and code generation'
    },
    'OPENAI_API_KEY': {
        'name': 'OpenAI API',
        'url': 'https://platform.openai.com/api-keys',
        'required': False,
        'priority': 2,
        'description': 'Alternative AI provider (can use instead of Gemini)'
    },
    'GOOGLE_API_KEY': {
        'name': 'Google API (alias)',
        'url': 'Same as GEMINI_API_KEY',
        'required': False,
        'priority': 3,
        'description': 'Usually set to ${GEMINI_API_KEY}'
    },
    'YOUTUBE_API_KEY': {
        'name': 'YouTube Data API v3',
        'url': 'https://console.cloud.google.com/apis/credentials',
        'required': False,
        'priority': 4,
        'description': 'Optional: Enhanced video metadata extraction'
    },
    'ANTHROPIC_API_KEY': {
        'name': 'Anthropic Claude API',
        'url': 'https://console.anthropic.com/settings/keys',
        'required': False,
        'priority': 5,
        'description': 'Optional: Additional AI provider'
    },
    'ASSEMBLYAI_API_KEY': {
        'name': 'AssemblyAI API',
        'url': 'https://www.assemblyai.com/app/account',
        'required': False,
        'priority': 6,
        'description': 'Optional: Alternative transcription service'
    }
}


def check_existing_env() -> Tuple[bool, Optional[Path]]:
    """Check if .env file already exists"""
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    return env_path.exists(), env_path


def load_existing_env(env_path: Path) -> Dict[str, str]:
    """Load existing environment variables from .env file"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def copy_env_template(project_root: Path) -> bool:
    """Copy .env.example to .env if it doesn't exist"""
    env_example = project_root / '.env.example'
    env_file = project_root / '.env'
    
    if not env_example.exists():
        print_error(f".env.example not found at {env_example}")
        return False
    
    if env_file.exists():
        response = input(f".env already exists. Overwrite? (y/N): ").lower()
        if response != 'y':
            print_warning("Keeping existing .env file")
            return True
    
    with open(env_example, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print_success(f"Created .env from template at {env_file}")
    return True


def get_api_key_input(key_name: str, key_info: dict, existing_value: Optional[str]) -> Optional[str]:
    """Interactively get an API key from the user"""
    print(f"\n{BOLD}{key_info['name']}{RESET}")
    print(f"Description: {key_info['description']}")
    
    if key_info['required']:
        print(f"{RED}Required: Yes{RESET}")
    else:
        print(f"{YELLOW}Required: No (optional){RESET}")
    
    print(f"Get your key from: {BLUE}{key_info['url']}{RESET}")
    
    if existing_value and existing_value not in PLACEHOLDER_VALUES:
        print(f"{GREEN}Current value: {existing_value[:20]}...{RESET}")
        response = input("Keep existing value? (Y/n): ").lower()
        if response != 'n':
            return existing_value
    
    value = input(f"Enter {key_name} (or press Enter to skip): ").strip()
    return value if value else None


def update_env_file(env_path: Path, key: str, value: str):
    """Update a specific key in the .env file"""
    lines = []
    key_found = False
    
    with open(env_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            # Only match uncommented lines
            if stripped and not stripped.startswith('#') and stripped.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                key_found = True
            else:
                lines.append(line)
    
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    with open(env_path, 'w') as f:
        f.writelines(lines)


def main():
    """Main setup flow"""
    print_header("🔑 EventRelay Environment Setup")
    
    # Check project structure
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")
    
    # Check for existing .env
    env_exists, env_path = check_existing_env()
    
    if env_exists:
        print_warning(f".env file already exists at {env_path}")
        response = input("Do you want to update it? (Y/n): ").lower()
        if response == 'n':
            print("Exiting without changes")
            return 0
    else:
        print("No .env file found. Creating from template...")
        if not copy_env_template(project_root):
            return 1
    
    # Load existing values
    existing_env = load_existing_env(env_path)
    
    # Interactive setup
    print_header("📝 API Key Configuration")
    print("Let's set up your API keys. You need at least one AI provider key.")
    print("Press Enter to skip optional keys.\n")
    
    # Sort by priority
    sorted_keys = sorted(API_KEYS.items(), key=lambda x: x[1]['priority'])
    
    updated_keys = []
    has_required = False
    
    for key_name, key_info in sorted_keys:
        existing_value = existing_env.get(key_name)
        new_value = get_api_key_input(key_name, key_info, existing_value)
        
        if new_value:
            update_env_file(env_path, key_name, new_value)
            updated_keys.append(key_name)
            print_success(f"Set {key_name}")
            
            if key_name in REQUIRED_AI_KEYS:
                has_required = True
    
    # Summary
    print_header("✅ Setup Complete")
    
    if updated_keys:
        print("Updated keys:")
        for key in updated_keys:
            print(f"  • {key}")
    else:
        print_warning("No keys were updated")
    
    # Validation
    if not has_required:
        print_error(f"\n⚠️  WARNING: You need at least ONE of the following:")
        for key in REQUIRED_AI_KEYS:
            print(f"  • {key}")
        print("\nThe application will not work without at least one AI provider key.")
        return 1
    
    print(f"\n{GREEN}✓ Your .env file is ready!{RESET}")
    print(f"\nNext steps:")
    print(f"  1. Review your .env file: {env_path}")
    print(f"  2. Validate your setup: python3 scripts/validate_env.py")
    print(f"  3. Start the application: uvicorn uvai.api.main:app --reload")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)
