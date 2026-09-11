from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/construction", tags=["construction"])


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.post("/projects", status_code=201, response_model=schemas.ProjectResponse)
def create_project(
    payload: schemas.ProjectCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    project = service.create_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        client_name=payload.client_name,
        location=payload.location,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return project


@router.get("/projects", response_model=list[schemas.ProjectResponse])
def list_projects(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_projects(db, tenant_id=tenant_id)


@router.get("/projects/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
    project_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_project(db, tenant_id=tenant_id, project_id=project_id)


@router.patch("/projects/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: UUID,
    payload: schemas.ProjectUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    project = service.update_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=project_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=project_id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

@router.post("/contracts", status_code=201, response_model=schemas.ContractResponse)
def create_contract(
    payload: schemas.ContractCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    contract = service.create_contract(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        contract_number=payload.contract_number,
        contract_type=payload.contract_type,
        title=payload.title,
        counterparty=payload.counterparty,
        contract_value=payload.contract_value,
        status=payload.status,
        signed_date=payload.signed_date,
        completion_date=payload.completion_date,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return contract


@router.get("/contracts", response_model=list[schemas.ContractResponse])
def list_contracts(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_contracts(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/contracts/{contract_id}", response_model=schemas.ContractResponse)
def get_contract(
    contract_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_contract(db, tenant_id=tenant_id, contract_id=contract_id)


@router.patch("/contracts/{contract_id}", response_model=schemas.ContractResponse)
def update_contract(
    contract_id: UUID,
    payload: schemas.ContractUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    contract = service.update_contract(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contract_id=contract_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return contract


@router.delete("/contracts/{contract_id}", status_code=204)
def delete_contract(
    contract_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_contract(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contract_id=contract_id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()


# ---------------------------------------------------------------------------
# BOQ
# ---------------------------------------------------------------------------

@router.post("/boqs", status_code=201, response_model=schemas.BOQResponse)
def create_boq(
    payload: schemas.BOQCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    boq = service.create_boq(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contract_id=payload.contract_id,
        version=payload.version,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return boq


@router.get("/boqs", response_model=list[schemas.BOQResponse])
def list_boqs(
    contract_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_boqs(db, tenant_id=tenant_id, contract_id=contract_id)


@router.get("/boqs/{boq_id}", response_model=schemas.BOQResponse)
def get_boq(
    boq_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_boq(db, tenant_id=tenant_id, boq_id=boq_id)


@router.post("/boqs/{boq_id}/items", status_code=201, response_model=schemas.BOQItemResponse)
def add_boq_item(
    boq_id: UUID,
    payload: schemas.BOQItemCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    item = service.add_boq_item(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        boq_id=boq_id,
        item_number=payload.item_number,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        unit_rate=payload.unit_rate,
        amount=payload.amount,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return item


@router.get("/boqs/{boq_id}/items", response_model=list[schemas.BOQItemResponse])
def list_boq_items(
    boq_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_boq_items(db, tenant_id=tenant_id, boq_id=boq_id)


@router.post("/boqs/{boq_id}/status", response_model=schemas.BOQResponse)
def update_boq_status(
    boq_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    boq = service.update_boq_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        boq_id=boq_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return boq


# ---------------------------------------------------------------------------
# Progress Claims
# ---------------------------------------------------------------------------

@router.post("/claims", status_code=201, response_model=schemas.ProgressClaimResponse)
def create_progress_claim(
    payload: schemas.ProgressClaimCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    claim = service.create_progress_claim(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        contract_id=payload.contract_id,
        claim_number=payload.claim_number,
        claim_date=payload.claim_date,
        period_start=payload.period_start,
        period_end=payload.period_end,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return claim


@router.get("/claims", response_model=list[schemas.ProgressClaimResponse])
def list_progress_claims(
    contract_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_progress_claims(db, tenant_id=tenant_id, contract_id=contract_id)


@router.get("/claims/{claim_id}", response_model=schemas.ProgressClaimResponse)
def get_progress_claim(
    claim_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_progress_claim(db, tenant_id=tenant_id, claim_id=claim_id)


@router.post("/claims/{claim_id}/lines", status_code=201, response_model=schemas.ProgressClaimLineResponse)
def add_claim_line(
    claim_id: UUID,
    payload: schemas.ProgressClaimLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_claim_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        claim_id=claim_id,
        boq_item_id=payload.boq_item_id,
        description=payload.description,
        quantity_completed=payload.quantity_completed,
        amount=payload.amount,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return line


@router.get("/claims/{claim_id}/lines", response_model=list[schemas.ProgressClaimLineResponse])
def list_claim_lines(
    claim_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_claim_lines(db, tenant_id=tenant_id, claim_id=claim_id)


@router.post("/claims/{claim_id}/status", response_model=schemas.ProgressClaimResponse)
def update_claim_status(
    claim_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    claim = service.update_claim_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        claim_id=claim_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return claim


# ---------------------------------------------------------------------------
# Procurement
# ---------------------------------------------------------------------------

@router.post("/procurements", status_code=201, response_model=schemas.ProcurementResponse)
def create_procurement(
    payload: schemas.ProcurementCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    proc = service.create_procurement(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        requisition_number=payload.requisition_number,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return proc


@router.get("/procurements", response_model=list[schemas.ProcurementResponse])
def list_procurements(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_procurements(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/procurements/{procurement_id}", response_model=schemas.ProcurementResponse)
def get_procurement(
    procurement_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_procurement(db, tenant_id=tenant_id, procurement_id=procurement_id)


@router.post("/procurements/{procurement_id}/lines", status_code=201, response_model=schemas.ProcurementLineResponse)
def add_procurement_line(
    procurement_id: UUID,
    payload: schemas.ProcurementLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_procurement_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        procurement_id=procurement_id,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        estimated_unit_price=payload.estimated_unit_price,
        estimated_total=payload.estimated_total,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return line


@router.get("/procurements/{procurement_id}/lines", response_model=list[schemas.ProcurementLineResponse])
def list_procurement_lines(
    procurement_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_procurement_lines(db, tenant_id=tenant_id, procurement_id=procurement_id)


@router.post("/procurements/{procurement_id}/status", response_model=schemas.ProcurementResponse)
def update_procurement_status(
    procurement_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    proc = service.update_procurement_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        procurement_id=procurement_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return proc
