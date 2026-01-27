import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Union

# Configure logging for this capability
logger = logging.getLogger(__name__)

# --- Data Models for Checkout Process ---

@dataclass
class CheckoutItem:
    """
    Represents a single item in the checkout cart.
    """
    item_id: str
    """Unique identifier for the product/SKU."""
    quantity: int
    """Number of units of this item."""
    unit_price: float
    """Price per unit of the item."""
    name: Optional[str] = None
    """Optional human-readable name of the item."""
    currency: str = "USD"
    """Currency of the unit price."""

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

@dataclass
class ShippingAddress:
    """
    Represents the shipping address for an order.
    """
    first_name: str
    last_name: str
    address_line1: str
    city: str
    state_province: str
    postal_code: str
    country: str
    address_line2: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

@dataclass
class PaymentMethod:
    """
    Represents a payment method to be used for checkout.
    This is a simplified model; a real UCP might use tokens or more complex structures.
    """
    method_type: str
    """Type of payment method (e.g., 'credit_card', 'paypal', 'ucp_token')."""
    details: Dict[str, Any] = field(default_factory=dict)
    """
    A dictionary containing specific details for the payment method.
    For 'credit_card', this might include 'card_number', 'expiry_month', 'expiry_year', 'cvc'.
    For 'ucp_token', it might be {'token': 'some_ucp_payment_token'}.
    """

# --- UCP Client Interface (Protocol) ---

class UCPClient(Protocol):
    """
    Protocol defining the interface for interacting with the Universal Commerce Platform (UCP).
    This allows for flexible implementation of the actual UCP API client.
    """

    def initiate_ucp_checkout(self, items: List[CheckoutItem]) -> str:
        """
        Initiates a new checkout session on the UCP.

        Args:
            items: A list of `CheckoutItem` objects representing the products to purchase.

        Returns:
            A unique identifier for the initiated checkout session.

        Raises:
            UCPClientError: If the UCP fails to initiate the checkout.
        """
        ...

    def update_shipping_details(self, checkout_session_id: str, address: ShippingAddress) -> bool:
        """
        Updates the shipping details for an existing UCP checkout session.

        Args:
            checkout_session_id: The ID of the checkout session.
            address: The `ShippingAddress` object containing the shipping details.

        Returns:
            True if the shipping details were successfully updated, False otherwise.

        Raises:
            UCPClientError: If the UCP fails to update shipping details.
        """
        ...

    def process_payment(self, checkout_session_id: str, payment_method: PaymentMethod, total_amount: float) -> str:
        """
        Triggers payment processing for a UCP checkout session.

        Args:
            checkout_session_id: The ID of the checkout session.
            payment_method: The `PaymentMethod` object specifying how to pay.
            total_amount: The total amount expected for the payment. UCP should validate this.

        Returns:
            A unique transaction ID if the payment was successful.

        Raises:
            UCPClientError: If the UCP fails to process the payment.
            PaymentError: If the payment itself is declined or fails.
        """
        ...

    def get_checkout_status(self, checkout_session_id: str) -> Dict[str, Any]:
        """
        Retrieves the current status of a UCP checkout session.

        Args:
            checkout_session_id: The ID of the checkout session.

        Returns:
            A dictionary containing the current status and relevant details of the checkout.
            Example: {'status': 'pending_shipping', 'total_amount': 123.45, ...}

        Raises:
            UCPClientError: If the UCP fails to retrieve the status.
        """
        ...

# --- Mock UCP Client Implementation (for demonstration/testing) ---

class MockUCPClient:
    """
    A mock implementation of the UCPClient protocol for testing and development.
    Simulates UCP interactions without actual API calls.
    """
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._next_session_id = 1
        logger.info("MockUCPClient initialized.")

    def initiate_ucp_checkout(self, items: List[CheckoutItem]) -> str:
        session_id = f"ucp_session_{self._next_session_id}"
        self._next_session_id += 1
        total_amount = sum(item.quantity * item.unit_price for item in items)
        self._sessions[session_id] = {
            "items": [item.__dict__ for item in items],
            "total_amount": total_amount,
            "status": "initiated",
            "shipping_address": None,
            "payment_method": None,
            "transaction_id": None,
        }
        logger.info(f"Mock UCP checkout initiated: {session_id} with {len(items)} items, total: {total_amount:.2f}")
        return session_id

    def update_shipping_details(self, checkout_session_id: str, address: ShippingAddress) -> bool:
        if checkout_session_id not in self._sessions:
            logger.error(f"Mock UCP: Session {checkout_session_id} not found for shipping update.")
            return False
        
        session = self._sessions[checkout_session_id]
        session["shipping_address"] = address.__dict__
        session["status"] = "shipping_details_provided"
        logger.info(f"Mock UCP: Shipping details updated for session {checkout_session_id}.")
        return True

    def process_payment(self, checkout_session_id: str, payment_method: PaymentMethod, total_amount: float) -> str:
        if checkout_session_id not in self._sessions:
            logger.error(f"Mock UCP: Session {checkout_session_id} not found for payment.")
            raise ValueError(f"Checkout session {checkout_session_id} not found.")

        session = self._sessions[checkout_session_id]
        if session["total_amount"] != total_amount:
            logger.warning(f"Mock UCP: Amount mismatch for session {checkout_session_id}. Expected {session['total_amount']:.2f}, got {total_amount:.2f}.")
            # In a real system, this might be an error or trigger a recalculation.
            # For mock, we'll proceed but log.

        # Simulate payment success/failure based on some simple logic
        if "fail_payment" in payment_method.details and payment_method.details["fail_payment"]:
            logger.error(f"Mock UCP: Payment failed for session {checkout_session_id} due to mock instruction.")
            raise ValueError("Payment declined by mock UCP.")

        transaction_id = f"ucp_txn_{checkout_session_id}_{self._next_session_id}" # Reusing counter for unique txn ID
        session["payment_method"] = payment_method.__dict__
        session["transaction_id"] = transaction_id
        session["status"] = "payment_processed"
        logger.info(f"Mock UCP: Payment processed for session {checkout_session_id}. Transaction ID: {transaction_id}")
        return transaction_id

    def get_checkout_status(self, checkout_session_id: str) -> Dict[str, Any]:
        if checkout_session_id not in self._sessions:
            logger.error(f"Mock UCP: Session {checkout_session_id} not found for status check.")
            return {"status": "not_found"}
        
        return self._sessions[checkout_session_id]

