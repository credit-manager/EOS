from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service
from .dashboard import project_dashboard

router = APIRouter(prefix="/api/v1/construction", tags=["construction"])


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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)


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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)


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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
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
    commit_db(db)
    return proc


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

@router.post("/budgets", status_code=201, response_model=schemas.BudgetResponse)
def create_budget(
    payload: schemas.BudgetCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    budget = service.create_budget(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        version=payload.version,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return budget


@router.get("/budgets", response_model=list[schemas.BudgetResponse])
def list_budgets(
    project_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_budgets(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/budgets/{budget_id}", response_model=schemas.BudgetResponse)
def get_budget(
    budget_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_budget(db, tenant_id=tenant_id, budget_id=budget_id)


@router.post("/budgets/{budget_id}/lines", status_code=201, response_model=schemas.BudgetLineResponse)
def add_budget_line(
    budget_id: UUID,
    payload: schemas.BudgetLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_budget_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        budget_id=budget_id,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        unit_rate=payload.unit_rate,
        amount=payload.amount,
        boq_item_id=payload.boq_item_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return line


@router.get("/budgets/{budget_id}/lines", response_model=list[schemas.BudgetLineResponse])
def list_budget_lines(
    budget_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_budget_lines(db, tenant_id=tenant_id, budget_id=budget_id)


@router.post("/budgets/{budget_id}/status", response_model=schemas.BudgetResponse)
def update_budget_status(
    budget_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    budget = service.update_budget_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        budget_id=budget_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return budget


# ---------------------------------------------------------------------------
# Change Order
# ---------------------------------------------------------------------------

@router.post("/change-orders", status_code=201, response_model=schemas.ChangeOrderResponse)
def create_change_order(
    payload: schemas.ChangeOrderCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    co = service.create_change_order(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        contract_id=payload.contract_id,
        change_order_number=payload.change_order_number,
        title=payload.title,
        description=payload.description,
        impact_type=payload.impact_type,
        cost_impact=payload.cost_impact,
        time_impact_days=payload.time_impact_days,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return co


@router.get("/change-orders", response_model=list[schemas.ChangeOrderResponse])
def list_change_orders(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_change_orders(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/change-orders/{change_order_id}", response_model=schemas.ChangeOrderResponse)
def get_change_order(
    change_order_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_change_order(db, tenant_id=tenant_id, change_order_id=change_order_id)


@router.post("/change-orders/{change_order_id}/status", response_model=schemas.ChangeOrderResponse)
def update_change_order_status(
    change_order_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    co = service.update_change_order_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        change_order_id=change_order_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return co


# ---------------------------------------------------------------------------
# Subcontract
# ---------------------------------------------------------------------------

@router.post("/subcontracts", status_code=201, response_model=schemas.SubcontractResponse)
def create_subcontract(
    payload: schemas.SubcontractCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    sub = service.create_subcontract(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        contract_id=payload.contract_id,
        subcontract_number=payload.subcontract_number,
        subcontractor_name=payload.subcontractor_name,
        scope=payload.scope,
        value=payload.value,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return sub


@router.get("/subcontracts", response_model=list[schemas.SubcontractResponse])
def list_subcontracts(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_subcontracts(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/subcontracts/{subcontract_id}", response_model=schemas.SubcontractResponse)
def get_subcontract(
    subcontract_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_subcontract(db, tenant_id=tenant_id, subcontract_id=subcontract_id)


@router.post("/subcontracts/{subcontract_id}/status", response_model=schemas.SubcontractResponse)
def update_subcontract_status(
    subcontract_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    sub = service.update_subcontract_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        subcontract_id=subcontract_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return sub


# ---------------------------------------------------------------------------
# Site Warehouse
# ---------------------------------------------------------------------------

@router.post("/warehouses", status_code=201, response_model=schemas.SiteWarehouseResponse)
def create_site_warehouse(
    payload: schemas.SiteWarehouseCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    wh = service.create_site_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        code=payload.code,
        name=payload.name,
        location=payload.location,
        manager_id=payload.manager_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return wh


@router.get("/warehouses", response_model=list[schemas.SiteWarehouseResponse])
def list_site_warehouses(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_site_warehouses(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/warehouses/{warehouse_id}", response_model=schemas.SiteWarehouseResponse)
def get_site_warehouse(
    warehouse_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_site_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)


@router.patch("/warehouses/{warehouse_id}", response_model=schemas.SiteWarehouseResponse)
def update_site_warehouse(
    warehouse_id: UUID,
    payload: schemas.SiteWarehouseUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    wh = service.update_site_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        warehouse_id=warehouse_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return wh


@router.delete("/warehouses/{warehouse_id}", status_code=204)
def delete_site_warehouse(
    warehouse_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_site_warehouse(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        warehouse_id=warehouse_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------

@router.post("/purchase-orders", status_code=201, response_model=schemas.PurchaseOrderResponse)
def create_purchase_order(
    payload: schemas.PurchaseOrderCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    po = service.create_purchase_order(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        procurement_id=payload.procurement_id,
        supplier_id=payload.supplier_id,
        po_number=payload.po_number,
        currency=payload.currency,
        terms=payload.terms,
        delivery_date=payload.delivery_date,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return po


@router.get("/purchase-orders", response_model=list[schemas.PurchaseOrderResponse])
def list_purchase_orders(
    procurement_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_purchase_orders(db, tenant_id=tenant_id, procurement_id=procurement_id)


@router.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrderResponse)
def get_purchase_order(
    po_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_purchase_order(db, tenant_id=tenant_id, po_id=po_id)


@router.post("/purchase-orders/{po_id}/lines", status_code=201, response_model=schemas.PurchaseOrderLineResponse)
def add_purchase_order_line(
    po_id: UUID,
    payload: schemas.PurchaseOrderLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_purchase_order_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        po_id=po_id,
        procurement_line_id=payload.procurement_line_id,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        line_total=payload.line_total,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return line


@router.get("/purchase-orders/{po_id}/lines", response_model=list[schemas.PurchaseOrderLineResponse])
def list_purchase_order_lines(
    po_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_purchase_order_lines(db, tenant_id=tenant_id, po_id=po_id)


@router.post("/purchase-orders/{po_id}/status", response_model=schemas.PurchaseOrderResponse)
def update_purchase_order_status(
    po_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    po = service.update_purchase_order_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        po_id=po_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return po


# ---------------------------------------------------------------------------
# Goods Receipt (GRN)
# ---------------------------------------------------------------------------

@router.post("/goods-receipts", status_code=201, response_model=schemas.GoodsReceiptResponse)
def create_goods_receipt(
    payload: schemas.GoodsReceiptCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    grn = service.create_goods_receipt(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        purchase_order_id=payload.purchase_order_id,
        grn_number=payload.grn_number,
        received_date=payload.received_date,
        warehouse_id=payload.warehouse_id,
        received_by=payload.received_by,
        notes=payload.notes,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return grn


@router.get("/goods-receipts", response_model=list[schemas.GoodsReceiptResponse])
def list_goods_receipts(
    po_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_goods_receipts(db, tenant_id=tenant_id, po_id=po_id)


@router.get("/goods-receipts/{grn_id}", response_model=schemas.GoodsReceiptResponse)
def get_goods_receipt(
    grn_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_goods_receipt(db, tenant_id=tenant_id, grn_id=grn_id)


@router.post("/goods-receipts/{grn_id}/lines", status_code=201, response_model=schemas.GoodsReceiptLineResponse)
def add_goods_receipt_line(
    grn_id: UUID,
    payload: schemas.GoodsReceiptLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_goods_receipt_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        grn_id=grn_id,
        po_line_id=payload.po_line_id,
        quantity_received=payload.quantity_received,
        quantity_accepted=payload.quantity_accepted,
        quantity_rejected=payload.quantity_rejected,
        notes=payload.notes,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return line


@router.get("/goods-receipts/{grn_id}/lines", response_model=list[schemas.GoodsReceiptLineResponse])
def list_goods_receipt_lines(
    grn_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_goods_receipt_lines(db, tenant_id=tenant_id, grn_id=grn_id)


@router.post("/goods-receipts/{grn_id}/status", response_model=schemas.GoodsReceiptResponse)
def update_goods_receipt_status(
    grn_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    grn = service.update_goods_receipt_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        grn_id=grn_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return grn


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------

@router.post("/supplier-invoices", status_code=201, response_model=schemas.SupplierInvoiceResponse)
def create_supplier_invoice(
    payload: schemas.SupplierInvoiceCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    inv = service.create_supplier_invoice(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        purchase_order_id=payload.purchase_order_id,
        grn_id=payload.grn_id,
        invoice_number=payload.invoice_number,
        supplier_invoice_number=payload.supplier_invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return inv


@router.get("/supplier-invoices", response_model=list[schemas.SupplierInvoiceResponse])
def list_supplier_invoices(
    po_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_supplier_invoices(db, tenant_id=tenant_id, po_id=po_id)


@router.get("/supplier-invoices/{invoice_id}", response_model=schemas.SupplierInvoiceResponse)
def get_supplier_invoice(
    invoice_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_supplier_invoice(db, tenant_id=tenant_id, invoice_id=invoice_id)


@router.post("/supplier-invoices/{invoice_id}/lines", status_code=201, response_model=schemas.SupplierInvoiceLineResponse)
def add_supplier_invoice_line(
    invoice_id: UUID,
    payload: schemas.SupplierInvoiceLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    line = service.add_supplier_invoice_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        invoice_id=invoice_id,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        line_total=payload.line_total,
        tax_rate=payload.tax_rate,
        tax_amount=payload.tax_amount,
        grn_line_id=payload.grn_line_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return line


@router.get("/supplier-invoices/{invoice_id}/lines", response_model=list[schemas.SupplierInvoiceLineResponse])
def list_supplier_invoice_lines(
    invoice_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_supplier_invoice_lines(db, tenant_id=tenant_id, invoice_id=invoice_id)


@router.post("/supplier-invoices/{invoice_id}/status", response_model=schemas.SupplierInvoiceResponse)
def update_supplier_invoice_status(
    invoice_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    inv = service.update_supplier_invoice_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        invoice_id=invoice_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return inv


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@router.post("/payments", status_code=201, response_model=schemas.PaymentResponse)
def create_payment(
    payload: schemas.PaymentCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    pay = service.create_payment(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        supplier_invoice_id=payload.supplier_invoice_id,
        payment_number=payload.payment_number,
        payment_method=payload.payment_method,
        amount=payload.amount,
        currency=payload.currency,
        payment_date=payload.payment_date,
        reference=payload.reference,
        notes=payload.notes,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return pay


@router.get("/payments", response_model=list[schemas.PaymentResponse])
def list_payments(
    invoice_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_payments(db, tenant_id=tenant_id, invoice_id=invoice_id)


@router.get("/payments/{payment_id}", response_model=schemas.PaymentResponse)
def get_payment(
    payment_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_payment(db, tenant_id=tenant_id, payment_id=payment_id)


@router.post("/payments/{payment_id}/status", response_model=schemas.PaymentResponse)
def update_payment_status(
    payment_id: UUID,
    status: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    pay = service.update_payment_status(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payment_id=payment_id,
        status=status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return pay


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    return project_dashboard(db, tenant_id)
