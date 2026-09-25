"""Core business tools for AI agents - search, aggregate, analyze."""
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

logger = logging.getLogger("2to-eos.ai.tools")


def search_records(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Search records across entity types."""
    from ...metadata.models import MetadataEntity
    from ...records.models import Record

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    entity_code = params.get("entity_code")
    query_text = params.get("query", "").lower()
    limit = min(params.get("limit", 20), 100)

    q = select(Record).where(Record.tenant_id == tenant_id)
    if entity_code:
        q = q.where(Record.entity_code == entity_code)

    records = db.scalars(q.limit(200)).all()

    results = []
    for rec in records:
        data = rec.data or {}
        title = data.get("name") or data.get("title") or str(rec.id)[-8:]
        if query_text and query_text not in json.dumps(data).lower():
            continue
        results.append({
            "id": str(rec.id),
            "entity_code": rec.entity_code,
            "title": str(title),
            "data": data,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
        })
        if len(results) >= limit:
            break

    return {"count": len(results), "results": results}


def aggregate_records(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Aggregate record counts by entity type."""
    from ...records.models import Record

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    entity_code = params.get("entity_code")

    q = select(
        Record.entity_code,
        func.count(Record.id).label("count"),
    ).where(Record.tenant_id == tenant_id).group_by(Record.entity_code)

    if entity_code:
        q = q.where(Record.entity_code == entity_code)

    rows = db.scalars(q).all()

    return {
        "aggregation": {row.entity_code: row.count for row in rows},
        "total": sum(row.count for row in rows),
    }


def get_financial_summary(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Get financial summary - account balances, trial balance."""
    from ...financial.models import Account, JournalEntry, JournalLine

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id, Account.is_active.is_(True))
    ).all()

    account_summary = []
    total_debit = 0
    total_credit = 0
    for acc in accounts:
        account_summary.append({
            "code": acc.code,
            "name": acc.name,
            "type": acc.account_type,
            "debit": acc.current_balance_debit,
            "credit": acc.current_balance_credit,
        })
        total_debit += acc.current_balance_debit
        total_credit += acc.current_balance_credit

    posted_entries = db.scalars(
        select(JournalEntry).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.status == "posted",
        )
    ).all()

    return {
        "accounts": account_summary,
        "total_accounts": len(account_summary),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "posted_entries": len(posted_entries),
        "is_balanced": total_debit == total_credit,
    }


def get_workflow_status(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Get workflow instance status and pending approvals."""
    from ...workflow.models import ApprovalTask, WorkflowInstance

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    instances = db.scalars(
        select(WorkflowInstance).where(WorkflowInstance.tenant_id == tenant_id)
    ).all()

    status_counts: dict[str, int] = {}
    for inst in instances:
        s = inst.current_state or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    pending_approvals = db.scalars(
        select(ApprovalTask).where(
            ApprovalTask.tenant_id == tenant_id,
            ApprovalTask.status == "pending",
        )
    ).all()

    approval_list = []
    for ap in pending_approvals:
        approval_list.append({
            "id": str(ap.id),
            "workflow_instance_id": str(ap.workflow_instance_id),
            "assigned_to": ap.assigned_to_role,
            "action": ap.action,
            "created_at": ap.created_at.isoformat() if ap.created_at else None,
        })

    return {
        "total_instances": len(instances),
        "status_distribution": status_counts,
        "pending_approvals": len(pending_approvals),
        "approvals": approval_list[:10],
    }


def get_recent_events(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Get recent system events."""
    from ...events.models import SystemEvent

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    limit = min(params.get("limit", 20), 100)
    event_type = params.get("event_type")

    q = select(SystemEvent).where(SystemEvent.tenant_id == tenant_id)
    if event_type:
        q = q.where(SystemEvent.event_type == event_type)
    q = q.order_by(SystemEvent.created_at.desc()).limit(limit)

    events = db.scalars(q).all()

    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "payload": json.loads(e.payload_json) if e.payload_json else {},
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


def get_project_health(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Analyze project health from metadata records."""
    from ...records.models import Record

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "project",
        )
    ).all()

    projects = []
    for rec in records:
        data = rec.data or {}
        budget = data.get("budget", 0)
        spent = data.get("spent", 0)
        utilization = (spent / budget * 100) if budget > 0 else 0
        status = data.get("status", "unknown")
        margin = data.get("margin", 0)

        risk_level = "low"
        if utilization > 90:
            risk_level = "critical"
        elif utilization > 75:
            risk_level = "high"
        elif utilization > 60:
            risk_level = "medium"

        projects.append({
            "id": str(rec.id),
            "name": data.get("name", "Unnamed"),
            "status": status,
            "budget": budget,
            "spent": spent,
            "utilization_pct": round(utilization, 1),
            "margin": margin,
            "risk_level": risk_level,
        })

    projects.sort(key=lambda p: p["utilization_pct"], reverse=True)

    return {
        "total_projects": len(projects),
        "at_risk": [p for p in projects if p["risk_level"] in ("high", "critical")],
        "projects": projects,
    }


def get_procurement_analysis(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Analyze procurement data."""
    from ...records.models import Record

    db: Session = context["db"]
    tenant_id = UUID(context["tenant_id"])

    procurement_records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "procurement",
        )
    ).all()

    supplier_records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == "supplier",
        )
    ).all()

    procurements = []
    for rec in procurement_records:
        data = rec.data or {}
        procurements.append({
            "id": str(rec.id),
            "title": data.get("title", data.get("name", "Unnamed")),
            "status": data.get("status", "unknown"),
            "amount": data.get("amount", 0),
            "supplier": data.get("supplier", "Unknown"),
            "priority": data.get("priority", "normal"),
        })

    suppliers = []
    for rec in supplier_records:
        data = rec.data or {}
        suppliers.append({
            "id": str(rec.id),
            "name": data.get("name", "Unknown"),
            "rating": data.get("rating", 0),
            "total_orders": data.get("total_orders", 0),
        })

    pending = [p for p in procurements if p["status"] in ("draft", "pending", "requested")]
    total_value = sum(p["amount"] for p in procurements)

    return {
        "total_procurements": len(procurements),
        "pending_count": len(pending),
        "total_value": total_value,
        "procurements": procurements[:10],
        "suppliers": suppliers[:10],
    }


# Tool registry for built-in tools
BUILTIN_TOOLS = {
    "search_records": search_records,
    "aggregate_records": aggregate_records,
    "get_financial_summary": get_financial_summary,
    "get_workflow_status": get_workflow_status,
    "get_recent_events": get_recent_events,
    "get_project_health": get_project_health,
    "get_procurement_analysis": get_procurement_analysis,
}
