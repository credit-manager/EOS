"""
AI Governance Models - data models for AI policy enforcement, execution limits,
human escalation, and audit trail.

These models provide the foundation for:
- Policy evaluation before agent execution
- Execution limits (hourly caps, token budgets, time budgets)
- Human escalation for sensitive operations
- Full audit trail for all AI actions
"""

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PolicyAction(str, Enum):
    """Policy action types."""
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class PolicyEffect(str, Enum):
    """Policy effect on agent actions."""
    PERMIT = "permit"
    DENY = "deny"
    ESCALATE = "escalate"
    LOG_ONLY = "log_only"


class EscalationStatus(str, Enum):
    """Human escalation request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionLimitType(str, Enum):
    """Types of execution limits."""
    HOURLY_ACTIONS = "hourly_actions"
    DAILY_ACTIONS = "daily_actions"
    TOKEN_BUDGET = "token_budget"
    TIME_BUDGET = "time_budget"
    FINANCIAL_LIMIT = "financial_limit"


class AuditActionType(str, Enum):
    """AI audit action types."""
    AGENT_EXECUTED = "ai.agent.executed"
    ACTION_ALLOWED = "ai.action.allowed"
    ACTION_DENIED = "ai.action.denied"
    ACTION_ESCALATED = "ai.action.escalated"
    POLICY_EVALUATED = "ai.policy.evaluated"
    LIMIT_CHECKED = "ai.limit.checked"
    ESCALATION_CREATED = "ai.escalation.created"
    ESCALATION_RESOLVED = "ai.escalation.resolved"


# ---------------------------------------------------------------------------
# AIPolicy - defines what actions are allowed/denied/escalated
# ---------------------------------------------------------------------------

class AIPolicy(Base):
    """AI Policy model - defines rules for what agents can/cannot do.

    Each policy can target specific:
    - Agent types (e.g., finance, procurement, project)
    - Action types (e.g., create_po, approve_payment, send_notification)
    - Conditions (e.g., amount > threshold, recipient role)
    - Effect (permit, deny, escalate, log_only)
    """

    __tablename__ = "ai_policies"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agent_types: Mapped[list[str]] = mapped_column(Text, default="[]")  # JSON list
    action_patterns: Mapped[list[str]] = mapped_column(Text, default="[]")  # JSON list of patterns
    effect: Mapped[str] = mapped_column(String(20), nullable=False, default="permit")
    conditions: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)  # JSON
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[UUID | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "agent_types": self.agent_types,
            "action_patterns": self.action_patterns,
            "effect": self.effect,
            "conditions": self.conditions,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# AIAgentLimit - execution limits per agent
# ---------------------------------------------------------------------------

class AIAgentLimit(Base):
    """Execution limits for AI agents.

    Controls:
    - Maximum actions per time window
    - Token budget per time window
    - Time budget per time window
    - Financial limits (for agents that can affect financials)
    """

    __tablename__ = "ai_agent_limits"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    limit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    max_value: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=True)  # e.g., 3600 for hourly
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_code": self.agent_code,
            "limit_type": self.limit_type,
            "max_value": self.max_value,
            "window_seconds": self.window_seconds,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# AIEscalation - human approval requests
# ---------------------------------------------------------------------------

class AIEscalation(Base):
    """Human escalation request for sensitive AI actions.

    When an agent tries to perform a sensitive action (e.g., approve a payment
    over threshold, change supplier bank account), an escalation is created
    and the action is blocked until a human approves/rejects.
    """

    __tablename__ = "ai_escalations"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_data: Mapped[str | None] = mapped_column(Text)  # JSON snapshot of the action
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_by: Mapped[UUID | None] = mapped_column(String(36), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_by: Mapped[UUID | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(String(36), nullable=True)
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
            "status": self.status,
            "requested_by": str(self.requested_by) if self.requested_by else None,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "resolved_by": str(self.resolved_by) if self.resolved_by else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "approved_by": str(self.approved_by) if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
        }


# ---------------------------------------------------------------------------
# AIExecutionAudit - full audit trail for AI actions
# ---------------------------------------------------------------------------

class AIExecutionAudit(Base):
    """Complete audit trail for AI actions.

    Records every AI action with:
    - Who (agent) did what
    - What action was taken
    - Was it allowed/denied/escalated
    - Policy that applied
    - Result and metadata
    - Timestamp and trace
    """

    __tablename__ = "ai_execution_audit"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "agent" | "human" | "system"
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    effect: Mapped[str] = mapped_column(String(20), nullable=False)  # "permit" | "deny" | "escalate"
    policy_applied: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[str | None] = mapped_column(Text)  # JSON result of the action
    metadata: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)  # JSON
    execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "effect": self.effect,
            "policy_applied": self.policy_applied,
            "result": self.result,
            "metadata": self.metadata,
            "execution_id": self.execution_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

# (No direct relationships needed - all queries are by tenant_id + code)
