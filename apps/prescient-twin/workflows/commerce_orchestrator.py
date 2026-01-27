from typing import Any, Dict, List, Optional, Protocol

# Define simple protocols for the agent and UCP client interfaces
# This helps with type hinting and clarifies expected methods without
# requiring concrete implementations in this file.

class AgentProtocol(Protocol):
    """
    Protocol defining the expected interface for an agent interacting with the orchestrator.
    """
    def decide_product_search_query(self, initial_query: str) -> str:
        """
        Asks the agent to formulate a product search query based on an initial user query.
        """
        ...

    def select_products_from_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Asks the agent to select products from a list of search results.
        Returns a list of selected product dictionaries.
        """
        ...

    def decide_cart_actions(self, current_cart: Dict[str, Any], available_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Asks the agent to decide on actions for the cart (add, update quantity, remove).
        Returns a list of action dictionaries, e.g.,
        [{"action": "add", "product_id": "p1", "quantity": 1},
         {"action": "update", "item_id": "c1", "quantity": 2},
         {"action": "remove", "item_id": "c2"}]
        """
        ...

    def confirm_checkout(self, cart_details: Dict[str, Any]) -> bool:
        """
        Asks the agent to confirm if the checkout process should proceed with the given cart.
        """
        ...

    def get_shipping_payment_info(self) -> Dict[str, Any]:
        """
        Asks the agent to provide or prompt for shipping and payment information.
        Returns a dictionary with 'shipping_address' and 'payment_details'.
        """
        ...

    def acknowledge_order_confirmation(self, order_details: Dict[str, Any]) -> None:
        """
        Informs the agent about the successful order confirmation.
        """
        ...

