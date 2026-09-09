from __future__ import annotations

from uuid import uuid4

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.workflow.service import WorkflowEngine
from eos_v2.domain.workflow.entities import WorkflowAction, WorkflowDefinition, WorkflowRule
from eos_v2.domain.workflow.events import DomainEvent
from eos_v2.domain.workflow.rules import RuleOperator, evaluate_rule
from eos_v2.infrastructure.events.bus import InMemoryEventBus


class Repo:
    def __init__(self, workflows):
        self.workflows = workflows

    def list_for_event(self, event_type):
        return [item for item in self.workflows if item.trigger_event_type == event_type]


def test_rule_language_is_deterministic() -> None:
    assert evaluate_rule({"amount": 150}, "amount", RuleOperator.GTE, 100)
    assert evaluate_rule({"status": "paid"}, "status", RuleOperator.IN, ["paid", "settled"])
    assert not evaluate_rule({}, "amount", RuleOperator.GT, 100)


def test_workflow_emits_only_when_all_rules_match() -> None:
    tenant = uuid4()
    workflow = WorkflowDefinition(
        tenant_id=tenant,
        name="approve_order",
        trigger_event_type="sales.order_created",
        rules=(WorkflowRule("total", RuleOperator.GTE, 1000), WorkflowRule("status", RuleOperator.EQ, "pending")),
        actions=(WorkflowAction("sales.approval_required", {"order_id": "$order_id"}),),
    )
    engine = WorkflowEngine(Repo([workflow]))
    token = set_tenant_context(TenantContext(tenant))
    try:
        event = DomainEvent(tenant, "sales.order_created", uuid4(), {"order_id": "O-1", "total": 1500, "status": "pending"})
        emitted = engine.handle(event)
        assert len(emitted) == 1
        assert emitted[0].event_type == "sales.approval_required"
        assert emitted[0].payload["order_id"] == "O-1"
    finally:
        reset_tenant_context(token)


def test_event_bus_restores_context_and_is_tenant_scoped() -> None:
    tenant = uuid4()
    bus = InMemoryEventBus()
    seen = []
    bus.subscribe("sales.created", lambda event: seen.append(event.tenant_id))
    bus.publish(DomainEvent(tenant, "sales.created", uuid4(), {}))
    assert seen == [tenant]
