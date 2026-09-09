"""
EOS System — Sales & CRM Module Router (with RBAC + Audit)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.sales import Customer, Lead, Opportunity, Quote, QuoteItem

router = APIRouter()


# Schemas
class CustomerCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    type: str = "individual"
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    name_ar: Optional[str]
    type: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    tax_id: Optional[str]
    is_active: bool
    created_at: datetime


class CustomerListResponse(BaseModel):
    customers: List[CustomerResponse]
    total: int


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    first_name_ar: Optional[str] = None
    last_name_ar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class LeadResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    first_name_ar: Optional[str]
    last_name_ar: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    source: Optional[str]
    status: str
    notes: Optional[str]
    assigned_to: Optional[str]
    created_at: datetime


class LeadListResponse(BaseModel):
    leads: List[LeadResponse]
    total: int


class QuoteCreate(BaseModel):
    customer_id: str
    valid_until: Optional[date] = None
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    id: str
    customer_id: str
    number: str
    status: str
    total: float
    currency: str
    valid_until: Optional[date]
    notes: Optional[str]
    created_at: datetime


class QuoteListResponse(BaseModel):
    quotes: List[QuoteResponse]
    total: int


# ─── CUSTOMERS ────────────────────────────────────────────

@router.get("/customers", response_model=CustomerListResponse)
async def list_customers(
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    query = select(Customer)
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%"))
            | (Customer.name_ar.ilike(f"%{search}%"))
            | (Customer.email.ilike(f"%{search}%"))
        )

    count_q = select(func.count(Customer.id))
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return CustomerListResponse(
        customers=[
            CustomerResponse(
                id=c.id, name=c.name, name_ar=c.name_ar, type=c.type,
                email=c.email, phone=c.phone, address=c.address,
                tax_id=c.tax_id, is_active=c.is_active,
                created_at=c.created_at,
            )
            for c in customers
        ],
        total=total,
    )


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer: CustomerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:create")

    new_cust = Customer(
        id=str(uuid.uuid4()), name=customer.name, name_ar=customer.name_ar,
        type=customer.type, email=customer.email, phone=customer.phone,
        address=customer.address, tax_id=customer.tax_id,
        is_active=True,
    )
    db.add(new_cust)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="sales",
        entity_type="Customer", entity_id=new_cust.id,
        entity_name=new_cust.name, request=request,
    )

    return CustomerResponse(
        id=new_cust.id, name=new_cust.name, name_ar=new_cust.name_ar,
        type=new_cust.type, email=new_cust.email, phone=new_cust.phone,
        address=new_cust.address, tax_id=new_cust.tax_id,
        is_active=new_cust.is_active, created_at=new_cust.created_at,
    )


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:delete" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:delete")

    result = await db.execute(select(Customer).filter(Customer.id == customer_id))
    cust = result.scalar()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    old_name = cust.name
    await db.delete(cust)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="delete", module="sales",
        entity_type="Customer", entity_id=customer_id,
        entity_name=old_name, request=request,
    )

    return {"message": "Customer deleted"}


# ─── LEADS ────────────────────────────────────────────────

@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    query = select(Lead)
    if status:
        query = query.filter(Lead.status == status)
    if search:
        query = query.filter(
            (Lead.first_name.ilike(f"%{search}%"))
            | (Lead.last_name.ilike(f"%{search}%"))
        )

    count_q = select(func.count(Lead.id))
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    leads = result.scalars().all()

    return LeadListResponse(
        leads=[
            LeadResponse(
                id=l.id, first_name=l.first_name, last_name=l.last_name,
                first_name_ar=l.first_name_ar, last_name_ar=l.last_name_ar,
                email=l.email, phone=l.phone, source=l.source, status=l.status,
                notes=l.notes, assigned_to=l.assigned_to, created_at=l.created_at,
            )
            for l in leads
        ],
        total=total,
    )


@router.post("/leads", response_model=LeadResponse)
async def create_lead(
    lead: LeadCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:create")

    new_lead = Lead(
        id=str(uuid.uuid4()), first_name=lead.first_name, last_name=lead.last_name,
        first_name_ar=lead.first_name_ar, last_name_ar=lead.last_name_ar,
        email=lead.email, phone=lead.phone, source=lead.source,
        notes=lead.notes, assigned_to=lead.assigned_to, status="new",
    )
    db.add(new_lead)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="sales",
        entity_type="Lead", entity_id=new_lead.id,
        entity_name=f"{new_lead.first_name} {new_lead.last_name}",
        request=request,
    )

    return LeadResponse(
        id=new_lead.id, first_name=new_lead.first_name, last_name=new_lead.last_name,
        first_name_ar=new_lead.first_name_ar, last_name_ar=new_lead.last_name_ar,
        email=new_lead.email, phone=new_lead.phone, source=new_lead.source,
        status=new_lead.status, notes=new_lead.notes,
        assigned_to=new_lead.assigned_to, created_at=new_lead.created_at,
    )


# ─── QUOTES ───────────────────────────────────────────────

@router.get("/quotes", response_model=QuoteListResponse)
async def list_quotes(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:read")

    query = select(Quote)
    if status:
        query = query.filter(Quote.status == status)

    count_q = select(func.count(Quote.id))
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    quotes = result.scalars().all()

    return QuoteListResponse(
        quotes=[
            QuoteResponse(
                id=q.id, customer_id=q.customer_id, number=q.number,
                status=q.status, total=float(q.total), currency=q.currency,
                valid_until=q.valid_until, notes=q.notes, created_at=q.created_at,
            )
            for q in quotes
        ],
        total=total,
    )


@router.post("/quotes", response_model=QuoteResponse)
async def create_quote(
    quote: QuoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "sales:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires sales:create")

    quote_num = f"Q-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    new_quote = Quote(
        id=str(uuid.uuid4()), customer_id=quote.customer_id,
        number=quote_num, status="draft", total=Decimal("0.00"),
        currency="EGP", valid_until=quote.valid_until, notes=quote.notes,
    )
    db.add(new_quote)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="sales",
        entity_type="Quote", entity_id=new_quote.id,
        entity_name=quote_num, request=request,
    )

    return QuoteResponse(
        id=new_quote.id, customer_id=new_quote.customer_id,
        number=new_quote.number, status=new_quote.status,
        total=float(new_quote.total), currency=new_quote.currency,
        valid_until=new_quote.valid_until, notes=new_quote.notes,
        created_at=new_quote.created_at,
    )
