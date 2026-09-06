from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from eos_v2.application.foundation.services import FoundationService
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.foundation_repository import FoundationRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission
from eos_v2.modules.purchasing import PurchaseOrderLine, PurchaseOrderStatus
from eos_v2.modules.sales import SalesOrderLine, SalesOrderStatus

router = APIRouter(prefix="/api/v1/foundation", tags=["foundation"])


class OrderLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class SalesCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: UUID
    currency: str = Field(min_length=3, max_length=3)
    lines: list[OrderLineRequest] = Field(min_length=1)


class PurchaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: UUID
    currency: str = Field(min_length=3, max_length=3)
    lines: list[PurchaseLineRequest] = Field(min_length=1)


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_number: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    hire_date: date


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date | None = None


class InventoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: UUID
    quantity: Decimal
    source: str = Field(min_length=1, max_length=100)


def _db(request: Request):
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return database


def _order_response(order) -> dict[str, object]:
    return {"id": str(order.id), "tenant_id": str(order.tenant_id), "status": order.status.value, "currency": order.currency, "total": str(sum((line.total for line in order.lines), Decimal("0")))}


def _purchase_response(order) -> dict[str, object]:
    return {"id": str(order.id), "tenant_id": str(order.tenant_id), "status": order.status.value, "currency": order.currency, "total": str(sum((line.total for line in order.lines), Decimal("0")))}


@router.post("/sales-orders", status_code=status.HTTP_201_CREATED)
def create_sales(payload: SalesCreateRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try:
        order = FoundationService.create_sales_order(payload.customer_id, payload.currency, tuple(SalesOrderLine(x.item_id, x.quantity, x.unit_price) for x in payload.lines))
        with _db(request).session() as session:
            FoundationRepository(session).save_sales(order)
            session.commit()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Sales order already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _order_response(order)


@router.get("/sales-orders/{order_id}")
def get_sales(order_id: UUID, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.READ)
    try:
        with _db(request).session() as session: return _order_response(FoundationRepository(session).get_sales(order_id))
    except KeyError as exc: raise HTTPException(status_code=404, detail="Sales order not found") from exc


@router.post("/sales-orders/{order_id}/transition")
def transition_sales(order_id: UUID, payload: TransitionRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try: target = SalesOrderStatus(payload.status)
    except ValueError as exc: raise HTTPException(status_code=422, detail="Invalid sales status") from exc
    try:
        with _db(request).session() as session:
            repository = FoundationRepository(session)
            updated = FoundationService.transition_sales_order(repository.get_sales(order_id), target)
            repository.save_sales(updated)
            session.commit()
    except KeyError as exc: raise HTTPException(status_code=404, detail="Sales order not found") from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _order_response(updated)


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
def create_purchase(payload: PurchaseCreateRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try:
        order = FoundationService.create_purchase_order(payload.supplier_id, payload.currency, tuple(PurchaseOrderLine(x.item_id, x.quantity, x.unit_cost) for x in payload.lines))
        with _db(request).session() as session:
            FoundationRepository(session).save_purchase(order)
            session.commit()
    except IntegrityError as exc: raise HTTPException(status_code=409, detail="Purchase order already exists") from exc
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _purchase_response(order)


@router.get("/purchase-orders/{order_id}")
def get_purchase(order_id: UUID, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.READ)
    try:
        with _db(request).session() as session: return _purchase_response(FoundationRepository(session).get_purchase(order_id))
    except KeyError as exc: raise HTTPException(status_code=404, detail="Purchase order not found") from exc


@router.post("/purchase-orders/{order_id}/transition")
def transition_purchase(order_id: UUID, payload: TransitionRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try: target = PurchaseOrderStatus(payload.status)
    except ValueError as exc: raise HTTPException(status_code=422, detail="Invalid purchase status") from exc
    try:
        with _db(request).session() as session:
            repository = FoundationRepository(session)
            updated = FoundationService.transition_purchase_order(repository.get_purchase(order_id), target)
            repository.save_purchase(updated)
            session.commit()
    except KeyError as exc: raise HTTPException(status_code=404, detail="Purchase order not found") from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _purchase_response(updated)


@router.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreateRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    employee = FoundationService.create_employee(payload.employee_number, payload.name, payload.hire_date)
    try:
        with _db(request).session() as session: FoundationRepository(session).save_employee(employee); session.commit()
    except IntegrityError as exc: raise HTTPException(status_code=409, detail="Employee number already exists") from exc
    return {"id": str(employee.id), "tenant_id": str(employee.tenant_id), "employee_number": employee.employee_number, "name": employee.name, "hire_date": employee.hire_date.isoformat(), "active": employee.active}


@router.get("/employees/{employee_id}")
def get_employee(employee_id: UUID, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.READ)
    try:
        with _db(request).session() as session: employee = FoundationRepository(session).get_employee(employee_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail="Employee not found") from exc
    return {"id": str(employee.id), "tenant_id": str(employee.tenant_id), "employee_number": employee.employee_number, "name": employee.name, "hire_date": employee.hire_date.isoformat(), "active": employee.active}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try: project = FoundationService.create_project(payload.code, payload.name, payload.start_date, payload.end_date)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        with _db(request).session() as session: FoundationRepository(session).save_project(project); session.commit()
    except IntegrityError as exc: raise HTTPException(status_code=409, detail="Project code already exists") from exc
    return {"id": str(project.id), "tenant_id": str(project.tenant_id), "code": project.code, "name": project.name, "status": project.status.value, "start_date": project.start_date.isoformat(), "end_date": project.end_date.isoformat() if project.end_date else None}


@router.get("/projects/{project_id}")
def get_project(project_id: UUID, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.READ)
    try:
        with _db(request).session() as session: project = FoundationRepository(session).get_project(project_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail="Project not found") from exc
    return {"id": str(project.id), "tenant_id": str(project.tenant_id), "code": project.code, "name": project.name, "status": project.status.value, "start_date": project.start_date.isoformat(), "end_date": project.end_date.isoformat() if project.end_date else None}


@router.post("/inventory/movements", status_code=status.HTTP_201_CREATED)
def inventory(payload: InventoryRequest, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.WRITE)
    try:
        with _db(request).session() as session:
            repository = FoundationRepository(session)
            movement, balance = FoundationService.apply_inventory_movement(payload.item_id, payload.quantity, payload.source, repository.get_stock(payload.item_id))
            repository.save_inventory(movement, balance)
            session.commit()
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"movement_id": str(movement.id), "tenant_id": str(movement.tenant_id), "item_id": str(movement.item_id), "quantity": str(balance.quantity)}


@router.get("/inventory/{item_id}")
def stock(item_id: UUID, request: Request, identity=Depends(get_current_identity)):
    require_permission(identity, Permission.READ)
    with _db(request).session() as session: balance = FoundationRepository(session).get_stock(item_id)
    return {"tenant_id": str(balance.tenant_id), "item_id": str(balance.item_id), "quantity": str(balance.quantity)}
