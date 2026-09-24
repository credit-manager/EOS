from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .models import (
    Product, POSTransaction, POSTransactionLine,
    InventoryCount, InventoryCountLine, LoyaltyMember,
)
from .schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    POSTransactionCreate, POSTransactionResponse,
    POSTransactionLineCreate, POSTransactionLineResponse,
    InventoryCountCreate, InventoryCountResponse,
    InventoryCountLineCreate, InventoryCountLineResponse,
    LoyaltyMemberCreate, LoyaltyMemberResponse, LoyaltyPointsAdd,
)

router = APIRouter(prefix="/api/v1/retail", tags=["retail"])


# ── Products ──

@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    payload: ProductCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = Product(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(Product)
        .filter(Product.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(Product).filter(
        Product.id == product_id, Product.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Product not found")
    return obj


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(Product).filter(
        Product.id == product_id, Product.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Product not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(Product).filter(
        Product.id == product_id, Product.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Product not found")
    db.delete(obj)
    db.commit()


# ── POS Transactions ──

@router.post("/transactions", response_model=POSTransactionResponse, status_code=201)
def create_transaction(
    payload: POSTransactionCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = POSTransaction(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/transactions", response_model=list[POSTransactionResponse])
def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(POSTransaction)
        .filter(POSTransaction.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/transactions/{transaction_id}", response_model=POSTransactionResponse)
def get_transaction(
    transaction_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(POSTransaction).filter(
        POSTransaction.id == transaction_id,
        POSTransaction.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(404, "Transaction not found")
    return obj


@router.post(
    "/transactions/{transaction_id}/lines",
    response_model=POSTransactionLineResponse,
    status_code=201,
)
def add_transaction_line(
    transaction_id: int,
    payload: POSTransactionLineCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    txn = db.query(POSTransaction).filter(
        POSTransaction.id == transaction_id,
        POSTransaction.tenant_id == tenant_id,
    ).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    line = POSTransactionLine(transaction_id=transaction_id, **payload.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


# ── Inventory Counts ──

@router.post("/inventory-counts", response_model=InventoryCountResponse, status_code=201)
def create_inventory_count(
    payload: InventoryCountCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = InventoryCount(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/inventory-counts", response_model=list[InventoryCountResponse])
def list_inventory_counts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(InventoryCount)
        .filter(InventoryCount.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post(
    "/inventory-counts/{count_id}/lines",
    response_model=InventoryCountLineResponse,
    status_code=201,
)
def add_inventory_count_line(
    count_id: int,
    payload: InventoryCountLineCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    ic = db.query(InventoryCount).filter(
        InventoryCount.id == count_id, InventoryCount.tenant_id == tenant_id
    ).first()
    if not ic:
        raise HTTPException(404, "Inventory count not found")
    line = InventoryCountLine(count_id=count_id, **payload.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.post("/inventory-counts/{count_id}/complete", response_model=InventoryCountResponse)
def complete_inventory_count(
    count_id: int,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(InventoryCount).filter(
        InventoryCount.id == count_id, InventoryCount.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Inventory count not found")
    obj.status = "completed"
    obj.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# ── Loyalty Members ──

@router.post("/loyalty-members", response_model=LoyaltyMemberResponse, status_code=201)
def create_loyalty_member(
    payload: LoyaltyMemberCreate,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = LoyaltyMember(**payload.model_dump(), tenant_id=tenant_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/loyalty-members", response_model=list[LoyaltyMemberResponse])
def list_loyalty_members(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(LoyaltyMember)
        .filter(LoyaltyMember.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/loyalty-members/{member_id}/points", response_model=LoyaltyMemberResponse)
def add_loyalty_points(
    member_id: int,
    payload: LoyaltyPointsAdd,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    obj = db.query(LoyaltyMember).filter(
        LoyaltyMember.id == member_id, LoyaltyMember.tenant_id == tenant_id
    ).first()
    if not obj:
        raise HTTPException(404, "Loyalty member not found")
    obj.points += payload.points
    db.commit()
    db.refresh(obj)
    return obj
