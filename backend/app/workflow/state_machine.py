"""Workflow State Machine — programmable business process automation."""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ApprovalTask, WorkflowDefinition, WorkflowInstance, WorkflowSLALog

logger = logging.getLogger("2to-eos.workflow.state_machine")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    code: str
    name: str
    type: str = "normal"  # "start", "normal", "end", "error"
    is_start: bool = False
    is_end: bool = False
    allowed_roles: list[str] = field(default_factory=list)
    on_enter: list[dict] = field(default_factory=list)
    on_exit: list[dict] = field(default_factory=list)
    timeout_hours: int | None = None
    timeout_action: str | None = None


@dataclass
class WorkflowTransition:
    code: str
    from_state: str
    to_state: str
    name: str
    actor_roles: list[str] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    require_approval: bool = False
    approvers: list[str] = field(default_factory=list)
    pre_actions: list[dict] = field(default_factory=list)
    post_actions: list[dict] = field(default_factory=list)
    compensation_state: str | None = None


@dataclass
class WorkflowTemplate:
    code: str
    name: str
    description: str = ""
    states: list[WorkflowState] = field(default_factory=list)
    transitions: list[WorkflowTransition] = field(default_factory=list)

    def get_state(self, code: str) -> WorkflowState | None:
        return next((s for s in self.states if s.code == code), None)

    def get_transition(self, code: str) -> WorkflowTransition | None:
        return next((t for t in self.transitions if t.code == code), None)

    def get_start_state(self) -> WorkflowState | None:
        return next((s for s in self.states if s.is_start), None)

    def get_transitions_from(self, state_code: str) -> list[WorkflowTransition]:
        return [t for t in self.transitions if t.from_state == state_code]


# ---------------------------------------------------------------------------
# Pre-built workflow templates
# ---------------------------------------------------------------------------

