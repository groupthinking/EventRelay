import os
from typing import Optional

"""
Configuration settings for the Prescient Twin application.

This file centralizes environment-specific and application-wide settings,
including database connections, API keys, and external service endpoints.
Sensitive information should be loaded from environment variables.
"""

# --- General Application Settings ---
APP_ENV: str = os.getenv("APP_ENV", "development")
"""The current application environment (e.g., 'development', 'staging', 'production')."""

DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
"""
A boolean indicating whether debug mode is enabled.
Set to 'True' or 'False' (case-insensitive) in environment variables.
"""

# --- UCP Retailer Endpoints Configuration ---
# This section defines configuration options for various UCP retailer endpoints.
# Each retailer might have its own base URL and authentication credentials.
# It is highly recommended to define these using environment variables for
# non-development environments.

# Example for a primary UCP Retailer (e.g., the main one or a default)
UCP_PRIMARY_RETAILER_BASE_URL: Optional[str] = os.getenv("UCP_PRIMARY_RETAILER_BASE_URL")
"""
The base URL for the primary UCP retailer's API endpoint.
Example: "https://api.primary-retailer.com/ucp/v1"
"""

UCP_PRIMARY_RETAILER_CLIENT_ID: Optional[str] = os.getenv("UCP_PRIMARY_RETAILER_CLIENT_ID")
"""
The client ID for authenticating with the primary UCP retailer's API.
"""

UCP_PRIMARY_RETAILER_CLIENT_SECRET: Optional[str] = os.getenv("UCP_PRIMARY_RETAILER_CLIENT_SECRET")
"""
The client secret for authenticating with the primary UCP retailer's API.
This should be kept highly confidential and loaded from secure environment variables.
"""

# Example for a secondary UCP Retailer (if multiple are supported)
UCP_SECONDARY_RETAILER_BASE_URL: Optional[str] = os.getenv("UCP_SECONDARY_RETAILER_BASE_URL")
"""
The base URL for a secondary UCP retailer's API endpoint.
Example: "https://api.secondary-retailer.com/ucp/v1"
"""

UCP_SECONDARY_RETAILER_CLIENT_ID: Optional[str] = os.getenv("UCP_SECONDARY_RETAILER_CLIENT_ID")
"""
The client ID for authenticating with the secondary UCP retailer's API.
"""

UCP_SECONDARY_RETAILER_CLIENT_SECRET: Optional[str] = os.getenv("UCP_SECONDARY_RETAILER_CLIENT_SECRET")
"""
The client secret for authenticating with the secondary UCP retailer's API.
This should be kept highly confidential and loaded from secure environment variables.
"""

# --- Other potential settings (placeholders for future expansion) ---
# DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./prescient_twin.db")
# """The database connection URL."""

# EXTERNAL_SERVICE_API_KEY: Optional[str] = os.getenv("EXTERNAL_SERVICE_API_KEY")
# """API key for an external service."""

# LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
# """The desired logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR')."""