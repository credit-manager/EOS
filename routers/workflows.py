"""
P17 Workflow Router — CRUD + instance lifecycle + approvals
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from core.workflow_engine import WorkflowEngine
from database import get_db

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Workflow & Approval"]
)


def _get_engine(db: Session=None):
    return WorkflowEngine(db)


# ──────────────────────────────────────────────────────────────
# WORKFLOW DEFINITION CRUD
# ──────────────────────────────────────────────────────────────

@router.get(
    "/workflows",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_workflows(
    entity_code: str | None = None,
    db: Session=None,
):
    """List workflow definitions."""
    conditions = []
    params = {}
    if entity_code:
        conditions.append("entity_code = :ec")
        params["ec"] = entity_code

    where = " AND ".join(conditions) if conditions else "1=1"
    rows = db.execute(
        __import__("sqlalchemy").text(
            f"SELECT id, code, name_en, name_ar, entity_code, "
            f"is_active, is_published, sla_hours, created_at "
            f"FROM dbp_workflow_definitions WHERE {where} ORDER BY code"
        ),
        params,
    ).fetchall()

    return {
        "status": "success",
        "data": [
            {
                "id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
                "entity_code": r[4], "is_active": bool(r[5]),
                "is_published": bool(r[6]), "sla_hours": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ],
    }


@router.post(
    "/workflows",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def create_workflow(
    body: dict,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Create a workflow definition."""
    engine = WorkflowEngine(db)
    tenant_id = user.get("tenant_id")

    code = body.get("code")
    name_en = body.get("name_en")
    entity_code = body.get("entity_code")

    if not code or not name_en or not entity_code:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "code, name_en, entity_code required"},
        })

    # Check unique code
    existing = db.execute(
        __import__("sqlalchemy").text("SELECT id FROM dbp_workflow_definitions WHERE code = :c"),
        {"c": code},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "DUPLICATE", "message": f"Workflow '{code}' already exists"},
        })

    wf_id = engine.create_workflow(
        code=code, name_en=name_en, entity_code=entity_code,
        tenant_id=tenant_id, name_ar=body.get("name_ar"),
        description=body.get("description"), sla_hours=body.get("sla_hours"),
    )
    db.commit()

    return {"status": "success", "data": {"id": wf_id, "code": code}}


@router.get(
    "/workflows/{workflow_id}",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def get_workflow(
    workflow_id: str,
    db: Session=None,
):
    """Get workflow with states and transitions."""
    engine = WorkflowEngine(db)
    result = engine.get_workflow_detail(workflow_id)
    if not result:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Workflow not found"},
        })
    return {"status": "success", "data": result}


@router.post(
    "/workflows/{workflow_id}/publish",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def publish_workflow(
    workflow_id: str,
    db: Session=None,
):
    """Publish a workflow (make it usable)."""
    engine = WorkflowEngine(db)
    ok = engine.publish_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Workflow not found"},
        })
    db.commit()
    return {"status": "success", "message": "Workflow published"}


@router.post(
    "/workflows/{workflow_id}/states",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def add_state(
    workflow_id: str,
    body: dict,
    db: Session=None,
):
    """Add a state to a workflow."""
    engine = WorkflowEngine(db)

    code = body.get("code")
    name_en = body.get("name_en")
    if not code or not name_en:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "code and name_en required"},
        })

    state_id = engine.add_state(
        workflow_id=workflow_id, code=code, name_en=name_en,
        state_type=body.get("state_type", "pending"),
        is_final=body.get("is_final", False),
        name_ar=body.get("name_ar"),
        allowed_roles=body.get("allowed_roles"),
    )
    db.commit()

    return {"status": "success", "data": {"id": state_id, "code": code}}


