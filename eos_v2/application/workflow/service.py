from __future__ import annotations

from typing import Protocol

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.workflow.entities import WorkflowDefinition
from eos_v2.domain.workflow.events import DomainEvent
from eos_v2.domain.workflow.rules import evaluate_rule


class WorkflowRepository(Protocol):
    def list_for_event(self, event_type: str) -> list[WorkflowDefinition]: ...


class WorkflowEngine:
    """Deterministic workflow engine; actions emit events and never execute user code."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def handle(self, event: DomainEvent) -> list[DomainEvent]:
        context = get_tenant_context()
        if context.tenant_id != event.tenant_id:
            raise PermissionError("Workflow event tenant does not match current tenant")
        emitted: list[DomainEvent] = []
        for workflow in self.repository.list_for_event(event.event_type):
            if not workflow.active or workflow.tenant_id != event.tenant_id:
                continue
            if not all(evaluate_rule(event.payload, rule.field, rule.operator, rule.expected) for rule in workflow.rules):
                continue
            for action in workflow.actions:
                payload = {
                    key: (event.payload[value[1:]] if isinstance(value, str) and value.startswith("$") and value[1:] in event.payload else value)
                    for key, value in action.payload_template.items()
                }
                emitted.append(DomainEvent(
                    tenant_id=event.tenant_id,
                    event_type=action.event_type,
                    aggregate_id=event.aggregate_id,
                    payload=payload,
                ))
        return emitted
