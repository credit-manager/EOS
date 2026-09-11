from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from .models import (
    BOQ,
    BOQItem,
    Budget,
    BudgetLine,
    ChangeOrder,
    Contract,
    GoodsReceipt,
    GoodsReceiptLine,
    Payment,
    Procurement,
    ProcurementLine,
    ProgressClaim,
    ProgressClaimLine,
    Project,
    PurchaseOrder,
    PurchaseOrderLine,
    SiteWarehouse,
    Subcontract,
    SupplierInvoice,
    SupplierInvoiceLine,
)

_ZERO = Decimal("0")


def _audit(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    request_id: str | None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            details=details or {},
        )
    )


def _next_number(db: Session, tenant_id: UUID, model: type, prefix: str) -> int:
    stmt = select(model).where(model.tenant_id == tenant_id).order_by(model.created_at.desc())
    last = db.scalars(stmt).first()
    if last is None:
        return 1
    num_attr = "entry_number" if hasattr(last, "entry_number") else None
    if num_attr and hasattr(model, "claim_number"):
        return 1
    return 1


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

def create_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    description: str | None = None,
    status: str = "planning",
    start_date=None,
    end_date=None,
    budget: Decimal = Decimal("0"),
    client_name: str | None = None,
    location: str | None = None,
    request_id: str | None = None,
) -> Project:
    existing = db.scalar(
        select(Project).where(Project.tenant_id == tenant_id, Project.code == code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="project code already exists")
    project = Project(
        tenant_id=tenant_id,
        created_by=user_id,
        code=code,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        client_name=client_name,
        location=location,
    )
    db.add(project)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.project.created",
        resource_type="project",
        resource_id=project.id,
        request_id=request_id,
        details={"code": code, "name": name},
    )
    db.flush()
    return project


def get_project(db: Session, *, tenant_id: UUID, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def list_projects(db: Session, *, tenant_id: UUID) -> list[Project]:
    return db.scalars(
        select(Project).where(Project.tenant_id == tenant_id).order_by(Project.created_at.desc())
    ).all()


def update_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Project:
    project = get_project(db, tenant_id=tenant_id, project_id=project_id)
    for key, value in data.items():
        if value is not None:
            setattr(project, key, value)
    project.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.project.updated",
        resource_type="project",
        resource_id=project.id,
        request_id=request_id,
        details=data,
    )
    db.flush()
    return project


def delete_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    request_id: str | None = None,
) -> None:
    project = get_project(db, tenant_id=tenant_id, project_id=project_id)
    contracts = db.scalars(
        select(Contract).where(Contract.tenant_id == tenant_id, Contract.project_id == project_id)
    ).all()
    if contracts:
        raise HTTPException(status_code=409, detail="cannot delete project with existing contracts")
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.project.deleted",
        resource_type="project",
        resource_id=project.id,
        request_id=request_id,
    )
    db.delete(project)
    db.flush()


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

def create_contract(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    contract_number: str,
    contract_type: str = "main",
    title: str,
    counterparty: str,
    contract_value: Decimal = Decimal("0"),
    status: str = "draft",
    signed_date=None,
    completion_date=None,
    request_id: str | None = None,
) -> Contract:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    existing = db.scalar(
        select(Contract).where(
            Contract.tenant_id == tenant_id, Contract.contract_number == contract_number
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="contract number already exists")
    contract = Contract(
        tenant_id=tenant_id,
        created_by=user_id,
        project_id=project_id,
        contract_number=contract_number,
        contract_type=contract_type,
        title=title,
        counterparty=counterparty,
        contract_value=contract_value,
        status=status,
        signed_date=signed_date,
        completion_date=completion_date,
    )
    db.add(contract)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.contract.created",
        resource_type="contract",
        resource_id=contract.id,
        request_id=request_id,
        details={"contract_number": contract_number, "title": title},
    )
    db.flush()
    return contract


def get_contract(db: Session, *, tenant_id: UUID, contract_id: UUID) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None or contract.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="contract not found")
    return contract


def list_contracts(db: Session, *, tenant_id: UUID, project_id: UUID | None = None) -> list[Contract]:
    stmt = select(Contract).where(Contract.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Contract.project_id == project_id)
    return db.scalars(stmt.order_by(Contract.created_at.desc())).all()


def update_contract(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contract_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Contract:
    contract = get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    for key, value in data.items():
        if value is not None:
            setattr(contract, key, value)
    contract.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.contract.updated",
        resource_type="contract",
        resource_id=contract.id,
        request_id=request_id,
        details=data,
    )
    db.flush()
    return contract


def delete_contract(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contract_id: UUID,
    request_id: str | None = None,
) -> None:
    contract = get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    if contract.status != "draft":
        raise HTTPException(status_code=409, detail="only draft contracts can be deleted")
    boqs = db.scalars(
        select(BOQ).where(BOQ.tenant_id == tenant_id, BOQ.contract_id == contract_id)
    ).all()
    if boqs:
        raise HTTPException(status_code=409, detail="cannot delete contract with existing BOQs")
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.contract.deleted",
        resource_type="contract",
        resource_id=contract.id,
        request_id=request_id,
    )
    db.delete(contract)
    db.flush()