# --- Checkout Capability Implementation ---

class CheckoutCapability:
    """
    A capability for prescient-twin agents to initiate and manage the UCP checkout process.

    This capability allows agents to:
    1. Initiate a new checkout session with a list of items.
    2. Specify shipping details for the session.
    3. Trigger payment using UCP-supported methods.
    4. Retrieve the current status of a checkout session.
    """

    def __init__(self, ucp_client: UCPClient):
        """
        Initializes the CheckoutCapability with a UCP client.

        Args:
            ucp_client: An instance of a class implementing the UCPClient protocol,
                        responsible for actual communication with the UCP.
        """
        self._ucp_client = ucp_client
        logger.info("CheckoutCapability initialized.")

    def initiate_checkout(self, items: List[CheckoutItem]) -> str:
        """
        Initiates a new checkout process on the Universal Commerce Platform (UCP).

        Args:
            items: A list of `CheckoutItem` objects representing the products to be purchased.

        Returns:
            A unique identifier for the initiated checkout session. This ID is used
            for subsequent operations like updating shipping or processing payment.

        Raises:
            Exception: If the UCP client fails to initiate the checkout.
        """
        if not items:
            logger.warning("Attempted to initiate checkout with an empty list of items.")
            raise ValueError("Cannot initiate checkout with an empty list of items.")

        try:
            checkout_session_id = self._ucp_client.initiate_ucp_checkout(items)
            logger.info(f"Checkout session {checkout_session_id} initiated successfully.")
            return checkout_session_id
        except Exception as e:
            logger.error(f"Failed to initiate UCP checkout: {e}", exc_info=True)
            raise

    def specify_shipping_details(self, checkout_session_id: str, address: ShippingAddress) -> bool:
        """
        Specifies or updates the shipping details for an ongoing checkout session.

        Args:
            checkout_session_id: The ID of the checkout session obtained from `initiate_checkout`.
            address: A `ShippingAddress` object containing the complete shipping information.

        Returns:
            True if the shipping details were successfully updated, False otherwise.

        Raises:
            Exception: If the UCP client fails to update the shipping details.
        """
        if not checkout_session_id:
            logger.warning("Attempted to specify shipping details with an empty checkout_session_id.")
            raise ValueError("Checkout session ID cannot be empty.")

        try:
            success = self._ucp_client.update_shipping_details(checkout_session_id, address)
            if success:
                logger.info(f"Shipping details updated for checkout session {checkout_session_id}.")
            else:
                logger.warning(f"Failed to update shipping details for checkout session {checkout_session_id}.")
            return success
        except Exception as e:
            logger.error(f"Failed to update shipping details for session {checkout_session_id}: {e}", exc_info=True)
            raise

    def trigger_payment(self, checkout_session_id: str, payment_method: PaymentMethod, total_amount: float) -> str:
        """
        Triggers the payment process for a checkout session using a specified payment method.

        Args:
            checkout_session_id: The ID of the checkout session.
            payment_method: A `PaymentMethod` object detailing the payment method to use.
            total_amount: The total amount expected for the payment. This should match
                          the amount calculated by UCP for the session.

        Returns:
            A unique transaction ID if the payment was successful.

        Raises:
            Exception: If the UCP client fails to process the payment, or if the payment is declined.
        """
        if not checkout_session_id:
            logger.warning("Attempted to trigger payment with an empty checkout_session_id.")
            raise ValueError("Checkout session ID cannot be empty.")
        if total_amount <= 0:
            logger.warning(f"Attempted to trigger payment for non-positive amount: {total_amount}.")
            raise ValueError("Payment amount must be positive.")

        try:
            transaction_id = self._ucp_client.process_payment(checkout_session_id, payment_method, total_amount)
            logger.info(f"Payment processed for session {checkout_session_id}. Transaction ID: {transaction_id}")
            return transaction_id
        except Exception as e:
            logger.error(f"Failed to trigger payment for session {checkout_session_id}: {e}", exc_info=True)
            raise

    def get_checkout_status(self, checkout_session_id: str) -> Dict[str, Any]:
        """
        Retrieves the current status and details of a specific checkout session.

        Args:
            checkout_session_id: The ID of the checkout session.

        Returns:
            A dictionary containing the current status and other relevant information
            about the checkout session from the UCP.

        Raises:
            Exception: If the UCP client fails to retrieve the status.
        """
        if not checkout_session_id:
            logger.warning("Attempted to get checkout status with an empty checkout_session_id.")
            raise ValueError("Checkout session ID cannot be empty.")

        try:
            status_details = self._ucp_client.get_checkout_status(checkout_session_id)
            logger.debug(f"Retrieved status for session {checkout_session_id}: {status_details.get('status')}")
            return status_details
        except Exception as e:
            logger.error(f"Failed to retrieve status for session {checkout_session_id}: {e}", exc_info=True)
            raise

