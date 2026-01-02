#!/usr/bin/env python3
"""
Services wrapper for deployment manager.
This module provides imports from backend.deployment_manager for backward compatibility.
"""

from ..backend.deployment_manager import (
    DeploymentManager,
    get_deployment_manager,
    validate_deployment_environment,
)

__all__ = [
    'DeploymentManager',
    'validate_deployment_environment',
    'get_deployment_manager'
]
