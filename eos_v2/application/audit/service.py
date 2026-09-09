from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context


def record_event(
    session: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    actor_id: UUID | None = None,
    request_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Persist a minimal, tenant-scoped audit record in the current transaction."""
    context = get_tenant_context()
    session.execute(
        text(
            """INSERT INTO eos_v2_audit_events
               (id, tenant_id, actor_id, action, resource_type, resource_id, request_id, metadata)
               VALUES (:id, :tenant_id, :actor_id, :action, :resource_type, :resource_id, :request_id, CAST(:metadata AS JSONB))"""
        ),
        {
            "id": str(uuid4()),
            "tenant_id": str(context.tenant_id),
            "actor_id": str(actor_id or context.actor_id) if (actor_id or context.actor_id) else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "request_id": request_id,
            "metadata": json.dumps(metadata or {}, separators=(",", ":")),
        },
    )
