"""Integration Connectors routes – connector test/push endpoints wired into the integration router.

These routes are mounted by main.py alongside the rest of the integration router.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from ..db import get_db
from ..tenant import require_tenant
from .connectors import get_connector
from .models import Integration

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations", "connectors"])

# ---------------------------------------------------------------------------
# Connector test / push endpoints
# ---------------------------------------------------------------------------

@router.post("/connectors/{integration_type}/{provider}/test")
def test_connector(
    integration_type: str,
    provider: str,
    payload: dict,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Test a connector's connection (dummy integration record)."""
    temp_integration = Integration(
        id="temp-test-" + str(int(__import__("time").time())),
        tenant_id=str(tenant_id),
        code=f"test_{integration_type}_{provider}",
        name=f"Test {provider}",
        integration_type=integration_type,
        provider=provider,
        config=payload,
        is_active=True,
    )
    connector = get_connector(temp_integration, db=db)
    if not connector:
        raise HTTPException(status_code=400, detail=f"No connector for {provider}")
    result = connector.test_connection()
    return {"connected": result.get("connected", False), "message": result.get("message", "")}

@router.post("/connectors/{integration_type}/{provider}/push")
def push_via_connector(
    integration_type: str,
    provider: str,
    payload: dict,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    """Push data through a connector (dummy integration record)."""
    temp_integration = Integration(
        id="temp-push-" + str(int(__import__("time").time())),
        tenant_id=str(tenant_id),
        code=f"test_{integration_type}_{provider}",
        name=f"Test {provider}",
        integration_type=integration_type,
        provider=provider,
        config=payload.get("config", {}),
        is_active=True,
    )
    connector = get_connector(temp_integration, db=db)
    if not connector:
        raise HTTPException(status_code=400, detail=f"No connector for {provider}")
    result = connector.push(payload.get("data", {}))
    return result