WORKFLOW_TEMPLATES: dict[str, WorkflowTemplate] = {
    "purchase_order": WorkflowTemplate(
        code="purchase_order",
        name="Purchase Order Approval",
        description="Multi-level purchase order approval with finance review",
        states=[
            WorkflowState(code="draft", name="Draft", type="start", is_start=True),
            WorkflowState(
                code="pending_manager",
                name="Pending Manager Approval",
                type="normal",
                timeout_hours=48,
                timeout_action="escalate",
            ),
            WorkflowState(
                code="pending_finance",
                name="Pending Finance Review",
                type="normal",
                timeout_hours=72,
                timeout_action="escalate",
            ),
            WorkflowState(code="approved", name="Approved", type="end", is_end=True),
            WorkflowState(code="rejected", name="Rejected", type="error", is_end=True),
        ],
        transitions=[
            WorkflowTransition(
                code="submit",
                from_state="draft",
                to_state="pending_manager",
                name="Submit for Approval",
                actor_roles=["user", "admin"],
            ),
            WorkflowTransition(
                code="manager_approve",
                from_state="pending_manager",
                to_state="pending_finance",
                name="Manager Approve",
                actor_roles=["manager", "admin"],
                require_approval=True,
                approvers=["finance", "admin"],
            ),
            WorkflowTransition(
                code="manager_reject",
                from_state="pending_manager",
                to_state="rejected",
                name="Manager Reject",
                actor_roles=["manager", "admin"],
            ),
            WorkflowTransition(
                code="finance_approve",
                from_state="pending_finance",
                to_state="approved",
                name="Finance Approve",
                actor_roles=["finance", "admin"],
                require_approval=True,
                approvers=["admin"],
            ),
            WorkflowTransition(
                code="finance_reject",
                from_state="pending_finance",
                to_state="rejected",
                name="Finance Reject",
                actor_roles=["finance", "admin"],
            ),
        ],
    ),
    "invoice_approval": WorkflowTemplate(
        code="invoice_approval",
        name="Invoice Approval",
        description="Invoice processing and approval workflow",
        states=[
            WorkflowState(code="draft", name="Draft", type="start", is_start=True),
            WorkflowState(
                code="pending_review",
                name="Pending Review",
                type="normal",
                timeout_hours=24,
                timeout_action="escalate",
            ),
            WorkflowState(
                code="pending_approval",
                name="Pending Approval",
                type="normal",
                timeout_hours=48,
                timeout_action="escalate",
            ),
            WorkflowState(code="approved", name="Approved", type="end", is_end=True),
            WorkflowState(code="rejected", name="Rejected", type="error", is_end=True),
            WorkflowState(code="paid", name="Paid", type="end", is_end=True),
        ],
        transitions=[
            WorkflowTransition(
                code="submit",
                from_state="draft",
                to_state="pending_review",
                name="Submit Invoice",
                actor_roles=["user", "admin"],
            ),
            WorkflowTransition(
                code="review_approve",
                from_state="pending_review",
                to_state="pending_approval",
                name="Review Approve",
                actor_roles=["manager", "admin"],
            ),
            WorkflowTransition(
                code="review_reject",
                from_state="pending_review",
                to_state="rejected",
                name="Review Reject",
                actor_roles=["manager", "admin"],
            ),
            WorkflowTransition(
                code="approve",
                from_state="pending_approval",
                to_state="approved",
                name="Approve Invoice",
                actor_roles=["finance", "admin"],
                require_approval=True,
                approvers=["admin"],
            ),
            WorkflowTransition(
                code="reject",
                from_state="pending_approval",
                to_state="rejected",
                name="Reject Invoice",
                actor_roles=["finance", "admin"],
            ),
            WorkflowTransition(
                code="mark_paid",
                from_state="approved",
                to_state="paid",
                name="Mark as Paid",
                actor_roles=["finance", "admin"],
            ),
        ],
    ),
    "contract_approval": WorkflowTemplate(
        code="contract_approval",
        name="Contract Approval",
        description="Contract review and approval with legal sign-off",
        states=[
            WorkflowState(code="draft", name="Draft", type="start", is_start=True),
            WorkflowState(
                code="pending_legal",
                name="Pending Legal Review",
                type="normal",
                timeout_hours=72,
                timeout_action="escalate",
            ),
            WorkflowState(
                code="pending_management",
                name="Pending Management Approval",
                type="normal",
                timeout_hours=48,
                timeout_action="escalate",
            ),
            WorkflowState(code="approved", name="Approved", type="end", is_end=True),
            WorkflowState(code="rejected", name="Rejected", type="error", is_end=True),
            WorkflowState(code="executed", name="Executed", type="end", is_end=True),
        ],
        transitions=[
            WorkflowTransition(
                code="submit",
                from_state="draft",
                to_state="pending_legal",
                name="Submit for Legal Review",
                actor_roles=["user", "admin"],
            ),
            WorkflowTransition(
                code="legal_approve",
                from_state="pending_legal",
                to_state="pending_management",
                name="Legal Approve",
                actor_roles=["legal", "admin"],
                require_approval=True,
                approvers=["management", "admin"],
            ),
            WorkflowTransition(
                code="legal_reject",
                from_state="pending_legal",
                to_state="rejected",
                name="Legal Reject",
                actor_roles=["legal", "admin"],
            ),
            WorkflowTransition(
                code="management_approve",
                from_state="pending_management",
                to_state="approved",
                name="Management Approve",
                actor_roles=["management", "admin"],
                require_approval=True,
                approvers=["admin"],
            ),
            WorkflowTransition(
                code="management_reject",
                from_state="pending_management",
                to_state="rejected",
                name="Management Reject",
                actor_roles=["management", "admin"],
            ),
            WorkflowTransition(
                code="execute",
                from_state="approved",
                to_state="executed",
                name="Execute Contract",
                actor_roles=["legal", "admin"],
            ),
        ],
    ),
    "expense_claim": WorkflowTemplate(
        code="expense_claim",
        name="Expense Claim",
        description="Employee expense claim and reimbursement workflow",
        states=[
            WorkflowState(code="draft", name="Draft", type="start", is_start=True),
            WorkflowState(
                code="pending_manager",
                name="Pending Manager Approval",
                type="normal",
                timeout_hours=24,
                timeout_action="escalate",
            ),
            WorkflowState(
                code="pending_finance",
                name="Pending Finance Processing",
                type="normal",
                timeout_hours=48,
                timeout_action="escalate",
            ),
            WorkflowState(code="approved", name="Approved", type="end", is_end=True),
            WorkflowState(code="rejected", name="Rejected", type="error", is_end=True),
            WorkflowState(code="reimbursed", name="Reimbursed", type="end", is_end=True),
        ],
        transitions=[
            WorkflowTransition(
                code="submit",
                from_state="draft",
                to_state="pending_manager",
                name="Submit Claim",
                actor_roles=["user", "admin"],
            ),
            WorkflowTransition(
                code="manager_approve",
                from_state="pending_manager",
                to_state="pending_finance",
                name="Manager Approve",
                actor_roles=["manager", "admin"],
                conditions=[{"field": "amount", "op": "<=", "value": 5000}],
            ),
            WorkflowTransition(
                code="manager_approve_large",
                from_state="pending_manager",
                to_state="pending_finance",
                name="Manager Approve (Large)",
                actor_roles=["manager", "admin"],
                conditions=[{"field": "amount", "op": ">", "value": 5000}],
                require_approval=True,
                approvers=["finance", "admin"],
            ),
            WorkflowTransition(
                code="manager_reject",
                from_state="pending_manager",
                to_state="rejected",
                name="Manager Reject",
                actor_roles=["manager", "admin"],
            ),
            WorkflowTransition(
                code="finance_approve",
                from_state="pending_finance",
                to_state="approved",
                name="Finance Approve",
                actor_roles=["finance", "admin"],
                require_approval=True,
                approvers=["admin"],
            ),
            WorkflowTransition(
                code="finance_reject",
                from_state="pending_finance",
                to_state="rejected",
                name="Finance Reject",
                actor_roles=["finance", "admin"],
            ),
            WorkflowTransition(
                code="reimburse",
                from_state="approved",
                to_state="reimbursed",
                name="Process Reimbursement",
                actor_roles=["finance", "admin"],
            ),
        ],
    ),
    "leave_request": WorkflowTemplate(
        code="leave_request",
        name="Leave Request",
        description="Employee leave/time-off request workflow",
        states=[
            WorkflowState(code="draft", name="Draft", type="start", is_start=True),
            WorkflowState(
                code="pending_approval",
                name="Pending Manager Approval",
                type="normal",
                timeout_hours=24,
                timeout_action="escalate",
            ),
            WorkflowState(code="approved", name="Approved", type="end", is_end=True),
            WorkflowState(code="rejected", name="Rejected", type="error", is_end=True),
        ],
        transitions=[
            WorkflowTransition(
                code="submit",
                from_state="draft",
                to_state="pending_approval",
                name="Submit Request",
                actor_roles=["user", "admin"],
            ),
            WorkflowTransition(
                code="approve",
                from_state="pending_approval",
                to_state="approved",
                name="Approve Leave",
                actor_roles=["manager", "admin"],
            ),
            WorkflowTransition(
                code="reject",
                from_state="pending_approval",
                to_state="rejected",
                name="Reject Leave",
                actor_roles=["manager", "admin"],
            ),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """Programmable workflow engine with conditions, timeouts, escalation, delegation, and compensation."""

    def __init__(self, db_session: Session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def _load_template(self, workflow_code: str) -> WorkflowTemplate:
        if workflow_code not in WORKFLOW_TEMPLATES:
            raise HTTPException(
                status_code=404,
                detail=f"workflow template not found: {workflow_code}",
            )
        return WORKFLOW_TEMPLATES[workflow_code]

    def _definition_to_template(self, definition: WorkflowDefinition) -> WorkflowTemplate:
        """Convert a stored WorkflowDefinition (JSON) into a WorkflowTemplate."""
        defn = definition.definition
        states = []
        for s in defn.get("states", []):
            if isinstance(s, str):
                states.append(WorkflowState(code=s, name=s, is_start=s == definition.initial_state))
            else:
                states.append(WorkflowState(**s))
        transitions = []
        for t in defn.get("transitions", []):
            transitions.append(
                WorkflowTransition(
                    code=t.get("action", t.get("code", "")),
                    from_state=t["from_state"],
                    to_state=t["to_state"],
                    name=t.get("action", t.get("code", "")),
                    actor_roles=t.get("roles", []),
                    conditions=[
                        {"field": c["field"], "op": c["op"], "value": c["value"]}
                        for c in t.get("conditions", [])
                    ] if t.get("conditions") else [],
                    require_approval=t.get("requires_approval", False),
                    pre_actions=t.get("pre_actions", []),
                    post_actions=t.get("actions", []),
                )
            )
        return WorkflowTemplate(
            code=definition.code,
            name=definition.name,
            states=states,
            transitions=transitions,
        )

    def _get_template(self, workflow_code: str, tenant_id: UUID | None = None) -> WorkflowTemplate:
        """Get template from built-in templates or from the database definition."""
        if workflow_code in WORKFLOW_TEMPLATES:
            return WORKFLOW_TEMPLATES[workflow_code]
        if tenant_id is not None:
            definition = self.db.scalar(
                select(WorkflowDefinition)
                .where(
                    WorkflowDefinition.tenant_id == tenant_id,
                    WorkflowDefinition.code == workflow_code,
                    WorkflowDefinition.is_active.is_(True),
                )
                .order_by(WorkflowDefinition.version.desc())
            )
            if definition is not None:
                return self._definition_to_template(definition)
        raise HTTPException(status_code=404, detail=f"workflow not found: {workflow_code}")

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    def _evaluate_conditions(
        self, conditions: list[dict], context: dict[str, Any]
    ) -> bool:
        """Evaluate transition conditions against a context dict.

        Conditions are dicts with: field, op, value.
        Ops: ==, !=, >, <, >=, <=, in, not_in, contains.
        """
        if not conditions:
            return True

        for cond in conditions:
            field_name = cond.get("field", "")
            op = cond.get("op", "==")
            expected = cond.get("value")
            actual = self._resolve_field(field_name, context)

            if op == "==":
                if actual != expected:
                    return False
            elif op == "!=":
                if actual == expected:
                    return False
            elif op == ">":
                if not (actual is not None and expected is not None and actual > expected):
                    return False
            elif op == "<":
                if not (actual is not None and expected is not None and actual < expected):
                    return False
            elif op == ">=":
                if not (actual is not None and expected is not None and actual >= expected):
                    return False
            elif op == "<=":
                if not (actual is not None and expected is not None and actual <= expected):
                    return False
            elif op == "in":
                if actual not in (expected if isinstance(expected, (list, tuple, set)) else [expected]):
                    return False
            elif op == "not_in":
                if actual in (expected if isinstance(expected, (list, tuple, set)) else [expected]):
                    return False
            elif op == "contains":
                if actual is None or expected not in actual:
                    return False
            else:
                logger.warning("Unknown condition operator: %s", op)
                return False

        return True

    def _resolve_field(self, field_name: str, context: dict[str, Any]) -> Any:
        """Resolve a dotted field name from context (e.g., 'payload.amount')."""
        parts = field_name.split(".")
        value: Any = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_actions(
        self,
        actions: list[dict],
        instance: WorkflowInstance,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a list of actions and return updated context.

        Action types:
          - set_context: set a value in the workflow context
          - log: log a message
          - notify: mark a notification to be sent
        """
        updated = deepcopy(context)
        for action in actions:
            action_type = action.get("type", "")
            if action_type == "set_context":
                key = action.get("key", "")
                value = action.get("value")
                updated.setdefault("data", {})[key] = value
            elif action_type == "log":
                msg = action.get("message", "")
                logger.info("Workflow %s: %s", instance.id, msg)
            elif action_type == "notify":
                updated.setdefault("notifications", []).append(
                    {
                        "recipient": action.get("recipient", ""),
                        "message": action.get("message", ""),
                        "at": datetime.now(UTC).isoformat(),
                    }
                )
            else:
                logger.warning("Unknown action type: %s", action_type)
        return updated

    # ------------------------------------------------------------------
    # Core engine methods
    # ------------------------------------------------------------------

    def start_workflow(
        self,
        workflow_code: str,
        entity_type: str,
        entity_id: str,
        started_by: str,
        tenant_id: UUID,
        context: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Start a new workflow instance."""
        template = self._get_template(workflow_code, tenant_id)
        start_state = template.get_start_state()
        if start_state is None:
            raise HTTPException(status_code=422, detail="workflow template has no start state")

        now = datetime.now(UTC)
        instance = WorkflowInstance(
            id=uuid4(),
            tenant_id=tenant_id,
            workflow_definition_id=uuid4(),  # placeholder; real binding done via template lookup
            reference_type=entity_type,
            reference_id=UUID(entity_id) if len(entity_id) == 36 else uuid4(),
            current_state=start_state.code,
            status="active",
            created_by=UUID(started_by) if len(started_by) == 36 else uuid4(),
            created_at=now,
            updated_at=now,
        )

        # Run on_enter actions
        ctx = {"data": context or {}, "workflow": {"entity_type": entity_type, "entity_id": entity_id}}
        if start_state.on_enter:
            ctx = self._execute_actions(start_state.on_enter, instance, ctx)

        # Set timeout deadline
        if start_state.timeout_hours is not None:
            instance.sla_deadline = now + timedelta(hours=start_state.timeout_hours)

        self.db.add(instance)
        self.db.flush()
        logger.info("Started workflow %s for %s/%s", instance.id, entity_type, entity_id)
        return instance

    def get_available_transitions(
        self, instance_id: str, user_role: str, tenant_id: UUID
    ) -> list[dict]:
        """Get transitions available to the current user from the current state."""
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.id == UUID(instance_id) if len(instance_id) == 36 else WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="workflow instance not found")
        if instance.status != "active":
            return []

        definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
        if definition is None:
            template = self._get_template(instance.reference_type, tenant_id)
        else:
            template = self._definition_to_template(definition)

        available = []
        for t in template.get_transitions_from(instance.current_state):
            if user_role in t.actor_roles or "admin" in t.actor_roles:
                ctx = {"workflow": {"current_state": instance.current_state}, "data": {}}
                conditions_met = self._evaluate_conditions(t.conditions, ctx)
                available.append(
                    {
                        "code": t.code,
                        "from_state": t.from_state,
                        "to_state": t.to_state,
                        "name": t.name,
                        "require_approval": t.require_approval,
                        "conditions_met": conditions_met,
                        "actor_roles": t.actor_roles,
                    }
                )
        return available

    def execute_transition(
        self,
        instance_id: str,
        transition_code: str,
        actor: str,
        comment: str = "",
        data: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
    ) -> WorkflowInstance:
        """Execute a transition. Validates conditions, permissions, and executes actions."""
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.id == UUID(instance_id) if len(instance_id) == 36 else WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="workflow instance not found")
        if instance.status != "active":
            raise HTTPException(status_code=409, detail="workflow instance is not active")

        definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
        if definition is None:
            template = self._get_template(instance.reference_type, tenant_id)
        else:
            template = self._definition_to_template(definition)

        transition = template.get_transition(transition_code)
        if transition is None:
            raise HTTPException(status_code=404, detail=f"transition not found: {transition_code}")

        # Validate from state
        if transition.from_state != instance.current_state:
            raise HTTPException(
                status_code=422,
                detail=f"transition '{transition_code}' cannot be applied from state '{instance.current_state}'",
            )

        # Evaluate conditions
        ctx = {"workflow": {"current_state": instance.current_state}, "data": data or {}}
        if not self._evaluate_conditions(transition.conditions, ctx):
            return {
                "status": "blocked",
                "detail": "transition conditions are not satisfied",
                "instance_id": str(instance.id),
                "current_state": instance.current_state,
                "attempted_transition": transition_code,
            }

        now = datetime.now(UTC)

        # Pre-actions
        if transition.pre_actions:
            ctx = self._execute_actions(transition.pre_actions, instance, ctx)

        # If requires approval, create approval task instead of transitioning
        if transition.require_approval:
            pending = self.db.scalar(
                select(ApprovalTask).where(
                    ApprovalTask.workflow_instance_id == instance.id,
                    ApprovalTask.status == "pending",
                )
            )
            if pending is not None:
                raise HTTPException(status_code=409, detail="workflow instance already has a pending approval")

            task = ApprovalTask(
                tenant_id=tenant_id or instance.tenant_id,
                workflow_instance_id=instance.id,
                action=transition_code,
                from_state=instance.current_state,
                to_state=transition.to_state,
                requested_by=UUID(actor) if len(actor) == 36 else uuid4(),
                status="pending",
                due_at=now + timedelta(hours=48),
                timeout_hours=48,
                escalation_role=transition.approvers[0] if transition.approvers else None,
            )
            self.db.add(task)
            self.db.flush()
            logger.info("Created approval task %s for workflow %s", task.id, instance.id)
            return instance

        # Execute direct transition
        # Run on_exit actions for current state
        current_state_obj = template.get_state(instance.current_state)
        if current_state_obj and current_state_obj.on_exit:
            ctx = self._execute_actions(current_state_obj.on_exit, instance, ctx)

        instance.current_state = transition.to_state
        instance.updated_at = now

        # Run on_enter actions for new state
        new_state_obj = template.get_state(transition.to_state)
        if new_state_obj and new_state_obj.on_enter:
            ctx = self._execute_actions(new_state_obj.on_enter, instance, ctx)

        # Set timeout for new state
        if new_state_obj and new_state_obj.timeout_hours is not None:
            instance.sla_deadline = now + timedelta(hours=new_state_obj.timeout_hours)
            instance.sla_status = "on_track"
        else:
            instance.sla_deadline = None

        # Post-actions
        if transition.post_actions:
            ctx = self._execute_actions(transition.post_actions, instance, ctx)

        # Check if terminal
        if new_state_obj and new_state_obj.is_end:
            instance.status = "completed"

        self.db.flush()
        logger.info("Executed transition %s on workflow %s -> %s", transition_code, instance.id, instance.current_state)
        return instance

    def cancel_workflow(self, instance_id: str, reason: str, tenant_id: UUID) -> WorkflowInstance:
        """Cancel a running workflow."""
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.id == UUID(instance_id) if len(instance_id) == 36 else WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="workflow instance not found")
        if instance.status != "active":
            raise HTTPException(status_code=409, detail="workflow instance is not active")

        instance.status = "cancelled"
        instance.updated_at = datetime.now(UTC)
        self.db.flush()
        logger.info("Cancelled workflow %s: %s", instance.id, reason)
        return instance

    def get_workflow_history(self, instance_id: str, tenant_id: UUID) -> list[dict]:
        """Get the full history of a workflow instance.

        Reconstructs history from approval tasks and SLA logs since the
        core instance table does not store an explicit history list.
        """
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.id == UUID(instance_id) if len(instance_id) == 36 else WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="workflow instance not found")

        history: list[dict] = []
        history.append(
            {
                "state": instance.current_state,
                "status": instance.status,
                "created_at": instance.created_at.isoformat() if instance.created_at else None,
                "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
                "created_by": str(instance.created_by),
            }
        )

        # Add approval tasks as history entries
        tasks = self.db.scalars(
            select(ApprovalTask)
            .where(ApprovalTask.workflow_instance_id == instance.id)
            .order_by(ApprovalTask.requested_at.asc())
        ).all()
        for task in tasks:
            history.append(
                {
                    "type": "approval_task",
                    "action": task.action,
                    "from_state": task.from_state,
                    "to_state": task.to_state,
                    "status": task.status,
                    "requested_by": str(task.requested_by),
                    "decided_by": str(task.decided_by) if task.decided_by else None,
                    "requested_at": task.requested_at.isoformat() if task.requested_at else None,
                    "decided_at": task.decided_at.isoformat() if task.decided_at else None,
                }
            )

        # Add SLA events
        sla_logs = self.db.scalars(
            select(WorkflowSLALog)
            .where(WorkflowSLALog.workflow_instance_id == instance.id)
            .order_by(WorkflowSLALog.created_at.asc())
        ).all()
        for log in sla_logs:
            history.append(
                {
                    "type": "sla_event",
                    "event_type": log.event_type,
                    "message": log.message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )

        return history

    def check_timeouts(self, tenant_id: UUID | None = None) -> list[dict]:
        """Check for workflows that have timed out and execute timeout actions.

        Returns a list of processed timeout events.
        """
        now = datetime.now(UTC)
        query = select(WorkflowInstance).where(
            WorkflowInstance.status == "active",
            WorkflowInstance.sla_deadline.is_not(None),
            WorkflowInstance.sla_deadline < now,
        )
        if tenant_id is not None:
            query = query.where(WorkflowInstance.tenant_id == tenant_id)

        expired = self.db.scalars(query).all()
        results: list[dict] = []

        for instance in expired:
            definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
            if definition is None:
                continue

            template = self._definition_to_template(definition)
            current_state = template.get_state(instance.current_state)
            if current_state is None:
                continue

            event: dict[str, Any] = {
                "instance_id": str(instance.id),
                "current_state": instance.current_state,
                "timeout_action": current_state.timeout_action,
                "sla_deadline": instance.sla_deadline.isoformat() if instance.sla_deadline else None,
            }

            if current_state.timeout_action == "escalate":
                instance.sla_status = "violated"
                instance.escalated_at = now
                self.db.add(
                    WorkflowSLALog(
                        tenant_id=instance.tenant_id,
                        workflow_instance_id=instance.id,
                        event_type="escalated",
                        sla_hours=current_state.timeout_hours,
                        actual_hours=int((now - (instance.created_at or now)).total_seconds() // 3600),
                        message=f"State '{instance.current_state}' timed out after {current_state.timeout_hours}h",
                    )
                )
                event["action_taken"] = "escalated"

            elif current_state.timeout_action == "auto_transition":
                # Find the first available transition from the current state
                available = template.get_transitions_from(instance.current_state)
                if available:
                    auto_t = available[0]
                    instance.current_state = auto_t.to_state
                    instance.updated_at = now
                    new_state = template.get_state(auto_t.to_state)
                    if new_state and new_state.is_end:
                        instance.status = "completed"
                    if new_state and new_state.timeout_hours:
                        instance.sla_deadline = now + timedelta(hours=new_state.timeout_hours)
                        instance.sla_status = "on_track"
                    event["action_taken"] = f"auto_transition:{auto_t.code}"
                else:
                    event["action_taken"] = "no_transition_available"

            elif current_state.timeout_action == "cancel":
                instance.status = "cancelled"
                instance.updated_at = now
                event["action_taken"] = "cancelled"

            else:
                event["action_taken"] = "no_action"

            results.append(event)

        self.db.flush()
        logger.info("Processed %d timed-out workflow instances", len(results))
        return results

    def get_pending_approvals(
        self, user_role: str, tenant_id: UUID
    ) -> list[dict]:
        """Get all workflows waiting for approval by role."""
        tasks = self.db.scalars(
            select(ApprovalTask)
            .where(
                ApprovalTask.tenant_id == tenant_id,
                ApprovalTask.status == "pending",
            )
            .order_by(ApprovalTask.requested_at.asc())
        ).all()

        results: list[dict] = []
        for task in tasks:
            instance = self.db.get(WorkflowInstance, task.workflow_instance_id)
            if instance is None:
                continue
            definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
            if definition is None:
                continue

            template = self._definition_to_template(definition)
            transition = template.get_transition(task.action)
            if transition is None:
                continue

            if user_role in transition.approvers or user_role == "admin":
                results.append(
                    {
                        "task_id": str(task.id),
                        "instance_id": str(instance.id),
                        "workflow_code": definition.code,
                        "workflow_name": definition.name,
                        "entity_type": instance.reference_type,
                        "entity_id": str(instance.reference_id),
                        "current_state": instance.current_state,
                        "transition_code": task.action,
                        "transition_name": transition.name,
                        "from_state": task.from_state,
                        "to_state": task.to_state,
                        "requested_by": str(task.requested_by),
                        "requested_at": task.requested_at.isoformat() if task.requested_at else None,
                        "due_at": task.due_at.isoformat() if task.due_at else None,
                    }
                )

        return results

    def get_workflow_status(self, entity_type: str, entity_id: str, tenant_id: UUID) -> dict | None:
        """Get the current workflow status for an entity."""
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.reference_type == entity_type,
                WorkflowInstance.reference_id == UUID(entity_id) if len(entity_id) == 36 else WorkflowInstance.reference_id == entity_id,
                WorkflowInstance.tenant_id == tenant_id,
            ).order_by(WorkflowInstance.created_at.desc())
        )
        if instance is None:
            return None

        definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
        template = self._definition_to_template(definition) if definition else self._get_template(entity_type, tenant_id)
        current_state = template.get_state(instance.current_state)

        return {
            "instance_id": str(instance.id),
            "workflow_code": definition.code if definition else template.code,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "current_state": instance.current_state,
            "current_state_name": current_state.name if current_state else instance.current_state,
            "status": instance.status,
            "sla_status": instance.sla_status,
            "sla_deadline": instance.sla_deadline.isoformat() if instance.sla_deadline else None,
            "escalated_at": instance.escalated_at.isoformat() if instance.escalated_at else None,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        }

    def compensate_transition(
        self,
        instance_id: str,
        transition_code: str,
        actor: str,
        reason: str = "",
        tenant_id: UUID | None = None,
    ) -> WorkflowInstance:
        """Compensate (undo) a transition by moving to the compensation state."""
        instance = self.db.scalar(
            select(WorkflowInstance).where(
                WorkflowInstance.id == UUID(instance_id) if len(instance_id) == 36 else WorkflowInstance.id == instance_id,
                WorkflowInstance.tenant_id == tenant_id,
            )
        )
        if instance is None:
            raise HTTPException(status_code=404, detail="workflow instance not found")

        definition = self.db.get(WorkflowDefinition, instance.workflow_definition_id)
        if definition is None:
            template = self._get_template(instance.reference_type, tenant_id)
        else:
            template = self._definition_to_template(definition)

        transition = template.get_transition(transition_code)
        if transition is None:
            raise HTTPException(status_code=404, detail=f"transition not found: {transition_code}")

        if transition.compensation_state is None:
            raise HTTPException(status_code=422, detail="transition has no compensation state defined")

        now = datetime.now(UTC)
        instance.current_state = transition.compensation_state
        instance.updated_at = now

        new_state = template.get_state(transition.compensation_state)
        if new_state and new_state.is_end:
            instance.status = "completed"

        self.db.flush()
        logger.info(
            "Compensated transition %s on workflow %s -> %s (reason: %s)",
            transition_code, instance.id, transition.compensation_state, reason,
        )
        return instance

    def delegate_approval(
        self,
        task_id: str,
        delegate_to: str,
        delegated_by: str,
        tenant_id: UUID,
    ) -> dict:
        """Delegate an approval task to another user/role."""
        task = self.db.scalar(
            select(ApprovalTask).where(
                ApprovalTask.id == UUID(task_id) if len(task_id) == 36 else ApprovalTask.id == task_id,
                ApprovalTask.tenant_id == tenant_id,
                ApprovalTask.status == "pending",
            )
        )
        if task is None:
            raise HTTPException(status_code=404, detail="approval task not found or not pending")

        task.escalation_role = delegate_to
        task.notes = f"Delegated by {delegated_by} to {delegate_to}"
        self.db.flush()

        logger.info("Delegated approval task %s from %s to %s", task_id, delegated_by, delegate_to)
        return {
            "task_id": str(task.id),
            "delegated_to": delegate_to,
            "delegated_by": delegated_by,
        }

    def list_templates(self) -> list[dict]:
        """List all available workflow templates."""
        return [
            {
                "code": t.code,
                "name": t.name,
                "description": t.description,
                "states": [
                    {"code": s.code, "name": s.name, "type": s.type, "is_start": s.is_start, "is_end": s.is_end}
                    for s in t.states
                ],
                "transitions": [
                    {
                        "code": tr.code,
                        "from_state": tr.from_state,
                        "to_state": tr.to_state,
                        "name": tr.name,
                        "actor_roles": tr.actor_roles,
                        "require_approval": tr.require_approval,
                    }
                    for tr in t.transitions
                ],
            }
            for t in WORKFLOW_TEMPLATES.values()
        ]