# ---------------------------------------------------------------------------
# BOQ
# ---------------------------------------------------------------------------

def create_boq(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contract_id: UUID,
    version: int = 1,
    request_id: str | None = None,
) -> BOQ:
    get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    existing = db.scalar(
        select(BOQ).where(
            BOQ.tenant_id == tenant_id,
            BOQ.contract_id == contract_id,
            BOQ.version == version,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="BOQ version already exists for this contract")
    boq = BOQ(
        tenant_id=tenant_id,
        created_by=user_id,
        contract_id=contract_id,
        version=version,
    )
    db.add(boq)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.boq.created",
        resource_type="boq",
        resource_id=boq.id,
        request_id=request_id,
        details={"contract_id": str(contract_id), "version": version},
    )
    db.flush()
    return boq


def get_boq(db: Session, *, tenant_id: UUID, boq_id: UUID) -> BOQ:
    boq = db.get(BOQ, boq_id)
    if boq is None or boq.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="BOQ not found")
    return boq


def list_boqs(db: Session, *, tenant_id: UUID, contract_id: UUID) -> list[BOQ]:
    return db.scalars(
        select(BOQ)
        .where(BOQ.tenant_id == tenant_id, BOQ.contract_id == contract_id)
        .order_by(BOQ.version)
    ).all()


def update_boq_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    boq_id: UUID,
    status: str,
    request_id: str | None = None,
) -> BOQ:
    boq = get_boq(db, tenant_id=tenant_id, boq_id=boq_id)
    valid_transitions = {
        "draft": {"submitted"},
        "submitted": {"approved"},
    }
    allowed = valid_transitions.get(boq.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition BOQ from '{boq.status}' to '{status}'",
        )
    boq.status = status
    boq.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.boq.{status}",
        resource_type="boq",
        resource_id=boq.id,
        request_id=request_id,
    )
    db.flush()
    return boq


def add_boq_item(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    boq_id: UUID,
    item_number: int,
    description: str,
    unit: str,
    quantity: Decimal,
    unit_rate: Decimal,
    amount: Decimal,
    request_id: str | None = None,
) -> BOQItem:
    boq = get_boq(db, tenant_id=tenant_id, boq_id=boq_id)
    if boq.status != "draft":
        raise HTTPException(status_code=409, detail="can only add items to draft BOQs")
    item = BOQItem(
        tenant_id=tenant_id,
        boq_id=boq_id,
        item_number=item_number,
        description=description,
        unit=unit,
        quantity=quantity,
        unit_rate=unit_rate,
        amount=amount,
    )
    db.add(item)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.boq_item.created",
        resource_type="boq_item",
        resource_id=item.id,
        request_id=request_id,
        details={"boq_id": str(boq_id), "item_number": item_number},
    )
    db.flush()
    return item


def list_boq_items(db: Session, *, tenant_id: UUID, boq_id: UUID) -> list[BOQItem]:
    return db.scalars(
        select(BOQItem)
        .where(BOQItem.tenant_id == tenant_id, BOQItem.boq_id == boq_id)
        .order_by(BOQItem.item_number)
    ).all()


# ---------------------------------------------------------------------------
# Progress Claim
# ---------------------------------------------------------------------------

def create_progress_claim(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    contract_id: UUID,
    claim_number: str,
    claim_date,
    period_start,
    period_end,
    request_id: str | None = None,
) -> ProgressClaim:
    get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    existing = db.scalar(
        select(ProgressClaim).where(
            ProgressClaim.tenant_id == tenant_id,
            ProgressClaim.claim_number == claim_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="claim number already exists")
    claim = ProgressClaim(
        tenant_id=tenant_id,
        created_by=user_id,
        contract_id=contract_id,
        claim_number=claim_number,
        claim_date=claim_date,
        period_start=period_start,
        period_end=period_end,
    )
    db.add(claim)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.progress_claim.created",
        resource_type="progress_claim",
        resource_id=claim.id,
        request_id=request_id,
        details={"claim_number": claim_number},
    )
    db.flush()
    return claim


def get_progress_claim(db: Session, *, tenant_id: UUID, claim_id: UUID) -> ProgressClaim:
    claim = db.get(ProgressClaim, claim_id)
    if claim is None or claim.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="progress claim not found")
    return claim


def list_progress_claims(
    db: Session, *, tenant_id: UUID, contract_id: UUID
) -> list[ProgressClaim]:
    return db.scalars(
        select(ProgressClaim)
        .where(
            ProgressClaim.tenant_id == tenant_id,
            ProgressClaim.contract_id == contract_id,
        )
        .order_by(ProgressClaim.created_at.desc())
    ).all()


