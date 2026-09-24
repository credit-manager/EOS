"""Stripe payment integration service."""
import logging
from typing import Any

import stripe
from ..config import get_settings

logger = logging.getLogger("2to-eos.stripe")

_client_initialized = False


def _init_client():
    global _client_initialized
    if _client_initialized:
        return
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key
    _client_initialized = True


def create_checkout_session(
    tenant_id: str,
    plan_code: str,
    success_url: str,
    cancel_url: str,
    trial_days: int = 0,
) -> dict[str, Any]:
    _init_client()
    from ..billing.models import Plan
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.code == plan_code, Plan.is_active).first()
        if not plan:
            raise ValueError(f"Plan {plan_code} not found")

        session_params: dict[str, Any] = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": plan.name, "description": plan.description or plan.name},
                    "unit_amount": int(plan.price_monthly * 100),
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"tenant_id": tenant_id, "plan_code": plan_code},
        }
        if trial_days > 0:
            session_params["subscription_data"] = {"trial_period_days": trial_days}

        session = stripe.checkout.Session.create(**session_params)
        return {"sessionId": session.id, "url": session.url}
    finally:
        db.close()


def create_portal_session(tenant_id: str, return_url: str) -> dict[str, Any]:
    _init_client()
    from ..billing.models import Subscription
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        sub = db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_(["active", "trialing"]),
        ).first()
        if not sub or not sub.stripe_customer_id:
            raise ValueError("No active subscription with Stripe customer")

        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )
        return {"url": session.url}
    finally:
        db.close()


def handle_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    _init_client()
    settings = get_settings()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise ValueError(f"Invalid webhook: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        _handle_checkout_completed(session)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        _handle_subscription_updated(subscription)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        _handle_subscription_deleted(subscription)
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        _handle_payment_failed(invoice)

    return {"status": "processed", "type": event["type"]}


def _handle_checkout_completed(session):
    from ..billing.models import Subscription, Plan
    from ..db import SessionLocal
    import uuid

    db = SessionLocal()
    try:
        tenant_id = session.get("metadata", {}).get("tenant_id", "")
        plan_code = session.get("metadata", {}).get("plan_code", "")
        stripe_sub_id = session.get("subscription", "")
        stripe_customer_id = session.get("customer", "")

        plan = db.query(Plan).filter(Plan.code == plan_code).first()
        if not plan:
            return

        existing = db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id, Subscription.status != "canceled"
        ).first()
        if existing:
            existing.plan_id = plan.id
            existing.status = "active"
            existing.stripe_subscription_id = stripe_sub_id
            existing.stripe_customer_id = stripe_customer_id
        else:
            sub = Subscription(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                plan_id=plan.id,
                status="active",
                billing_cycle="monthly",
                stripe_subscription_id=stripe_sub_id,
                stripe_customer_id=stripe_customer_id,
            )
            db.add(sub)
        db.commit()
    finally:
        db.close()


def _handle_subscription_updated(stripe_sub):
    from ..billing.models import Subscription
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.get("id")
        ).first()
        if sub:
            status_map = {"active": "active", "trialing": "trialing", "past_due": "past_due", "canceled": "canceled"}
            sub.status = status_map.get(stripe_sub.get("status", ""), sub.status)
            db.commit()
    finally:
        db.close()


def _handle_subscription_deleted(stripe_sub):
    from ..billing.models import Subscription
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.get("id")
        ).first()
        if sub:
            sub.status = "canceled"
            db.commit()
    finally:
        db.close()


def _handle_payment_failed(invoice):
    from ..billing.models import Subscription
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        stripe_sub_id = invoice.get("subscription", "")
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub_id
        ).first()
        if sub:
            sub.status = "past_due"
            db.commit()
    finally:
        db.close()