class UCPClientProtocol(Protocol):
    """
    Protocol defining the expected interface for a UCP (Unified Commerce Platform) client.
    """
    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches for products using the UCP.
        Returns a list of product dictionaries.
        """
        ...

    def get_cart(self) -> Dict[str, Any]:
        """
        Retrieves the current state of the shopping cart from the UCP.
        Returns a dictionary representing the cart.
        """
        ...

    def add_to_cart(self, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        Adds a product to the cart in the UCP.
        Returns the updated cart details.
        """
        ...

    def update_cart_item(self, item_id: str, quantity: int) -> Dict[str, Any]:
        """
        Updates the quantity of an item in the cart in the UCP.
        Returns the updated cart details.
        """
        ...

    def remove_from_cart(self, item_id: str) -> Dict[str, Any]:
        """
        Removes an item from the cart in the UCP.
        Returns the updated cart details.
        """
        ...

    def initiate_checkout(self, cart_id: str, shipping_info: Dict[str, Any], payment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiates the checkout process in the UCP.
        Returns order confirmation details.
        """
        ...

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieves the status of an order from the UCP.
        """
        ...


class CommerceOrchestrator:
    """
    An orchestration layer to manage complex agentic commerce workflows.

    This orchestrator guides an agent through product discovery, cart management,
    and checkout processes by leveraging Unified Commerce Platform (UCP) capabilities.
    """

    def __init__(self, agent: AgentProtocol, ucp_client: UCPClientProtocol):
        """
        Initializes the CommerceOrchestrator with an agent and a UCP client.

        Args:
            agent: An object conforming to AgentProtocol, responsible for decision-making.
            ucp_client: An object conforming to UCPClientProtocol, responsible for
                        interacting with the Unified Commerce Platform.
        """
        self._agent = agent
        self._ucp_client = ucp_client
        self._current_cart: Dict[str, Any] = {}
        self._available_products: List[Dict[str, Any]] = [] # Products discovered during the session

    def _product_discovery_stage(self, initial_query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Guides the agent through the product discovery process.

        Args:
            initial_query: The initial user query for product discovery.

        Returns:
            A list of selected products if discovery is successful, otherwise None.
        """
        print(f"Orchestrator: Starting product discovery for query: '{initial_query}'")
        try:
            # Agent decides the actual search query
            search_query = self._agent.decide_product_search_query(initial_query)
            print(f"Agent decided to search for: '{search_query}'")

            # UCP client performs the search
            search_results = self._ucp_client.search_products(search_query)
            if not search_results:
                print("No products found for the query.")
                return None

            self._available_products.extend(search_results) # Keep track of discovered products
            print(f"Found {len(search_results)} products. Asking agent to select.")

            # Agent selects products from the search results
            selected_products = self._agent.select_products_from_results(search_results)

            if not selected_products:
                print("Agent did not select any products.")
                return None

            print(f"Agent selected {len(selected_products)} products.")
            return selected_products

        except Exception as e:
            print(f"Error during product discovery: {e}")
            return None

    def _cart_management_stage(self, products_to_consider: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Manages the shopping cart based on agent decisions.

        Args:
            products_to_consider: A list of products that the agent might want to add/manage.

        Returns:
            The final state of the cart if management is successful, otherwise None.
        """
        print("Orchestrator: Starting cart management stage.")
        try:
            # Get current cart state from UCP
            self._current_cart = self._ucp_client.get_cart()
            print(f"Current cart state: {self._current_cart}")

            # Agent decides on cart actions (add, update, remove)
            # The agent might use products_to_consider and current_cart to make decisions.
            cart_actions = self._agent.decide_cart_actions(self._current_cart, products_to_consider)

            if not cart_actions:
                print("Agent decided no cart actions are needed.")
                return self._current_cart

            print(f"Agent decided {len(cart_actions)} cart actions.")
            for action in cart_actions:
                action_type = action.get("action")
                if action_type == "add":
                    product_id = action.get("product_id")
                    quantity = action.get("quantity", 1)
                    if product_id:
                        print(f"Adding product {product_id} (qty: {quantity}) to cart.")
                        self._current_cart = self._ucp_client.add_to_cart(product_id, quantity)
                elif action_type == "update":
                    item_id = action.get("item_id")
                    quantity = action.get("quantity")
                    if item_id is not None and quantity is not None:
                        print(f"Updating cart item {item_id} to quantity {quantity}.")
                        self._current_cart = self._ucp_client.update_cart_item(item_id, quantity)
                elif action_type == "remove":
                    item_id = action.get("item_id")
                    if item_id is not None:
                        print(f"Removing cart item {item_id}.")
                        self._current_cart = self._ucp_client.remove_from_cart(item_id)
                else:
                    print(f"Unknown cart action: {action_type}")

            print(f"Cart after actions: {self._current_cart}")
            return self._current_cart

        except Exception as e:
            print(f"Error during cart management: {e}")
            return None

    def _checkout_stage(self, cart_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Guides the agent through the checkout process.

        Args:
            cart_details: The current state of the shopping cart.

        Returns:
            Order confirmation details if checkout is successful, otherwise None.
        """
        print("Orchestrator: Starting checkout stage.")
        if not cart_details or not cart_details.get("items"):
            print("Cart is empty or invalid, cannot proceed to checkout.")
            return None

        try:
            # Agent confirms checkout
            if not self._agent.confirm_checkout(cart_details):
                print("Agent decided not to proceed with checkout.")
                return None

            print("Agent confirmed checkout. Gathering shipping and payment info.")
            # Agent provides/prompts for shipping and payment info
            checkout_info = self._agent.get_shipping_payment_info()
            shipping_info = checkout_info.get("shipping_address")
            payment_info = checkout_info.get("payment_details")

            if not shipping_info or not payment_info:
                print("Missing shipping or payment information for checkout.")
                return None

            # UCP client initiates checkout
            cart_id = cart_details.get("id", "default_cart_id") # Assuming cart has an ID
            order_confirmation = self._ucp_client.initiate_checkout(cart_id, shipping_info, payment_info)

            if order_confirmation and order_confirmation.get("order_id"):
                print(f"Checkout successful! Order ID: {order_confirmation['order_id']}")
                # Inform the agent about the successful order
                self._agent.acknowledge_order_confirmation(order_confirmation)
                return order_confirmation
            else:
                print("Checkout failed or no order ID returned.")
                return None

        except Exception as e:
            print(f"Error during checkout: {e}")
            return None

    def run_workflow(self, initial_query: str) -> Optional[Dict[str, Any]]:
        """
        Runs the complete agentic commerce workflow from discovery to checkout.

        Args:
            initial_query: The initial user query to start the commerce journey.

        Returns:
            The final order confirmation details if the workflow completes successfully,
            otherwise None.
        """
        print(f"\n--- Starting Commerce Workflow for: '{initial_query}' ---")

        # 1. Product Discovery
        selected_products = self._product_discovery_stage(initial_query)
        if not selected_products:
            print("Workflow terminated: Product discovery failed or no products selected.")
            return None

        # 2. Cart Management
        # The agent might want to add the selected products to the cart,
        # or modify existing items.
        current_cart = self._cart_management_stage(selected_products)
        if not current_cart:
            print("Workflow terminated: Cart management failed.")
            return None

        # Check if the cart has items before proceeding to checkout
        if not current_cart.get("items"):
            print("Workflow terminated: Cart is empty after management, cannot checkout.")
            return None

        # 3. Checkout
        order_confirmation = self._checkout_stage(current_cart)
        if not order_confirmation:
            print("Workflow terminated: Checkout failed.")
            return None

        print(f"--- Commerce Workflow Completed Successfully! Order ID: {order_confirmation.get('order_id')} ---")
        return order_confirmation