def update_claim_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    claim_id: UUID,
    status: str,
    request_id: str | None = None,
) -> ProgressClaim:
    claim = get_progress_claim(db, tenant_id=tenant_id, claim_id=claim_id)
    valid_transitions = {
        "draft": {"submitted"},
        "submitted": {"approved"},
        "approved": {"paid"},
    }
    allowed = valid_transitions.get(claim.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition claim from '{claim.status}' to '{status}'",
        )
    claim.status = status
    claim.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.progress_claim.{status}",
        resource_type="progress_claim",
        resource_id=claim.id,
        request_id=request_id,
    )
    db.flush()
    return claim


def add_claim_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    claim_id: UUID,
    boq_item_id: UUID,
    description: str,
    quantity_completed: Decimal,
    amount: Decimal,
    request_id: str | None = None,
) -> ProgressClaimLine:
    claim = get_progress_claim(db, tenant_id=tenant_id, claim_id=claim_id)
    if claim.status != "draft":
        raise HTTPException(status_code=409, detail="can only add lines to draft claims")
    line = ProgressClaimLine(
        tenant_id=tenant_id,
        claim_id=claim_id,
        boq_item_id=boq_item_id,
        description=description,
        quantity_completed=quantity_completed,
        amount=amount,
    )
    db.add(line)
    db.flush()
    claim.total_amount = _sum_claim_amounts(db, claim_id)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.progress_claim_line.created",
        resource_type="progress_claim_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def _sum_claim_amounts(db: Session, claim_id: UUID) -> Decimal:
    lines = db.scalars(
        select(ProgressClaimLine).where(ProgressClaimLine.claim_id == claim_id)
    ).all()
    return sum((line.amount for line in lines), _ZERO)


def list_claim_lines(db: Session, *, tenant_id: UUID, claim_id: UUID) -> list[ProgressClaimLine]:
    return db.scalars(
        select(ProgressClaimLine)
        .where(
            ProgressClaimLine.tenant_id == tenant_id,
            ProgressClaimLine.claim_id == claim_id,
        )
        .order_by(ProgressClaimLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Procurement
# ---------------------------------------------------------------------------

def create_procurement(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    requisition_number: str,
    title: str,
    description: str | None = None,
    priority: str = "medium",
    request_id: str | None = None,
) -> Procurement:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    existing = db.scalar(
        select(Procurement).where(
            Procurement.tenant_id == tenant_id,
            Procurement.requisition_number == requisition_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="requisition number already exists")
    proc = Procurement(
        tenant_id=tenant_id,
        project_id=project_id,
        requested_by=user_id,
        requisition_number=requisition_number,
        title=title,
        description=description,
        priority=priority,
    )
    db.add(proc)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.procurement.created",
        resource_type="procurement",
        resource_id=proc.id,
        request_id=request_id,
        details={"requisition_number": requisition_number, "title": title},
    )
    db.flush()
    return proc


def get_procurement(db: Session, *, tenant_id: UUID, procurement_id: UUID) -> Procurement:
    proc = db.get(Procurement, procurement_id)
    if proc is None or proc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="procurement not found")
    return proc


def list_procurements(
    db: Session, *, tenant_id: UUID, project_id: UUID | None = None
) -> list[Procurement]:
    stmt = select(Procurement).where(Procurement.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Procurement.project_id == project_id)
    return db.scalars(stmt.order_by(Procurement.created_at.desc())).all()


def update_procurement_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    procurement_id: UUID,
    status: str,
    request_id: str | None = None,
) -> Procurement:
    proc = get_procurement(db, tenant_id=tenant_id, procurement_id=procurement_id)
    valid_transitions = {
        "draft": {"pending_approval"},
        "pending_approval": {"approved", "cancelled"},
        "approved": {"ordered"},
        "ordered": {"received"},
    }
    allowed = valid_transitions.get(proc.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition procurement from '{proc.status}' to '{status}'",
        )
    proc.status = status
    proc.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.procurement.{status}",
        resource_type="procurement",
        resource_id=proc.id,
        request_id=request_id,
    )
    db.flush()
    return proc


def add_procurement_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    procurement_id: UUID,
    description: str,
    unit: str,
    quantity: Decimal,
    estimated_unit_price: Decimal,
    estimated_total: Decimal,
    request_id: str | None = None,
) -> ProcurementLine:
    proc = get_procurement(db, tenant_id=tenant_id, procurement_id=procurement_id)
    if proc.status != "draft":
        raise HTTPException(
            status_code=409, detail="can only add lines to draft procurements"
        )
    line = ProcurementLine(
        tenant_id=tenant_id,
        procurement_id=procurement_id,
        description=description,
        unit=unit,
        quantity=quantity,
        estimated_unit_price=estimated_unit_price,
        estimated_total=estimated_total,
    )
    db.add(line)
    db.flush()
    proc.total_estimated = _sum_procurement_totals(db, procurement_id)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.procurement_line.created",
        resource_type="procurement_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def _sum_procurement_totals(db: Session, procurement_id: UUID) -> Decimal:
    lines = db.scalars(
        select(ProcurementLine).where(ProcurementLine.procurement_id == procurement_id)
    ).all()
    return sum((line.estimated_total for line in lines), _ZERO)


