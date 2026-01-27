import uuid
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

# --- Placeholder UCP Client ---
# In a real implementation, this would be a robust client handling API calls,
# authentication, error handling, etc., to the Unified Commerce Platform (UCP).
# For demonstration purposes, it simulates UCP interactions with in-memory data.

class UCPClient:
    """
    A placeholder client for interacting with the Unified Commerce Platform (UCP).
    Simulates product search, cart management, and checkout functionalities.
    """
    _products: Dict[str, Dict[str, Any]] = PrivateAttr()
    _cart: Dict[str, Dict[str, Any]] = PrivateAttr()
    _orders: List[Dict[str, Any]] = PrivateAttr()
    _user_id: str = PrivateAttr()

    def __init__(self, user_id: str = "default_user") -> None:
        self._user_id = user_id
        self._products = {
            "prod_1": {"id": "prod_1", "name": "Laptop Pro X", "description": "High-performance laptop with 16GB RAM and SSD.", "price": 1200.00, "category": "Electronics", "stock": 10},
            "prod_2": {"id": "prod_2", "name": "Wireless Mouse", "description": "Ergonomic wireless mouse with long battery life.", "price": 25.00, "category": "Electronics", "stock": 50},
            "prod_3": {"id": "prod_3", "name": "Mechanical Keyboard", "description": "RGB mechanical keyboard with tactile switches for gaming and typing.", "price": 90.00, "category": "Electronics", "stock": 20},
            "prod_4": {"id": "prod_4", "name": "Coffee Mug", "description": "Ceramic coffee mug, 12oz, dishwasher safe.", "price": 15.00, "category": "Home Goods", "stock": 100},
            "prod_5": {"id": "prod_5", "name": "Desk Lamp", "description": "Adjustable LED desk lamp with multiple brightness settings.", "price": 45.00, "category": "Home Goods", "stock": 30},
            "prod_6": {"id": "prod_6", "name": "Python Programming Book", "description": "A comprehensive guide to Python programming, 3rd edition.", "price": 50.00, "category": "Books", "stock": 15},
            "prod_7": {"id": "prod_7", "name": "Noise-Cancelling Headphones", "description": "Over-ear headphones with active noise cancellation.", "price": 199.99, "category": "Electronics", "stock": 8},
        }
        self._cart = {}
        self._orders = []

    def search_products(self, query: str, category: Optional[str] = None,
                        min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Simulates searching for products in the UCP catalog.
        Filters by query, category, and price range.
        """
        results = []
        query_lower = query.lower()
        for prod_id, product in self._products.items():
            match_query = query_lower in product["name"].lower() or query_lower in product["description"].lower()
            match_category = category is None or product["category"].lower() == category.lower()
            match_min_price = min_price is None or product["price"] >= min_price
            match_max_price = max_price is None or product["price"] <= max_price

            if match_query and match_category and match_min_price and match_max_price:
                results.append(product)
        return results

    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Simulates retrieving detailed information for a specific product."""
        return self._products.get(product_id)

    def add_to_cart(self, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Simulates adding a product to the user's shopping cart."""
        product = self._products.get(product_id)
        if not product:
            return {"success": False, "message": f"Product with ID '{product_id}' not found."}
        if product["stock"] < quantity:
            return {"success": False, "message": f"Not enough stock for product '{product['name']}'. Available: {product['stock']}"}

        if product_id in self._cart:
            self._cart[product_id]["quantity"] += quantity
        else:
            self._cart[product_id] = {"product": product, "quantity": quantity}
        return {"success": True, "message": f"Added {quantity} of '{product['name']}' to cart."}

    def get_cart_contents(self) -> List[Dict[str, Any]]:
        """Simulates retrieving the current contents of the shopping cart."""
        return list(self._cart.values())

    def update_cart_item(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """
        Simulates updating the quantity of a product in the cart or removing it.
        Setting quantity to 0 removes the item.
        """
        if product_id not in self._cart:
            return {"success": False, "message": f"Product with ID '{product_id}' not in cart."}

        product = self._cart[product_id]["product"]
        if quantity <= 0:
            del self._cart[product_id]
            return {"success": True, "message": f"Removed '{product['name']}' from cart."}
        elif product["stock"] < quantity:
            return {"success": False, "message": f"Not enough stock for product '{product['name']}'. Available: {product['stock']}"}
        else:
            self._cart[product_id]["quantity"] = quantity
            return {"success": True, "message": f"Updated quantity of '{product['name']}' to {quantity}."}

    def checkout(self, shipping_address: str, payment_method_id: str) -> Dict[str, Any]:
        """Simulates completing a purchase of items in the cart."""
        if not self._cart:
            return {"success": False, "message": "Cart is empty. Cannot checkout."}

        order_id = str(uuid.uuid4())
        total_amount = sum(item["product"]["price"] * item["quantity"] for item in self._cart.values())
        order = {
            "order_id": order_id,
            "user_id": self._user_id,
            "items": list(self._cart.values()),
            "shipping_address": shipping_address,
            "payment_method_id": payment_method_id,
            "total_amount": total_amount,
            "status": "completed"
        }
        self._orders.append(order)
        # Deduct stock
        for item in self._cart.values():
            prod_id = item["product"]["id"]
            if prod_id in self._products: # Ensure product still exists in catalog
                self._products[prod_id]["stock"] -= item["quantity"]
        self._cart.clear() # Empty cart after checkout
        return {"success": True, "message": f"Order '{order_id}' placed successfully.", "order": order}

    def get_order_history(self) -> List[Dict[str, Any]]:
        """Simulates retrieving the user's past purchase orders."""
        return self._orders


# --- Agent Tools ---

class UCPToolMixin(BaseModel):
    """
    A mixin for UCP-related tools to inject the UCPClient instance.
    This allows tools to share the same client for stateful interactions.
    """
    ucp_client: UCPClient = Field(exclude=True) # Exclude from serialization/dumping

    class Config:
        """Pydantic configuration for the mixin."""
        arbitrary_types_allowed = True


class UCPProductSearchInput(BaseModel):
    """Input schema for UCPProductSearchTool."""
    query: str = Field(description="The search query for products (e.g., 'laptop', 'coffee mug').")
    category: Optional[str] = Field(None, description="Optional: Filter products by category (e.g., 'Electronics', 'Home Goods', 'Books').")
    min_price: Optional[float] = Field(None, description="Optional: Minimum price for products.")
    max_price: Optional[float] = Field(None, description="Optional: Maximum price for products.")


class UCPProductSearchTool(UCPToolMixin, BaseTool):
    """
    A tool to search for products in the Unified Commerce Platform (UCP) catalog.
    This tool allows agents to discover products based on keywords, categories, and price ranges.
    """
    name: str = "ucp_product_search"
    description: str = (
        "Search for products in the UCP catalog based on a query, category, and price range. "
        "Returns a list of matching products with their details (id, name, description, price, category, stock). "
        "Use this tool to find products before adding them to the cart or viewing details."
    )
    args_schema: Type[BaseModel] = UCPProductSearchInput

    def _run(self, query: str, category: Optional[str] = None,
             min_price: Optional[float] = None, max_price: Optional[float] = None) -> str:
        """
        Executes the product search using the UCP client.
        Returns a formatted string of search results or an error message.
        """
        try:
            products = self.ucp_client.search_products(query, category, min_price, max_price)
            if not products:
                return "No products found matching the criteria."
            
            formatted_products = []
            for p in products:
                formatted_products.append(
                    f"ID: {p['id']}, Name: {p['name']}, Price: ${p['price']:.2f}, Category: {p['category']}, Stock: {p['stock']}"
                )
            return "Found products:\n" + "\n".join(formatted_products)
        except Exception as e:
            return f"Error searching for products: {e}"


class UCPProductDetailsInput(BaseModel):
    """Input schema for UCPProductDetailsTool."""
    product_id: str = Field(description="The unique identifier of the product to retrieve details for.")


class UCPProductDetailsTool(UCPToolMixin, BaseTool):
    """
    A tool to retrieve detailed information for a specific product from the UCP catalog.
    Useful for getting more context about a product found via search or by a known ID.
    """
    name: str = "ucp_product_details"
    description: str = (
        "Retrieve detailed information for a specific product using its unique ID. "
        "Returns product details including ID, name, description, price, category, and current stock. "
        "Use this after searching for products to get more information about a specific item."
    )
    args_schema: Type[BaseModel] = UCPProductDetailsInput

    def _run(self, product_id: str) -> str:
        """
        Executes the product details retrieval using the UCP client.
        Returns a formatted string of product details or an error message.
        """
        try:
            product = self.ucp_client.get_product_details(product_id)
            if not product:
                return f"Product with ID '{product_id}' not found."
            
            return (
                f"Product Details for ID '{product_id}':\n"
                f"Name: {product['name']}\n"
                f"Description: {product['description']}\n"
                f"Price: ${product['price']:.2f}\n"
                f"Category: {product['category']}\n"
                f"Stock: {product['stock']}"
            )
        except Exception as e:
            return f"Error retrieving product details: {e}"


class UCPAddToCartInput(BaseModel):
    """Input schema for UCPAddToCartTool."""
    product_id: str = Field(description="The unique identifier of the product to add to the cart.")
    quantity: int = Field(1, description="The quantity of the product to add. Must be a positive integer.")


class UCPAddToCartTool(UCPToolMixin, BaseTool):
    """
    A tool to add a specified quantity of a product to the user's shopping cart in UCP.
    """
    name: str = "ucp_add_to_cart"
    description: str = (
        "Add a specified quantity of a product to the user's shopping cart. "
        "Requires the product's unique ID and the desired quantity. "
        "Returns a confirmation message or an error if the product is not found or out of stock. "
        "Ensure the product ID is valid and quantity is positive."
    )
    args_schema: Type[BaseModel] = UCPAddToCartInput

    def _run(self, product_id: str, quantity: int = 1) -> str:
        """
        Executes the add to cart operation using the UCP client.
        Returns a confirmation or error message.
        """
        if quantity <= 0:
            return "Quantity must be a positive integer to add to cart."
        try:
            result = self.ucp_client.add_to_cart(product_id, quantity)
            return result["message"]
        except Exception as e:
            return f"Error adding product to cart: {e}"


class UCPViewCartInput(BaseModel):
    """Input schema for UCPViewCartTool."""
    # No specific inputs needed for viewing the cart.


class UCPViewCartTool(UCPToolMixin, BaseTool):
    """
    A tool to view the current contents of the user's shopping cart in UCP.
    """
    name: str = "ucp_view_cart"
    description: str = (
        "View the current contents of the user's shopping cart. "
        "Returns a list of items in the cart, including product details and quantities, "
        "and the total cart value, or a message if the cart is empty."
    )
    args_schema: Type[BaseModel] = UCPViewCartInput

    def _run(self) -> str:
        """
        Executes the view cart operation using the UCP client.
        Returns a formatted string of cart contents or an empty cart message.
        """
        try:
            cart_contents = self.ucp_client.get_cart_contents()
            if not cart_contents:
                return "Your shopping cart is empty."
            
            formatted_items = []
            total_price = 0.0
            for item in cart_contents:
                product = item["product"]
                quantity = item["quantity"]
                item_total = product["price"] * quantity
                total_price += item_total
                formatted_items.append(
                    f"  - {product['name']} (ID: {product['id']}), Quantity: {quantity}, Price: ${product['price']:.2f} each, Total: ${item_total:.2f}"
                )
            
            return "Current shopping cart:\n" + "\n".join(formatted_items) + f"\nTotal Cart Value: ${total_price:.2f}"
        except Exception as e:
            return f"Error viewing cart contents: {e}"


class UCPUpdateCartItemInput(BaseModel):
    """Input schema for UCPUpdateCartItemTool."""
    product_id: str = Field(description="The unique identifier of the product in the cart to update.")
    quantity: int = Field(description="The new quantity for the product. Set to 0 to remove the item from the cart. Must be a non-negative integer.")


class UCPUpdateCartItemTool(UCPToolMixin, BaseTool):
    """
    A tool to update the quantity of an item in the shopping cart or remove it entirely.
    """
    name: str = "ucp_update_cart_item"
    description: str = (
        "Update the quantity of a specific product in the shopping cart. "
        "Provide the product's unique ID and the new desired quantity. "
        "Setting the quantity to 0 will remove the item from the cart. "
        "Returns a confirmation message or an error. Ensure quantity is non-negative."
    )
    args_schema: Type[BaseModel] = UCPUpdateCartItemInput

    def _run(self, product_id: str, quantity: int) -> str:
        """
        Executes the update cart item operation using the UCP client.
        Returns a confirmation or error message.
        """
        if quantity < 0:
            return "Quantity cannot be negative. Use 0 to remove an item."
        try:
            result = self.ucp_client.update_cart_item(product_id, quantity)
            return result["message"]
        except Exception as e:
            return f"Error updating cart item: {e}"


class UCPCheckoutInput(BaseModel):
    """Input schema for UCPCheckoutTool."""
    shipping_address: str = Field(description="The full shipping address for the order (e.g., '123 Main St, Anytown, USA').")
    payment_method_id: str = Field(description="The ID of the payment method to use for the purchase (e.g., 'credit_card_123', 'paypal_account').")


class UCPCheckoutTool(UCPToolMixin, BaseTool):
    """
    A tool to complete the purchase of items currently in the shopping cart.
    This tool finalizes the transaction, creating an order and clearing the cart.
    """
    name: str = "ucp_checkout"
    description: str = (
        "Complete the purchase of all items currently in the shopping cart. "
        "Requires a shipping address and a payment method ID. "
        "Returns an order confirmation with order ID and total amount, or an error if the cart is empty or checkout fails."
    )
    args_schema: Type[BaseModel] = UCPCheckoutInput

    def _run(self, shipping_address: str, payment_method_id: str) -> str:
        """
        Executes the checkout operation using the UCP client.
        Returns an order confirmation or error message.
        """
        try:
            result = self.ucp_client.checkout(shipping_address, payment_method_id)
            if result["success"]:
                order = result["order"]
                return (
                    f"Purchase completed successfully! Order ID: {order['order_id']}. "
                    f"Total amount: ${order['total_amount']:.2f}. "
                    f"Shipping to: {order['shipping_address']}."
                )
            else:
                return result["message"]
        except Exception as e:
            return f"Error during checkout: {e}"


class UCPViewOrderHistoryInput(BaseModel):
    """Input schema for UCPViewOrderHistoryTool."""
    # No specific inputs needed for viewing order history.


class UCPViewOrderHistoryTool(UCPToolMixin, BaseTool):
    """
    A tool to view the user's past purchase orders from UCP.
    """
    name: str = "ucp_view_order_history"
    description: str = (
        "View a list of the user's past purchase orders. "
        "Returns a summary of each order, including order ID, total amount, status, and items purchased, "
        "or a message if no orders are found."
    )
    args_schema: Type[BaseModel] = UCPViewOrderHistoryInput

    def _run(self) -> str:
        """
        Executes the view order history operation using the UCP client.
        Returns a formatted string of past orders or a message if no orders exist.
        """
        try:
            orders = self.ucp_client.get_order_history()
            if not orders:
                return "You have no past orders."
            
            formatted_orders = []
            for order in orders:
                items_summary = ", ".join([f"{item['quantity']}x {item['product']['name']}" for item in order['items']])
                formatted_orders.append(
                    f"Order ID: {order['order_id']}, Total: ${order['total_amount']:.2f}, Status: {order['status']}, Items: {items_summary}"
                )
            return "Your past orders:\n" + "\n".join(formatted_orders)
        except Exception as e:
            return f"Error retrieving order history: {e}"