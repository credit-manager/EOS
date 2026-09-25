"""
Test the AI Governance Service pre_execution_check flow.

Verifies that:
- Policy evaluation correctly matches agent types and actions
- DENY policies raise PolicyViolationError
- ESCALATE policies create a pending escalation and return requires_approval=True
- PERMIT policies pass through with allowed=True
- Conditions (amount_gte) are evaluated correctly
- Multiple policies are sorted by priority
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import pytest

# ---------------------------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from backend.app.db import Base
from backend.app.ai.governance.service import AIGovernanceService
from backend.app.ai.governance.models import (
    AIPolicy,
    AIAgentLimit,
    AIEscalation,
    AIExecutionAudit,
    LimitType,
    PolicyEffect,
)
from backend.app.ai.governance.policies import PolicyViolationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db() -> Session:
    """Fresh in-memory SQLite session per test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


# Ensure all transitive FK dependencies are imported
import backend.app.events.models  # noqa: F401 — registers system_events table


@pytest.fixture()
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def governance(db: Session, tenant_id: uuid.UUID) -> AIGovernanceService:
    return AIGovernanceService(db, tenant_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_policy(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
    agent_types: list[str],
    action_patterns: list[str],
    effect: str = "permit",
    priority: int = 100,
    conditions: dict | None = None,
    is_active: bool = True,
) -> AIPolicy:
    row = AIPolicy(
        tenant_id=tenant_id,
        code=code,
        name=name,
        agent_types=json.dumps(agent_types),
        action_patterns=json.dumps(action_patterns),
        effect=PolicyEffect(effect),
        priority=priority,
        conditions=json.dumps(conditions) if conditions else None,
        is_active=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_limit(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    agent_code: str,
    limit_type: str = "hourly_actions",
    max_value: int = 10,
    window_seconds: int = 3600,
    is_active: bool = True,
) -> AIAgentLimit:
    row = AIAgentLimit(
        tenant_id=tenant_id,
        agent_code=agent_code,
        limit_type=LimitType(limit_type),
        max_value=max_value,
        window_seconds=window_seconds,
        is_active=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_audit(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    agent_id: str,
    action: str = "create_payment",
) -> AIExecutionAudit:
    row = AIExecutionAudit(
        tenant_id=tenant_id,
        actor_type="agent",
        actor_id=agent_id,
        action=action,
        resource_type="ai_agent",
        resource_id=None,
        effect="permit",
        result="ok",
        audit_metadata=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_escalation(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    agent_code: str,
    action_type: str = "create_payment",
    reason: str = "test",
    status: str = "pending",
) -> AIEscalation:
    row = AIEscalation(
        tenant_id=tenant_id,
        agent_code=agent_code,
        action_type=action_type,
        reason=reason,
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ===========================================================================
# 1. Policy evaluation — matching logic
# ===========================================================================

class TestPolicyMatching:
    """Verify that _policy_matches (via evaluate_policies) works as expected."""

    def test_no_policies_returns_empty(self, db: Session, tenant_id: uuid.UUID):
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies("finance", "finance", "create_payment")
        assert evals == []

    def test_agent_type_must_match(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_finance_only",
            name="Finance agents only",
            agent_types=["finance"],
            action_patterns=["*"],
        )
        svc = AIGovernanceService(db, tenant_id)
        # Matching agent type -> policy applies
        evals = svc.evaluate_policies("finance", "finance", "create_payment")
        assert len(evals) == 1
        assert evals[0]["policy_code"] == "p_finance_only"
        # Non-matching agent type -> no policy
        evals = svc.evaluate_policies("general", "procurement", "create_payment")
        assert evals == []

    def test_action_pattern_substring_match(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_create_actions",
            name="Create actions",
            agent_types=["*"],
            action_patterns=["create_"],
        )
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies("general", "finance", "create_payment")
        assert len(evals) == 1
        evals = svc.evaluate_policies("general", "finance", "read_data")
        assert evals == []

    def test_action_pattern_wildcard_match(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_approve_star",
            name="Approve anything",
            agent_types=["*"],
            action_patterns=["approve_*"],
        )
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies("general", "finance", "approve_invoice")
        assert len(evals) == 1
        assert evals[0]["policy_code"] == "p_approve_star"

    def test_star_agent_and_star_action_matches_everything(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_catchall",
            name="Catch-all",
            agent_types=["*"],
            action_patterns=["*"],
        )
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies("any_agent", "any_action", "anything")
        assert len(evals) == 1
        assert evals[0]["policy_code"] == "p_catchall"

    def test_conditions_amount_gte_blocks_below_threshold(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_high_value",
            name="High value escalation",
            agent_types=["finance"],
            action_patterns=["create_payment"],
            effect="escalate",
            conditions={"amount_gte": 100000},
        )
        svc = AIGovernanceService(db, tenant_id)
        # Below threshold -> policy does NOT match
        evals = svc.evaluate_policies(
            "finance", "finance", "create_payment",
            input_data={"amount": 50000},
        )
        matching = [e for e in evals if e["policy_code"] == "p_high_value"]
        assert matching == []
        # Above threshold -> policy matches
        evals = svc.evaluate_policies(
            "finance", "finance", "create_payment",
            input_data={"amount": 150000},
        )
        matching = [e for e in evals if e["policy_code"] == "p_high_value"]
        assert len(matching) == 1

    def test_conditions_recipient_role_must_match(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_director_only",
            name="Director recipient",
            agent_types=["*"],
            action_patterns=["send_payment"],
            effect="escalate",
            conditions={"recipient_role": "director"},
        )
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies(
            "general", "finance", "send_payment",
            input_data={"recipient_role": "manager"},
        )
        matching = [e for e in evals if e["policy_code"] == "p_director_only"]
        assert matching == []
        evals = svc.evaluate_policies(
            "general", "finance", "send_payment",
            input_data={"recipient_role": "director"},
        )
        matching = [e for e in evals if e["policy_code"] == "p_director_only"]
        assert len(matching) == 1


# ===========================================================================
# 2. Policy effects — DENY / ESCALATE / PERMIT
# ===========================================================================

class TestPolicyEffects:
    """Verify DENY raises, ESCALATE creates escalation + returns requires_approval,
    and PERMIT passes through."""

    def test_deny_policy_raises_violation(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_no_payments",
            name="No payments allowed",
            agent_types=["finance"],
            action_patterns=["create_payment"],
            effect="deny",
            priority=10,
        )
        svc = AIGovernanceService(db, tenant_id)
        with pytest.raises(PolicyViolationError, match="denies action"):
            svc.pre_execution_check("finance", "finance", "create_payment")

    def test_escalate_policy_creates_pending_escalation(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_approve_large",
            name="Approve large payments",
            agent_types=["finance"],
            action_patterns=["create_payment"],
            effect="escalate",
            conditions={"amount_gte": 100000},
            priority=20,
        )
        svc = AIGovernanceService(db, tenant_id)
        result = svc.pre_execution_check(
            "finance", "finance", "create_payment",
            input_data={"amount": 150000},
        )
        assert result.allowed is False
        assert result.requires_approval is True
        assert result.policy_applied == "p_approve_large"
        # Escalation row must exist in DB
        pending = (
            db.query(AIEscalation)
            .filter(AIEscalation.tenant_id == tenant_id, AIEscalation.status == "pending")
            .order_by(AIEscalation.requested_at.desc())
            .first()
        )
        assert pending is not None
        assert pending.action_type == "create_payment"

    def test_permit_policy_passes_through(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_allow_small_payments",
            name="Allow small payments",
            agent_types=["finance"],
            action_patterns=["create_payment"],
            effect="permit",
            conditions={"amount_gte": 0},
            priority=5,
        )
        svc = AIGovernanceService(db, tenant_id)
        result = svc.pre_execution_check(
            "finance", "finance", "create_payment",
            input_data={"amount": 1000},
        )
        assert result.allowed is True
        assert result.policy_applied == "p_allow_small_payments"


# ===========================================================================
# 3. Priority ordering
# ===========================================================================

class TestPriorityOrdering:
    """When multiple policies match, the one with the lowest priority number wins
    for the effect decision in pre_execution_check."""

    def test_higher_priority_deny_wins_over_lower_priority_permit(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_permit_everything",
            name="Permit everything",
            agent_types=["*"],
            action_patterns=["*"],
            effect="permit",
            priority=200,
        )
        _make_policy(
            db, tenant_id,
            code="p_deny_payments",
            name="Deny payments",
            agent_types=["finance"],
            action_patterns=["create_payment"],
            effect="deny",
            priority=10,
        )
        svc = AIGovernanceService(db, tenant_id)
        with pytest.raises(PolicyViolationError):
            svc.pre_execution_check("finance", "finance", "create_payment")

    def test_escalation_policy_evaluations_are_sorted(self, db: Session, tenant_id: uuid.UUID):
        _make_policy(
            db, tenant_id,
            code="p_low_priority",
            name="Low priority escalation",
            agent_types=["*"],
            action_patterns=["*"],
            effect="permit",
            priority=200,
        )
        _make_policy(
            db, tenant_id,
            code="p_high_priority",
            name="High priority escalation",
            agent_types=["*"],
            action_patterns=["*"],
            effect="escalate",
            priority=5,
        )
        svc = AIGovernanceService(db, tenant_id)
        evals = svc.evaluate_policies("general", "general", "any_action")
        assert len(evals) == 2
        assert evals[0]["priority"] < evals[1]["priority"]


# ===========================================================================
# 4. Execution limits
# ===========================================================================

class TestExecutionLimits:
    def test_below_limit_passes(self, db: Session, tenant_id: uuid.UUID):
        _make_limit(db, tenant_id, agent_code="agent_one", max_value=10, window_seconds=3600)
        svc = AIGovernanceService(db, tenant_id)
        result = svc.check_limits("agent_one", "create_payment")
        assert result.allowed is True

    def test_at_limit_is_allowed(self, db: Session, tenant_id: uuid.UUID):
        _make_limit(db, tenant_id, agent_code="agent_two", max_value=1, window_seconds=3600)
        _make_audit(db, tenant_id, agent_id="agent_two", action="create_payment")
        svc = AIGovernanceService(db, tenant_id)
        result = svc.check_limits("agent_two", "create_payment")
        assert result.allowed is True

    def test_over_limit_blocks(self, db: Session, tenant_id: uuid.UUID):
        _make_limit(db, tenant_id, agent_code="agent_three", max_value=1, window_seconds=3600)
        for _ in range(2):
            _make_audit(db, tenant_id, agent_id="agent_three", action="create_payment")
        svc = AIGovernanceService(db, tenant_id)
        result = svc.check_limits("agent_three", "create_payment")
        assert result.allowed is False
        assert result.limit_exceeded is True


# ===========================================================================
# 5. Post-execution audit
# ===========================================================================

class TestPostExecutionAudit:
    def test_audit_row_is_created(self, db: Session, tenant_id: uuid.UUID):
        svc = AIGovernanceService(db, tenant_id)
        svc.post_execution_log(
            agent_code="agent_x",
            agent_type="finance",
            action="create_payment",
            result={"status": "ok"},
            execution_time_ms=150,
        )
        audit = (
            db.query(AIExecutionAudit)
            .filter(AIExecutionAudit.tenant_id == tenant_id, AIExecutionAudit.actor_id == "agent_x")
            .first()
        )
        assert audit is not None
        assert audit.action == "create_payment"
        assert audit.effect == "permit"
        assert json.loads(audit.audit_metadata) == {
            "agent_type": "finance",
            "execution_time_ms": 150,
            "status": "completed",
            "error": None,
        }


# ===========================================================================
# 6. Escalation management
# ===========================================================================

class TestEscalationManagement:
    def test_get_pending_escalations_returns_only_pending(self, db: Session, tenant_id: uuid.UUID):
        for status in ("pending", "approved", "rejected"):
            _make_escalation(db, tenant_id, agent_code="agent_a", reason="test", status=status)
        db.commit()
        svc = AIGovernanceService(db, tenant_id)
        pending = svc.get_pending_escalations()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_resolve_escalation_approves(self, db: Session, tenant_id: uuid.UUID):
        esc = _make_escalation(db, tenant_id, agent_code="agent_a", reason="test")
        resolved_by = uuid.uuid4()
        svc = AIGovernanceService(db, tenant_id)
        resolved = svc.resolve_escalation(esc.id, approved=True, resolved_by=resolved_by)
        assert resolved is not None
        assert resolved.status == "approved"
        assert resolved.approved_by == resolved_by
        assert resolved.approved_at is not None

    def test_resolve_escalation_rejects(self, db: Session, tenant_id: uuid.UUID):
        esc = _make_escalation(db, tenant_id, agent_code="agent_a", reason="test")
        svc = AIGovernanceService(db, tenant_id)
        resolved = svc.resolve_escalation(esc.id, approved=False, resolved_by=uuid.uuid4())
        assert resolved.status == "rejected"
        assert resolved.rejection_reason == "Rejected by human review"