def list_procurement_lines(
    db: Session, *, tenant_id: UUID, procurement_id: UUID
) -> list[ProcurementLine]:
    return db.scalars(
        select(ProcurementLine)
        .where(
            ProcurementLine.tenant_id == tenant_id,
            ProcurementLine.procurement_id == procurement_id,
        )
        .order_by(ProcurementLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

def create_budget(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    version: int = 1,
    request_id: str | None = None,
) -> Budget:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    existing = db.scalar(
        select(Budget).where(
            Budget.tenant_id == tenant_id,
            Budget.project_id == project_id,
            Budget.version == version,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="budget version already exists for this project")
    budget = Budget(
        tenant_id=tenant_id,
        created_by=user_id,
        project_id=project_id,
        version=version,
    )
    db.add(budget)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.budget.created",
        resource_type="budget",
        resource_id=budget.id,
        request_id=request_id,
        details={"project_id": str(project_id), "version": version},
    )
    db.flush()
    return budget


def get_budget(db: Session, *, tenant_id: UUID, budget_id: UUID) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="budget not found")
    return budget


def list_budgets(db: Session, *, tenant_id: UUID, project_id: UUID) -> list[Budget]:
    return db.scalars(
        select(Budget)
        .where(Budget.tenant_id == tenant_id, Budget.project_id == project_id)
        .order_by(Budget.version)
    ).all()


def update_budget_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    budget_id: UUID,
    status: str,
    request_id: str | None = None,
) -> Budget:
    budget = get_budget(db, tenant_id=tenant_id, budget_id=budget_id)
    valid_transitions = {
        "draft": {"approved"},
        "approved": {"baselined"},
    }
    allowed = valid_transitions.get(budget.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition budget from '{budget.status}' to '{status}'",
        )
    budget.status = status
    budget.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.budget.{status}",
        resource_type="budget",
        resource_id=budget.id,
        request_id=request_id,
    )
    db.flush()
    return budget


def add_budget_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    budget_id: UUID,
    description: str,
    unit: str,
    quantity: Decimal,
    unit_rate: Decimal,
    amount: Decimal,
    boq_item_id: UUID | None = None,
    request_id: str | None = None,
) -> BudgetLine:
    budget = get_budget(db, tenant_id=tenant_id, budget_id=budget_id)
    if budget.status != "draft":
        raise HTTPException(status_code=409, detail="can only add lines to draft budgets")
    line = BudgetLine(
        tenant_id=tenant_id,
        budget_id=budget_id,
        boq_item_id=boq_item_id,
        description=description,
        unit=unit,
        quantity=quantity,
        unit_rate=unit_rate,
        amount=amount,
    )
    db.add(line)
    db.flush()
    budget.total_amount = _sum_budget_amounts(db, budget_id)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.budget_line.created",
        resource_type="budget_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def _sum_budget_amounts(db: Session, budget_id: UUID) -> Decimal:
    lines = db.scalars(
        select(BudgetLine).where(BudgetLine.budget_id == budget_id)
    ).all()
    return sum((line.amount for line in lines), _ZERO)


def list_budget_lines(db: Session, *, tenant_id: UUID, budget_id: UUID) -> list[BudgetLine]:
    return db.scalars(
        select(BudgetLine)
        .where(
            BudgetLine.tenant_id == tenant_id,
            BudgetLine.budget_id == budget_id,
        )
        .order_by(BudgetLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Change Order
# ---------------------------------------------------------------------------

def create_change_order(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    contract_id: UUID,
    change_order_number: str,
    title: str,
    description: str,
    impact_type: str = "cost",
    cost_impact: Decimal = Decimal("0"),
    time_impact_days: int = 0,
    request_id: str | None = None,
) -> ChangeOrder:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    existing = db.scalar(
        select(ChangeOrder).where(
            ChangeOrder.tenant_id == tenant_id,
            ChangeOrder.change_order_number == change_order_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="change order number already exists")
    co = ChangeOrder(
        tenant_id=tenant_id,
        created_by=user_id,
        project_id=project_id,
        contract_id=contract_id,
        change_order_number=change_order_number,
        title=title,
        description=description,
        impact_type=impact_type,
        cost_impact=cost_impact,
        time_impact_days=time_impact_days,
    )
    db.add(co)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.change_order.created",
        resource_type="change_order",
        resource_id=co.id,
        request_id=request_id,
        details={"change_order_number": change_order_number, "title": title},
    )
    db.flush()
    return co


def get_change_order(db: Session, *, tenant_id: UUID, change_order_id: UUID) -> ChangeOrder:
    co = db.get(ChangeOrder, change_order_id)
    if co is None or co.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="change order not found")
    return co


def list_change_orders(
    db: Session, *, tenant_id: UUID, project_id: UUID | None = None
) -> list[ChangeOrder]:
    stmt = select(ChangeOrder).where(ChangeOrder.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(ChangeOrder.project_id == project_id)
    return db.scalars(stmt.order_by(ChangeOrder.created_at.desc())).all()


def update_change_order_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    change_order_id: UUID,
    status: str,
    request_id: str | None = None,
) -> ChangeOrder:
    co = get_change_order(db, tenant_id=tenant_id, change_order_id=change_order_id)
    valid_transitions = {
        "draft": {"pending_approval"},
        "pending_approval": {"approved", "rejected"},
        "approved": {"implemented"},
    }
    allowed = valid_transitions.get(co.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition change order from '{co.status}' to '{status}'",
        )
    co.status = status
    co.updated_at = datetime.now(UTC)
    if status == "approved":
        co.approved_by = user_id
        co.approved_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.change_order.{status}",
        resource_type="change_order",
        resource_id=co.id,
        request_id=request_id,
    )
    db.flush()
    return co


