from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class MetadataEntity(Base):
    __tablename__ = "metadata_entities"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version", name="uq_metadata_version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
