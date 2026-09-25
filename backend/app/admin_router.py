"""Admin API - tenant and user management for system owner."""
from uuid import UUID
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .auth.security import Principal, require_principal
from .auth.models import Tenant, User, TenantMembership
from .notification.models import Notification as NotifModel
from .health import check_db_health
from .config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_super_admin(principal: Principal = Depends(require_principal)):
    if principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return principal


@router.get("/tenants")
def list_tenants(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(Tenant)
    if search:
        query = query.filter(Tenant.name.ilike(f"%{search}%"))
    total = query.count()
    tenants = query.order_by(Tenant.created_at.desc()).offset(offset).limit(limit).all()
    memberships = db.query(TenantMembership).filter(
        TenantMembership.tenant_id.in_([t.id for t in tenants])
    ).all()
    membership_count = {}
    for m in memberships:
        membership_count[str(m.tenant_id)] = membership_count.get(str(m.tenant_id), 0) + 1
    result = []
    for t in tenants:
        result.append({
            "id": str(t.id),
            "name": t.name,
            "owner": "",
            "industry": t.industry or "",
            "country": t.country or "",
            "plan": t.plan or "",
            "status": t.status,
            "users": membership_count.get(str(t.id), 0),
            "storage": f"{t.storage_gb}GB",
            "aiUsage": f"{t.ai_usage_pct}%",
            "createdAt": t.created_at.isoformat() if t.created_at else "",
            "lastActive": "",
        })
    return {"tenants": result, "total": total}


@router.get("/users")
def list_users(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(User).join(TenantMembership, User.id == TenantMembership.user_id)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for u in users:
        membership = db.query(TenantMembership).filter(
            TenantMembership.user_id == u.id
        ).first()
        result.append({
            "id": str(u.id),
            "email": u.email,
            "tenant": str(membership.tenant_id) if membership else "",
            "role": membership.role if membership else "member",
            "status": "active" if u.is_active else "suspended",
            "mfa": u.mfa_enabled,
            "lastLogin": u.last_login.isoformat() if u.last_login else "",
            "created": u.created_at.isoformat() if u.created_at else "",
            "sessions": 0,
            "riskStatus": u.risk_status,
        })
    return {"users": result, "total": total}


@router.get("/health")
def get_system_health(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    uptime = int(__import__('time').time() - settings.app_start_time)
    return {
        "api": {"status": "operational", "latency": 1},
        "database": {"status": check_db_health().get("status", "operational")},
        "aiServices": {"status": "operational"},
        "backgroundJobs": {"status": "operational"},
        "queue": {"status": "operational"},
        "storage": {"status": "operational"},
        "emailService": {"status": "operational"},
        "paymentGateway": {"status": "operational"},
        "externalIntegrations": {"status": "operational"},
        "uptime": uptime,
    }


@router.get("/notifications")
def list_notifications(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
):
    notifications = db.query(NotifModel).order_by(NotifModel.created_at.desc()).limit(limit).all()
    result = []
    for n in notifications:
        result.append({
            "id": str(n.id),
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "isRead": n.is_read,
            "actionUrl": n.action_url,
            "recipientType": "user" if n.user_id else "tenant",
            "recipientId": str(n.user_id) if n.user_id else str(n.tenant_id),
            "status": "sent",
            "createdAt": n.created_at.isoformat() if n.created_at else "",
        })
    return {"notifications": result}


@router.post("/notifications")
def create_notification(
    data: dict,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    tenant_id = None
    user_id = None
    if data.get("tenantId"):
        try:
            tenant_id = UUID(data["tenantId"])
        except (ValueError, TypeError):
            pass
    if data.get("userId"):
        try:
            user_id = UUID(data["userId"])
        except (ValueError, TypeError):
            pass
    if tenant_id is None and user_id is None:
        tenant_id = UUID()
    notif = NotifModel(
        id=UUID(),
        notification_type=data.get("type", "announcement"),
        title=data.get("title", ""),
        message=data.get("message", ""),
        category=data.get("category", "system"),
        tenant_id=tenant_id or UUID(),
        user_id=user_id or UUID(),
        is_read=False,
        created_at=datetime.now(UTC),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return {"id": str(notif.id), "status": "created"}


@router.get("/metrics")
def get_metrics(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return {
        "cpu": {"usage": 45, "cores": 4},
        "ram": {"usage": 62, "total": "16GB"},
        "disk": {"usage": 38, "total": "500GB"},
        "database": {"connections": 12, "queriesPerSec": 45},
        "apiLatency": {"p50": 12, "p95": 45, "p99": 120},
        "requestsPerSec": 156,
        "errorRate": 0.02,
        "queue": {"pending": 3, "processing": 2},
        "backgroundJobs": {"active": 5, "completed": 1247},
    }


@router.patch("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: str,
    data: dict,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == UUID(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if "status" in data:
        tenant.is_active = data["status"] == "active"
    if "name" in data:
        tenant.name = data["name"]
    db.commit()
    db.refresh(tenant)
    return {"id": str(tenant.id), "name": tenant.name, "status": "active" if tenant.is_active else "suspended"}


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    data: dict,
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "is_active" in data:
        user.is_active = data["is_active"]
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "email": user.email, "status": "active" if user.is_active else "suspended"}


@router.get("/billing/invoices")
def list_invoices(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    from ..billing.models import Invoice as BillingInvoice
    invoices = db.query(BillingInvoice).order_by(BillingInvoice.created_at.desc()).limit(limit).all()
    result = []
    for inv in invoices:
        result.append({
            "id": str(inv.id),
            "tenantId": str(inv.tenant_id),
            "subscriptionId": str(inv.subscription_id),
            "amount": inv.amount,
            "currency": inv.currency,
            "status": inv.status,
            "dueDate": inv.due_date.isoformat() if inv.due_date else "",
            "paidAt": inv.paid_at.isoformat() if inv.paid_at else "",
            "createdAt": inv.created_at.isoformat() if inv.created_at else "",
        })
    return {"invoices": result}


@router.get("/billing/kpis")
def get_billing_kpis(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    from ..billing.models import Invoice as BillingInvoice, Plan, Subscription
    from sqlalchemy import func as sa_func

    total_revenue = db.query(sa_func.coalesce(sa_func.sum(BillingInvoice.amount), 0)).filter(
        BillingInvoice.status == "paid"
    ).scalar()
    pending_amount = db.query(sa_func.coalesce(sa_func.sum(BillingInvoice.amount), 0)).filter(
        BillingInvoice.status.in_(["pending", "open"])
    ).scalar()
    plan_count = db.query(sa_func.count(Plan.id)).scalar()
    active_subs = db.query(sa_func.count(Subscription.id)).filter(
        Subscription.status == "active"
    ).scalar()
    return {
        "mrr": float(total_revenue) if total_revenue else 0,
        "arr": float(total_revenue) * 12 if total_revenue else 0,
        "totalRevenue": float(total_revenue) if total_revenue else 0,
        "outstanding": float(pending_amount) if pending_amount else 0,
        "activeSubscriptions": active_subs or 0,
        "totalPlans": plan_count or 0,
    }


@router.get("/ai/stats")
def get_ai_stats(
    principal: Principal = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    from ..ai.models import AIAgentExecution, AILLMConfig
    from sqlalchemy import func as sa_func

    total_executions = db.query(sa_func.count(AIAgentExecution.id)).scalar() or 0
    avg_latency = db.query(sa_func.avg(AIAgentExecution.execution_time_ms)).scalar() or 0
    llm_configs = db.query(sa_func.count(AILLMConfig.id)).scalar() or 0
    return {
        "apiRequests": total_executions,
        "avgLatencyMs": round(float(avg_latency), 0),
        "totalLlmConfigs": llm_configs,
        "tokenUsage": "0",
        "cost": 0,
    }
