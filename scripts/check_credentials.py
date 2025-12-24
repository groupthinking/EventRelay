#!/usr/bin/env python3
"""
Credentials and Security Check Script
=====================================

Analyzes the codebase for:
- Missing API keys and tokens
- Hardcoded credentials
- Security vulnerabilities
- Proper environment variable usage
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict

class CredentialsChecker:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.required_keys = {
            # Core API Keys
            "YOUTUBE_API_KEY": {
                "description": "YouTube Data API v3 key",
                "pattern": r"AIzaSy[a-zA-Z0-9_-]{33}",
                "required": True
            },
            "GEMINI_API_KEY": {
                "description": "Google Gemini API key",
                "alternates": ["GOOGLE_API_KEY"],
                "required": True
            },
            "OPENAI_API_KEY": {
                "description": "OpenAI API key for GPT models",
                "pattern": r"sk-[a-zA-Z0-9]{48}",
                "required": False
            },
            "ANTHROPIC_API_KEY": {
                "description": "Anthropic Claude API key",
                "required": False
            },
            "GROK_API_KEY": {
                "description": "xAI Grok API key",
                "alternates": ["XAI_API_KEY"],
                "required": False
            },
            
            # MCP Configuration
            "MCP_SERVER_URL": {
                "description": "MCP server endpoint",
                "default": "http://localhost:8080",
                "required": True
            },
            "MCP_BRIDGE_URL": {
                "description": "MCP bridge endpoint",
                "default": "http://localhost:8004",
                "required": True
            },
            
            # External Services
            "LIVEKIT_URL": {
                "description": "LiveKit WebRTC server URL",
                "required": False
            },
            "LIVEKIT_API_KEY": {
                "description": "LiveKit API key",
                "required": False
            },
            "LIVEKIT_API_SECRET": {
                "description": "LiveKit API secret",
                "required": False
            },
            "MOZILLA_AI_URL": {
                "description": "Mozilla AI service endpoint",
                "required": False
            },
            
            # Database/Cache
            "REDIS_URL": {
                "description": "Redis connection URL",
                "default": "redis://localhost:6379",
                "required": False
            },
            
            # Observability
            "OTEL_EXPORTER_OTLP_ENDPOINT": {
                "description": "OpenTelemetry collector endpoint",
                "default": "http://localhost:4317",
                "required": False
            }
        }
        
        self.security_patterns = [
            # Hardcoded credentials
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            
            # Specific API key patterns
            (r'AIzaSy[a-zA-Z0-9_-]{33}', "Exposed YouTube API key"),
            (r'sk-[a-zA-Z0-9]{48}', "Exposed OpenAI API key"),
            
            # Base64 encoded secrets
            (r'[A-Za-z0-9+/]{40,}={0,2}', "Possible base64 encoded secret"),
            
            # Private keys
            (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', "Private key in code"),
        ]
        
        self.report = {
            "missing_required_keys": [],
            "missing_optional_keys": [],
            "found_keys": {},
            "hardcoded_credentials": [],
            "security_issues": [],
            "env_files": []
        }
        
    def check_env_files(self):
        """Check all environment files"""
        env_files = [
            ".env",
            ".env.example",
            ".env.local",
            ".env.production",
            "env_template.txt"
        ]
        
        for env_file in env_files:
            env_path = self.base_path / env_file
            if env_path.exists():
                self.report["env_files"].append(str(env_file))
                self.parse_env_file(env_path)
                
    def parse_env_file(self, env_path: Path):
        """Parse environment file for keys"""
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key in self.required_keys:
                                self.report["found_keys"][key] = {
                                    "file": str(env_path),
                                    "has_value": bool(value and value != "")
                                }
        except Exception as e:
            print(f"Error parsing {env_path}: {e}")
            
    def scan_for_hardcoded_credentials(self):
        """Scan code for hardcoded credentials"""
        ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", 
                      "archived_dev_artifacts", "models", ".cache"}
        
        for file_path in self.base_path.rglob("*.py"):
            # Skip ignored directories
            if any(ignore_dir in file_path.parts for ignore_dir in ignore_dirs):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for security patterns
                for pattern, issue_type in self.security_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Get line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Skip if it's in a comment or string
                        line_content = content.split('\n')[line_num - 1]
                        if '#' in line_content and line_content.index('#') < match.start():
                            continue
                            
                        self.report["hardcoded_credentials"].append({
                            "file": str(file_path.relative_to(self.base_path)),
                            "line": line_num,
                            "type": issue_type,
                            "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
                        })
                        
            except Exception as e:
                pass
                
    def check_missing_keys(self):
        """Check for missing required keys"""
        for key, config in self.required_keys.items():
            found = False
            
            # Check if key is found
            if key in self.report["found_keys"]:
                found = self.report["found_keys"][key]["has_value"]
            else:
                # Check alternates
                if "alternates" in config:
                    for alt in config["alternates"]:
                        if alt in self.report["found_keys"]:
                            found = self.report["found_keys"][alt]["has_value"]
                            break
                            
            if not found:
                if config.get("required", True):
                    self.report["missing_required_keys"].append({
                        "key": key,
                        "description": config.get("description", ""),
                        "default": config.get("default", None)
                    })
                else:
                    self.report["missing_optional_keys"].append({
                        "key": key,
                        "description": config.get("description", "")
                    })
                    
    def check_api_usage(self):
        """Check where APIs are actually used in code"""
        api_usage = defaultdict(list)
        
        patterns = {
            "YOUTUBE_API_KEY": [r"youtube.*api", r"YouTube.*API", r"build\(['\"](youtube)"],
            "GEMINI_API_KEY": [r"gemini.*api", r"google.*generative", r"genai\."],
            "OPENAI_API_KEY": [r"openai", r"OpenAI", r"gpt-"],
            "ANTHROPIC_API_KEY": [r"anthropic", r"claude", r"Claude"],
        }
        
        for file_path in self.base_path.rglob("*.py"):
            if any(ignore in str(file_path) for ignore in [".venv", "__pycache__", "node_modules"]):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for key, patterns_list in patterns.items():
                    for pattern in patterns_list:
                        if re.search(pattern, content, re.IGNORECASE):
                            api_usage[key].append(str(file_path.relative_to(self.base_path)))
                            break
            except:
                pass
                
        self.report["api_usage"] = dict(api_usage)
        
    def generate_report(self):
        """Generate comprehensive credentials report"""
        print("\n=== CREDENTIALS & SECURITY ANALYSIS ===\n")
        
        # Environment files found
        print(f"Environment files found: {', '.join(self.report['env_files']) if self.report['env_files'] else 'NONE'}")
        
        # Missing required keys
        if self.report["missing_required_keys"]:
            print("\n❌ MISSING REQUIRED KEYS:")
            for item in self.report["missing_required_keys"]:
                print(f"  - {item['key']}: {item['description']}")
                if item.get('default'):
                    print(f"    Default: {item['default']}")
                    
        # Missing optional keys
        if self.report["missing_optional_keys"]:
            print("\n⚠️  MISSING OPTIONAL KEYS:")
            for item in self.report["missing_optional_keys"]:
                print(f"  - {item['key']}: {item['description']}")
                
        # Found keys
        if self.report["found_keys"]:
            print("\n✅ CONFIGURED KEYS:")
            for key, info in self.report["found_keys"].items():
                status = "✓ Has value" if info["has_value"] else "✗ Empty"
                print(f"  - {key} ({info['file']}): {status}")
                
        # Hardcoded credentials
        if self.report["hardcoded_credentials"]:
            print("\n🚨 SECURITY ISSUES - HARDCODED CREDENTIALS:")
            for issue in self.report["hardcoded_credentials"][:10]:  # Show first 10
                print(f"  - {issue['file']}:{issue['line']} - {issue['type']}")
                print(f"    Found: {issue['match']}")
                
        # API usage
        if self.report.get("api_usage"):
            print("\n📍 API USAGE LOCATIONS:")
            for api, files in self.report["api_usage"].items():
                print(f"\n  {api} used in:")
                for file in files[:5]:  # Show first 5
                    print(f"    - {file}")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more files")
                    
        # Save detailed report
        report_path = self.base_path / "CREDENTIALS_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(self.report, f, indent=2)
            
        print(f"\n\nDetailed report saved to: {report_path}")
        
        # Summary
        print("\n=== SUMMARY ===")
        print(f"Missing required keys: {len(self.report['missing_required_keys'])}")
        print(f"Missing optional keys: {len(self.report['missing_optional_keys'])}")
        print(f"Security issues found: {len(self.report['hardcoded_credentials'])}")
        
    def run(self):
        """Run all credential checks"""
        print("Starting credentials and security analysis...")
        
        self.check_env_files()
        self.scan_for_hardcoded_credentials()
        self.check_missing_keys()
        self.check_api_usage()
        self.generate_report()
        

if __name__ == "__main__":
    checker = CredentialsChecker()
    checker.run()
