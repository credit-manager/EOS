from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, JSON, String, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import Uuid

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.workflow.events import DomainEvent


class OutboxBase(DeclarativeBase):
    pass


class OutboxEventModel(OutboxBase):
    __tablename__ = "eos_v2_outbox_events"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SqlAlchemyOutbox:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, event: DomainEvent) -> None:
        tenant_id = get_tenant_context().tenant_id
        if event.tenant_id != tenant_id:
            raise PermissionError("Event tenant does not match current tenant")
        self.session.add(OutboxEventModel(
            id=event.id,
            tenant_id=tenant_id,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
        ))

    def claim_unpublished(self, limit: int = 100) -> list[OutboxEventModel]:
        tenant_id = get_tenant_context().tenant_id
        return list(self.session.scalars(select(OutboxEventModel).where(
            OutboxEventModel.tenant_id == tenant_id,
            OutboxEventModel.published_at.is_(None),
        ).order_by(OutboxEventModel.occurred_at).limit(limit)))

    def mark_published(self, event_id: UUID) -> bool:
        tenant_id = get_tenant_context().tenant_id
        result = self.session.execute(update(OutboxEventModel).where(
            OutboxEventModel.id == event_id,
            OutboxEventModel.tenant_id == tenant_id,
            OutboxEventModel.published_at.is_(None),
        ).values(published_at=datetime.now(timezone.utc)))
        return result.rowcount == 1