# ---------------------------------------------------------------------------
# Subcontract
# ---------------------------------------------------------------------------

def create_subcontract(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    contract_id: UUID,
    subcontract_number: str,
    subcontractor_name: str,
    scope: str,
    value: Decimal = Decimal("0"),
    status: str = "draft",
    start_date=None,
    end_date=None,
    request_id: str | None = None,
) -> Subcontract:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    get_contract(db, tenant_id=tenant_id, contract_id=contract_id)
    existing = db.scalar(
        select(Subcontract).where(
            Subcontract.tenant_id == tenant_id,
            Subcontract.subcontract_number == subcontract_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="subcontract number already exists")
    sub = Subcontract(
        tenant_id=tenant_id,
        created_by=user_id,
        project_id=project_id,
        contract_id=contract_id,
        subcontract_number=subcontract_number,
        subcontractor_name=subcontractor_name,
        scope=scope,
        value=value,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(sub)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.subcontract.created",
        resource_type="subcontract",
        resource_id=sub.id,
        request_id=request_id,
        details={"subcontract_number": subcontract_number, "subcontractor_name": subcontractor_name},
    )
    db.flush()
    return sub


def get_subcontract(db: Session, *, tenant_id: UUID, subcontract_id: UUID) -> Subcontract:
    sub = db.get(Subcontract, subcontract_id)
    if sub is None or sub.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="subcontract not found")
    return sub


def list_subcontracts(
    db: Session, *, tenant_id: UUID, project_id: UUID | None = None
) -> list[Subcontract]:
    stmt = select(Subcontract).where(Subcontract.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Subcontract.project_id == project_id)
    return db.scalars(stmt.order_by(Subcontract.created_at.desc())).all()


def update_subcontract_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    subcontract_id: UUID,
    status: str,
    request_id: str | None = None,
) -> Subcontract:
    sub = get_subcontract(db, tenant_id=tenant_id, subcontract_id=subcontract_id)
    valid_transitions = {
        "draft": {"pending_approval"},
        "pending_approval": {"active", "cancelled"},
        "active": {"completed"},
    }
    allowed = valid_transitions.get(sub.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition subcontract from '{sub.status}' to '{status}'",
        )
    sub.status = status
    sub.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.subcontract.{status}",
        resource_type="subcontract",
        resource_id=sub.id,
        request_id=request_id,
    )
    db.flush()
    return sub


# ---------------------------------------------------------------------------
# Site Warehouse
# ---------------------------------------------------------------------------

def create_site_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    code: str,
    name: str,
    location: str | None = None,
    manager_id: UUID | None = None,
    request_id: str | None = None,
) -> SiteWarehouse:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    existing = db.scalar(
        select(SiteWarehouse).where(
            SiteWarehouse.tenant_id == tenant_id,
            SiteWarehouse.code == code,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="warehouse code already exists")
    wh = SiteWarehouse(
        tenant_id=tenant_id,
        project_id=project_id,
        code=code,
        name=name,
        location=location,
        manager_id=manager_id,
    )
    db.add(wh)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.site_warehouse.created",
        resource_type="site_warehouse",
        resource_id=wh.id,
        request_id=request_id,
        details={"code": code, "name": name},
    )
    db.flush()
    return wh


def get_site_warehouse(db: Session, *, tenant_id: UUID, warehouse_id: UUID) -> SiteWarehouse:
    wh = db.get(SiteWarehouse, warehouse_id)
    if wh is None or wh.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="site warehouse not found")
    return wh


def list_site_warehouses(
    db: Session, *, tenant_id: UUID, project_id: UUID | None = None
) -> list[SiteWarehouse]:
    stmt = select(SiteWarehouse).where(SiteWarehouse.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(SiteWarehouse.project_id == project_id)
    return db.scalars(stmt.order_by(SiteWarehouse.created_at.desc())).all()


def update_site_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    warehouse_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> SiteWarehouse:
    wh = get_site_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    for key, value in data.items():
        if value is not None:
            setattr(wh, key, value)
    wh.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.site_warehouse.updated",
        resource_type="site_warehouse",
        resource_id=wh.id,
        request_id=request_id,
        details=data,
    )
    db.flush()
    return wh


def delete_site_warehouse(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    warehouse_id: UUID,
    request_id: str | None = None,
) -> None:
    wh = get_site_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.site_warehouse.deleted",
        resource_type="site_warehouse",
        resource_id=wh.id,
        request_id=request_id,
    )
    db.delete(wh)
    db.flush()


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------

