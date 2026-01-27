from typing import Dict, Optional, List
from pydantic import BaseModel, Field, HttpUrl


class UCPRetailerConfig(BaseModel):
    """
    Represents the configuration for a UCP-compliant retailer.

    This configuration allows `prescient-twin` to connect to and interact
    with the retailer's Universal Commerce Platform (UCP) endpoint.
    """
    retailer_id: str = Field(
        ...,
        description="A unique identifier for the retailer within the Prescient Twin ecosystem."
    )
    base_url: HttpUrl = Field(
        ...,
        description="The base URL for the retailer's Universal Commerce Platform (UCP) API."
    )
    api_key: Optional[str] = Field(
        None,
        description="API key for authentication with the UCP endpoint, if applicable."
    )
    client_id: Optional[str] = Field(
        None,
        description="Client ID for OAuth2 authentication with the UCP endpoint, if applicable."
    )
    client_secret: Optional[str] = Field(
        None,
        description="Client secret for OAuth2 authentication with the UCP endpoint, if applicable."
    )
    commerce_platform: str = Field(
        ...,
        description="The underlying commerce platform (e.g., 'shopify', 'magento', 'custom') "
                    "that the UCP abstracts. Used for platform-specific logic."
    )
    config_details: Dict[str, str] = Field(
        default_factory=dict,
        description="A dictionary for additional platform-specific configuration details "
                    "(e.g., store_hash, access_token_url, scope)."
    )

    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Ensure no unexpected fields are passed


class UCPRetailerRegistry:
    """
    A central registry service for UCP-compliant retailers.

    This registry allows `prescient-twin` to dynamically discover and
    configure connections to various commerce endpoints by storing and
    retrieving `UCPRetailerConfig` objects.

    It is implemented as a class with class methods, effectively acting
    as a singleton accessible globally via import.
    """

    _retailers: Dict[str, UCPRetailerConfig] = {}

    @classmethod
    def register_retailer(cls, config: UCPRetailerConfig) -> None:
        """
        Registers a new UCP-compliant retailer's configuration.

        If a retailer with the same `retailer_id` is already registered,
        its configuration will be updated.

        Args:
            config: An instance of `UCPRetailerConfig` containing the
                    details for the retailer's UCP connection.
        """
        if config.retailer_id in cls._retailers:
            # In a real application, this might use a logging system.
            print(f"Warning: Retailer '{config.retailer_id}' already registered. Updating configuration.")
        cls._retailers[config.retailer_id] = config

    @classmethod
    def get_retailer_config(cls, retailer_id: str) -> Optional[UCPRetailerConfig]:
        """
        Retrieves the UCP configuration for a specific retailer.

        Args:
            retailer_id: The unique identifier of the retailer.

        Returns:
            An instance of `UCPRetailerConfig` if found, otherwise None.
        """
        return cls._retailers.get(retailer_id)

    @classmethod
    def list_retailers(cls) -> List[UCPRetailerConfig]:
        """
        Lists all registered UCP-compliant retailers.

        Returns:
            A list of `UCPRetailerConfig` objects for all registered retailers.
        """
        return list(cls._retailers.values())

    @classmethod
    def unregister_retailer(cls, retailer_id: str) -> bool:
        """
        Unregisters a UCP-compliant retailer's configuration.

        Args:
            retailer_id: The unique identifier of the retailer to unregister.

        Returns:
            True if the retailer was successfully unregistered, False otherwise.
        """
        if retailer_id in cls._retailers:
            del cls._retailers[retailer_id]
            return True
        return False

    @classmethod
    def clear_registry(cls) -> None:
        """
        Clears all registered retailer configurations from the registry.
        This method is primarily for testing or reinitialization purposes.
        """
        cls._retailers.clear()