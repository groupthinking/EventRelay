#!/usr/bin/env python3
"""
Environment Configuration Validator
===================================

Validates .env file configuration and checks API key availability.
Provides actionable feedback on missing or invalid configurations.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import re

# Import shared constants
sys.path.insert(0, str(Path(__file__).parent))
from env_constants import (
    PLACEHOLDER_VALUES, 
    REQUIRED_AI_KEYS, 
    RECOMMENDED_KEYS,
    KEY_PATTERNS
)

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


class EnvValidator:
    """Validates environment configuration"""
    
    # Use shared constants
    REQUIRED_AI_KEYS = REQUIRED_AI_KEYS
    RECOMMENDED_KEYS = RECOMMENDED_KEYS
    KEY_PATTERNS = KEY_PATTERNS
    PLACEHOLDER_VALUES = PLACEHOLDER_VALUES
    
    def __init__(self, env_path: Path = None):
        self.project_root = Path(__file__).parent.parent
        self.env_path = env_path or self.project_root / '.env'
        self.env_vars = {}
        self.errors = []
        self.warnings = []
        self.info = []
        
    def load_env(self) -> bool:
        """Load environment variables from .env file"""
        if not self.env_path.exists():
            self.errors.append(f".env file not found at {self.env_path}")
            self.info.append("Run: cp .env.example .env")
            self.info.append("Or: python3 scripts/setup_env.py")
            return False
        
        with open(self.env_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    self.env_vars[key.strip()] = value.strip()
        
        return True
    
    def validate_required_keys(self) -> bool:
        """Check if at least one required AI key is present"""
        found_keys = []
        
        for key in self.REQUIRED_AI_KEYS:
            value = self.env_vars.get(key, '')
            if value and value not in self.PLACEHOLDER_VALUES:
                found_keys.append(key)
        
        if not found_keys:
            keys_list = '\n'.join(f"  • {key}" for key in self.REQUIRED_AI_KEYS)
            self.errors.append(
                f"No valid AI provider key found. You need at least ONE of:\n{keys_list}"
            )
            self.info.append("Get Gemini key: https://aistudio.google.com/app/apikey")
            self.info.append("Get OpenAI key: https://platform.openai.com/api-keys")
            return False
        
        return True
    
    def validate_key_format(self, key: str, value: str) -> bool:
        """Validate API key format using regex patterns"""
        if key not in self.KEY_PATTERNS:
            return True  # No pattern defined, skip validation
        
        pattern = self.KEY_PATTERNS[key]
        if not re.match(pattern, value):
            self.warnings.append(
                f"{key} format looks incorrect. Please verify the key is correct."
            )
            return False
        
        return True
    
    def check_placeholder_values(self):
        """Check for placeholder values that need to be replaced"""
        for key, value in self.env_vars.items():
            if value in self.PLACEHOLDER_VALUES:
                if key in self.REQUIRED_AI_KEYS:
                    self.errors.append(f"{key} contains placeholder value: {value}")
                else:
                    self.warnings.append(f"{key} contains placeholder value: {value}")
    
    def check_recommended_keys(self):
        """Check for recommended but optional keys"""
        for key in self.RECOMMENDED_KEYS:
            value = self.env_vars.get(key, '')
            if not value or value in self.PLACEHOLDER_VALUES:
                self.info.append(
                    f"{key} is not set (optional but recommended for enhanced features)"
                )
    
    def validate_all(self) -> bool:
        """Run all validations"""
        if not self.load_env():
            return False
        
        # Check required keys
        has_required = self.validate_required_keys()
        
        # Check for placeholder values
        self.check_placeholder_values()
        
        # Validate key formats
        for key, value in self.env_vars.items():
            if key in self.KEY_PATTERNS and value not in self.PLACEHOLDER_VALUES:
                self.validate_key_format(key, value)
        
        # Check recommended keys
        self.check_recommended_keys()
        
        return has_required and len(self.errors) == 0
    
    def print_results(self):
        """Print validation results"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}🔍 Environment Validation Results{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
        
        # Print errors
        if self.errors:
            print(f"{BOLD}{RED}❌ ERRORS:{RESET}")
            for error in self.errors:
                print(f"{RED}  • {error}{RESET}")
            print()
        
        # Print warnings
        if self.warnings:
            print(f"{BOLD}{YELLOW}⚠️  WARNINGS:{RESET}")
            for warning in self.warnings:
                print(f"{YELLOW}  • {warning}{RESET}")
            print()
        
        # Print info
        if self.info:
            print(f"{BOLD}{BLUE}ℹ️  INFO:{RESET}")
            for info in self.info:
                print(f"{BLUE}  • {info}{RESET}")
            print()
        
        # Summary
        if not self.errors:
            print(f"{BOLD}{GREEN}✅ Environment validation passed!{RESET}")
            print(f"\nConfigured API keys:")
            for key in self.REQUIRED_AI_KEYS + self.RECOMMENDED_KEYS:
                value = self.env_vars.get(key, '')
                if value and value not in self.PLACEHOLDER_VALUES:
                    # Use consistent masking for security
                    masked = '****' if value else ''
                    print(f"{GREEN}  ✓ {key}: {masked}{RESET}")
            
            print(f"\n{GREEN}You're ready to run the application!{RESET}")
        else:
            print(f"{BOLD}{RED}❌ Environment validation failed{RESET}")
            print(f"\nTo fix these issues:")
            print(f"  1. Edit your .env file: {self.env_path}")
            print(f"  2. Add required API keys")
            print(f"  3. Run this validator again: python3 scripts/validate_env.py")
            print(f"\nOr use the interactive setup: python3 scripts/setup_env.py")
        
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}\n")


def main():
    """Main validation entry point"""
    validator = EnvValidator()
    is_valid = validator.validate_all()
    validator.print_results()
    
    return 0 if is_valid else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nValidation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Validation failed: {e}{RESET}")
        sys.exit(1)
