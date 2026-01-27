from typing import Dict, List, Optional, TypedDict, Any

class CartItem(TypedDict):
    """
    Represents a single item within the shopping cart, designed to be UCP-compliant.

    Attributes:
        item_id (str): A unique identifier for the item.
        name (str): The name or title of the item.
        description (Optional[str]): An optional detailed description of the item.
        price (float): The unit price of the item.
        currency (str): The currency code for the item's price (e.g., "USD", "EUR").
        quantity (int): The number of units of this item in the cart.
        metadata (Dict[str, Any]): A dictionary for any additional UCP-specific
                                    or custom fields associated with the item.
    """
    item_id: str
    name: str
    description: Optional[str]
    price: float
    currency: str
    quantity: int
    metadata: Dict[str, Any]


class ShoppingCart:
    """
    Manages a shopping cart capability for a prescient-twin agent.

    This class provides methods to add, update, and remove items from a
    UCP-compliant shopping cart, along with utility functions to inspect
    the cart's contents and totals.
    """
    _cart: Dict[str, CartItem]

    def __init__(self) -> None:
        """
        Initializes an empty shopping cart.
        """
        self._cart = {}

    def add_item(
        self,
        item_id: str,
        name: str,
        price: float,
        quantity: int,
        currency: str = "USD",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Adds a new item to the shopping cart or increases the quantity of an existing item.

        If an item with the given `item_id` already exists in the cart, its quantity
        will be incremented by the specified `quantity`. Other attributes (name, price, etc.)
        of the existing item will remain unchanged.

        Args:
            item_id: A unique identifier for the item.
            name: The name of the item.
            price: The unit price of the item.
            quantity: The quantity of the item to add. Must be a positive integer.
            currency: The currency of the item price (default: "USD").
            description: An optional description of the item.
            metadata: Optional additional UCP-compliant metadata for the item.

        Raises:
            ValueError: If the provided quantity is not a positive integer.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        if item_id in self._cart:
            # If item exists, update its quantity
            self._cart[item_id]["quantity"] += quantity
        else:
            # Add new item
            item: CartItem = {
                "item_id": item_id,
                "name": name,
                "description": description,
                "price": price,
                "currency": currency,
                "quantity": quantity,
                "metadata": metadata if metadata is not None else {},
            }
            self._cart[item_id] = item

    def update_item_quantity(self, item_id: str, new_quantity: int) -> None:
        """
        Updates the quantity of an existing item in the shopping cart.

        If `new_quantity` is 0 or less, the item will be removed from the cart.

        Args:
            item_id: The unique identifier of the item to update.
            new_quantity: The new quantity for the item. Must be a non-negative integer.

        Raises:
            KeyError: If the item with the given `item_id` does not exist in the cart.
            ValueError: If `new_quantity` is a negative integer.
        """
        if item_id not in self._cart:
            raise KeyError(f"Item with ID '{item_id}' not found in the cart.")
        if not isinstance(new_quantity, int) or new_quantity < 0:
            raise ValueError("New quantity must be a non-negative integer.")

        if new_quantity == 0:
            self.remove_item(item_id)
        else:
            self._cart[item_id]["quantity"] = new_quantity

    def remove_item(self, item_id: str) -> None:
        """
        Removes an item completely from the shopping cart.

        Args:
            item_id: The unique identifier of the item to remove.

        Raises:
            KeyError: If the item with the given `item_id` does not exist in the cart.
        """
        if item_id not in self._cart:
            raise KeyError(f"Item with ID '{item_id}' not found in the cart.")
        del self._cart[item_id]

    def get_item(self, item_id: str) -> Optional[CartItem]:
        """
        Retrieves a specific item from the shopping cart by its ID.

        Args:
            item_id: The unique identifier of the item to retrieve.

        Returns:
            The `CartItem` dictionary if found, otherwise `None`.
        """
        return self._cart.get(item_id)

    def get_all_items(self) -> List[CartItem]:
        """
        Retrieves all items currently in the shopping cart.

        Returns:
            A list of all `CartItem` dictionaries in the cart.
        """
        return list(self._cart.values())

    def get_total_items(self) -> int:
        """
        Calculates the total number of distinct item types in the cart.

        Returns:
            The count of distinct items.
        """
        return len(self._cart)

    def get_total_quantity(self) -> int:
        """
        Calculates the total quantity of all items (sum of quantities) in the cart.

        Returns:
            The sum of quantities of all items.
        """
        return sum(item["quantity"] for item in self._cart.values())

    def get_total_price(self) -> float:
        """
        Calculates the total price of all items in the cart.

        Note: This method assumes all items are in the same currency.
        For multi-currency carts, a more sophisticated currency conversion
        or per-currency total calculation would be required.

        Returns:
            The sum of (price * quantity) for all items.
        """
        return sum(item["price"] * item["quantity"] for item in self._cart.values())

    def clear_cart(self) -> None:
        """
        Empties the entire shopping cart, removing all items.
        """
        self._cart.clear()

    def is_empty(self) -> bool:
        """
        Checks if the shopping cart is empty.

        Returns:
            True if the cart contains no items, False otherwise.
        """
        return not bool(self._cart)