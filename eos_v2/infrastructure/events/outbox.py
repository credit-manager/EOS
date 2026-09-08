from __future__

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, select, update
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
    claim_token: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_attempts: Mapped[int] = mapped_column(nullable=False, default=0)


class SqlAlchemyOutbox:
    CLAIM_LEASE = timedelta(minutes=5)

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
        """Claim a leased batch; expired claims become eligible for retry.

        Delivery is at-least-once. The returned claim_token must be supplied to
        mark_published after the external publish succeeds. Consumers must
        deduplicate using the immutable event id.
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("Outbox claim limit must be between 1 and 1000")
        tenant_id = get_tenant_context().tenant_id
        now = datetime.now(timezone.utc)
        cutoff = now - self.CLAIM_LEASE
        statement = (
            select(OutboxEventModel)
            .where(
                OutboxEventModel.tenant_id == tenant_id,
                OutboxEventModel.published_at.is_(None),
                (OutboxEventModel.claimed_at.is_(None) | (OutboxEventModel.claimed_at < cutoff)),
            )
            .order_by(OutboxEventModel.occurred_at, OutboxEventModel.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list(self.session.scalars(statement))
        for event in events:
            event.claim_token = uuid4()
            event.claimed_at = now
            event.delivery_attempts += 1
        self.session.flush()
        return events

    def mark_published(self, event_id: UUID, claim_token: UUID) -> bool:
        """Mark an event published only while this worker still owns its lease."""
        if claim_token is None:
            raise ValueError("claim_token is required to mark an outbox event published")
        tenant_id = get_tenant_context().tenant_id
        now = datetime.now(timezone.utc)
        cutoff = now - self.CLAIM_LEASE
        result = self.session.execute(
            update(OutboxEventModel)
            .where(
                OutboxEventModel.id == event_id,
                OutboxEventModel.tenant_id == tenant_id,
                OutboxEventModel.published_at.is_(None),
                OutboxEventModel.claim_token == claim_token,
                OutboxEventModel.claimed_at.is_not(None),
                OutboxEventModel.claimed_at >= cutoff,
            )
            .values(
                published_at=now,
                claim_token=None,
                claimed_at=None,
            )
        )
        return result.rowcount == 1
