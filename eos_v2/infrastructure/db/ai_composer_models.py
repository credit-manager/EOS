from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class AIComposerBase(DeclarativeBase):
    pass


class ComposerProposalModel(AIComposerBase):
    __tablename__ = "eos_v2_ai_composer_proposals"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    actor_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    prompt: Mapped[str] = mapped_column(String(12000), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    changes: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