def create_purchase_order(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    procurement_id: UUID,
    supplier_id: UUID,
    po_number: str,
    currency: str = "USD",
    terms: str | None = None,
    delivery_date: date | None = None,
    request_id: str | None = None,
) -> PurchaseOrder:
    get_procurement(db, tenant_id=tenant_id, procurement_id=procurement_id)
    existing = db.scalar(
        select(PurchaseOrder).where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.po_number == po_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="PO number already exists")
    po = PurchaseOrder(
        tenant_id=tenant_id,
        created_by=user_id,
        procurement_id=procurement_id,
        supplier_id=supplier_id,
        po_number=po_number,
        currency=currency,
        terms=terms,
        delivery_date=delivery_date,
    )
    db.add(po)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.purchase_order.created",
        resource_type="purchase_order",
        resource_id=po.id,
        request_id=request_id,
        details={"po_number": po_number, "procurement_id": str(procurement_id)},
    )
    db.flush()
    return po


def get_purchase_order(db: Session, *, tenant_id: UUID, po_id: UUID) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return po


def list_purchase_orders(
    db: Session, *, tenant_id: UUID, procurement_id: UUID | None = None
) -> list[PurchaseOrder]:
    stmt = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
    if procurement_id:
        stmt = stmt.where(PurchaseOrder.procurement_id == procurement_id)
    return db.scalars(stmt.order_by(PurchaseOrder.created_at.desc())).all()


def update_purchase_order_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    po_id: UUID,
    status: str,
    request_id: str | None = None,
) -> PurchaseOrder:
    po = get_purchase_order(db, tenant_id=tenant_id, po_id=po_id)
    valid_transitions = {
        "draft": {"sent"},
        "sent": {"acknowledged"},
        "acknowledged": {"partial_received", "received"},
        "partial_received": {"received"},
    }
    allowed = valid_transitions.get(po.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition PO from '{po.status}' to '{status}'",
        )
    po.status = status
    po.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.purchase_order.{status}",
        resource_type="purchase_order",
        resource_id=po.id,
        request_id=request_id,
    )
    db.flush()
    return po


def add_purchase_order_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    po_id: UUID,
    procurement_line_id: UUID,
    description: str,
    unit: str,
    quantity: Decimal,
    unit_price: Decimal,
    line_total: Decimal,
    request_id: str | None = None,
) -> PurchaseOrderLine:
    po = get_purchase_order(db, tenant_id=tenant_id, po_id=po_id)
    if po.status != "draft":
        raise HTTPException(status_code=409, detail="can only add lines to draft POs")
    line = PurchaseOrderLine(
        tenant_id=tenant_id,
        purchase_order_id=po_id,
        procurement_line_id=procurement_line_id,
        description=description,
        unit=unit,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
    )
    db.add(line)
    db.flush()
    po.total_amount = _sum_po_amounts(db, po_id)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.purchase_order_line.created",
        resource_type="purchase_order_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def _sum_po_amounts(db: Session, po_id: UUID) -> Decimal:
    lines = db.scalars(
        select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == po_id)
    ).all()
    return sum((line.line_total for line in lines), _ZERO)


def list_purchase_order_lines(
    db: Session, *, tenant_id: UUID, po_id: UUID
) -> list[PurchaseOrderLine]:
    return db.scalars(
        select(PurchaseOrderLine)
        .where(
            PurchaseOrderLine.tenant_id == tenant_id,
            PurchaseOrderLine.purchase_order_id == po_id,
        )
        .order_by(PurchaseOrderLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Goods Receipt (GRN)
# ---------------------------------------------------------------------------

def create_goods_receipt(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    purchase_order_id: UUID,
    grn_number: str,
    received_date: date,
    warehouse_id: UUID,
    received_by: UUID,
    notes: str | None = None,
    request_id: str | None = None,
) -> GoodsReceipt:
    get_purchase_order(db, tenant_id=tenant_id, po_id=purchase_order_id)
    get_site_warehouse(db, tenant_id=tenant_id, warehouse_id=warehouse_id)
    existing = db.scalar(
        select(GoodsReceipt).where(
            GoodsReceipt.tenant_id == tenant_id,
            GoodsReceipt.grn_number == grn_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="GRN number already exists")
    grn = GoodsReceipt(
        tenant_id=tenant_id,
        purchase_order_id=purchase_order_id,
        grn_number=grn_number,
        received_date=received_date,
        warehouse_id=warehouse_id,
        received_by=received_by,
        notes=notes,
    )
    db.add(grn)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.goods_receipt.created",
        resource_type="goods_receipt",
        resource_id=grn.id,
        request_id=request_id,
        details={"grn_number": grn_number, "po_id": str(purchase_order_id)},
    )
    db.flush()
    return grn


def get_goods_receipt(db: Session, *, tenant_id: UUID, grn_id: UUID) -> GoodsReceipt:
    grn = db.get(GoodsReceipt, grn_id)
    if grn is None or grn.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="goods receipt not found")
    return grn


def list_goods_receipts(
    db: Session, *, tenant_id: UUID, po_id: UUID | None = None
) -> list[GoodsReceipt]:
    stmt = select(GoodsReceipt).where(GoodsReceipt.tenant_id == tenant_id)
    if po_id:
        stmt = stmt.where(GoodsReceipt.purchase_order_id == po_id)
    return db.scalars(stmt.order_by(GoodsReceipt.created_at.desc())).all()


def update_goods_receipt_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    grn_id: UUID,
    status: str,
    request_id: str | None = None,
) -> GoodsReceipt:
    grn = get_goods_receipt(db, tenant_id=tenant_id, grn_id=grn_id)
    valid_transitions = {
        "draft": {"partial", "completed"},
        "partial": {"completed"},
    }
    allowed = valid_transitions.get(grn.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition GRN from '{grn.status}' to '{status}'",
        )
    grn.status = status
    grn.updated_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.goods_receipt.{status}",
        resource_type="goods_receipt",
        resource_id=grn.id,
        request_id=request_id,
    )
    db.flush()
    return grn


