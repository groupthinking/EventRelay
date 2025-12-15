#!/usr/bin/env python3
"""
Production Configuration
========================

Production-grade configuration management for deployment environments.
Handles environment variables, security settings, and performance optimizations.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class ProductionConfig:
    """
    Production configuration management class.
    Centralizes all configuration settings with environment variable support.
    """
    
    def __init__(self):
        """Initialize production configuration"""
        self.environment = os.getenv("ENVIRONMENT", "production").lower()
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.api_workers = int(os.getenv("API_WORKERS", "4"))
        
        # Security Configuration
        self.allowed_origins = self._parse_list(os.getenv(
            "ALLOWED_ORIGINS", 
            "https://youtube-extension-frontend.vercel.app,https://*.vercel.app"
        ))
        self.api_key_header = os.getenv("API_KEY_HEADER", "X-API-Key")
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "300"))
        self.max_request_size = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
        
        # Database Configuration (if needed in future)
        self.database_url = os.getenv("DATABASE_URL", "")
        self.redis_url = os.getenv("REDIS_URL", "")
        
        # Cache Configuration
        self.cache_dir = os.getenv("CACHE_DIR", "youtube_processed_videos/markdown_analysis")
        self.cache_max_size_gb = float(os.getenv("CACHE_MAX_SIZE_GB", "5.0"))
        self.cache_retention_days = int(os.getenv("CACHE_RETENTION_DAYS", "30"))
        
        # Video Processing Configuration
        self.video_processor_type = os.getenv("VIDEO_PROCESSOR_TYPE", "enhanced")
        self.max_concurrent_processes = int(os.getenv("MAX_CONCURRENT_PROCESSES", "10"))
        self.processing_timeout_seconds = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))
        
        # External Service URLs
        self.livekit_url = os.getenv("LIVEKIT_URL", "")
        self.mozilla_ai_url = os.getenv("MOZILLA_AI_URL", "")
        
        # API Keys (validation only - keys should be accessed directly from env)
        self.has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        self.has_youtube_key = bool(os.getenv("YOUTUBE_API_KEY"))
        self.has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        self.has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        
        # Monitoring Configuration
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.metrics_port = int(os.getenv("METRICS_PORT", "8001"))
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
        
        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file = os.getenv("LOG_FILE", "logs/youtube_extension_api.log")
        self.enable_json_logging = os.getenv("JSON_LOGGING", "true").lower() == "true"
        self.log_max_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "100"))
        self.log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # Performance Configuration
        self.enable_gzip = os.getenv("ENABLE_GZIP", "true").lower() == "true"
        self.gzip_min_size = int(os.getenv("GZIP_MIN_SIZE", "1024"))
        self.request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        
        # WebSocket Configuration
        self.websocket_max_connections = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "100"))
        self.websocket_heartbeat_interval = int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30"))
        
        # Deployment Configuration
        self.deployment_environment = os.getenv("DEPLOYMENT_ENV", "production")
        self.version = os.getenv("APP_VERSION", "2.0.0")
        self.build_hash = os.getenv("BUILD_HASH", "unknown")
        
    def _parse_list(self, value: str, separator: str = ",") -> list:
        """Parse comma-separated string into list"""
        if not value:
            return []
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """Get Uvicorn server configuration"""
        return {
            "host": self.api_host,
            "port": self.api_port,
            "workers": self.api_workers if not self.debug else 1,
            "reload": self.debug,
            "log_level": self.log_level.lower(),
            "access_log": True,
            "use_colors": not self.enable_json_logging,
            "timeout_keep_alive": 5,
            "timeout_graceful_shutdown": 10,
            "limit_max_requests": 10000,
            "limit_concurrency": self.max_concurrent_processes,
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS middleware configuration"""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
            "allow_headers": ["*"],
            "expose_headers": ["*"],
            "max_age": 3600,
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache service configuration"""
        return {
            "cache_dir": self.cache_dir,
            "max_size_gb": self.cache_max_size_gb,
            "retention_days": self.cache_retention_days,
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring and metrics configuration"""
        return {
            "enable_metrics": self.enable_metrics,
            "metrics_port": self.metrics_port,
            "health_check_interval": self.health_check_interval,
            "rate_limit_per_minute": self.rate_limit_per_minute,
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "log_level": self.log_level,
            "log_file": self.log_file,
            "enable_json_logging": self.enable_json_logging,
            "max_size_mb": self.log_max_size_mb,
            "backup_count": self.log_backup_count,
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            "api_key_header": self.api_key_header,
            "max_request_size": self.max_request_size,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "request_timeout_seconds": self.request_timeout_seconds,
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate production configuration and return status report.
        
        Returns:
            Configuration validation report
        """
        issues = []
        warnings = []
        
        # Check required API keys
        if not self.has_gemini_key:
            issues.append("Missing GEMINI_API_KEY or GOOGLE_API_KEY")
        if not self.has_youtube_key:
            issues.append("Missing YOUTUBE_API_KEY")
        
        # Check cache directory
        cache_path = Path(self.cache_dir)
        if not cache_path.parent.exists():
            warnings.append(f"Cache parent directory does not exist: {cache_path.parent}")
        
        # Check log directory
        if self.log_file:
            log_path = Path(self.log_file)
            if not log_path.parent.exists():
                warnings.append(f"Log parent directory does not exist: {log_path.parent}")
        
        # Performance warnings
        if self.api_workers > 8:
            warnings.append(f"High worker count ({self.api_workers}) may impact performance")
        
        if self.max_concurrent_processes > 20:
            warnings.append(f"High concurrency limit ({self.max_concurrent_processes}) may impact stability")
        
        # Security checks
        if self.debug and self.environment == "production":
            issues.append("Debug mode enabled in production environment")
        
        if not self.allowed_origins or "*" in self.allowed_origins:
            warnings.append("CORS origins not properly restricted")
        
        return {
            "status": "valid" if not issues else "invalid",
            "environment": self.environment,
            "issues": issues,
            "warnings": warnings,
            "api_keys_configured": {
                "gemini": self.has_gemini_key,
                "youtube": self.has_youtube_key,
                "openai": self.has_openai_key,
                "anthropic": self.has_anthropic_key,
            },
            "external_services": {
                "livekit": bool(self.livekit_url),
                "mozilla_ai": bool(self.mozilla_ai_url),
            }
        }
    
    def get_deployment_info(self) -> Dict[str, Any]:
        """Get deployment information"""
        return {
            "environment": self.deployment_environment,
            "version": self.version,
            "build_hash": self.build_hash,
            "debug_mode": self.debug,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "workers": self.api_workers,
        }
    
    def export_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Export configuration for logging or debugging.
        
        Args:
            include_secrets: Whether to include sensitive information
            
        Returns:
            Configuration dictionary
        """
        config = {
            "environment": self.environment,
            "debug": self.debug,
            "api": {
                "host": self.api_host,
                "port": self.api_port,
                "workers": self.api_workers,
            },
            "cache": self.get_cache_config(),
            "monitoring": self.get_monitoring_config(),
            "logging": self.get_logging_config(),
            "performance": {
                "enable_gzip": self.enable_gzip,
                "max_concurrent_processes": self.max_concurrent_processes,
                "processing_timeout": self.processing_timeout_seconds,
            },
            "websocket": {
                "max_connections": self.websocket_max_connections,
                "heartbeat_interval": self.websocket_heartbeat_interval,
            },
        }
        
        if include_secrets:
            config["api_keys"] = {
                "gemini": "configured" if self.has_gemini_key else "missing",
                "youtube": "configured" if self.has_youtube_key else "missing",
                "openai": "configured" if self.has_openai_key else "missing",
                "anthropic": "configured" if self.has_anthropic_key else "missing",
            }
        
        return config


# Global configuration instance
_config_instance: Optional[ProductionConfig] = None


def get_config() -> ProductionConfig:
    """
    Get or create global configuration instance.
    
    Returns:
        Production configuration instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ProductionConfig()
    
    return _config_instance


def load_config_from_file(config_file: str) -> None:
    """
    Load configuration from file (for development/testing).
    
    Args:
        config_file: Path to configuration file
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(config_file)
        
        # Reload configuration instance
        global _config_instance
        _config_instance = None
        
    except ImportError:
        raise ImportError("python-dotenv required for loading config files")


def validate_production_readiness() -> Dict[str, Any]:
    """
    Validate that the application is ready for production deployment.
    
    Returns:
        Production readiness report
    """
    config = get_config()
    validation = config.validate_configuration()
    
    readiness_report = {
        "ready_for_production": validation["status"] == "valid" and config.environment == "production",
        "configuration_validation": validation,
        "deployment_info": config.get_deployment_info(),
        "recommendations": []
    }
    
    # Add specific recommendations
    if validation["issues"]:
        readiness_report["recommendations"].append("Fix configuration issues before deploying")
    
    if validation["warnings"]:
        readiness_report["recommendations"].append("Review configuration warnings")
    
    if config.debug:
        readiness_report["recommendations"].append("Disable debug mode in production")
    
    if not config.enable_json_logging:
        readiness_report["recommendations"].append("Enable JSON logging for production monitoring")
    
    return readiness_report