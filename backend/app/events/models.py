from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class SystemEvent(Base):
    """Fact table of the platform event bus.

    Append-only; consumers read via the events API. Payload is stored as
    JSON text so it works identically on SQLite and PostgreSQL.
    """

    __tablename__ = "system_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def payload(self) -> dict | None:
        if not self.payload_json:
            return None
        import json

        return json.loads(self.payload_json)


class PersistentSubscription(Base):
    """Database-backed event subscription that survives restarts."""

    __tablename__ = "event_persistent_subscriptions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_delivery_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventDeliveryAttempt(Base):
    """Track individual delivery attempts for webhook subscriptions."""

    __tablename__ = "event_delivery_attempts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("event_persistent_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("system_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, success, failed
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeadLetterEvent(Base):
    """Events that failed all delivery attempts and need manual intervention."""

    __tablename__ = "event_dead_letters"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("system_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("event_persistent_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, retried, resolved
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
