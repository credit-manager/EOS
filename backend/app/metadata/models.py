from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class MetadataEntity(Base):
    __tablename__ = "metadata_entities"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version", name="uq_metadata_version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetadataDashboardKPI(Base):
    """Dashboard KPI definitions for Metadata Engine V2"""
    __tablename__ = "metadata_dashboard_kpis"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    kpi_type: Mapped[str] = mapped_column(String(50), nullable=False)
    formula_json: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_interval: Mapped[int] = mapped_column(Integer, default=3600)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetadataTemplate(Base):
    """Schema template for Metadata Engine V2"""
    __tablename__ = "metadata_templates"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_metadata_template_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    permissions_json: Mapped[str] = mapped_column(Text, nullable=False)
    groups_json: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    category: Mapped[str | None] = mapped_column(String(100))
    tags_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
