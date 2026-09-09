from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from .rules import RuleOperator


@dataclass(frozen=True, slots=True)
class WorkflowRule:
    field: str
    operator: RuleOperator
    expected: Any = None


@dataclass(frozen=True, slots=True)
class WorkflowAction:
    event_type: str
    payload_template: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    tenant_id: UUID
    name: str
    trigger_event_type: str
    rules: tuple[WorkflowRule, ...] = ()
    actions: tuple[WorkflowAction, ...] = ()
    id: UUID = field(default_factory=uuid4)
    active: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum() or self.name[0].isdigit():
            raise ValueError("Workflow name must be a valid identifier")
        if "." not in self.trigger_event_type:
            raise ValueError("Workflow trigger must be a namespaced event type")
        if any("." not in action.event_type for action in self.actions):
            raise ValueError("Workflow action events must be namespaced")
