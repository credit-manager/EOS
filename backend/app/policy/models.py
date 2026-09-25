from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Policy(Base):
    """Policy Engine V2 - Core policy model"""
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_policy_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # WHEN/IF/THEN/ELSE structure
    when_clause: Mapped[dict] = mapped_column(JSON, nullable=False)
    if_clause: Mapped[dict] = mapped_column(JSON, nullable=False)
    then_actions: Mapped[dict] = mapped_column(JSON, nullable=False)
    else_actions: Mapped[dict | None] = mapped_column(JSON)

    # Metadata
    category: Mapped[str | None] = mapped_column(String(100))
    tags_json: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PolicyExecution(Base):
    """Policy Engine V2 - Execution log"""
    __tablename__ = "policy_executions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    policy_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    policy_code: Mapped[str] = mapped_column(String(100), nullable=False)

    # Execution context
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_resource_type: Mapped[str | None] = mapped_column(String(100))
    trigger_resource_id: Mapped[str | None] = mapped_column(String(100))

    # Result
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actions_executed: Mapped[dict] = mapped_column(JSON, nullable=False)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
