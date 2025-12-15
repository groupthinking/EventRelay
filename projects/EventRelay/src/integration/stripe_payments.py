"""
Stripe - Monetization for Generated Apps
-----------------------------------------
Payment processing, subscriptions, and checkout for generated applications.
"""

import os
import asyncio
import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class Product:
    """Stripe product definition."""
    id: str
    name: str
    description: str
    active: bool
    default_price_id: Optional[str] = None


@dataclass
class Price:
    """Stripe price definition."""
    id: str
    product_id: str
    unit_amount: int  # in cents
    currency: str
    recurring: Optional[dict] = None


@dataclass
class CheckoutSession:
    """Stripe checkout session."""
    id: str
    url: str
    payment_status: str
    customer_email: Optional[str] = None


class StripePaymentService:
    """Stripe payment service for monetizing generated apps."""
    
    API_BASE = "https://api.stripe.com/v1"
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get("STRIPE_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("STRIPE_SECRET_KEY required")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            auth=(self.secret_key, "")
        )
    
    async def create_product(
        self,
        name: str,
        description: str = "",
        metadata: Optional[dict] = None
    ) -> Product:
        """Create a new product."""
        
        data = {
            "name": name,
            "description": description,
        }
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v
        
        response = await self.client.post(
            f"{self.API_BASE}/products",
            data=data
        )
        response.raise_for_status()
        result = response.json()
        
        return Product(
            id=result["id"],
            name=result["name"],
            description=result.get("description", ""),
            active=result["active"],
            default_price_id=result.get("default_price")
        )
    
    async def create_price(
        self,
        product_id: str,
        unit_amount: int,
        currency: str = "usd",
        recurring_interval: Optional[str] = None  # "month", "year"
    ) -> Price:
        """Create a price for a product."""
        
        data = {
            "product": product_id,
            "unit_amount": unit_amount,
            "currency": currency,
        }
        
        if recurring_interval:
            data["recurring[interval]"] = recurring_interval
        
        response = await self.client.post(
            f"{self.API_BASE}/prices",
            data=data
        )
        response.raise_for_status()
        result = response.json()
        
        return Price(
            id=result["id"],
            product_id=result["product"],
            unit_amount=result["unit_amount"],
            currency=result["currency"],
            recurring=result.get("recurring")
        )
    
    async def create_checkout_session(
        self,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "payment",  # "payment", "subscription"
        customer_email: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> CheckoutSession:
        """Create a checkout session for payment."""
        
        data = {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        
        if customer_email:
            data["customer_email"] = customer_email
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v
        
        response = await self.client.post(
            f"{self.API_BASE}/checkout/sessions",
            data=data
        )
        response.raise_for_status()
        result = response.json()
        
        return CheckoutSession(
            id=result["id"],
            url=result["url"],
            payment_status=result["payment_status"],
            customer_email=result.get("customer_email")
        )
    
    async def create_payment_link(
        self,
        price_id: str,
        quantity: int = 1
    ) -> str:
        """Create a reusable payment link."""
        
        data = {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": str(quantity),
        }
        
        response = await self.client.post(
            f"{self.API_BASE}/payment_links",
            data=data
        )
        response.raise_for_status()
        return response.json()["url"]
    
    async def get_checkout_session(self, session_id: str) -> dict:
        """Retrieve checkout session details."""
        
        response = await self.client.get(
            f"{self.API_BASE}/checkout/sessions/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def list_products(self, active_only: bool = True) -> list[Product]:
        """List all products."""
        
        params = {"limit": 100}
        if active_only:
            params["active"] = "true"
        
        response = await self.client.get(
            f"{self.API_BASE}/products",
            params=params
        )
        response.raise_for_status()
        
        return [
            Product(
                id=p["id"],
                name=p["name"],
                description=p.get("description", ""),
                active=p["active"],
                default_price_id=p.get("default_price")
            )
            for p in response.json()["data"]
        ]
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """Create a customer record."""
        
        data = {"email": email}
        if name:
            data["name"] = name
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v
        
        response = await self.client.post(
            f"{self.API_BASE}/customers",
            data=data
        )
        response.raise_for_status()
        return response.json()
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0
    ) -> dict:
        """Create a subscription for a customer."""
        
        data = {
            "customer": customer_id,
            "items[0][price]": price_id,
        }
        if trial_days > 0:
            data["trial_period_days"] = str(trial_days)
        
        response = await self.client.post(
            f"{self.API_BASE}/subscriptions",
            data=data
        )
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def generate_webhook_handler_code() -> str:
        """Generate webhook handler code for generated apps."""
        return '''
import stripe
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Handle successful payment
        await handle_successful_payment(session)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        # Handle subscription update
        await handle_subscription_update(subscription)
    
    return {"status": "success"}
'''
    
    async def close(self):
        await self.client.aclose()
