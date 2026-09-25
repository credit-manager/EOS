from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from ..db import Base


class BOM(Base):
    __tablename__ = "mfg_boms"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BOMItem(Base):
    __tablename__ = "mfg_bom_items"

    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("mfg_boms.id"), nullable=False, index=True)
    material_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Integer, nullable=False, default=0)


class WorkOrder(Base):
    __tablename__ = "mfg_work_orders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    order_number = Column(String(64), unique=True, nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey("mfg_boms.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="planned")
    planned_start = Column(DateTime, nullable=True)
    planned_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProductionTracking(Base):
    __tablename__ = "mfg_production_tracking"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("mfg_work_orders.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    good_quantity = Column(Integer, nullable=False, default=0)
    scrap_quantity = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)


class QualityInspection(Base):
    __tablename__ = "mfg_quality_inspections"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("mfg_work_orders.id"), nullable=False, index=True)
    inspector = Column(String(128), nullable=False)
    result = Column(String(16), nullable=False, default="pending")
    defect_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
