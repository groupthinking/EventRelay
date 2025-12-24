#!/usr/bin/env python3
"""
Core deployment adapter infrastructure for UVAI platform.
Provides base classes, error handling, and common functionality.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

@dataclass
class DeploymentError(Exception):
    """Base exception for deployment failures"""
    platform: str
    operation: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = False

@dataclass
class DeploymentResult:
    """Standardized deployment result structure"""
    status: str  # 'success', 'failed', 'skipped', 'pending'
    platform: str
    deployment_id: Optional[str] = None
    url: Optional[str] = None
    build_log_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamps: Dict[str, datetime] = field(default_factory=dict)

class EnvironmentValidator:
    """Centralized environment variable validation"""

    REQUIRED_TOKENS = {
        'vercel': ['VERCEL_TOKEN'],
        'netlify': ['NETLIFY_AUTH_TOKEN'],
        'fly': ['FLY_API_TOKEN'],
        'github': ['GITHUB_TOKEN']
    }

    OPTIONAL_TOKENS = {
        'vercel': ['VERCEL_PROJECT_NAME', 'VERCEL_ORG_ID'],
        'netlify': ['NETLIFY_SITE_NAME'],
        'fly': ['FLY_APP_NAME']
    }

    @classmethod
    def validate_for_platform(cls, platform: str) -> Dict[str, Any]:
        """Validate environment for specific platform deployment"""
        result = {
            'valid': True,
            'missing_required': [],
            'missing_optional': [],
            'available_tokens': {}
        }

        # Check required tokens
        required = cls.REQUIRED_TOKENS.get(platform, [])
        for token in required:
            value = os.getenv(token)
            if not value or value.startswith('['):  # Template placeholder
                result['missing_required'].append(token)
                result['valid'] = False
            else:
                result['available_tokens'][token] = '***masked***'

        # Check optional tokens
        optional = cls.OPTIONAL_TOKENS.get(platform, [])
        for token in optional:
            value = os.getenv(token)
            if not value or value.startswith('['):
                result['missing_optional'].append(token)
            else:
                result['available_tokens'][token] = '***masked***'

        return result

    @classmethod
    def get_token(cls, token_name: str) -> Optional[str]:
        """Safely get token value"""
        value = os.getenv(token_name)
        if not value or value.startswith('['):  # Template placeholder
            return None
        return value

class RetryConfig:
    """Configuration for retry logic"""
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 retryable_status_codes: List[int] = None):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_status_codes = retryable_status_codes or [429, 500, 502, 503, 504]

class BaseDeploymentAdapter(ABC):
    """Base class for all deployment adapters"""

    def __init__(self, platform: str, retry_config: Optional[RetryConfig] = None):
        self.platform = platform
        self.retry_config = retry_config or RetryConfig()
        self.logger = logging.getLogger(f"{__name__}.{platform}")

    async def deploy(self, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> DeploymentResult:
        """Main deployment entry point with error handling and validation"""
        start_time = datetime.now()

        try:
            # Validate environment
            env_validation = EnvironmentValidator.validate_for_platform(self.platform)
            if not env_validation['valid']:
                return DeploymentResult(
                    status='skipped',
                    platform=self.platform,
                    error_message=f"Missing required tokens: {', '.join(env_validation['missing_required'])}",
                    metadata={'env_validation': env_validation}
                )

            self.logger.info(f"🚀 Starting {self.platform} deployment")

            # Execute platform-specific deployment
            result = await self._deploy_impl(project_path, project_config, env)
            result.timestamps['completed'] = datetime.now()
            result.timestamps['duration_seconds'] = (result.timestamps['completed'] - start_time).total_seconds()

            self.logger.info(f"✅ {self.platform} deployment {result.status}: {result.url or 'N/A'}")
            return result

        except DeploymentError as e:
            self.logger.error(f"❌ {self.platform} deployment failed: {e.message}")
            return DeploymentResult(
                status='failed',
                platform=self.platform,
                error_message=e.message,
                metadata={'error_details': e.details, 'recoverable': e.recoverable}
            )
        except Exception as e:
            self.logger.error(f"❌ Unexpected {self.platform} deployment error: {str(e)}")
            return DeploymentResult(
                status='failed',
                platform=self.platform,
                error_message=f"Unexpected error: {str(e)}"
            )

    @abstractmethod
    async def _deploy_impl(self, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> DeploymentResult:
        """Platform-specific deployment implementation"""
        pass

    async def _make_request_with_retry(self,
                                     method: str,
                                     url: str,
                                     headers: Optional[Dict[str, str]] = None,
                                     json_data: Optional[Dict] = None,
                                     timeout: float = 30.0) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""

        for attempt in range(self.retry_config.max_attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json_data
                    )

                    if response.status_code < 400:
                        return response.json()

                    if response.status_code not in self.retry_config.retryable_status_codes:
                        raise DeploymentError(
                            platform=self.platform,
                            operation=f"{method} {url}",
                            message=f"HTTP {response.status_code}: {response.text}",
                            details={'status_code': response.status_code, 'response': response.text}
                        )

                    if attempt < self.retry_config.max_attempts - 1:
                        delay = min(
                            self.retry_config.base_delay * (self.retry_config.backoff_factor ** attempt),
                            self.retry_config.max_delay
                        )
                        self.logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise DeploymentError(
                            platform=self.platform,
                            operation=f"{method} {url}",
                            message=f"HTTP {response.status_code} after {self.retry_config.max_attempts} attempts",
                            details={'status_code': response.status_code, 'response': response.text}
                        )

            except httpx.TimeoutException:
                if attempt < self.retry_config.max_attempts - 1:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.backoff_factor ** attempt),
                        self.retry_config.max_delay
                    )
                    self.logger.warning(f"Request timeout (attempt {attempt + 1}), retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DeploymentError(
                        platform=self.platform,
                        operation=f"{method} {url}",
                        message=f"Request timeout after {self.retry_config.max_attempts} attempts",
                        recoverable=True
                    )
            except httpx.RequestError as e:
                if attempt < self.retry_config.max_attempts - 1:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.backoff_factor ** attempt),
                        self.retry_config.max_delay
                    )
                    self.logger.warning(f"Request error (attempt {attempt + 1}): {str(e)}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise DeploymentError(
                        platform=self.platform,
                        operation=f"{method} {url}",
                        message=f"Request error after {self.retry_config.max_attempts} attempts: {str(e)}",
                        recoverable=True
                    )

    async def _poll_deployment_status(self,
                                    status_url: str,
                                    success_statuses: List[str],
                                    timeout_minutes: int = 10) -> Dict[str, Any]:
        """Poll deployment status until completion or timeout"""

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            try:
                status_data = await self._make_request_with_retry('GET', status_url)

                status = status_data.get('status', '').lower()
                if status in success_statuses:
                    return status_data
                elif status in ['failed', 'error', 'cancelled']:
                    raise DeploymentError(
                        platform=self.platform,
                        operation='status_check',
                        message=f"Deployment {status}: {status_data.get('error', 'Unknown error')}",
                        details=status_data
                    )

                # Wait before next poll
                await asyncio.sleep(10)

            except DeploymentError:
                raise
            except Exception as e:
                self.logger.warning(f"Status check error: {str(e)}, continuing to poll...")
                await asyncio.sleep(10)

        raise DeploymentError(
            platform=self.platform,
            operation='status_check',
            message=f"Deployment status check timed out after {timeout_minutes} minutes",
            recoverable=True
        )
