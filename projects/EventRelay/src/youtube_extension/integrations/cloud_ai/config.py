"""
Cloud AI Configuration Management

Handles configuration validation, loading, and management for all cloud AI providers.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from dataclasses import dataclass

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a single cloud AI provider."""
    enabled: bool = False
    validated: bool = False
    available: bool = False
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class CloudAIConfig:
    """Manages configuration for all cloud AI providers."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.providers: Dict[str, ProviderConfig] = {}
        self._load_config(config_dict or {})
    
    def _load_config(self, config_dict: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        # Initialize all providers
        self.providers["google_cloud"] = ProviderConfig()
        self.providers["aws_rekognition"] = ProviderConfig()
        self.providers["azure_vision"] = ProviderConfig()
        
        # Update with provided config
        for provider_name, provider_config in config_dict.items():
            if provider_name in self.providers:
                self.providers[provider_name].config.update(provider_config)
                self.providers[provider_name].enabled = provider_config.get("enabled", False)
    
    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all provider configurations."""
        validation_results = {}
        
        for provider_name, provider_config in self.providers.items():
            if provider_config.enabled:
                validation_results[provider_name] = self.validate_provider(provider_name)
        
        return validation_results
    
    def validate_provider(self, provider_name: str) -> List[str]:
        """Validate configuration for a specific provider."""
        if provider_name not in self.providers:
            return [f"Unknown provider: {provider_name}"]
        
        provider_config = self.providers[provider_name]
        errors = []
        
        # Provider-specific validation
        if provider_name == "google_cloud":
            errors.extend(self._validate_google_cloud(provider_config.config))
        elif provider_name == "aws_rekognition":
            errors.extend(self._validate_aws_rekognition(provider_config.config))
        elif provider_name == "azure_vision":
            errors.extend(self._validate_azure_vision(provider_config.config))
        
        # Mark as validated if no errors
        provider_config.validated = len(errors) == 0
        
        return errors
    
    def _validate_google_cloud(self, config: Dict[str, Any]) -> List[str]:
        """Validate Google Cloud configuration."""
        errors = []
        
        if not config.get("project_id"):
            errors.append("Google Cloud project_id is required")
        
        # Check for credentials
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not config.get("credentials_path"):
            errors.append("Google Cloud credentials not found (set GOOGLE_APPLICATION_CREDENTIALS or credentials_path)")
        
        # Validate location
        valid_locations = ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
        location = config.get("location_id", "us-central1")
        if location not in valid_locations:
            errors.append(f"Invalid Google Cloud location: {location}. Valid locations: {valid_locations}")
        
        return errors
    
    def _validate_aws_rekognition(self, config: Dict[str, Any]) -> List[str]:
        """Validate AWS Rekognition configuration."""
        errors = []
        
        if not config.get("aws_access_key_id"):
            errors.append("AWS access_key_id is required")
        
        if not config.get("aws_secret_access_key"):
            errors.append("AWS secret_access_key is required")
        
        if not config.get("region"):
            errors.append("AWS region is required")
        
        # Validate region format
        region = config.get("region", "")
        if region and not (region.count("-") >= 2 and len(region) >= 8):
            errors.append(f"Invalid AWS region format: {region}")
        
        return errors
    
    def _validate_azure_vision(self, config: Dict[str, Any]) -> List[str]:
        """Validate Azure Vision configuration."""
        errors = []
        
        if not config.get("subscription_key"):
            errors.append("Azure subscription_key is required")
        
        if not config.get("endpoint"):
            errors.append("Azure endpoint is required")
        
        # Validate endpoint format
        endpoint = config.get("endpoint", "")
        if endpoint and not endpoint.startswith("https://"):
            errors.append("Azure endpoint must start with https://")
        
        return errors
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed for each provider."""
        availability = {}
        
        # Google Cloud
        try:
            import google.cloud.videointelligence
            import google.cloud.vision
            availability["google_cloud"] = True
            self.providers["google_cloud"].available = True
        except ImportError:
            availability["google_cloud"] = False
        
        # AWS Rekognition
        try:
            import boto3
            availability["aws_rekognition"] = True
            self.providers["aws_rekognition"].available = True
        except ImportError:
            availability["aws_rekognition"] = False
        
        # Azure Vision
        try:
            import azure.cognitiveservices.vision.computervision
            availability["azure_vision"] = True
            self.providers["azure_vision"].available = True
        except ImportError:
            availability["azure_vision"] = False
        
        # Apple FastVLM (always available - local model)
        return availability
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled and validated providers."""
        return [
            name for name, config in self.providers.items()
            if config.enabled and config.validated and config.available
        ]
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if provider_name not in self.providers:
            raise ConfigurationError(f"Unknown provider: {provider_name}")
        
        return self.providers[provider_name].config
    
    def is_provider_ready(self, provider_name: str) -> bool:
        """Check if a provider is enabled, configured, and available."""
        if provider_name not in self.providers:
            return False
        
        provider = self.providers[provider_name]
        return provider.enabled and provider.validated and provider.available
    
    @classmethod
    def from_file(cls, config_path: str) -> 'CloudAIConfig':
        """Load configuration from a JSON or YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yml', '.yaml']:
                    import yaml
                    config_dict = yaml.safe_load(f)
                else:
                    config_dict = json.load(f)
            
            return cls(config_dict)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file: {e}")
    
    @classmethod
    def from_environment(cls) -> 'CloudAIConfig':
        """Create configuration from environment variables."""
        config_dict = {
            "google_cloud": {
                "enabled": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location_id": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                "timeout": int(os.getenv("GOOGLE_CLOUD_TIMEOUT", "300"))
            },
            "aws_rekognition": {
                "enabled": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "region": os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
                "s3_bucket": os.getenv("AWS_S3_BUCKET"),
                "max_wait_time": int(os.getenv("AWS_REKOGNITION_TIMEOUT", "600"))
            },
            "azure_vision": {
                "enabled": bool(os.getenv("AZURE_COGNITIVE_SERVICES_KEY")),
                "subscription_key": os.getenv("AZURE_COGNITIVE_SERVICES_KEY"),
                "endpoint": os.getenv("AZURE_COGNITIVE_SERVICES_ENDPOINT")
            }
        }
        
        return cls(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            name: {
                "enabled": config.enabled,
                "validated": config.validated,
                "available": config.available,
                **config.config
            }
            for name, config in self.providers.items()
        }
    
    def save_to_file(self, config_path: str, format: str = "json") -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_dict = self.to_dict()
        
        try:
            with open(config_path, 'w') as f:
                if format.lower() == "yaml":
                    import yaml
                    yaml.safe_dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)
                    
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
