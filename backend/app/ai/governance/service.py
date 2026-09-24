"""
AI Governance Service - enforces policy checks, execution limits, and
human approval before and after agent execution.

Every agent execution flows through:
    pre_execution_check  ->  policy evaluation + limits + escalation check
    execute_agent        ->  actual tool execution
    post_execution_log   ->  audit trail recording
"""

import json
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import (
    AIPolicy,
    AIAgentLimit,
    AIEscalation,
    AIExecutionAudit,
)
from .policies import PolicyViolationError


class GovernanceResult:
    """Result of a pre-execution governance check."""

    def __init__(
        self,
        allowed: bool,
        action: str = "read_data",
        policy_applied: str | None = None,
        requires_approval: bool = False,
        escalation_reason: str | None = None,
        limit_exceeded: bool = False,
        limit_remaining: int | None = None,
    ):
        self.allowed = allowed
        self.action = action
        self.policy_applied = policy_applied
        self.requires_approval = requires_approval
        self.escalation_reason = escalation_reason
        self.limit_exceeded = limit_exceeded
        self.limit_remaining = limit_remaining

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "policy_applied": self.policy_applied,
            "requires_approval": self.requires_approval,
            "escalation_reason": self.escalation_reason,
            "limit_exceeded": self.limit_exceeded,
            "limit_remaining": self.limit_remaining,
        }


