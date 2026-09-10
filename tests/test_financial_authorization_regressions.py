from unittest.mock import patch

import pytest
from fastapi import HTTPException

from core.auth import require_financial_settlement


@pytest.mark.asyncio
async def test_regular_tenant_user_cannot_settle_payment():
    with pytest.raises(HTTPException) as exc:
        await require_financial_settlement(
            {
                "roles": ["user"],
                "permissions": ["payments:create"],
            }
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user",
    [
        {"roles": ["admin"], "permissions": []},
        {"roles": ["finance_manager"], "permissions": []},
        {"roles": ["billing_manager"], "permissions": []},
        {"roles": ["user"], "permissions": ["payments:settle"]},
        {"roles": ["user"], "permissions": ["payments:refund"]},
    ],
)
async def test_financial_roles_can_settle_payment(user):
    assert await require_financial_settlement(user) is user
