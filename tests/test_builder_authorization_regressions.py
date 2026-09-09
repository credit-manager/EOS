import pytest
from fastapi import HTTPException

from core.auth import require_builder_publish


@pytest.mark.asyncio
async def test_regular_dynamic_operator_cannot_publish_to_production():
    with pytest.raises(HTTPException) as exc:
        await require_builder_publish(
            {"roles": ["dynamic_operator"], "permissions": ["dynamic:update"]}
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user",
    [
        {"roles": ["dynamic_manager"], "permissions": []},
        {"roles": ["admin"], "permissions": []},
        {"roles": ["platform_owner"], "permissions": []},
        {"roles": ["user"], "permissions": ["builder:publish"]},
        {"roles": ["user"], "permissions": ["dynamic:publish"]},
    ],
)
async def test_authorized_builder_roles_can_publish(user):
    assert await require_builder_publish(user) is user
