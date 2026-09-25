"""Billing API — plans, subscriptions, invoices."""
import uuid
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant, require_admin
from .models import Plan, Subscription, Invoice
from .schemas import PlanOut, SubscriptionOut, SubscribeRequest, SubscribeResponse, CancelResponse

def _tenant_id_str(tenant_id) -> str:
    """Convert tenant_id to string (handles UUID from tenant module)."""
    return str(tenant_id)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)) -> list[PlanOut]:
    plans = db.query(Plan).filter(Plan.is_active).all()
    return [PlanOut(
        id=p.id, code=p.code, name=p.name, description=p.description,
        price_monthly=p.price_monthly, price_yearly=p.price_yearly,
        max_users=p.max_users, max_storage_gb=p.max_storage_gb,
        features=p.features,
    ) for p in plans]

@router.get("/subscription")
def get_subscription(
    tenant_id = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    tid = _tenant_id_str(tenant_id)
    sub = db.query(Subscription).filter(
        Subscription.tenant_id == tid,
        Subscription.status.in_(["active", "trialing"]),
    ).first()
    if not sub:
        return SubscriptionOut(status="none")
    plan = db.get(Plan, sub.plan_id)
    return SubscriptionOut(
        id=sub.id, status=sub.status, billing_cycle=sub.billing_cycle,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
        plan={"code": plan.code, "name": plan.name} if plan else None,
    )

@router.post("/subscribe")
def subscribe(
    body: SubscribeRequest,
    tenant_id = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SubscribeResponse:
    tid = _tenant_id_str(tenant_id)
    plan = db.query(Plan).filter(Plan.code == body.plan_code, Plan.is_active).first()
    if not plan:
        raise HTTPException(404, "Plan not found")

    existing = db.query(Subscription).filter(
        Subscription.tenant_id == tid,
        Subscription.status.in_(["active", "trialing"]),
    ).first()
    if existing:
        raise HTTPException(409, "Active subscription exists")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=30 if body.billing_cycle == "monthly" else 365)

    sub = Subscription(
        id=str(uuid.uuid4()),
        tenant_id=tid,
        plan_id=plan.id,
        status="active",
        billing_cycle=body.billing_cycle,
        current_period_start=now,
        current_period_end=period_end,
    )
    db.add(sub)
    db.commit()
    return SubscribeResponse(subscription_id=sub.id, status="active")

@router.post("/subscription/cancel")
def cancel_subscription(
    tenant_id = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CancelResponse:
    tid = _tenant_id_str(tenant_id)
    sub = db.query(Subscription).filter(
        Subscription.tenant_id == tid,
        Subscription.status == "active",
    ).first()
    if not sub:
        raise HTTPException(404, "No active subscription")
    sub.cancel_at_period_end = True
    db.commit()
    return CancelResponse(status="cancellation_scheduled", end_date=sub.current_period_end.isoformat())
