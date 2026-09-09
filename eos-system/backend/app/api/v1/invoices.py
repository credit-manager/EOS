"""
EOS System — Invoices Router (Sales Invoices + Supplier Invoices)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.sales_ext import (
    SalesInvoice, SalesInvoiceLine,
    SupplierInvoice, SupplierInvoiceLine,
)

router = APIRouter()


# ─── Sales Invoice Schemas ────────────────────────────────

class SalesInvoiceLineCreate(BaseModel):
    product_id: Optional[str] = None
    description: Optional[str] = None
    quantity: int
    unit_price: Decimal
    discount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total: Decimal


class SalesInvoiceCreate(BaseModel):
    customer_id: str
    sales_order_id: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    discount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    notes: Optional[str] = None
    lines: List[SalesInvoiceLineCreate] = []


class SalesInvoiceLineResponse(BaseModel):
    id: str
    product_id: Optional[str]
    description: Optional[str]
    quantity: int
    unit_price: float
    discount: float
    tax_amount: float
    total: float


class SalesInvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    customer_id: str
    customer_name: Optional[str]
    invoice_date: date
    due_date: Optional[date]
    status: str
    subtotal: float
    tax_amount: float
    discount: float
    total: float
    amount_paid: float
    currency: str
    notes: Optional[str]
    created_at: datetime


class SalesInvoiceListResponse(BaseModel):
    invoices: List[SalesInvoiceResponse]
    total: int


# ─── Supplier Invoice Schemas ─────────────────────────────

class SupplierInvoiceLineCreate(BaseModel):
    product_id: Optional[str] = None
    description: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal = Decimal("0")
    total: Decimal


class SupplierInvoiceCreate(BaseModel):
    supplier_id: str
    purchase_order_id: Optional[str] = None
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    tax_amount: Decimal = Decimal("0")
    notes: Optional[str] = None
    lines: List[SupplierInvoiceLineCreate] = []


class SupplierInvoiceLineResponse(BaseModel):
    id: str
    product_id: Optional[str]
    description: Optional[str]
    quantity: int
    unit_price: float
    tax_amount: float
    total: float


class SupplierInvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    supplier_id: str
    supplier_name: Optional[str]
    invoice_date: date
    due_date: Optional[date]
    status: str
    subtotal: float
    tax_amount: float
    total: float
    amount_paid: float
    currency: str
    notes: Optional[str]
    created_at: datetime


class SupplierInvoiceListResponse(BaseModel):
    invoices: List[SupplierInvoiceResponse]
    total: int


# ─── SALES INVOICES ───────────────────────────────────────

@router.get("/sales-invoices", response_model=SalesInvoiceListResponse)
async def list_sales_invoices(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    query = select(SalesInvoice).options(selectinload(SalesInvoice.customer))
    query = query.filter(SalesInvoice.tenant_id == current_user["tenant_id"])
    if customer_id:
        query = query.filter(SalesInvoice.customer_id == customer_id)
    if status:
        query = query.filter(SalesInvoice.status == status)
    query = query.order_by(SalesInvoice.created_at.desc())

    count_q = select(func.count(SalesInvoice.id)).filter(
        SalesInvoice.tenant_id == current_user["tenant_id"]
    )
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invoices = result.scalars().all()

    return SalesInvoiceListResponse(
        invoices=[
            SalesInvoiceResponse(
                id=inv.id, invoice_number=inv.invoice_number,
                customer_id=inv.customer_id,
                customer_name=inv.customer.name if inv.customer else None,
                invoice_date=inv.invoice_date, due_date=inv.due_date,
                status=inv.status, subtotal=float(inv.subtotal),
                tax_amount=float(inv.tax_amount), discount=float(inv.discount),
                total=float(inv.total), amount_paid=float(inv.amount_paid),
                currency=inv.currency, notes=inv.notes, created_at=inv.created_at,
            )
            for inv in invoices
        ],
        total=total,
    )


@router.post("/sales-invoices", response_model=SalesInvoiceResponse)
async def create_sales_invoice(
    invoice: SalesInvoiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:create")

    inv_num = f"SI-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    subtotal = sum(line.total for line in invoice.lines)

    new_inv = SalesInvoice(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        invoice_number=inv_num,
        customer_id=invoice.customer_id, sales_order_id=invoice.sales_order_id,
        invoice_date=invoice.invoice_date, due_date=invoice.due_date,
        status="draft", subtotal=subtotal, tax_amount=invoice.tax_amount,
        discount=invoice.discount, total=subtotal + invoice.tax_amount - invoice.discount,
        amount_paid=Decimal("0"), currency="EGP", notes=invoice.notes,
        created_by=current_user["id"],
    )
    db.add(new_inv)
    await db.flush()

    for line in invoice.lines:
        db.add(SalesInvoiceLine(
            id=str(uuid.uuid4()), invoice_id=new_inv.id,
            product_id=line.product_id, description=line.description,
            quantity=line.quantity, unit_price=line.unit_price,
            discount=line.discount, tax_amount=line.tax_amount, total=line.total,
        ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="sales",
        entity_type="SalesInvoice", entity_id=new_inv.id,
        entity_name=inv_num, request=request,
    )

    return SalesInvoiceResponse(
        id=new_inv.id, invoice_number=new_inv.invoice_number,
        customer_id=new_inv.customer_id,
        customer_name=None, invoice_date=new_inv.invoice_date,
        due_date=new_inv.due_date, status=new_inv.status,
        subtotal=float(new_inv.subtotal), tax_amount=float(new_inv.tax_amount),
        discount=float(new_inv.discount), total=float(new_inv.total),
        amount_paid=float(new_inv.amount_paid), currency=new_inv.currency,
        notes=new_inv.notes, created_at=new_inv.created_at,
    )


@router.get("/sales-invoices/{invoice_id}", response_model=SalesInvoiceResponse)
async def get_sales_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    result = await db.execute(
        select(SalesInvoice).options(selectinload(SalesInvoice.customer))
        .filter(SalesInvoice.id == invoice_id, SalesInvoice.tenant_id == current_user["tenant_id"])
    )
    inv = result.scalar()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return SalesInvoiceResponse(
        id=inv.id, invoice_number=inv.invoice_number,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else None,
        invoice_date=inv.invoice_date, due_date=inv.due_date,
        status=inv.status, subtotal=float(inv.subtotal),
        tax_amount=float(inv.tax_amount), discount=float(inv.discount),
        total=float(inv.total), amount_paid=float(inv.amount_paid),
        currency=inv.currency, notes=inv.notes, created_at=inv.created_at,
    )


@router.post("/sales-invoices/{invoice_id}/send")
async def send_sales_invoice(
    invoice_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:update")

    result = await db.execute(
        select(SalesInvoice).filter(
            SalesInvoice.id == invoice_id,
            SalesInvoice.tenant_id == current_user["tenant_id"],
        )
    )
    inv = result.scalar()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be sent")

    inv.status = "sent"
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="sales",
        entity_type="SalesInvoice", entity_id=invoice_id,
        entity_name=inv.invoice_number, new_values="sent", request=request,
    )

    return {"message": "Invoice sent", "status": "sent"}


# ─── SUPPLIER INVOICES ────────────────────────────────────

@router.get("/supplier-invoices", response_model=SupplierInvoiceListResponse)
async def list_supplier_invoices(
    supplier_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    query = select(SupplierInvoice).options(selectinload(SupplierInvoice.supplier))
    query = query.filter(SupplierInvoice.tenant_id == current_user["tenant_id"])
    if supplier_id:
        query = query.filter(SupplierInvoice.supplier_id == supplier_id)
    if status:
        query = query.filter(SupplierInvoice.status == status)
    query = query.order_by(SupplierInvoice.created_at.desc())

    count_q = select(func.count(SupplierInvoice.id)).filter(
        SupplierInvoice.tenant_id == current_user["tenant_id"]
    )
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invoices = result.scalars().all()

    return SupplierInvoiceListResponse(
        invoices=[
            SupplierInvoiceResponse(
                id=inv.id, invoice_number=inv.invoice_number,
                supplier_id=inv.supplier_id,
                supplier_name=inv.supplier.name if inv.supplier else None,
                invoice_date=inv.invoice_date, due_date=inv.due_date,
                status=inv.status, subtotal=float(inv.subtotal),
                tax_amount=float(inv.tax_amount), total=float(inv.total),
                amount_paid=float(inv.amount_paid), currency=inv.currency,
                notes=inv.notes, created_at=inv.created_at,
            )
            for inv in invoices
        ],
        total=total,
    )


@router.post("/supplier-invoices", response_model=SupplierInvoiceResponse)
async def create_supplier_invoice(
    invoice: SupplierInvoiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:create")

    subtotal = sum(line.total for line in invoice.lines)

    new_inv = SupplierInvoice(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        invoice_number=invoice.invoice_number,
        supplier_id=invoice.supplier_id, purchase_order_id=invoice.purchase_order_id,
        invoice_date=invoice.invoice_date, due_date=invoice.due_date,
        status="draft", subtotal=subtotal, tax_amount=invoice.tax_amount,
        total=subtotal + invoice.tax_amount,
        amount_paid=Decimal("0"), currency="EGP", notes=invoice.notes,
        created_by=current_user["id"],
    )
    db.add(new_inv)
    await db.flush()

    for line in invoice.lines:
        db.add(SupplierInvoiceLine(
            id=str(uuid.uuid4()), invoice_id=new_inv.id,
            product_id=line.product_id, description=line.description,
            quantity=line.quantity, unit_price=line.unit_price,
            tax_amount=line.tax_amount, total=line.total,
        ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="sales",
        entity_type="SupplierInvoice", entity_id=new_inv.id,
        entity_name=invoice.invoice_number, request=request,
    )

    return SupplierInvoiceResponse(
        id=new_inv.id, invoice_number=new_inv.invoice_number,
        supplier_id=new_inv.supplier_id,
        supplier_name=None, invoice_date=new_inv.invoice_date,
        due_date=new_inv.due_date, status=new_inv.status,
        subtotal=float(new_inv.subtotal), tax_amount=float(new_inv.tax_amount),
        total=float(new_inv.total), amount_paid=float(new_inv.amount_paid),
        currency=new_inv.currency, notes=new_inv.notes, created_at=new_inv.created_at,
    )


@router.post("/supplier-invoices/{invoice_id}/approve")
async def approve_supplier_invoice(
    invoice_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:update")

    result = await db.execute(select(SupplierInvoice).filter(SupplierInvoice.id == invoice_id))
    inv = result.scalar()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be approved")

    inv.status = "approved"
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="sales",
        entity_type="SupplierInvoice", entity_id=invoice_id,
        entity_name=inv.invoice_number, new_values="approved", request=request,
    )

    return {"message": "Invoice approved", "status": "approved"}
