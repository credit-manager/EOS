"""Stripe webhook and payment endpoints."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..db import get_db
from ..auth.security import Principal, require_principal
from .payment import create_checkout_session, create_portal_session, handle_webhook

router = APIRouter(prefix="/api/v1/billing", tags=["billing-payment"])


@router.post("/checkout")
def checkout(
    data: dict,
    principal: Principal = Depends(require_principal),
    db=Depends(get_db),
):
    try:
        result = create_checkout_session(
            tenant_id=str(principal.tenant_id),
            plan_code=data.get("planCode", ""),
            success_url=data.get("successUrl", "http://localhost:5173/billing/success"),
            cancel_url=data.get("cancelUrl", "http://localhost:5173/billing/cancel"),
            trial_days=data.get("trialDays", 0),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal")
def portal(
    principal: Principal = Depends(require_principal),
    db=Depends(get_db),
):
    try:
        result = create_portal_session(
            tenant_id=str(principal.tenant_id),
            return_url="http://localhost:5173/billing",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature"),
):
    payload = await request.body()
    try:
        result = handle_webhook(payload, stripe_signature)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
