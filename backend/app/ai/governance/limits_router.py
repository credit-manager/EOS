"""
AI Limits Router - lightweight endpoints to check and manage execution limits.

Provides a quick health check for whether an agent is within its limits.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...tenant import require_tenant
from .models import AIAgentLimit, AIExecutionAudit


router = APIRouter(prefix="/api/v1/ai/limits", tags=["ai-limits"])


@router.get("/check/{agent_code}")
def check_agent_limits(
    agent_code: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Quick check: is the agent within its execution limits?

    Returns current usage vs limits for each active limit type.
    """
    from datetime import datetime, UTC

    now = datetime.now(UTC)
    limits = db.scalars(
        select(AIAgentLimit).where(
            AIAgentLimit.tenant_id == tenant_id,
            AIAgentLimit.agent_code == agent_code,
            AIAgentLimit.is_active.is_(True),
        )
    ).all()

    results = []
    for limit in limits:
        window_start = now.timestamp() - (limit.window_seconds or 3600)
        usage = db.scalar(
            select(AIExecutionAudit)
            .where(
                AIExecutionAudit.tenant_id == tenant_id,
                AIExecutionAudit.actor_id == agent_code,
                AIExecutionAudit.created_at > datetime.fromtimestamp(window_start),
            )
            .count()
        )
        remaining = max(0, limit.max_value - (usage or 0))
        results.append(
            {
                "limit_type": limit.limit_type,
                "max_value": limit.max_value,
                "window_seconds": limit.window_seconds,
                "current_usage": usage or 0,
                "remaining": remaining,
                "allowed": remaining > 0,
            }
        )
    return {"agent_code": agent_code, "limits": results}