def add_goods_receipt_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    grn_id: UUID,
    po_line_id: UUID,
    quantity_received: Decimal,
    quantity_accepted: Decimal,
    quantity_rejected: Decimal = Decimal("0"),
    notes: str | None = None,
    request_id: str | None = None,
) -> GoodsReceiptLine:
    grn = get_goods_receipt(db, tenant_id=tenant_id, grn_id=grn_id)
    if grn.status == "completed":
        raise HTTPException(status_code=409, detail="cannot add lines to completed GRN")
    line = GoodsReceiptLine(
        tenant_id=tenant_id,
        goods_receipt_id=grn_id,
        po_line_id=po_line_id,
        quantity_received=quantity_received,
        quantity_accepted=quantity_accepted,
        quantity_rejected=quantity_rejected,
        notes=notes,
    )
    db.add(line)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.goods_receipt_line.created",
        resource_type="goods_receipt_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def list_goods_receipt_lines(
    db: Session, *, tenant_id: UUID, grn_id: UUID
) -> list[GoodsReceiptLine]:
    return db.scalars(
        select(GoodsReceiptLine)
        .where(
            GoodsReceiptLine.tenant_id == tenant_id,
            GoodsReceiptLine.goods_receipt_id == grn_id,
        )
        .order_by(GoodsReceiptLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------

def create_supplier_invoice(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    purchase_order_id: UUID,
    grn_id: UUID | None,
    invoice_number: str,
    supplier_invoice_number: str,
    invoice_date: date,
    due_date: date,
    currency: str = "USD",
    request_id: str | None = None,
) -> SupplierInvoice:
    get_purchase_order(db, tenant_id=tenant_id, po_id=purchase_order_id)
    if grn_id:
        get_goods_receipt(db, tenant_id=tenant_id, grn_id=grn_id)
    existing = db.scalar(
        select(SupplierInvoice).where(
            SupplierInvoice.tenant_id == tenant_id,
            SupplierInvoice.invoice_number == invoice_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="invoice number already exists")
    inv = SupplierInvoice(
        tenant_id=tenant_id,
        submitted_by=user_id,
        purchase_order_id=purchase_order_id,
        grn_id=grn_id,
        invoice_number=invoice_number,
        supplier_invoice_number=supplier_invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        currency=currency,
    )
    db.add(inv)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.supplier_invoice.created",
        resource_type="supplier_invoice",
        resource_id=inv.id,
        request_id=request_id,
        details={"invoice_number": invoice_number, "po_id": str(purchase_order_id)},
    )
    db.flush()
    return inv


def get_supplier_invoice(db: Session, *, tenant_id: UUID, invoice_id: UUID) -> SupplierInvoice:
    inv = db.get(SupplierInvoice, invoice_id)
    if inv is None or inv.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="supplier invoice not found")
    return inv


def list_supplier_invoices(
    db: Session, *, tenant_id: UUID, po_id: UUID | None = None
) -> list[SupplierInvoice]:
    stmt = select(SupplierInvoice).where(SupplierInvoice.tenant_id == tenant_id)
    if po_id:
        stmt = stmt.where(SupplierInvoice.purchase_order_id == po_id)
    return db.scalars(stmt.order_by(SupplierInvoice.created_at.desc())).all()


def update_supplier_invoice_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    invoice_id: UUID,
    status: str,
    request_id: str | None = None,
) -> SupplierInvoice:
    inv = get_supplier_invoice(db, tenant_id=tenant_id, invoice_id=invoice_id)
    valid_transitions = {
        "draft": {"pending_approval"},
        "pending_approval": {"approved", "rejected"},
        "approved": {"paid"},
    }
    allowed = valid_transitions.get(inv.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition invoice from '{inv.status}' to '{status}'",
        )
    inv.status = status
    inv.updated_at = datetime.now(UTC)
    if status == "approved":
        inv.approved_by = user_id
        inv.approved_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.supplier_invoice.{status}",
        resource_type="supplier_invoice",
        resource_id=inv.id,
        request_id=request_id,
    )
    db.flush()
    return inv


