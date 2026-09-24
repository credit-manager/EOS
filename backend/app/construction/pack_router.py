"""Construction Pack router - industry pack endpoints.

Exposes:
- Pack info & metadata
- Project health KPI
- Construction dashboards (project health, cash projection)
- Construction-specific rules definitions
- Construction analyst AI agent execution
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..construction.pack import (
    ConstructionAnalystAgent,
    ConstructionPackService,
    get_construction_pack_service,
)
from ..db import get_db
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/construction/pack", tags=["construction-pack"])


# -------------------------------------------------------------------
# Pack info
# -------------------------------------------------------------------

@router.get("/info")
def pack_info(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Get Construction Pack metadata."""
    svc = get_construction_pack_service(db, tenant_id)
    return svc.get_pack_info()


# -------------------------------------------------------------------
# Project health
# -------------------------------------------------------------------

@router.get("/projects/{project_id}/health")
def project_health(
    project_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Compute health KPIs for a single construction project."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    result = svc.compute_project_health(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/projects/{project_id}/margin")
def project_margin(
    project_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Compute margin KPIs for a project."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    result = svc.compute_project_margin(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# -------------------------------------------------------------------
# Dashboards
# -------------------------------------------------------------------

@router.get("/dashboards/project-health")
def project_health_dashboard(
    project_id: UUID | None = Query(default=None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Project health dashboard (single project or portfolio)."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.get_project_health_dashboard(project_id)


@router.get("/dashboards/cash-projection")
def cash_projection(
    months: int = Query(default=3, ge=1, le=12),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Cash projection dashboard based on unpaid supplier invoices."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.get_cash_projection(months)


# -------------------------------------------------------------------
# Procurement & claims KPIs
# -------------------------------------------------------------------

@router.get("/procurement/pipeline")
def procurement_pipeline(
    project_id: UUID | None = Query(default=None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Procurement pipeline KPIs."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.compute_procurement_pipeline(project_id)


@router.get("/contracts/status")
def contracts_status(
    project_id: UUID | None = Query(default=None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Contract status KPIs."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.compute_contract_status(project_id)


@router.get("/claims/kpi")
def claims_kpi(
    project_id: UUID | None = Query(default=None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Progress claim KPIs."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.compute_claims_kpi(project_id)


# -------------------------------------------------------------------
# Construction rules definitions
# -------------------------------------------------------------------

@router.get("/rules")
def construction_rules(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get construction-specific rule definitions ready for the Rules Engine."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    return svc.create_construction_rules()


# -------------------------------------------------------------------
# AI Analyst Agent
# -------------------------------------------------------------------

class AnalystRequest:
    def __init__(self, project_id: UUID):
        self.project_id = project_id


@router.post("/analyze/{project_id}")
def analyze_project(
    project_id: UUID,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Run Construction Analyst AI Agent on a project."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    agent = ConstructionAnalystAgent(svc)
    result = agent.analyze_project_health(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# -------------------------------------------------------------------
# Pack installation / activation
# -------------------------------------------------------------------

@router.post("/activate")
def activate_pack(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Activate Construction Pack for tenant (idempotent)."""
    svc = get_construction_pack_service(db, principal.tenant_id)
    # In a fuller implementation, this would persist pack activation state.
    return {
        "status": "activated",
        "pack": svc.get_pack_info(),
        "message": "Construction Pack is now active for this tenant",
    }
