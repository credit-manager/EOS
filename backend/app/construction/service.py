from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from .models import (
    BOQ,
    BOQItem,
    Contract,
    Procurement,
    ProcurementLine,
    ProgressClaim,
    ProgressClaimLine,
    Project,
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