def add_supplier_invoice_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    invoice_id: UUID,
    description: str,
    unit: str,
    quantity: Decimal,
    unit_price: Decimal,
    line_total: Decimal,
    tax_rate: Decimal = Decimal("0"),
    tax_amount: Decimal = Decimal("0"),
    grn_line_id: UUID | None = None,
    request_id: str | None = None,
) -> SupplierInvoiceLine:
    inv = get_supplier_invoice(db, tenant_id=tenant_id, invoice_id=invoice_id)
    if inv.status != "draft":
        raise HTTPException(status_code=409, detail="can only add lines to draft invoices")
    line = SupplierInvoiceLine(
        tenant_id=tenant_id,
        supplier_invoice_id=invoice_id,
        grn_line_id=grn_line_id,
        description=description,
        unit=unit,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
    )
    db.add(line)
    db.flush()
    inv.subtotal = _sum_invoice_subtotals(db, invoice_id)
    inv.tax_amount = _sum_invoice_tax(db, invoice_id)
    inv.total_amount = inv.subtotal + inv.tax_amount
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.supplier_invoice_line.created",
        resource_type="supplier_invoice_line",
        resource_id=line.id,
        request_id=request_id,
    )
    db.flush()
    return line


def _sum_invoice_subtotals(db: Session, invoice_id: UUID) -> Decimal:
    lines = db.scalars(
        select(SupplierInvoiceLine).where(SupplierInvoiceLine.supplier_invoice_id == invoice_id)
    ).all()
    return sum((line.line_total for line in lines), _ZERO)


def _sum_invoice_tax(db: Session, invoice_id: UUID) -> Decimal:
    lines = db.scalars(
        select(SupplierInvoiceLine).where(SupplierInvoiceLine.supplier_invoice_id == invoice_id)
    ).all()
    return sum((line.tax_amount for line in lines), _ZERO)


def list_supplier_invoice_lines(
    db: Session, *, tenant_id: UUID, invoice_id: UUID
) -> list[SupplierInvoiceLine]:
    return db.scalars(
        select(SupplierInvoiceLine)
        .where(
            SupplierInvoiceLine.tenant_id == tenant_id,
            SupplierInvoiceLine.supplier_invoice_id == invoice_id,
        )
        .order_by(SupplierInvoiceLine.created_at)
    ).all()


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

def create_payment(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    supplier_invoice_id: UUID,
    payment_number: str,
    payment_method: str = "bank_transfer",
    amount: Decimal,
    currency: str = "USD",
    payment_date: date,
    reference: str | None = None,
    notes: str | None = None,
    request_id: str | None = None,
) -> Payment:
    get_supplier_invoice(db, tenant_id=tenant_id, invoice_id=supplier_invoice_id)
    existing = db.scalar(
        select(Payment).where(
            Payment.tenant_id == tenant_id,
            Payment.payment_number == payment_number,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="payment number already exists")
    pay = Payment(
        tenant_id=tenant_id,
        created_by=user_id,
        supplier_invoice_id=supplier_invoice_id,
        payment_number=payment_number,
        payment_method=payment_method,
        amount=amount,
        currency=currency,
        payment_date=payment_date,
        reference=reference,
        notes=notes,
    )
    db.add(pay)
    db.flush()
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="construction.payment.created",
        resource_type="payment",
        resource_id=pay.id,
        request_id=request_id,
        details={"payment_number": payment_number, "invoice_id": str(supplier_invoice_id)},
    )
    db.flush()
    return pay


def get_payment(db: Session, *, tenant_id: UUID, payment_id: UUID) -> Payment:
    pay = db.get(Payment, payment_id)
    if pay is None or pay.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="payment not found")
    return pay


def list_payments(
    db: Session, *, tenant_id: UUID, invoice_id: UUID | None = None
) -> list[Payment]:
    stmt = select(Payment).where(Payment.tenant_id == tenant_id)
    if invoice_id:
        stmt = stmt.where(Payment.supplier_invoice_id == invoice_id)
    return db.scalars(stmt.order_by(Payment.created_at.desc())).all()


def update_payment_status(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payment_id: UUID,
    status: str,
    request_id: str | None = None,
) -> Payment:
    pay = get_payment(db, tenant_id=tenant_id, payment_id=payment_id)
    valid_transitions = {
        "draft": {"pending_approval"},
        "pending_approval": {"approved", "cancelled"},
        "approved": {"processing"},
        "processing": {"completed", "failed"},
    }
    allowed = valid_transitions.get(pay.status, set())
    if status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"cannot transition payment from '{pay.status}' to '{status}'",
        )
    pay.status = status
    pay.updated_at = datetime.now(UTC)
    if status == "approved":
        pay.approved_by = user_id
        pay.approved_at = datetime.now(UTC)
    elif status == "completed":
        pay.processed_at = datetime.now(UTC)
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"construction.payment.{status}",
        resource_type="payment",
        resource_id=pay.id,
        request_id=request_id,
    )
    db.flush()
    return pay
