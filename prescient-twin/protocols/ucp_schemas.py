from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Helper Models

class Address(BaseModel):
    """
    Represents a physical address, commonly used for shipping or billing.
    """
    street: str = Field(..., description="Street name and house number (e.g., '123 Main St').")
    city: str = Field(..., description="City name (e.g., 'Anytown').")
    state: Optional[str] = Field(None, description="State or province, if applicable (e.g., 'CA', 'Ontario').")
    zip_code: str = Field(..., description="Postal or ZIP code (e.g., '90210', 'M5V 1A1').")
    country: str = Field(..., description="Country name (e.g., 'USA', 'Canada').")
    attention_to: Optional[str] = Field(None, description="Name of the person or entity the address is for.")


class CartItem(BaseModel):
    """
    Represents a single item within a shopping cart, referencing a product offer.
    """
    product_offer_id: UUID = Field(..., description="The unique identifier of the product offer being added to the cart.")
    quantity: int = Field(..., gt=0, description="The quantity of the product offer item.")
    price_at_time_of_addition: float = Field(..., ge=0, description="The price of the item when it was added to the cart. This might differ from the current offer price.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the item's price (e.g., 'USD', 'EUR').")
    item_total: float = Field(..., ge=0, description="The total price for this item (quantity * price_at_time_of_addition).")


class OrderItem(BaseModel):
    """
    Represents a single item within a confirmed order, capturing its state at the time of purchase.
    """
    product_offer_id: UUID = Field(..., description="The unique identifier of the product offer that was purchased.")
    quantity: int = Field(..., gt=0, description="The quantity of the product offer item purchased.")
    price_at_purchase: float = Field(..., ge=0, description="The price of the item at the time of purchase.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the item's price (e.g., 'USD', 'EUR').")
    item_total: float = Field(..., ge=0, description="The total price for this item (quantity * price_at_purchase).")


# Main UCP Schemas

class ProductOffer(BaseModel):
    """
    Represents a specific offer for a product, including its price, availability, and validity period.
    This model describes a single product offer.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this product offer.")
    product_id: UUID = Field(..., description="The unique identifier of the underlying product that this offer is for.")
    name: str = Field(..., min_length=1, description="The name of the product being offered.")
    description: Optional[str] = Field(None, description="A detailed description of the product offer.")
    price: float = Field(..., ge=0, description="The price of the product offer per unit.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the offer price (e.g., 'USD', 'EUR').")
    available_quantity: int = Field(..., ge=0, description="The number of units available for this offer.")
    seller_id: UUID = Field(..., description="The unique identifier of the seller making this offer.")
    valid_from: Optional[datetime] = Field(None, description="The UTC datetime from which this offer is valid.")
    valid_until: Optional[datetime] = Field(None, description="The UTC datetime until which this offer is valid.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when this offer was created or last updated.")


class Cart(BaseModel):
    """
    Represents a shopping cart, holding items selected by a customer before checkout.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this cart.")
    customer_id: UUID = Field(..., description="The unique identifier of the customer who owns this cart.")
    items: List[CartItem] = Field(default_factory=list, description="A list of items currently in the cart.")
    total_amount: float = Field(..., ge=0, description="The total monetary value of all items in the cart.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the cart's total amount.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the cart was created.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the cart was last updated.")


class PaymentRequest(BaseModel):
    """
    Represents a request to process a payment for a specific amount, potentially linked to an order or cart.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this payment request.")
    order_id: Optional[UUID] = Field(None, description="Optional: The unique identifier of the order associated with this payment request.")
    cart_id: Optional[UUID] = Field(None, description="Optional: The unique identifier of the cart associated with this payment request.")
    customer_id: UUID = Field(..., description="The unique identifier of the customer making the payment.")
    amount: float = Field(..., gt=0, description="The total amount requested for payment.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the payment amount.")
    payment_method: str = Field(..., description="The requested payment method (e.g., 'credit_card', 'paypal', 'crypto').")
    status: str = Field("pending", description="The current status of the payment request (e.g., 'pending', 'paid', 'failed', 'refunded').")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the payment request was created.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the payment request was last updated.")
    transaction_id: Optional[str] = Field(None, description="The transaction ID provided by the payment gateway, if available.")
    return_url: Optional[str] = Field(None, description="URL to redirect the user to after successful payment, if applicable.")
    cancel_url: Optional[str] = Field(None, description="URL to redirect the user to if payment is cancelled or fails, if applicable.")


class OrderConfirmation(BaseModel):
    """
    Represents a confirmed order, detailing the purchased items, total amount, status, and associated addresses.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this order.")
    customer_id: UUID = Field(..., description="The unique identifier of the customer who placed the order.")
    cart_id: Optional[UUID] = Field(None, description="Optional: The unique identifier of the cart from which this order was placed.")
    items: List[OrderItem] = Field(..., description="A list of items included in the order.")
    total_amount: float = Field(..., ge=0, description="The total monetary value of the confirmed order.")
    currency: str = Field(..., min_length=3, max_length=3, description="The ISO 4217 currency code for the order's total amount.")
    status: str = Field("pending", description="The current status of the order (e.g., 'pending', 'processing', 'shipped', 'delivered', 'cancelled').")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the order was created.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="The UTC datetime when the order was last updated.")
    payment_id: Optional[UUID] = Field(None, description="Optional: The unique identifier of the successful payment associated with this order.")
    shipping_address: Optional[Address] = Field(None, description="The shipping address for the order, if applicable.")
    billing_address: Optional[Address] = Field(None, description="The billing address for the order, if applicable.")