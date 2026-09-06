from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from uuid import UUID

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.domain.workflow.events import DomainEvent

EventHandler = Callable[[DomainEvent], None]


class InMemoryEventBus:
    """Deterministic test/event-kernel implementation; production delivery uses the outbox."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers.get(event.event_type, ())):
            token = set_tenant_context(TenantContext(event.tenant_id))
            try:
                handler(event)
            finally:
                reset_tenant_context(token)
