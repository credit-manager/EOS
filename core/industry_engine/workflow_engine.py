"""
EOS Industry Engine — Workflow Engine
Approval chains, state machines, escalation, notifications.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class StepType(str, Enum):
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    CONDITION = "condition"
    AUTO_ACTION = "auto_action"
    PARALLEL = "parallel"


class EscalationType(str, Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    REJECTION = "rejection"


@dataclass
class WorkflowStep:
    code: str
    name: str
    name_ar: str
    step_type: StepType
    assignee_role: str = ""       # Role required to approve
    assignee_user: str = ""       # Specific user
    assignee_field: str = ""      # Field containing assignee
    auto_action: str = ""         # Auto-action code
    timeout_hours: int = 0        # Escalation timeout
    escalation_type: EscalationType = EscalationType.NONE
    escalation_to: str = ""       # Escalation target
    conditions: List[Dict[str, Any]] = field(default_factory=list)  # When to skip/require
    parallel_steps: List[str] = field(default_factory=list)  # For parallel approval
    order: int = 0


@dataclass
class WorkflowDefinition:
    code: str
    name: str
    name_ar: str
    entity: str                    # Entity this workflow applies to
    module: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    auto_start: bool = False       # Auto-start on entity creation
    allow_cancel: bool = True
    allow_rework: bool = False     # Allow sending back for rework
    notification_template: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowInstance:
    id: str
    workflow_code: str
    entity_id: str
    entity_code: str
    tenant_id: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    current_step: str = ""
    initiated_by: str = ""
    initiated_at: Optional[str] = None
    completed_at: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)


class WorkflowEngine:
    """
    Manages workflow definitions and instances.
    Handles approval chains, state transitions, and escalation.
    """

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in platform workflows."""
        self.register(WorkflowDefinition(
            code="PURCHASE_APPROVAL", name="Purchase Approval", name_ar="الموافقة على الشراء",
            entity="purchase_order", module="procurement",
            description="Multi-level approval for purchase orders",
            steps=[
                WorkflowStep("STEP1", "Manager Approval", "موافقة المدير", StepType.APPROVAL,
                           assignee_role="manager", timeout_hours=24,
                           escalation_type=EscalationType.TIMEOUT, escalation_to="director", order=1),
                WorkflowStep("STEP2", "Finance Approval", "موافقة المالية", StepType.APPROVAL,
                           assignee_role="finance", timeout_hours=48,
                           conditions=[{"field": "total_amount", "operator": "gt", "value": 10000}], order=2),
                WorkflowStep("STEP3", "Director Approval", "موافقة المدير العام", StepType.APPROVAL,
                           assignee_role="director", timeout_hours=72,
                           conditions=[{"field": "total_amount", "operator": "gt", "value": 50000}], order=3),
            ],
            auto_start=True,
        ))

        self.register(WorkflowDefinition(
            code="EXPENSE_APPROVAL", name="Expense Approval", name_ar="الموافقة على المصروفات",
            entity="expense_claim", module="accounting",
            description="Expense claim approval workflow",
            steps=[
                WorkflowStep("STEP1", "Direct Manager", "المدير المباشر", StepType.APPROVAL,
                           assignee_role="manager", timeout_hours=24, order=1),
                WorkflowStep("STEP2", "Finance", "المحاسبة", StepType.APPROVAL,
                           assignee_role="finance", timeout_hours=48,
                           conditions=[{"field": "amount", "operator": "gt", "value": 5000}], order=2),
            ],
            auto_start=True,
        ))

        self.register(WorkflowDefinition(
            code="LEAVE_REQUEST", name="Leave Request", name_ar="طلب إجازة",
            entity="leave_request", module="hr",
            description="Employee leave request approval",
            steps=[
                WorkflowStep("STEP1", "Direct Manager", "المدير المباشر", StepType.APPROVAL,
                           assignee_role="manager", timeout_hours=48, order=1),
            ],
            auto_start=True,
        ))

        self.register(WorkflowDefinition(
            code="CONTRACT_APPROVAL", name="Contract Approval", name_ar="الموافقة على العقد",
            entity="contract", module="projects",
            description="Contract approval for construction projects",
            steps=[
                WorkflowStep("STEP1", "Project Manager", "مدير المشروع", StepType.APPROVAL,
                           assignee_role="project_manager", timeout_hours=48, order=1),
                WorkflowStep("STEP2", "Commercial Manager", "المدير التجاري", StepType.APPROVAL,
                           assignee_role="commercial_manager", timeout_hours=48, order=2),
                WorkflowStep("STEP3", "CEO Approval", "موافقة الرئيس", StepType.APPROVAL,
                           assignee_role="ceo", timeout_hours=72,
                           conditions=[{"field": "contract_value", "operator": "gt", "value": 1000000}], order=3),
            ],
            auto_start=True,
        ))

    def register(self, workflow: WorkflowDefinition):
        """Register a new workflow definition."""
        self._workflows[workflow.code] = workflow

    def get(self, code: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by code."""
        return self._workflows.get(code)

    def get_all(self) -> Dict[str, WorkflowDefinition]:
        """Get all registered workflows."""
        return dict(self._workflows)

    def get_by_entity(self, entity_code: str) -> List[WorkflowDefinition]:
        """Get workflows for an entity."""
        return [w for w in self._workflows.values() if w.entity == entity_code]

    def start_workflow(self, workflow_code: str, entity_id: str, entity_code: str,
                       tenant_id: str, initiated_by: str, entity_data: Dict[str, Any] = None) -> WorkflowInstance:
        """Start a new workflow instance."""
        workflow = self._workflows.get(workflow_code)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_code}' not found")

        # Find first applicable step
        first_step = self._find_next_step(workflow, None, entity_data or {})

        instance = WorkflowInstance(
            id=f"wf_{tenant_id[:8]}_{entity_id[:8]}",
            workflow_code=workflow_code,
            entity_id=entity_id,
            entity_code=entity_code,
            tenant_id=tenant_id,
            status=WorkflowStatus.PENDING if first_step else WorkflowStatus.APPROVED,
            current_step=first_step.code if first_step else "",
            initiated_by=initiated_by,
            history=[{
                "action": "started",
                "by": initiated_by,
                "step": first_step.code if first_step else "auto_approved",
            }],
        )

        self._instances[instance.id] = instance
        return instance

    def approve_step(self, instance_id: str, step_code: str, approved_by: str,
                     comments: str = "", entity_data: Dict[str, Any] = None) -> WorkflowInstance:
        """Approve a workflow step."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        workflow = self._workflows.get(instance.workflow_code)
        if not workflow:
            raise ValueError(f"Workflow '{instance.workflow_code}' not found")

        # Record the approval
        instance.history.append({
            "action": "approved",
            "step": step_code,
            "by": approved_by,
            "comments": comments,
        })

        # Find next step
        next_step = self._find_next_step(workflow, step_code, entity_data or {})

        if next_step:
            instance.current_step = next_step.code
            instance.status = WorkflowStatus.PENDING
        else:
            # Workflow complete
            instance.status = WorkflowStatus.APPROVED
            instance.current_step = ""
            instance.completed_at = "now"  # Will be set properly in real implementation

        self._instances[instance_id] = instance
        return instance

    def reject_step(self, instance_id: str, step_code: str, rejected_by: str,
                    comments: str = "") -> WorkflowInstance:
        """Reject a workflow step."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        workflow = self._workflows.get(instance.workflow_code)

        instance.history.append({
            "action": "rejected",
            "step": step_code,
            "by": rejected_by,
            "comments": comments,
        })

        # Check if rework is allowed
        if workflow and workflow.allow_rework:
            instance.status = WorkflowStatus.DRAFT
            instance.current_step = workflow.steps[0].code if workflow.steps else ""
        else:
            instance.status = WorkflowStatus.REJECTED
            instance.current_step = ""

        self._instances[instance_id] = instance
        return instance

    def cancel_workflow(self, instance_id: str, cancelled_by: str) -> WorkflowInstance:
        """Cancel a workflow."""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        instance.status = WorkflowStatus.CANCELLED
        instance.current_step = ""
        instance.history.append({
            "action": "cancelled",
            "by": cancelled_by,
        })

        self._instances[instance_id] = instance
        return instance

    def _find_next_step(self, workflow: WorkflowDefinition, current_step: str,
                        entity_data: Dict[str, Any]) -> Optional[WorkflowStep]:
        """Find the next applicable step after current."""
        sorted_steps = sorted(workflow.steps, key=lambda s: s.order)

        if not current_step:
            # Return first applicable step
            for step in sorted_steps:
                if self._step_applies(step, entity_data):
                    return step
            return None

        # Find current step index
        found_current = False
        for step in sorted_steps:
            if step.code == current_step:
                found_current = True
                continue
            if found_current and self._step_applies(step, entity_data):
                return step

        return None

    def _step_applies(self, step: WorkflowStep, entity_data: Dict[str, Any]) -> bool:
        """Check if a step applies based on conditions."""
        for condition in step.conditions:
            field_name = condition.get("field", "")
            operator = condition.get("operator", "eq")
            expected = condition.get("value")
            actual = entity_data.get(field_name)

            if operator == "gt" and float(actual or 0) <= float(expected):
                return False
            elif operator == "lt" and float(actual or 0) >= float(expected):
                return False
            elif operator == "eq" and actual != expected:
                return False
            elif operator == "gte" and float(actual or 0) < float(expected):
                return False

        return True

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get workflow instance."""
        return self._instances.get(instance_id)

    def get_pending_for_user(self, user_id: str, role: str = "") -> List[WorkflowInstance]:
        """Get pending workflows for a user."""
        pending = []
        for inst in self._instances.values():
            if inst.status == WorkflowStatus.PENDING:
                workflow = self._workflows.get(inst.workflow_code)
                if workflow:
                    for step in workflow.steps:
                        if step.code == inst.current_step:
                            if step.assignee_user == user_id or step.assignee_role == role:
                                pending.append(inst)
        return pending

    def get_workflow_history(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get approval history for a workflow instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return []
        return instance.history

    def export_workflows(self, module_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export workflow definitions for templates."""
        workflows = self._workflows.values()
        if module_code:
            workflows = [w for w in workflows if w.module == module_code]

        return [{
            "code": w.code,
            "name": w.name,
            "name_ar": w.name_ar,
            "entity": w.entity,
            "module": w.module,
            "steps": [{
                "code": s.code,
                "name": s.name,
                "name_ar": s.name_ar,
                "type": s.step_type.value,
                "assignee_role": s.assignee_role,
                "timeout_hours": s.timeout_hours,
                "order": s.order,
            } for s in w.steps],
        } for w in workflows]
