from typing import List, Dict, Any, Optional, Tuple

# Assuming these imports based on common patterns in agent frameworks
# and the UVAI codebase structure.
from prescient_twin.capabilities.base import BaseCapability
from uvai.ucp.client import UCPClient
from uvai.ucp.models import ProductSearchResult, ProductSearchQuery

class ProductDiscovery(BaseCapability):
    """
    A capability for Prescient-Twin agents to discover products across UCP-compliant
    retailers using the Universal Commerce Protocol (UCP) client.

    This capability enables agents to search for products based on various criteria,
    retrieve detailed product information, and potentially filter results from
    multiple UCP-compliant retail sources.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ProductDiscovery capability with a UCP client.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary for the UCP client.
                                                Expected keys for the 'ucp_client' sub-dictionary
                                                include 'api_key' and 'base_url'.
                                                Example:
                                                {
                                                    "ucp_client": {
                                                        "api_key": "your_ucp_api_key",
                                                        "base_url": "https://api.ucp.example.com"
                                                    }
                                                }
        Raises:
            ValueError: If required UCP client configuration (api_key, base_url) is missing.
            RuntimeError: If the UCP client fails to initialize for other reasons.
        """
        super().__init__()
        self.config = config if config is not None else {}

        ucp_client_settings = self.config.get("ucp_client", {})
        api_key = ucp_client_settings.get("api_key")
        base_url = ucp_client_settings.get("base_url")

        if not api_key:
            raise ValueError(
                "UCP client 'api_key' must be provided in the capability configuration "
                "under the 'ucp_client' key."
            )
        if not base_url:
            raise ValueError(
                "UCP client 'base_url' must be provided in the capability configuration "
                "under the 'ucp_client' key."
            )

        try:
            self.ucp_client = UCPClient(api_key=api_key, base_url=base_url)
        except Exception as e:
            # Catch any potential errors during UCPClient instantiation (e.g., invalid URL format)
            raise RuntimeError(f"Failed to initialize UCPClient for ProductDiscovery: {e}") from e

    def search_products(
        self,
        query: str,
        retailer_ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ProductSearchResult], int]:
        """
        Searches for products across UCP-compliant retailers using the configured UCP client.

        Args:
            query (str): The primary search query string (e.g., "laptop", "running shoes").
            retailer_ids (Optional[List[str]]): A list of specific retailer IDs to search within.
                                                 If None, the search may span all configured or available retailers.
            category (Optional[str]): Filters products by a specific category (e.g., "Electronics", "Apparel").
            min_price (Optional[float]): Minimum price for products (inclusive).
            max_price (Optional[float]): Maximum price for products (inclusive).
            limit (int): Maximum number of products to return in the current page of results.
            offset (int): The starting index for the results, used for pagination.
                          (e.g., 0 for the first page, 10 for the second page with limit=10).
            sort_by (Optional[str]): Field and order to sort results by (e.g., 'price_asc', 'price_desc', 'relevance').
            filters (Optional[Dict[str, Any]]): A dictionary of additional key-value filters
                                                 (e.g., {"brand": "Nike", "color": "blue", "size": "M"}).

        Returns:
            Tuple[List[ProductSearchResult], int]: A tuple containing:
                - A list of `ProductSearchResult` objects, each representing a found product.
                  The length of this list will not exceed `limit`.
                - The total number of matching products found across all retailers,
                  which might be greater than the length of the returned list if `limit` is applied.

        Raises:
            RuntimeError: If the UCP client encounters an error during the search operation
                          (e.g., network issues, API errors).
        """
        try:
            # Construct the ProductSearchQuery object for the UCP client
            search_query = ProductSearchQuery(
                query=query,
                retailer_ids=retailer_ids,
                category=category,
                min_price=min_price,
                max_price=max_price,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                filters=filters,
            )
            
            # Call the UCP client's search method.
            # We assume ucp_client.search_products returns a tuple of (results_list, total_count).
            results, total_count = self.ucp_client.search_products(search_query)
            return results, total_count
        except Exception as e:
            # Log the error (in a real system) and re-raise as a RuntimeError for the agent to handle.
            raise RuntimeError(f"Product discovery failed for query '{query}': {e}") from e