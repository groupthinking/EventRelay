from abc import ABC, abstractmethod
from typing import List, Dict, Any, TypedDict

# --- Type Definitions for Commerce Entities ---

class ProductInfo(TypedDict):
    """Basic information about a product."""
    product_id: str
    name: str
    price: float
    currency: str
    description: str
    image_url: str
    # Add more common fields as needed, e.g., 'category', 'brand'

class ProductDetails(ProductInfo):
    """Detailed information about a product."""
    sku: str
    category: str
    brand: str
    attributes: Dict[str, Any]  # e.g., {'color': 'red', 'size': 'M'}
    availability: int  # Current stock level
    # Add more detailed fields as needed, e.g., 'reviews', 'related_products'

class CartItem(TypedDict):
    """Represents an item within a shopping cart."""
    item_id: str  # Unique ID for this specific cart item instance (not product_id)
    product_id: str
    name: str
    quantity: int
    price: float  # Price per unit at the time of adding to cart
    total_price: float  # quantity * price

class CartDetails(TypedDict):
    """Details of the current shopping cart."""
    cart_id: str
    items: List[CartItem]
    subtotal: float
    total: float
    currency: str
    # Add more fields like 'discounts', 'shipping_estimates', etc.

class OrderConfirmation(TypedDict):
    """Confirmation details after a successful checkout."""
    order_id: str
    status: str  # e.g., "pending", "confirmed", "failed"
    total_amount: float
    currency: str
    confirmation_date: str  # ISO format date string
    # Add more fields like 'estimated_delivery', 'payment_status', etc.

class OrderSummary(TypedDict):
    """Summary information for an order."""
    order_id: str
    order_date: str  # ISO format date string
    total_amount: float
    currency: str
    status: str  # e.g., "shipped", "delivered", "cancelled"

class OrderDetails(OrderSummary):
    """Detailed information for a specific order."""
    items: List[CartItem]  # Or a similar structure for ordered items
    shipping_address: Dict[str, Any]  # Can be a more specific TypedDict if needed
    billing_address: Dict[str, Any]  # Can be a more specific TypedDict if needed
    payment_method: str
    # Add more fields as needed, e.g., 'shipping_method', 'tracking_number'

class Address(TypedDict):
    """Standard address structure."""
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    # Add more fields like 'apartment', 'address_line_2', etc.

class PaymentInfo(TypedDict):
    """Abstract payment information structure."""
    method: str  # e.g., "credit_card", "paypal", "apple_pay"
    details: Dict[str, Any]  # Specific details for the payment method (e.g., token, last 4 digits)

# --- UCPCommerceAgent Interface Definition ---

class UCPCommerceAgent(ABC):
    """
    Abstract Base Class (ABC) for agents designed to perform commerce tasks
    via a Unified Commerce Platform (UCP).

    This interface defines the core capabilities expected from any UCP commerce agent,
    ensuring a consistent interaction model for various commerce operations.
    Subclasses must implement all abstract methods.
    """

    @abstractmethod
    async def search_products(self, query: str, **kwargs: Any) -> List[ProductInfo]:
        """
        Searches for products based on a given query string.

        Args:
            query: The search term or phrase.
            **kwargs: Additional search parameters (e.g., filters, pagination, category, brand).

        Returns:
            A list of ProductInfo dictionaries matching the search criteria.
            Returns an empty list if no products are found.
        """
        pass

    @abstractmethod
    async def get_product_details(self, product_id: str) -> ProductDetails:
        """
        Retrieves detailed information for a specific product.

        Args:
            product_id: The unique identifier of the product.

        Returns:
            A ProductDetails dictionary for the specified product.

        Raises:
            ProductNotFoundError: If the product with the given ID is not found.
        """
        pass

    @abstractmethod
    async def add_to_cart(self, product_id: str, quantity: int = 1, **kwargs: Any) -> CartDetails:
        """
        Adds a specified quantity of a product to the shopping cart.

        Args:
            product_id: The unique identifier of the product to add.
            quantity: The number of units to add (defaults to 1).
            **kwargs: Additional parameters (e.g., product options like size, color, variant_id).

        Returns:
            The current state of the shopping cart after the operation.

        Raises:
            ProductNotFoundError: If the product does not exist.
            InsufficientStockError: If the product is out of stock or quantity exceeds available.
            InvalidProductOptionError: If provided product options are invalid.
        """
        pass

    @abstractmethod
    async def view_cart(self) -> CartDetails:
        """
        Retrieves the current contents and details of the shopping cart.

        Returns:
            A CartDetails dictionary representing the current cart.
            Returns an empty cart structure if the cart is empty or not initialized.
        """
        pass

    @abstractmethod
    async def update_cart_item(self, item_id: str, quantity: int) -> CartDetails:
        """
        Updates the quantity of a specific item already in the cart.

        Args:
            item_id: The unique identifier of the item within the cart (not product_id).
            quantity: The new quantity for the item. If 0, the item should be removed.

        Returns:
            The current state of the shopping cart after the operation.

        Raises:
            CartItemNotFoundError: If the item with the given ID is not found in the cart.
            InsufficientStockError: If the new quantity exceeds available stock.
            InvalidQuantityError: If the quantity is negative.
        """
        pass

    @abstractmethod
    async def remove_from_cart(self, item_id: str) -> CartDetails:
        """
        Removes a specific item from the shopping cart.

        Args:
            item_id: The unique identifier of the item within the cart.

        Returns:
            The current state of the shopping cart after the operation.

        Raises:
            CartItemNotFoundError: If the item with the given ID is not found in the cart.
        """
        pass

    @abstractmethod
    async def checkout(self, shipping_address: Address, payment_info: PaymentInfo, **kwargs: Any) -> OrderConfirmation:
        """
        Initiates the checkout process, creating an order from the current cart.

        Args:
            shipping_address: The address for shipping the order.
            payment_info: Details required for processing payment.
            **kwargs: Additional checkout parameters (e.g., billing address, shipping method, discount codes).

        Returns:
            An OrderConfirmation dictionary upon successful order placement.

        Raises:
            EmptyCartError: If the cart is empty.
            PaymentProcessingError: If payment fails.
            InvalidAddressError: If the shipping address is invalid.
            CheckoutError: For other general checkout failures.
        """
        pass

    @abstractmethod
    async def get_order_history(self, **kwargs: Any) -> List[OrderSummary]:
        """
        Retrieves a list of past orders for the current user/session.

        Args:
            **kwargs: Additional parameters for filtering or pagination of order history.

        Returns:
            A list of OrderSummary dictionaries.
            Returns an empty list if no orders are found.
        """
        pass

    @abstractmethod
    async def get_order_details(self, order_id: str) -> OrderDetails:
        """
        Retrieves detailed information for a specific order.

        Args:
            order_id: The unique identifier of the order.

        Returns:
            An OrderDetails dictionary for the specified order.

        Raises:
            OrderNotFoundError: If the order with the given ID is not found.
        """
        pass