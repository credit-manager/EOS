from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from eos_v2.infrastructure.db.metadata_models import Base


class IndustryPackInstallationModel(Base):
    __tablename__ = "eos_v2_industry_pack_installations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pack_key", "pack_version", name="uq_v2_industry_pack_installation"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    pack_key: Mapped[str] = mapped_column(String(100), nullable=False)
    pack_version: Mapped[str] = mapped_column(String(50), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
