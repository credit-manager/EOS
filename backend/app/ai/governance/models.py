"""
AI Governance Models - data models for policy enforcement, execution limits,
human escalation, and full audit trail.

Enables the AI workforce to operate under strict governance:
- Every action is evaluated against active policies (permit/deny/escalate)
- Execution limits prevent runaway automation (hourly/daily caps, token/time budgets)
- Sensitive actions require human approval before execution
- Every AI action is recorded in an immutable audit trail
"""

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base
from sqlalchemy import UUID as SA_UUID


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PolicyEffect(str, Enum):
    PERMIT = "permit"
    DENY = "deny"
    ESCALATE = "escalate"


class EscalationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LimitType(str, Enum):
    HOURLY_ACTIONS = "hourly_actions"
    DAILY_ACTIONS = "daily_actions"
    TOKEN_BUDGET = "token_budget"
    TIME_BUDGET = "time_budget"


# ---------------------------------------------------------------------------
# AIPolicy
# ---------------------------------------------------------------------------

class AIPolicy(Base):
    """Policy rule: which agent types can/cannot perform which actions.

    Example:
        agent_types = ["finance"]
        action_patterns = ["create_payment", "post_journal"]
        effect = "escalate"
        conditions = {"amount_gte": 100000}
    """

    __tablename__ = "ai_policies"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(SA_UUID, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agent_types: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON list, e.g. '["finance", "procurement"]'
    action_patterns: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON list, e.g. '["create_payment", "approve_*"]'
    effect: Mapped[PolicyEffect] = mapped_column(
        SAEnum(PolicyEffect, name="policy_effect", create_type=False),
        nullable=False,
        default=PolicyEffect.PERMIT,
    )
    conditions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON conditions, e.g. '{"amount_gte": 100000}'
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=func.cast(True, Boolean)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "agent_types": self.agent_types,
            "action_patterns": self.action_patterns,
            "effect": self.effect.value,
            "conditions": self.conditions,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# AIAgentLimit
# ---------------------------------------------------------------------------

class AIAgentLimit(Base):
    """Execution limits per agent (hourly/daily caps, token budgets, time budgets)."""

    __tablename__ = "ai_agent_limits"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(SA_UUID, nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    limit_type: Mapped[LimitType] = mapped_column(
        SAEnum(LimitType, name="ai_limit_type", create_type=False),
        nullable=False,
    )
    max_value: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=func.cast(True, Boolean)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_code": self.agent_code,
            "limit_type": self.limit_type.value,
            "max_value": self.max_value,
            "window_seconds": self.window_seconds,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# AIEscalation
# ---------------------------------------------------------------------------

class AIEscalation(Base):
    """Human approval request for a sensitive AI action."""

    __tablename__ = "ai_escalations"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(SA_UUID, nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_data: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EscalationStatus] = mapped_column(
        SAEnum(EscalationStatus, name="escalation_status", create_type=False),
        nullable=False,
        default=EscalationStatus.PENDING,
    )
    requested_by: Mapped[UUID | None] = mapped_column(SA_UUID, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_by: Mapped[UUID | None] = mapped_column(SA_UUID, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(SA_UUID, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_code": self.agent_code,
            "action_type": self.action_type,
            "action_data": self.action_data,
            "reason": self.reason,
            "status": self.status.value,
            "requested_by": str(self.requested_by) if self.requested_by else None,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "resolved_by": str(self.resolved_by) if self.resolved_by else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "approved_by": str(self.approved_by) if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
        }


# ---------------------------------------------------------------------------
# AIExecutionAudit
# ---------------------------------------------------------------------------

class AIExecutionAudit(Base):
    """Full audit trail for every AI action."""

    __tablename__ = "ai_execution_audit"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(SA_UUID, nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(SA_UUID, nullable=True)
    effect: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "permit" | "deny" | "escalate"
    policy_applied: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    result: Mapped[str | None] = mapped_column(Text)
    audit_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "effect": self.effect,
            "policy_applied": self.policy_applied,
            "result": self.result,
            "metadata": self.audit_metadata,
            "execution_id": self.execution_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
