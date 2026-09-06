from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class RecordBase(DeclarativeBase):
    pass


class DynamicRecordModel(RecordBase):
    __tablename__ = "eos_v2_dynamic_records"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_eos_v2_record_tenant_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), index=True, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(), index=True, nullable=False)
    entity_version: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class DynamicRecordUniqueValueModel(RecordBase):
    """Transactional uniqueness registry for metadata-defined unique fields."""

    __tablename__ = "eos_v2_dynamic_record_unique_values"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "entity_id", "field_name", "value_key",
            name="uq_eos_v2_record_unique_value",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_key: Mapped[str] = mapped_column(String(2048), nullable=False)
    record_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