# Example Usage (for testing/demonstration purposes, not part of the capability itself)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Initialize the mock UCP client
    mock_ucp = MockUCPClient()

    # Initialize the Checkout Capability with the mock client
    checkout_capability = CheckoutCapability(mock_ucp)

    print("\n--- Scenario 1: Successful Checkout ---")
    try:
        # 1. Define items for purchase
        items_to_buy = [
            CheckoutItem(item_id="PROD001", name="Wireless Headphones", quantity=1, unit_price=199.99),
            CheckoutItem(item_id="ACC005", name="Charging Cable", quantity=2, unit_price=15.50)
        ]

        # 2. Initiate checkout
        session_id = checkout_capability.initiate_checkout(items_to_buy)
        print(f"Initiated checkout session: {session_id}")

        # 3. Define shipping address
        shipping_addr = ShippingAddress(
            first_name="John",
            last_name="Doe",
            address_line1="123 Main St",
            city="Anytown",
            state_province="CA",
            postal_code="90210",
            country="USA",
            email="john.doe@example.com"
        )

        # 4. Specify shipping details
        if checkout_capability.specify_shipping_details(session_id, shipping_addr):
            print(f"Shipping details updated for session {session_id}.")
        else:
            print(f"Failed to update shipping details for session {session_id}.")

        # 5. Define payment method (e.g., a UCP token or credit card details)
        payment_method = PaymentMethod(
            method_type="credit_card",
            details={
                "card_number": "************1234",
                "expiry_month": "12",
                "expiry_year": "2025",
                "cvc": "***"
            }
        )

        # Calculate total amount (UCP would typically do this, but we pass it for validation)
        total_amount = sum(item.quantity * item.unit_price for item in items_to_buy)

        # 6. Trigger payment
        transaction_id = checkout_capability.trigger_payment(session_id, payment_method, total_amount)
        print(f"Payment successful! Transaction ID: {transaction_id}")

        # 7. Get final checkout status
        final_status = checkout_capability.get_checkout_status(session_id)
        print(f"Final checkout status for {session_id}: {final_status['status']}")
        assert final_status['status'] == 'payment_processed'
        assert final_status['transaction_id'] == transaction_id

    except Exception as e:
        print(f"An error occurred during successful checkout scenario: {e}")

    print("\n--- Scenario 2: Checkout with Payment Failure ---")
    try:
        items_for_failure = [CheckoutItem(item_id="PROD002", name="Smartwatch", quantity=1, unit_price=299.00)]
        session_id_fail = checkout_capability.initiate_checkout(items_for_failure)
        print(f"Initiated checkout session for failure test: {session_id_fail}")

        checkout_capability.specify_shipping_details(session_id_fail, shipping_addr)

        # Payment method configured to fail
        failing_payment_method = PaymentMethod(
            method_type="credit_card",
            details={"fail_payment": True} # Mock specific instruction to fail
        )
        total_amount_fail = sum(item.quantity * item.unit_price for item in items_for_failure)

        transaction_id_fail = checkout_capability.trigger_payment(session_id_fail, failing_payment_method, total_amount_fail)
        print(f"This line should not be reached if payment fails: {transaction_id_fail}")

    except ValueError as e:
        print(f"Expected payment failure occurred: {e}")
        status_after_fail = checkout_capability.get_checkout_status(session_id_fail)
        print(f"Status after payment attempt: {status_after_fail['status']}")
        assert status_after_fail['status'] == 'shipping_details_provided' # Should not be 'payment_processed'
    except Exception as e:
        print(f"An unexpected error occurred during payment failure scenario: {e}")

    print("\n--- Scenario 3: Invalid Checkout Initiation ---")
    try:
        checkout_capability.initiate_checkout([])
    except ValueError as e:
        print(f"Expected error for empty items list: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")