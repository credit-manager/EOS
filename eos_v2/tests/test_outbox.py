from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.domain.workflow.events import DomainEvent
from eos_v2.infrastructure.events.outbox import OutboxBase, SqlAlchemyOutbox


def test_outbox_is_tenant_scoped_and_claims_pending_events() -> None:
    engine = create_engine("sqlite:///:memory:")
    OutboxBase.metadata.create_all(engine)
    tenant = uuid4()
    token = set_tenant_context(TenantContext(tenant))
    try:
        with Session(engine) as session:
            outbox = SqlAlchemyOutbox(session)
            event = DomainEvent(tenant, "sales.created", uuid4(), {"amount": 10})
            outbox.append(event)
            session.commit()
            pending = outbox.claim_unpublished()
            assert len(pending) == 1
            assert outbox.mark_published(event.id)
            session.commit()
            assert outbox.claim_unpublished() == []
    finally:
        reset_tenant_context(token)
