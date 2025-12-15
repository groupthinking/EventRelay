#!/usr/bin/env python3
"""
Logging Configuration
====================

Structured logging configuration for production-grade monitoring and debugging.
Provides consistent log formatting, multiple handlers, and performance monitoring.
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging with enhanced metadata.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data"""
        
        # Add custom fields to log record
        record.service_name = "youtube-extension-api"
        record.version = "2.0.0"
        record.architecture = "service-oriented"
        
        # Add performance timing if available
        if hasattr(record, 'duration'):
            record.performance_ms = f"{record.duration * 1000:.2f}ms"
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            record.correlation_id = record.request_id
        
        # Format the base message
        formatted_message = super().format(record)
        
        return formatted_message
    
    def formatException(self, ei) -> str:
        """Format exception with enhanced stack trace"""
        result = super().formatException(ei)
        return f"Exception Details:\n{result}"


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    enable_json_logging: bool = False,
    max_log_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_json_logging: Enable JSON formatted logs for production
        max_log_size: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
    """
    
    # Ensure logs directory exists
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Define log formats
    detailed_format = (
        "%(asctime)s - %(service_name)s[%(process)d] - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d:%(funcName)s] - %(message)s"
    )
    
    simple_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    json_format = (
        '{"timestamp": "%(asctime)s", "service": "%(service_name)s", '
        '"version": "%(version)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s", '
        '"module": "%(filename)s", "line": %(lineno)d, '
        '"function": "%(funcName)s", "process": %(process)d}'
    )
    
    # Choose format based on configuration
    if enable_json_logging:
        log_format = json_format
    else:
        log_format = detailed_format if log_level == "DEBUG" else detailed_format
    
    # Logging configuration dictionary
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": simple_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "backend": {  # Our application logger
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "structured",
            "filename": log_file,
            "maxBytes": max_log_size,
            "backupCount": backup_count,
            "encoding": "utf8"
        }
        
        # Add file handler to all loggers
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("file")
        
        # Add separate error log file
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "structured",
            "filename": log_file.replace(".log", "_errors.log"),
            "maxBytes": max_log_size,
            "backupCount": backup_count,
            "encoding": "utf8"
        }
        
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("error_file")
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log configuration summary
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file or 'Console only'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class PerformanceLogger:
    """
    Context manager for performance logging.
    """
    
    def __init__(self, logger: logging.Logger, operation: str, log_level: int = logging.INFO):
        """
        Initialize performance logger.
        
        Args:
            logger: Logger instance to use
            operation: Description of operation being timed
            log_level: Logging level for performance logs
        """
        self.logger = logger
        self.operation = operation
        self.log_level = log_level
        self.start_time = None
    
    def __enter__(self):
        """Start timing"""
        self.start_time = datetime.now()
        self.logger.log(self.log_level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type:
                self.logger.error(
                    f"{self.operation} failed after {duration:.3f}s - {exc_type.__name__}: {exc_val}"
                )
            else:
                self.logger.log(
                    self.log_level,
                    f"{self.operation} completed in {duration:.3f}s",
                    extra={"duration": duration}
                )


def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""
    
    # Reduce noise from common libraries
    noisy_loggers = [
        "urllib3.connectionpool",
        "requests.packages.urllib3",
        "aiohttp.access",
        "asyncio"
    ]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    # Set specific levels for important libraries
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def setup_production_logging():
    """Setup logging configuration optimized for production"""
    
    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/youtube_extension_api.log")
    enable_json = os.getenv("JSON_LOGGING", "false").lower() == "true"
    
    # Setup logging
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        enable_json_logging=enable_json
    )
    
    # Configure third-party loggers
    configure_third_party_loggers()
    
    logger = get_logger(__name__)
    logger.info("Production logging configuration applied")


def setup_development_logging():
    """Setup logging configuration optimized for development"""
    
    setup_logging(
        log_level="DEBUG",
        log_file="logs/youtube_extension_dev.log",
        enable_json_logging=False
    )
    
    # Less restrictive third-party logging in development
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    logger = get_logger(__name__)
    logger.info("Development logging configuration applied")


# Auto-configure based on environment
if os.getenv("ENVIRONMENT", "development").lower() == "production":
    setup_production_logging()
else:
    setup_development_logging()