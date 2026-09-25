from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from ..db import Base


class Product(Base):
    __tablename__ = "retail_products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(128), nullable=True)
    unit_price = Column(Integer, nullable=False, default=0)
    cost_price = Column(Integer, nullable=False, default=0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    min_stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class POSTransaction(Base):
    __tablename__ = "retail_pos_transactions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    transaction_number = Column(String(64), unique=True, nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    total_amount = Column(Integer, nullable=False, default=0)
    tax_amount = Column(Integer, nullable=False, default=0)
    payment_method = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class POSTransactionLine(Base):
    __tablename__ = "retail_pos_transaction_lines"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("retail_pos_transactions.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("retail_products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)


class InventoryCount(Base):
    __tablename__ = "retail_inventory_counts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    count_number = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="in_progress")
    counted_by = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class InventoryCountLine(Base):
    __tablename__ = "retail_inventory_count_lines"

    id = Column(Integer, primary_key=True, index=True)
    count_id = Column(Integer, ForeignKey("retail_inventory_counts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("retail_products.id"), nullable=False, index=True)
    expected_qty = Column(Integer, nullable=False, default=0)
    counted_qty = Column(Integer, nullable=False, default=0)
    variance = Column(Integer, nullable=False, default=0)


class LoyaltyMember(Base):
    __tablename__ = "retail_loyalty_members"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    member_number = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)
    points = Column(Integer, nullable=False, default=0)
    tier = Column(String(32), nullable=False, default="standard")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
