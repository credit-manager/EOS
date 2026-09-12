"""Construction Dashboard KPIs and project health overview."""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    ChangeOrder,
    ProgressClaim,
    Project,
    PurchaseOrder,
    SupplierInvoice,
)

_ZERO = Decimal("0")


def project_dashboard(db: Session, tenant_id) -> dict:
    """Aggregate KPIs across all projects for the tenant."""
    projects = db.scalars(
        select(Project).where(Project.tenant_id == tenant_id)
    ).all()

    status_counts: dict[str, int] = {}
    total_budget = _ZERO
    total_spent = _ZERO

    for p in projects:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1
        total_budget += p.budget or _ZERO

    total_projects = len(projects)
    active_count = sum(1 for p in projects if p.status == "active")
    completed_count = sum(1 for p in projects if p.status == "completed")

    active_project_ids = [p.id for p in projects if p.status == "active"]

    # Aggregate spending from supplier invoices on active projects
    if active_project_ids:
        invoice_total = db.scalar(
            select(func.coalesce(func.sum(SupplierInvoice.total_amount), 0)).where(
                SupplierInvoice.tenant_id == tenant_id,
                SupplierInvoice.project_id.in_(active_project_ids),
            )
        ) or 0
        total_spent = Decimal(str(invoice_total))

    # Pending approvals
    pending_change_orders = db.scalar(
        select(func.count()).where(
            ChangeOrder.tenant_id == tenant_id,
            ChangeOrder.status == "pending_approval",
        )
    ) or 0

    pending_claims = db.scalar(
        select(func.count()).where(
            ProgressClaim.tenant_id == tenant_id,
            ProgressClaim.status == "submitted",
        )
    ) or 0

    pending_pos = db.scalar(
        select(func.count()).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status == "pending_approval",
        )
    ) or 0

    # Budget utilization
    budget_utilization = _ZERO
    if total_budget > 0:
        budget_utilization = (total_spent / total_budget * 100).quantize(Decimal("0.01"))

    return {
        "total_projects": total_projects,
        "active_projects": active_count,
        "completed_projects": completed_count,
        "by_status": status_counts,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "budget_utilization_pct": budget_utilization,
        "pending_approvals": {
            "change_orders": int(pending_change_orders),
            "progress_claims": int(pending_claims),
            "purchase_orders": int(pending_pos),
        },
    }