class AIGovernanceService:
    """Full governance layer for AI agent execution."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Policy evaluation
    # ------------------------------------------------------------------

    def evaluate_policies(
        self,
        agent_code: str,
        agent_type: str,
        action: str,
        input_data: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Evaluate all active policies against the proposed action.

        Returns list of policy evaluations (one per matching policy).
        """
        rows = self.db.scalars(
            select(AIPolicy).where(
                AIPolicy.tenant_id == self.tenant_id,
                AIPolicy.is_active.is_(True),
            )
        ).all()

        evaluations = []
        for policy in rows:
            if not self._policy_matches(policy, agent_type, action, input_data):
                continue
            effect = policy.effect
            evaluations.append(
                {
                    "policy_code": policy.code,
                    "policy_name": policy.name,
                    "effect": effect,
                    "priority": policy.priority,
                }
            )
        # Sort by priority (lower number = higher priority)
        evaluations.sort(key=lambda e: e["priority"])
        return evaluations

    def _policy_matches(
        self,
        policy: AIPolicy,
        agent_type: str,
        action: str,
        input_data: dict[str, Any] | None,
    ) -> bool:
        """Check if a policy applies to the given (agent_type, action, data)."""
        import json

        # agent_types match (with wildcard support)
        try:
            policy_agent_types = json.loads(policy.agent_types) if policy.agent_types else []
        except (json.JSONDecodeError, TypeError):
            policy_agent_types = []
        if policy_agent_types and "*" not in policy_agent_types and agent_type not in policy_agent_types:
            return False

        # action_patterns match (substring or wildcard)
        try:
            patterns = json.loads(policy.action_patterns) if policy.action_patterns else []
        except (json.JSONDecodeError, TypeError):
            patterns = []
        if patterns and "*" not in patterns:
            matched = any(
                p.replace("*", "") in action or action.startswith(p.rstrip("*"))
                for p in patterns
            )
            if not matched:
                return False

        # conditions match (basic numeric thresholds)
        if policy.conditions:
            try:
                conds = json.loads(policy.conditions) if policy.conditions else {}
            except (json.JSONDecodeError, TypeError):
                conds = {}
            if conds:
                # e.g. {"amount_gte": 100000, "recipient_role": "director"}
                for key, expected in conds.items():
                    if key.startswith("amount"):
                        actual = self._extract_amount(input_data, key)
                        if actual is not None:
                            if key == "amount_gt" and not (actual > expected):
                                return False
                            if key == "amount_gte" and not (actual >= expected):
                                return False
                            if key == "amount_lt" and not (actual < expected):
                                return False
                            if key == "amount_lte" and not (actual <= expected):
                                return False
                    elif key == "recipient_role":
                        actual = self._extract_string(input_data, "recipient_role")
                        if actual is not None and actual != expected:
                            return False
        return True

    @staticmethod
    def _extract_amount(data: dict | None, key: str) -> float | None:
        """Extract numeric amount from nested input data."""
        if not data:
            return None
        # Try keys like "amount", "value", "total", "sum"
        for candidate in ("amount", "value", "total", "sum", "balance"):
            if candidate in data and isinstance(data[candidate], (int, float)):
                return float(data[candidate])
        # Try nested "data.amount" patterns
        if "data" in data and isinstance(data["data"], dict):
            return AIGovernanceService._extract_amount(data["data"], key)
        return None

    @staticmethod
    def _extract_string(data: dict | None, key: str) -> str | None:
        """Extract a string field from input data."""
        if not data:
            return None
        if key in data and isinstance(data[key], str):
            return data[key]
        if "data" in data and isinstance(data["data"], dict):
            return AIGovernanceService._extract_string(data["data"], key)
        return None

    # ------------------------------------------------------------------
    # Execution limits
    # ------------------------------------------------------------------

    def check_limits(
        self,
        agent_code: str,
        action: str,
    ) -> GovernanceResult:
        """Check if the agent has exceeded any execution limits.

        Returns a GovernanceResult with limit_exceeded flag.
        """
        now = datetime.now(UTC)
        rows = self.db.scalars(
            select(AIAgentLimit).where(
                AIAgentLimit.tenant_id == self.tenant_id,
                AIAgentLimit.agent_code == agent_code,
                AIAgentLimit.is_active.is_(True),
            )
        ).all()

        for limit in rows:
            window_start = now.timestamp() - (limit.window_seconds or 3600)
            recent = self.db.scalar(
                select(func.count())
                .select_from(AIExecutionAudit)
                .where(
                    AIExecutionAudit.tenant_id == self.tenant_id,
                    AIExecutionAudit.actor_id == agent_code,
                    AIExecutionAudit.created_at
                    > datetime.fromtimestamp(window_start, UTC),
                )
            ) or 0
            if recent > limit.max_value:
                return GovernanceResult(
                    allowed=False,
                    action=action,
                    limit_exceeded=True,
                    limit_remaining=0,
                    policy_applied=f"limit:{limit.limit_type}",
                )
        return GovernanceResult(allowed=True, action=action)

    # ------------------------------------------------------------------
    # Escalation check
    # ------------------------------------------------------------------

    def check_escalation_required(
        self,
        agent_code: str,
        action: str,
        input_data: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        """Check if action requires human approval before execution."""
        # Check policies requiring escalation
        evaluations = self.evaluate_policies(agent_code, "general", action, input_data)
        for ev in evaluations:
            if ev["effect"] == "escalate":
                reason = (
                    f"Action '{action}' requires human approval "
                    f"per policy '{ev['policy_name']}'"
                )
                escalation = AIEscalation(
                    tenant_id=self.tenant_id,
                    agent_code=agent_code,
                    action_type=action,
                    action_data=str(input_data) if input_data else None,
                    reason=reason,
                    status="pending",
                )
                self.db.add(escalation)
                self.db.commit()
                return GovernanceResult(
                    allowed=False,
                    action=action,
                    requires_approval=True,
                    escalation_reason=reason,
                    policy_applied=ev["policy_code"],
                )
        return GovernanceResult(allowed=True, action=action)

    # ------------------------------------------------------------------
    # Combined pre-execution check
    # ------------------------------------------------------------------

    def pre_execution_check(
        self,
        agent_code: str,
        agent_type: str,
        action: str,
        input_data: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        """Run all governance checks before agent execution.

        Order:
        1. Policy evaluation (deny/permit/escalate)
        2. Execution limits
        3. Escalation required
        """
        # Step 1: Policy evaluation
        evaluations = self.evaluate_policies(agent_code, agent_type, action, input_data)

        # Check for deny
        for ev in evaluations:
            if ev["effect"] == "deny":
                raise PolicyViolationError(
                    f"Policy '{ev['policy_name']}' denies action '{action}'"
                )

        # Check for escalate
        for ev in evaluations:
            if ev["effect"] == "escalate":
                reason = (
                    f"Action '{action}' requires human approval "
                    f"per policy '{ev['policy_name']}'"
                )
                escalation = AIEscalation(
                    tenant_id=self.tenant_id,
                    agent_code=agent_code,
                    action_type=action,
                    action_data=str(input_data) if input_data else None,
                    reason=reason,
                    status="pending",
                )
                self.db.add(escalation)
                self.db.commit()
                return GovernanceResult(
                    allowed=False,
                    action=action,
                    requires_approval=True,
                    escalation_reason=reason,
                    policy_applied=ev["policy_code"],
                )

        # Step 2: Check limits
        limit_result = self.check_limits(agent_code, action)
        if not limit_result.allowed:
            return limit_result

        # Step 3: Check escalation (custom logic beyond policies)
        escalation_result = self.check_escalation_required(agent_code, action, input_data)
        if not escalation_result.allowed:
            return escalation_result

        # All checks passed
        policy_applied = evaluations[0]["policy_code"] if evaluations else None
        return GovernanceResult(
            allowed=True,
            action=action,
            policy_applied=policy_applied,
        )

    # ------------------------------------------------------------------
    # Post-execution audit
    # ------------------------------------------------------------------

    def post_execution_log(
        self,
        agent_code: str,
        agent_type: str,
        action: str,
        result: dict[str, Any] | None,
        execution_time_ms: int | None = None,
        status: str = "completed",
        error: str | None = None,
    ) -> None:
        """Record post-execution audit entry."""
        audit = AIExecutionAudit(
            tenant_id=self.tenant_id,
            actor_type="agent",
            actor_id=agent_code,
            action=action,
            resource_type="ai_agent",
            resource_id=None,
            effect="permit",
            result=str(result) if result else None,
            audit_metadata=json.dumps({
                "agent_type": agent_type,
                "execution_time_ms": execution_time_ms,
                "status": status,
                "error": error,
            }),
        )
        self.db.add(audit)
        self.db.commit()

    # ------------------------------------------------------------------
    # Escalation management
    # ------------------------------------------------------------------

    def get_pending_escalations(self, limit: int = 50) -> list[AIEscalation]:
        """Get all pending human approvals."""
        return (
            self.db.query(AIEscalation)
            .filter(
                AIEscalation.tenant_id == self.tenant_id,
                AIEscalation.status == "pending",
            )
            .order_by(AIEscalation.requested_at.desc())
            .limit(limit)
            .all()
        )

    def resolve_escalation(
        self,
        escalation_id: UUID,
        approved: bool,
        resolved_by: UUID | None = None,
    ) -> AIEscalation | None:
        """Approve or reject a pending escalation."""
        esc = self.db.query(AIEscalation).filter(
            AIEscalation.id == escalation_id,
            AIEscalation.tenant_id == self.tenant_id,
        ).first()
        if not esc:
            return None
        if esc.status != "pending":
            return esc
        esc.status = "approved" if approved else "rejected"
        esc.resolved_by = resolved_by
        esc.resolved_at = datetime.now(UTC)
        if approved:
            esc.approved_by = resolved_by
            esc.approved_at = datetime.now(UTC)
        else:
            esc.rejection_reason = "Rejected by human review"
        self.db.commit()
        return esc
