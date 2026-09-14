from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base

__all__ = ["Rule", "RuleExecution"]


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    conditions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions_json: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RuleExecution(Base):
    __tablename__ = "rule_executions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_event_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("system_events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())