@router.post(
    "/workflows/{workflow_id}/transitions",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def add_transition(
    workflow_id: str,
    body: dict,
    db: Session=None,
):
    """Add a transition to a workflow."""
    engine = WorkflowEngine(db)

    from_state = body.get("from_state_id")
    to_state = body.get("to_state_id")
    if not from_state or not to_state:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "from_state_id and to_state_id required"},
        })

    trans_id = engine.add_transition(
        workflow_id=workflow_id,
        code=body.get("code", str(uuid.uuid4())[:8]),
        name_en=body.get("name_en", body.get("code", "transition")),
        from_state_id=from_state,
        to_state_id=to_state,
        action=body.get("action", "approve"),
        required_roles=body.get("required_roles"),
        conditions=body.get("conditions"),
    )
    db.commit()

    return {"status": "success", "data": {"id": trans_id}}


# ──────────────────────────────────────────────────────────────
# WORKFLOW INSTANCES
# ──────────────────────────────────────────────────────────────

@router.post(
    "/workflow-instances",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def start_instance(
    body: dict,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Start a workflow instance for a record."""
    engine = WorkflowEngine(db)
    user_id = user.get("id") or user.get("user_id")
    tenant_id = user.get("tenant_id")

    wf_id = body.get("workflow_id")
    entity_code = body.get("entity_code")
    record_id = body.get("record_id")

    if not wf_id or not entity_code or not record_id:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "workflow_id, entity_code, record_id required"},
        })

    instance_id = engine.start_instance(
        workflow_id=wf_id, entity_code=entity_code,
        record_id=record_id, initiated_by=user_id,
        tenant_id=tenant_id, priority=body.get("priority", 0),
    )

    if not instance_id:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "CANNOT_START", "message": "Cannot start instance (workflow not published or not found)"},
        })

    db.commit()
    return {"status": "success", "data": {"id": instance_id}}


@router.get(
    "/workflow-instances",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_instances(
    workflow_id: str | None = None,
    entity_code: str | None = None,
    status: str | None = None,
    limit: int | None=None,
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List workflow instances."""
    engine = WorkflowEngine(db)
    tenant_id = user.get("tenant_id")

    instances = engine.list_instances(
        workflow_id=workflow_id, entity_code=entity_code,
        status=status, tenant_id=tenant_id,
        limit=limit, offset=offset,
    )

    return {"status": "success", "data": instances}


@router.get(
    "/workflow-instances/{instance_id}",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def get_instance(
    instance_id: str,
    db: Session=None,
):
    """Get workflow instance with history."""
    engine = WorkflowEngine(db)
    result = engine.get_instance(instance_id)
    if not result:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Instance not found"},
        })
    return {"status": "success", "data": result}


@router.post(
    "/workflow-instances/{instance_id}/approve",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def approve_instance(
    instance_id: str,
    body: dict | None = None,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Approve a workflow instance."""
    if body is None:
        body = {}
    engine = WorkflowEngine(db)
    user_id = user.get("id") or user.get("user_id")
    user_roles = user.get("roles", [])

    result = engine.execute_transition(
        instance_id=instance_id, action="approve",
        performed_by=user_id, comment=body.get("comment"),
        user_roles=user_roles,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "TRANSITION_FAILED", "message": result["error"]},
        })

    db.commit()
    return {"status": "success", "data": result}


@router.post(
    "/workflow-instances/{instance_id}/reject",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def reject_instance(
    instance_id: str,
    body: dict | None = None,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Reject a workflow instance."""
    if body is None:
        body = {}
    engine = WorkflowEngine(db)
    user_id = user.get("id") or user.get("user_id")
    user_roles = user.get("roles", [])

    result = engine.execute_transition(
        instance_id=instance_id, action="reject",
        performed_by=user_id, comment=body.get("comment"),
        user_roles=user_roles,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "TRANSITION_FAILED", "message": result["error"]},
        })

    db.commit()
    return {"status": "success", "data": result}


@router.post(
    "/workflow-instances/{instance_id}/cancel",
    dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)],
)
async def cancel_instance(
    instance_id: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Cancel a workflow instance."""
    engine = WorkflowEngine(db)
    user_id = user.get("id") or user.get("user_id")

    result = engine.cancel_instance(instance_id, user_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "CANCEL_FAILED", "message": result["error"]},
        })

    db.commit()
    return {"status": "success", "data": result}
