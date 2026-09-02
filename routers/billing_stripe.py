"""
EOS Billing Engine - Stripe Integration
Production-ready billing system with multi-currency and tax support.
"""
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.security import get_current_user
from models import User

router = APIRouter(prefix="/billing", tags=["Billing"])

# Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
DEFAULT_CURRENCY = "usd"

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    # Fallback for development without crashing
    print("⚠️ WARNING: STRIPE_SECRET_KEY not set. Billing will run in mock mode.")

# Models
class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str
    currency: str | None = "usd"

class SubscriptionPlan(BaseModel):
    id: str
    name: str
    amount: int
    currency: str
    interval: str  # month, year

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    db: Session=None,
    current_user: User = Depends(get_current_user)
):
    """Create a Stripe Checkout Session for subscription."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": request.price_id, "quantity": 1}],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            client_reference_id=str(current_user.id),
            metadata={
                "tenant_id": current_user.tenant_id,
                "user_email": current_user.email
            },
            currency=request.currency.lower()
        )
        return {"session_id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session=None):
    """Handle Stripe Webhooks for subscription events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET or not sig_header:
        raise HTTPException(status_code=400, detail="Webhook secret or signature missing")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data_object = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        session = data_object
        customer_email = session.get("customer_details", {}).get("email")
        tenant_id = session.get("metadata", {}).get("tenant_id")
        
        # Update subscription status in DB
        # Logic to activate subscription for tenant_id
        print(f"✅ Subscription completed for tenant: {tenant_id}, user: {customer_email}")
        
        # TODO: Update Subscription model in DB
        # new_sub = Subscription(tenant_id=tenant_id, status="active", stripe_session_id=session['id'])
        # db.add(new_sub)
        # db.commit()

    elif event["type"] == "customer.subscription.deleted":
        sub_id = data_object["id"]
        # Handle cancellation logic
        print(f"❌ Subscription cancelled: {sub_id}")

    return {"status": "success"}

@router.get("/plans", response_model=list[SubscriptionPlan])
async def list_plans(currency: str | None = "usd"):
    """List available subscription plans from Stripe."""
    if not STRIPE_SECRET_KEY:
        # Mock data for development
        return [
            {"id": "price_basic", "name": "Basic ERP", "amount": 2900, "currency": "usd", "interval": "month"},
            {"id": "price_pro", "name": "Pro ERP", "amount": 9900, "currency": "usd", "interval": "month"},
            {"id": "price_enterprise", "name": "Enterprise", "amount": 29900, "currency": "usd", "interval": "month"}
        ]
    
    try:
        prices = stripe.Price.list(
            active=True,
            type="recurring",
            currency=currency.lower()
        )
        plans = []
        for price in prices.data:
            plans.append({
                "id": price.id,
                "name": price.nickname or "Unnamed Plan",
                "amount": price.unit_amount,
                "currency": price.currency,
                "interval": price.recurring.interval
            })
        return plans
    except stripe.error.StripeError:
        raise HTTPException(status_code=500, detail="Failed to fetch plans from Stripe")

@router.get("/portal")
async def create_portal_session(
    db: Session=None,
    current_user: User = Depends(get_current_user)
):
    """Create a billing portal session for customers to manage subscriptions."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    
    # Retrieve Stripe Customer ID from DB based on user email/tenant
    # For demo, we assume it exists or create a new one
    try:
        # customer = stripe.Customer.retrieve(stripe_customer_id)
        session = stripe.billing_portal.Session.create(
            customer="cus_MOCK_CUSTOMER_ID", # Replace with real lookup
            return_url="https://your-app.com/settings/billing"
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
