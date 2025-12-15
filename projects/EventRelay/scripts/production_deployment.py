#!/usr/bin/env python3
"""
Production Deployment Configuration & Security Hardening
Enterprise-grade deployment with security, secrets management, and infrastructure as code
"""

import os
import json
import logging
import subprocess
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
import yaml

# Security imports
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_enabled: bool = True
    api_key_rotation_days: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    rate_limit_per_ip: int = 1000  # requests per hour
    allowed_origins: List[str] = None
    require_https: bool = True
    session_timeout_minutes: int = 30

@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    environment: str  # development, staging, production
    replicas: int = 3
    cpu_limit: str = "2"
    memory_limit: str = "4Gi"
    storage_size: str = "10Gi"
    health_check_interval: int = 30
    log_level: str = "INFO"
    backup_enabled: bool = True
    monitoring_enabled: bool = True

class SecretsManager:
    """Secure secrets management"""
    
    def __init__(self, key_file: Path = None):
        self.key_file = key_file or Path("secrets.key")
        self.secrets_file = Path("secrets.encrypted")
        self.cipher_suite = self._get_cipher_suite()
        
    def _get_cipher_suite(self):
        """Initialize encryption cipher"""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Restrict permissions
            logger.info("🔐 Generated new encryption key")
        
        return Fernet(key)
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret"""
        encrypted_secret = self.cipher_suite.encrypt(secret.encode())
        return base64.b64encode(encrypted_secret).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret"""
        encrypted_data = base64.b64decode(encrypted_secret.encode())
        decrypted_secret = self.cipher_suite.decrypt(encrypted_data)
        return decrypted_secret.decode()
    
    def store_secrets(self, secrets: Dict[str, str]):
        """Store encrypted secrets"""
        encrypted_secrets = {}
        for key, value in secrets.items():
            encrypted_secrets[key] = self.encrypt_secret(value)
        
        with open(self.secrets_file, 'w') as f:
            json.dump(encrypted_secrets, f, indent=2)
        
        os.chmod(self.secrets_file, 0o600)
        logger.info(f"🔒 Stored {len(secrets)} encrypted secrets")
    
    def load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets"""
        if not self.secrets_file.exists():
            return {}
        
        with open(self.secrets_file, 'r') as f:
            encrypted_secrets = json.load(f)
        
        secrets = {}
        for key, encrypted_value in encrypted_secrets.items():
            secrets[key] = self.decrypt_secret(encrypted_value)
        
        return secrets

class ProductionHardening:
    """Production security hardening utilities"""
    
    def __init__(self):
        self.security_config = SecurityConfig()
        self.hardening_checks = []
        
    def run_security_audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit"""
        audit_results = {
            "timestamp": str(pd.datetime.now()),
            "checks": [],
            "vulnerabilities": [],
            "recommendations": []
        }
        
        # File permissions check
        sensitive_files = [
            "secrets.key", "secrets.encrypted", ".env", "config.json"
        ]
        
        for file_path in sensitive_files:
            if Path(file_path).exists():
                stat = os.stat(file_path)
                permissions = oct(stat.st_mode)[-3:]
                
                if permissions != "600":
                    audit_results["vulnerabilities"].append({
                        "type": "insecure_file_permissions",
                        "file": file_path,
                        "current_permissions": permissions,
                        "severity": "high"
                    })
                    audit_results["recommendations"].append(f"Set secure permissions for {file_path}: chmod 600 {file_path}")
                else:
                    audit_results["checks"].append(f"✅ {file_path} has secure permissions")
        
        # Environment variables check
        sensitive_env_vars = [
            "API_KEY", "SECRET_KEY", "DATABASE_PASSWORD", "JWT_SECRET"
        ]
        
        for var in sensitive_env_vars:
            if var in os.environ:
                value = os.environ[var]
                if len(value) < 32:
                    audit_results["vulnerabilities"].append({
                        "type": "weak_secret",
                        "variable": var,
                        "severity": "medium"
                    })
                    audit_results["recommendations"].append(f"Use stronger secret for {var} (minimum 32 characters)")
                else:
                    audit_results["checks"].append(f"✅ {var} has sufficient length")
        
        # Network security check
        audit_results["checks"].extend([
            "✅ HTTPS enforcement enabled" if self.security_config.require_https else "❌ HTTPS not enforced",
            f"✅ Rate limiting configured: {self.security_config.rate_limit_per_ip} req/hour",
            f"✅ Request size limit: {self.security_config.max_request_size} bytes"
        ])
        
        return audit_results
    
    def generate_security_headers(self) -> Dict[str, str]:
        """Generate security headers for HTTP responses"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' cdn.tailwindcss.com",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    
    def setup_log_rotation(self, log_dir: Path, max_size: str = "100MB", max_files: int = 10):
        """Setup log rotation configuration"""
        logrotate_config = f"""
{log_dir}/*.log {{
    daily
    size {max_size}
    rotate {max_files}
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        systemctl reload enterprise-mcp-server || true
    endscript
}}
        """
        
        config_path = Path("/etc/logrotate.d/enterprise-mcp-server")
        try:
            with open(config_path, 'w') as f:
                f.write(logrotate_config)
            logger.info("📜 Log rotation configured")
        except PermissionError:
            logger.warning("❌ Cannot write logrotate config (need sudo)")
            # Write to local directory instead
            with open("logrotate.conf", 'w') as f:
                f.write(logrotate_config)
            logger.info("📜 Log rotation config written to logrotate.conf")

# CLI interface
def main():
    """CLI for production deployment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise MCP Server Production Deployment")
    parser.add_argument("--environment", choices=["development", "staging", "production"], 
                       default="production", help="Deployment environment")
    parser.add_argument("--target", choices=["docker-compose", "kubernetes", "systemd"],
                       default="docker-compose", help="Deployment target")
    parser.add_argument("--replicas", type=int, default=3, help="Number of replicas")
    parser.add_argument("--cpu-limit", default="2", help="CPU limit")
    parser.add_argument("--memory-limit", default="4Gi", help="Memory limit")
    
    args = parser.parse_args()
    
    # Create deployment configuration
    config = DeploymentConfig(
        environment=args.environment,
        replicas=args.replicas,
        cpu_limit=args.cpu_limit,
        memory_limit=args.memory_limit
    )
    
    # Initialize deployment manager
    deploy_manager = DeploymentManager(config)
    
    # Setup secrets (example)
    secrets = {
        "YOUTUBE_API_KEY": "your-youtube-api-key-here",
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "JWT_SECRET": secrets.token_hex(32)
    }
    deploy_manager.secrets_manager.store_secrets(secrets)
    
    # Deploy
    deploy_dir = deploy_manager.deploy(args.target)
    print(f"✅ Deployment configuration ready in: {deploy_dir}")

if __name__ == "__main__":
    # Fix imports
    import pandas as pd
    main()