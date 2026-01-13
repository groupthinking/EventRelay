from typing import Any, Dict, List, Optional, Protocol

# Define a protocol for the UCP client dependency
class UCPClientProtocol(Protocol):
    """
    Protocol defining the expected interface for a UCP client.
    This allows for dependency injection and easier testing, ensuring that
    any client passed to UCPProductDiscoveryService adheres to this contract.
    """

    async def search_products(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Searches for products in the UCP based on various criteria.

        Expected to return a dictionary containing search results, typically
        with a 'products' key holding a list of product dictionaries, and
        potentially other metadata like 'total_results'.

        Args:
            query: A search string (e.g., product name, description keywords).
            filters: A dictionary of key-value pairs for filtering (e.g., {"category": "electronics"}).
            limit: The maximum number of products to return.
            offset: The number of products to skip from the beginning of the results.

        Returns:
            A dictionary containing the search results.
        """
        ...

    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information for a specific product by its ID.

        Expected to return a dictionary representing the product's details if found,
        or None if the product does not exist or cannot be retrieved.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            A dictionary containing the product's details, or None.
        """
        ...


class UCPProductDiscoveryService:
    """
    Service for abstracting UCP client interactions for product search and retrieval.

    This service provides a simplified, agent-friendly interface to discover and
    retrieve product information from the Unified Commerce Platform (UCP),
    handling the underlying complexities of the UCP client.
    """

    def __init__(self, ucp_client: UCPClientProtocol):
        """
        Initializes the UCPProductDiscoveryService with a UCP client.

        Args:
            ucp_client: An instance of a UCP client that conforms to `UCPClientProtocol`.
        """
        self._ucp_client = ucp_client

    async def search_products(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Searches for products in the UCP based on a query string and optional filters.

        This method translates the high-level search request into a call to the
        underlying UCP client and processes its response.

        Args:
            query: A search string to find relevant products (e.g., product name, description).
            filters: A dictionary of key-value pairs to filter products (e.g., {"category": "electronics"}).
            limit: The maximum number of products to return. Defaults to 10.
            offset: The number of products to skip before starting to return results. Defaults to 0.

        Returns:
            A list of dictionaries, where each dictionary represents a product.
            Returns an empty list if no products are found, an error occurs, or the UCP client
            response does not contain a 'products' key.
            Each product dictionary is expected to contain at least 'id', 'name', 'description', 'price'.
        """
        try:
            ucp_response = await self._ucp_client.search_products(
                query=query, filters=filters, limit=limit, offset=offset
            )
            # Assuming the UCP client returns a dictionary like {"products": [...], "total_results": ...}
            products = ucp_response.get("products", [])
            return products
        except Exception as e:
            # In a real application, a proper logging framework should be used.
            # For now, a simple print statement is used for demonstration.
            print(f"Error searching products in UCP: {e}")
            # Depending on the desired error handling strategy, a custom exception
            # could be raised, or an empty list returned for graceful degradation.
            return []

    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information for a specific product by its ID.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            A dictionary containing the product's details if found, otherwise None.
            The dictionary is expected to contain at least 'id', 'name', 'description', 'price'.
        """
        try:
            ucp_response = await self._ucp_client.get_product_details(product_id)
            # Assuming the UCP client returns the product details directly or None
            return ucp_response
        except Exception as e:
            print(f"Error retrieving product details for ID '{product_id}' from UCP: {e}")
            return None

    async def get_products_by_category(
        self, category_id: str, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves products belonging to a specific category.

        This method leverages the generic `search_products` method by applying a category filter,
        providing a more specific interface for common agent requests.

        Args:
            category_id: The ID of the category to filter by.
            limit: The maximum number of products to return. Defaults to 10.
            offset: The number of products to skip before starting to return results. Defaults to 0.

        Returns:
            A list of dictionaries, where each dictionary represents a product.
            Returns an empty list if no products are found or an error occurs.
        """
        return await self.search_products(filters={"category_id": category_id}, limit=limit, offset=offset)

# Example of a simple mock UCP client for testing purposes (would typically be in a test file)
class MockUCPClient:
    """A mock UCP client for testing UCPProductDiscoveryService."""
    def __init__(self):
        self._products = {
            "prod123": {"id": "prod123", "name": "Laptop Pro", "description": "High-performance laptop", "price": 1200.00, "category_id": "electronics"},
            "prod124": {"id": "prod124", "name": "Mechanical Keyboard", "description": "Tactile RGB keyboard", "price": 150.00, "category_id": "accessories"},
            "prod125": {"id": "prod125", "name": "Wireless Mouse", "description": "Ergonomic wireless mouse", "price": 75.00, "category_id": "accessories"},
            "prod126": {"id": "prod126", "name": "Smartwatch X", "description": "Fitness tracker with notifications", "price": 299.99, "category_id": "electronics"},
        }

    async def search_products(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        results = []
        for product_id, product in self._products.items():
            match = True
            if query:
                if query.lower() not in product["name"].lower() and query.lower() not in product["description"].lower():
                    match = False
            if filters:
                for key, value in filters.items():
                    if product.get(key) != value:
                        match = False
                        break
            if match:
                results.append(product)

        total_results = len(results)
        paginated_results = results[offset : offset + limit]
        return {"products": paginated_results, "total_results": total_results}

    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self._products.get(product_id)

# Example of how to use the service (would typically be in an agent or main application file)
async def main():
    mock_ucp_client = MockUCPClient()
    product_service = UCPProductDiscoveryService(ucp_client=mock_ucp_client)

    print("Searching for 'laptop':")
    laptops = await product_service.search_products(query="laptop")
    for product in laptops:
        print(f"- {product['name']} ({product['id']}) - ${product['price']:.2f}")

    print("\nSearching for products in 'accessories' category:")
    accessories = await product_service.get_products_by_category(category_id="accessories")
    for product in accessories:
        print(f"- {product['name']} ({product['id']}) - ${product['price']:.2f}")

    print("\nGetting details for 'prod123':")
    product_details = await product_service.get_product_details(product_id="prod123")
    if product_details:
        print(f"Details: {product_details}")
    else:
        print("Product 'prod123' not found.")

    print("\nGetting details for 'nonexistent_prod':")
    nonexistent_product = await product_service.get_product_details(product_id="nonexistent_prod")
    if nonexistent_product:
        print(f"Details: {nonexistent_product}")
    else:
        print("Product 'nonexistent_prod' not found.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())